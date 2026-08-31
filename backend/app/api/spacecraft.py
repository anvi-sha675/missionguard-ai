from fastapi import APIRouter
from app.services import store, pipeline
from app.ml.features import telemetry_to_frame

router = APIRouter(prefix="/spacecraft", tags=["spacecraft"])


@router.get("")
def list_spacecraft():
    """Command Center roster. Health/status are refreshed from whatever
    telemetry/anomalies already exist for each spacecraft's mission, so the
    Command Center reflects real computed state, not a hardcoded card."""
    craft = store.list_spacecraft()
    out = []
    for sc in craft:
        mission_id = sc["mission_id"]
        points = store.get_telemetry(mission_id)
        if points:
            df = telemetry_to_frame(points)
            anomalies = store.get_anomalies(mission_id)
            forecast = pipeline.forecast_for_anomaly(df, anomalies[-1]) if anomalies else None
            risk = pipeline.risk_for_run(df, anomalies, forecast)
            health = pipeline.mission_health_score(anomalies, risk.risk_score)
            status = "CRITICAL" if risk.risk_level == "CRITICAL" else "WARNING" if risk.risk_level in ("HIGH", "MEDIUM") else "HEALTHY"
            store.upsert_spacecraft(sc["spacecraft_id"], status=status, health=health)
            out.append({**sc, "status": status, "health": health})
        else:
            out.append(sc)
    return out
