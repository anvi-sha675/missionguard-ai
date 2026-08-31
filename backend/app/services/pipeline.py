from __future__ import annotations
import uuid
from typing import List, Tuple
import pandas as pd

from app.schemas.models import Anomaly, AnomalyContributor, TelemetryPoint
from app.ml.features import telemetry_to_frame, RAW_PARAMS
from app.ml.anomaly import run_anomaly_detection
from app.ml.forecasting import forecast_parameter, WARNING_THRESHOLDS
from app.services.risk import compute_risk


def analyze_run(points: List[TelemetryPoint], detector_name: str = "isolation_forest") -> Tuple[pd.DataFrame, List[Anomaly]]:

    df = telemetry_to_frame(points)
    results = run_anomaly_detection(df, detector_name=detector_name)

    cooldown_points = max(3, len(results) // 15)
    anomalies: List[Anomaly] = []
    in_incident = False
    last_incident_end = -cooldown_points
    current: Anomaly | None = None

    for r in results:
        row = df.iloc[r.index]
        if r.severity_band in ("WARNING", "CRITICAL"):
            if in_incident and current is not None:
                if r.anomaly_score > current.anomaly_score:
                    current.anomaly_score = r.anomaly_score
                    current.severity_band = r.severity_band
                continue
            if r.index - last_incident_end < cooldown_points:
                in_incident = True
                continue
            in_incident = True
            top = r.contributors[0]["parameter"] if r.contributors else RAW_PARAMS[0]
            observations = _observations_for(df, r.index, top)
            current = Anomaly(
                id=str(uuid.uuid4())[:8],
                mission_id=row["mission_id"],
                spacecraft_id=row["spacecraft_id"],
                subsystem=row["subsystem"],
                parameter=top,
                timestamp=row["timestamp"],
                anomaly_score=r.anomaly_score,
                severity_band=r.severity_band,
                confidence=r.confidence,
                observations=observations,
                contributors=[AnomalyContributor(parameter=c["parameter"], contribution=c["contribution"]) for c in r.contributors],
            )
            anomalies.append(current)
        else:
            if in_incident:
                last_incident_end = r.index
            in_incident = False

    return df, anomalies


def _observations_for(df: pd.DataFrame, idx: int, parameter: str) -> List[str]:
    window = max(0, idx - 30)  # ~15 min lookback at a 30s cadence, for a representative delta
    if parameter not in df.columns or idx - window < 2:
        return [f"{parameter.replace('_', ' ')} deviated from baseline near this timestamp."]
    start_val = df[parameter].iloc[window]
    end_val = df[parameter].iloc[idx]
    minutes = (df["timestamp"].iloc[idx] - df["timestamp"].iloc[window]).total_seconds() / 60
    if start_val == 0:
        pct = 0
    else:
        pct = (end_val - start_val) / abs(start_val) * 100
    direction = "decreased" if end_val < start_val else "increased"
    obs = [f"{parameter.replace('_', ' ').capitalize()} {direction} {abs(pct):.1f}% over {minutes:.0f} minutes"]

    power = df["power_consumption"]
    if parameter != "power_consumption" and idx - window >= 1:
        p_change = (power.iloc[idx] - power.iloc[window]) / max(abs(power.iloc[window]), 1e-6) * 100
        if abs(p_change) > 3:
            obs.append(f"Power consumption {'increased' if p_change > 0 else 'decreased'} {abs(p_change):.1f}%")
    return obs


def forecast_for_anomaly(df: pd.DataFrame, anomaly: Anomaly):
    if anomaly.parameter in WARNING_THRESHOLDS:
        return forecast_parameter(df, anomaly.parameter)
    return forecast_parameter(df, anomaly.parameter)


def risk_for_run(df: pd.DataFrame, anomalies: List[Anomaly], forecast=None):
    subsystem_scores = {}
    for a in anomalies:
        subsystem_scores[a.subsystem] = max(subsystem_scores.get(a.subsystem, 0), a.anomaly_score)
    if not subsystem_scores:
        subsystem_scores = {df["subsystem"].iloc[-1]: 5.0}
    mission_id = df["mission_id"].iloc[-1]
    spacecraft_id = df["spacecraft_id"].iloc[-1]
    return compute_risk(mission_id, spacecraft_id, subsystem_scores, forecast)


def mission_health_score(anomalies: List[Anomaly], risk_score: float) -> float:

    if not anomalies:
        worst_penalty = 0
    else:
        worst_band = max(anomalies, key=lambda a: a.anomaly_score).severity_band
        worst_penalty = {"NORMAL": 0, "LOW": 8, "WARNING": 25, "CRITICAL": 45}.get(worst_band, 0)
    extra_incidents_penalty = min(15, max(0, len(anomalies) - 1) * 3)
    health = 100 - worst_penalty - extra_incidents_penalty - risk_score * 0.3
    return round(max(0.0, min(100.0, health)), 1)
