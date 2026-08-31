from __future__ import annotations
from datetime import datetime, timezone
from typing import List
import numpy as np

from app.schemas.models import ScenarioRequest, DetectorMetrics, EvaluationReport
from app.services.simulator import generate_scenario
from app.ml.features import telemetry_to_frame, model_feature_matrix
from app.ml.anomaly import get_detector, raw_to_scores, score_band, DETECTOR_REGISTRY
from app.ml.forecasting import forecast_parameter


def _ground_truth_labels(n: int, scenario: str, onset_fraction: float = 0.45) -> np.ndarray:
    """True label = 1 from the point the injected anomaly's ramp becomes
    detectable onward. 'normal' scenario has no true anomalies at all."""
    if scenario == "normal":
        return np.zeros(n, dtype=int)
    onset = int(n * onset_fraction)
    y = np.zeros(n, dtype=int)
    y[onset:] = 1
    return y


def evaluate_detectors(
    scenario: str = "battery_degradation",
    severity: int = 70,
    duration_minutes: int = 90,
    interval_seconds: int = 30,
    eval_seed: int = 20260829,  # deliberately different from demo-run seeds
) -> EvaluationReport:
    req = ScenarioRequest(
        mission_id="EVAL", spacecraft_id="EVAL-SC", scenario=scenario,
        duration_minutes=duration_minutes, severity=severity,
        interval_seconds=interval_seconds, seed=eval_seed,
    )
    points = generate_scenario(req)
    df = telemetry_to_frame(points)
    n = len(df)
    baseline_n = max(5, int(n * 0.35))
    X = model_feature_matrix(df)
    y_true = _ground_truth_labels(n, scenario)

    results: List[DetectorMetrics] = []
    for name in DETECTOR_REGISTRY:
        detector = get_detector(name)
        detector.fit(X.iloc[:baseline_n])
        raw = detector.decision_scores(X)
        scores = raw_to_scores(np.asarray(raw), baseline_n)
        y_pred = np.array([1 if score_band(s) in ("WARNING", "CRITICAL") else 0 for s in scores])

        tp = int(np.sum((y_pred == 1) & (y_true == 1)))
        fp = int(np.sum((y_pred == 1) & (y_true == 0)))
        fn = int(np.sum((y_pred == 0) & (y_true == 1)))
        tn = int(np.sum((y_pred == 0) & (y_true == 0)))

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        fpr = fp / (fp + tn) if (fp + tn) else 0.0

        # detection latency: how many points after true onset before the
        # detector first flags an anomaly (None if it never does)
        latency = None
        true_onset_idx = np.argmax(y_true) if y_true.any() else None
        if true_onset_idx is not None:
            flagged_after = np.where(y_pred[true_onset_idx:] == 1)[0]
            latency = float(flagged_after[0]) if len(flagged_after) else None

        results.append(DetectorMetrics(
            detector=name,
            precision=round(precision, 3),
            recall=round(recall, 3),
            f1_score=round(f1, 3),
            false_positive_rate=round(fpr, 3),
            detection_latency_points=latency,
            n_eval_points=n,
            n_true_anomalies=int(y_true.sum()),
        ))

    return EvaluationReport(
        scenario=scenario,
        generated_at=datetime.now(timezone.utc),
        results=results,
        note=(
            "Computed on a freshly generated, separately-seeded evaluation run of the "
            "named scenario. Ground truth is derived from the simulator's own injection "
            "point, not hand-labeled real telemetry -- this measures relative detector "
            "behavior on simulated data, not certified real-world accuracy."
        ),
    )


def evaluate_forecast(
    scenario: str = "battery_degradation",
    parameter: str = "battery_voltage",
    severity: int = 70,
    duration_minutes: int = 90,
    interval_seconds: int = 30,
    eval_seed: int = 20260830,
    holdout_fraction: float = 0.2,
) -> dict:
    """MAE/RMSE for the forecasting module (spec section 26). Generates a
    fresh run, fits the forecast on the first (1 - holdout_fraction) of the
    points, then compares the linear projection against the actually-
    generated held-out points -- a real accuracy measurement, not a
    fabricated figure."""
    req = ScenarioRequest(
        mission_id="EVAL-FORECAST", spacecraft_id="EVAL-SC", scenario=scenario,
        duration_minutes=duration_minutes, severity=severity,
        interval_seconds=interval_seconds, seed=eval_seed,
    )
    points = generate_scenario(req)
    df = telemetry_to_frame(points)
    n = len(df)
    split = int(n * (1 - holdout_fraction))
    if split < 6 or n - split < 2:
        return {"sufficient_data": False, "note": "Run too short for a meaningful holdout evaluation."}

    train_df = df.iloc[:split].reset_index(drop=True)
    holdout_df = df.iloc[split:].reset_index(drop=True)

    fc = forecast_parameter(train_df, parameter)
    if not fc.sufficient_data:
        return {"sufficient_data": False, "note": fc.note}

    t0 = train_df["timestamp"].iloc[0]
    hold_hours = (holdout_df["timestamp"] - t0).dt.total_seconds() / 3600.0
    predicted = fc.trend_per_hour * hold_hours + (fc.current_value - fc.trend_per_hour * (
        (train_df["timestamp"].iloc[-1] - t0).total_seconds() / 3600.0
    ))
    actual = holdout_df[parameter].values

    errors = predicted.values - actual
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    return {
        "sufficient_data": True,
        "scenario": scenario,
        "parameter": parameter,
        "n_train_points": split,
        "n_holdout_points": n - split,
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "note": (
            "Computed by holding out the final "
            f"{holdout_fraction*100:.0f}% of a freshly generated run and comparing the "
            "linear trend fit on the remaining points against the actual generated values. "
            "This measures forecast accuracy on simulated data with a known linear injection "
            "pattern, not real spacecraft behavior."
        ),
    }
