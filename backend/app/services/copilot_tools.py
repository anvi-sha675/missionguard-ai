from __future__ import annotations
from typing import Optional

from app.services import store, pipeline
from app.services.evidence import build_evidence
from app.ml.features import telemetry_to_frame
from app.services.mission_planner import evaluate_mission_plan as _evaluate_plan


def get_spacecraft_status(mission_id: str) -> dict:
    points = store.get_telemetry(mission_id)
    anomalies = store.get_anomalies(mission_id)
    if not points:
        return {"available": False, "note": "No telemetry recorded for this mission yet."}
    df = telemetry_to_frame(points)
    forecast = pipeline.forecast_for_anomaly(df, anomalies[-1]) if anomalies else None
    risk = pipeline.risk_for_run(df, anomalies, forecast)
    health = pipeline.mission_health_score(anomalies, risk.risk_score)
    return {
        "available": True,
        "mission_health": health,
        "risk_level": risk.risk_level,
        "risk_score": risk.risk_score,
        "active_anomalies": len(anomalies),
        "subsystem_breakdown": risk.subsystem_breakdown,
    }


def get_recent_anomalies(mission_id: str, limit: int = 5) -> list[dict]:
    anomalies = store.get_anomalies(mission_id)[-limit:]
    return [
        {
            "id": a.id, "subsystem": a.subsystem, "parameter": a.parameter,
            "severity_band": a.severity_band, "anomaly_score": a.anomaly_score,
            "timestamp": a.timestamp.isoformat(), "status": a.status,
        }
        for a in anomalies
    ]


def get_forecast(mission_id: str, parameter: str = "battery_voltage") -> Optional[dict]:
    points = store.get_telemetry(mission_id)
    if not points:
        return None
    df = telemetry_to_frame(points)
    from app.ml.forecasting import forecast_parameter
    fc = forecast_parameter(df, parameter)
    return fc.model_dump()


def get_risk_assessment(mission_id: str) -> Optional[dict]:
    points = store.get_telemetry(mission_id)
    if not points:
        return None
    df = telemetry_to_frame(points)
    anomalies = store.get_anomalies(mission_id)
    forecast = pipeline.forecast_for_anomaly(df, anomalies[-1]) if anomalies else None
    risk = pipeline.risk_for_run(df, anomalies, forecast)
    return risk.model_dump()


def get_mission_plan(mission_id: str) -> Optional[dict]:
    plans = store.get_mission_plans(mission_id)
    return plans[-1].model_dump() if plans else None


def evaluate_mission_plan(mission_id: str, plan_request) -> Optional[dict]:
    points = store.get_telemetry(mission_id)
    if not points:
        return None
    df = telemetry_to_frame(points)
    evaluation = _evaluate_plan(df, plan_request)
    return evaluation.model_dump()


def get_conjunctions(mission_id: str) -> list[dict]:
    return [c.model_dump() for c in store.get_conjunctions(mission_id)]


def get_recommendations(mission_id: str) -> list[dict]:
    return [r.model_dump() for r in store.get_recommendations(mission_id)]


def get_evidence_for_worst_anomaly(mission_id: str):
    """Returns a full EvidencePackage object (not dict) for the most severe
    active anomaly -- used when the copilot needs to ground a free-form
    explanation rather than return structured tool data directly."""
    points = store.get_telemetry(mission_id)
    anomalies = store.get_anomalies(mission_id)
    if not points or not anomalies:
        return None
    df = telemetry_to_frame(points)
    worst = sorted(anomalies, key=lambda a: a.anomaly_score, reverse=True)[0]
    forecast = pipeline.forecast_for_anomaly(df, worst)
    risk = pipeline.risk_for_run(df, anomalies, forecast)
    return build_evidence(df, worst, forecast, risk)
