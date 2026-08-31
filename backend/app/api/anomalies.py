from fastapi import APIRouter, HTTPException

from app.services import store, pipeline
from app.services.evidence import build_evidence
from app.ml.features import telemetry_to_frame
from app.api.deps import provider

router = APIRouter(tags=["anomalies"])


@router.get("/anomalies")
def list_anomalies(mission_id: str):
    return store.get_anomalies(mission_id)


def _detail(mission_id: str, anomaly_id: str):
    a = store.get_anomaly(mission_id, anomaly_id)
    if not a:
        raise HTTPException(404, "Anomaly not found")
    df = telemetry_to_frame(store.get_telemetry(mission_id))
    forecast = pipeline.forecast_for_anomaly(df, a)
    risk = pipeline.risk_for_run(df, store.get_anomalies(mission_id), forecast)
    evidence = build_evidence(df, a, forecast, risk)
    explanation = provider.explain_anomaly(evidence)
    return {"anomaly": a, "forecast": forecast, "risk": risk, "explanation": explanation}


@router.get("/anomalies/{mission_id}/{anomaly_id}")
def get_anomaly_detail(mission_id: str, anomaly_id: str):
    return _detail(mission_id, anomaly_id)


@router.post("/anomalies/{mission_id}/{anomaly_id}/status")
def set_status(mission_id: str, anomaly_id: str, status: str):
    ok = store.update_anomaly_status(mission_id, anomaly_id, status)
    if not ok:
        raise HTTPException(404, "Anomaly not found")
    return {"ok": True}


@router.get("/predictions/{mission_id}")
def get_predictions(mission_id: str, parameter: str = "battery_voltage"):
    df = telemetry_to_frame(store.get_telemetry(mission_id))
    if df.empty:
        raise HTTPException(404, "No telemetry for mission")
    from app.ml.forecasting import forecast_parameter
    return forecast_parameter(df, parameter)


@router.post("/ai/explain")
def ai_explain(mission_id: str, anomaly_id: str):
    return _detail(mission_id, anomaly_id)["explanation"]


@router.get("/recommendations")
def list_recommendations(mission_id: str):
    return store.get_recommendations(mission_id)
