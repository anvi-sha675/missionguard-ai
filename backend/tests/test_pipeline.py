import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.schemas.models import ScenarioRequest, MissionPlanRequest
from app.services.simulator import generate_scenario
from app.ml.features import telemetry_to_frame
from app.ml.forecasting import forecast_parameter
from app.services.risk import compute_risk
from app.services.mission_planner import evaluate_mission_plan
from app.services import ssa
from app.ml.anomaly import score_band, get_detector, raw_to_scores
import numpy as np


def _quiet_df():
    req = ScenarioRequest(mission_id="T", spacecraft_id="T-1", scenario="normal",
                           duration_minutes=60, severity=5, interval_seconds=30, seed=1)
    return telemetry_to_frame(generate_scenario(req))


def _degraded_df():
    req = ScenarioRequest(mission_id="T", spacecraft_id="T-1", scenario="battery_degradation",
                           duration_minutes=90, severity=80, interval_seconds=30, seed=1)
    return telemetry_to_frame(generate_scenario(req))


# --------------------------------------------------------------- score_band
def test_score_band_boundaries():
    assert score_band(0) == "NORMAL"
    assert score_band(30.9) == "NORMAL"
    assert score_band(31) == "LOW"
    assert score_band(60.9) == "LOW"
    assert score_band(61) == "WARNING"
    assert score_band(80.9) == "WARNING"
    assert score_band(81) == "CRITICAL"
    assert score_band(100) == "CRITICAL"
    # regression check for the float-gap bug found during manual testing
    assert score_band(30.5) == "NORMAL"


# --------------------------------------------------------------- forecasting
def test_forecast_insufficient_data_is_honest():
    df = _quiet_df().head(3)  # below MIN_POINTS
    fc = forecast_parameter(df, "battery_voltage")
    assert fc.sufficient_data is False
    assert "insufficient" in fc.note.lower()


def test_forecast_detects_declining_trend():
    df = _degraded_df()
    fc = forecast_parameter(df, "battery_voltage")
    assert fc.sufficient_data is True
    assert fc.trend_per_hour < 0  # voltage should be trending down


def test_forecast_normal_scenario_flat_trend():
    df = _quiet_df()
    fc = forecast_parameter(df, "temperature")
    assert fc.sufficient_data is True
    assert abs(fc.trend_per_hour) < 2.0  # should stay close to flat


# --------------------------------------------------------------- risk engine
def test_risk_zero_anomalies_is_low():
    risk = compute_risk("T", "T-1", {"power": 5.0}, None)
    assert risk.risk_level == "LOW"
    assert risk.risk_score < 20


def test_risk_scales_with_anomaly_severity():
    low = compute_risk("T", "T-1", {"power": 20.0}, None)
    high = compute_risk("T", "T-1", {"power": 90.0}, None)
    assert high.risk_score > low.risk_score


def test_risk_criticality_weighting():
    # power (criticality 1.0) should contribute more risk than a lower
    # criticality subsystem at the same anomaly score
    power_risk = compute_risk("T", "T-1", {"power": 70.0}, None)
    compute_risk_comm = compute_risk("T", "T-1", {"communication": 70.0}, None)
    assert power_risk.risk_score >= compute_risk_comm.risk_score


# --------------------------------------------------------------- mission planner
def test_mission_planner_flags_unsafe_power():
    df = _quiet_df()
    req = MissionPlanRequest(
        mission_id="T", spacecraft_id="T-1", objective="Test high-power activity",
        required_power_w=500,  # deliberately huge, should blow the prototype bus budget
    )
    evaluation = evaluate_mission_plan(df, req)
    power_check = next(c for c in evaluation.checks if c.constraint == "Power")
    assert power_check.status == "UNSAFE"
    assert evaluation.overall in ("UNSAFE", "CONDITIONAL")


def test_mission_planner_safe_when_margins_healthy():
    df = _quiet_df()
    req = MissionPlanRequest(
        mission_id="T", spacecraft_id="T-1", objective="Low-power check-in",
        required_power_w=5, requires_communication=False, requires_attitude_maneuver=False,
    )
    evaluation = evaluate_mission_plan(df, req)
    assert evaluation.overall == "SAFE"


# --------------------------------------------------------------- SSA
def test_conjunction_screening_is_deterministic_for_seed():
    a = ssa.generate_conjunctions("T", "T-1", seed=99)
    b = ssa.generate_conjunctions("T", "T-1", seed=99)
    assert [e.object_id for e in a] == [e.object_id for e in b]
    assert [e.closest_approach_km for e in a] == [e.closest_approach_km for e in b]


def test_conjunction_events_labeled_simulated():
    events = ssa.generate_conjunctions("T", "T-1", seed=5)
    assert all(e.data_source == "SIMULATED" for e in events)


def test_conjunction_risk_classification_monotonic():
    close_risk = ssa._risk_level(2.0, 12.0)
    far_risk = ssa._risk_level(80.0, 3.0)
    assert close_risk == "HIGH"
    assert far_risk == "LOW"


# --------------------------------------------------------------- detectors
def test_all_registered_detectors_run_without_error():
    df = _degraded_df()
    from app.ml.features import model_feature_matrix
    X = model_feature_matrix(df)
    baseline_n = int(len(df) * 0.35)
    for name in ("isolation_forest", "one_class_svm", "autoencoder"):
        detector = get_detector(name)
        detector.fit(X.iloc[:baseline_n])
        raw = detector.decision_scores(X)
        scores = raw_to_scores(np.asarray(raw), baseline_n)
        assert len(scores) == len(df)
        assert scores.max() <= 100 and scores.min() >= 0
