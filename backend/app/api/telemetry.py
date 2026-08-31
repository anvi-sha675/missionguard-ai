from fastapi import APIRouter, Query

from app.schemas.models import ScenarioRequest
from app.services import store, pipeline
from app.services.evidence import build_evidence
from app.ml.features import telemetry_to_frame
from app.api.deps import provider

router = APIRouter(tags=["telemetry"])


@router.post("/telemetry/simulate")
def simulate_telemetry(req: ScenarioRequest, detector: str = Query("isolation_forest", description="isolation_forest | one_class_svm | autoencoder")):
    from app.services.simulator import generate_scenario
    points = generate_scenario(req)
    store.save_telemetry(req.mission_id, points)

    df, anomalies = pipeline.analyze_run(points, detector_name=detector)
    store.save_anomalies(req.mission_id, anomalies)

    forecast = None
    if anomalies:
        forecast = pipeline.forecast_for_anomaly(df, anomalies[-1])
    risk = pipeline.risk_for_run(df, anomalies, forecast)
    health = pipeline.mission_health_score(anomalies, risk.risk_score)

    for a in anomalies:
        evidence = build_evidence(df, a, forecast, risk)
        cards = provider.generate_recommendations(evidence)
        store.save_recommendations(req.mission_id, cards)

    status = "CRITICAL" if risk.risk_level == "CRITICAL" else "WARNING" if risk.risk_level in ("HIGH", "MEDIUM") else "HEALTHY"
    store.upsert_spacecraft(req.spacecraft_id, mission_id=req.mission_id, status=status, health=health)

    return {
        "mission_id": req.mission_id,
        "detector": detector,
        "points_generated": len(points),
        "anomalies_detected": len(anomalies),
        "mission_health": health,
        "risk": risk,
    }


@router.get("/telemetry/{mission_id}")
def get_telemetry(mission_id: str, limit: int = 500):
    points = store.get_telemetry(mission_id)
    return points[-limit:]


@router.get("/missions/{mission_id}/status")
def mission_status(mission_id: str):
    """Current health/risk snapshot derived from whatever telemetry/anomalies
    already exist -- lets any page (not just the page that ran the scenario)
    rehydrate correct state on load."""
    points = store.get_telemetry(mission_id)
    anomalies = store.get_anomalies(mission_id)
    if not points:
        return {"mission_health": 100.0, "risk": None, "anomalies_detected": 0, "points_generated": 0}
    df = telemetry_to_frame(points)
    forecast = pipeline.forecast_for_anomaly(df, anomalies[-1]) if anomalies else None
    risk = pipeline.risk_for_run(df, anomalies, forecast)
    health = pipeline.mission_health_score(anomalies, risk.risk_score)
    return {
        "mission_health": health,
        "risk": risk,
        "anomalies_detected": len(anomalies),
        "points_generated": len(points),
    }
