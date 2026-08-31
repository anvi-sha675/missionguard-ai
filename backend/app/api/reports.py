import uuid
import datetime
from fastapi import APIRouter, HTTPException

from app.schemas.models import MissionReport
from app.services import store, pipeline
from app.services.evidence import build_evidence
from app.ml.features import telemetry_to_frame
from app.api.deps import provider

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate")
def generate_report(mission_id: str):
    df = telemetry_to_frame(store.get_telemetry(mission_id))
    if df.empty:
        raise HTTPException(404, "No telemetry for mission")
    anomalies = store.get_anomalies(mission_id)
    forecast = pipeline.forecast_for_anomaly(df, anomalies[-1]) if anomalies else None
    risk = pipeline.risk_for_run(df, anomalies, forecast)
    health = pipeline.mission_health_score(anomalies, risk.risk_score)

    explanations = []
    actions = set()
    for a in anomalies:
        ev = build_evidence(df, a, forecast, risk)
        exp = provider.explain_anomaly(ev)
        explanations.append(exp.likely_explanation)
        actions.update(exp.recommended_actions)

    subsystem_status = {}
    for sub, vals in risk.subsystem_breakdown.items():
        band = "CRITICAL" if vals["subsystem_risk"] >= 80 else "HIGH" if vals["subsystem_risk"] >= 60 else "MODERATE" if vals["subsystem_risk"] >= 30 else "NOMINAL"
        subsystem_status[sub] = band

    context = {"mission_health": health, "active_anomalies": anomalies, "risk_level": risk.risk_level}
    summary = provider.summarize_report(context)

    conjunctions = store.get_conjunctions(mission_id)
    if conjunctions:
        high = [c for c in conjunctions if c.risk_level == "HIGH"]
        summary += (
            f" Space Situational Awareness: {len(conjunctions)} tracked conjunction(s) screened"
            f"{f', {len(high)} at HIGH risk' if high else ''} (SIMULATED data)."
        )

    report = MissionReport(
        id=str(uuid.uuid4())[:8],
        mission_id=mission_id,
        generated_at=datetime.datetime.now(datetime.timezone.utc),
        executive_summary=summary,
        mission_health=health,
        active_anomalies=anomalies,
        subsystem_status=subsystem_status,
        risk_assessment=risk,
        forecasts=[forecast] if forecast else [],
        ai_explanations=explanations,
        recommended_actions=list(actions),
        limitations=(
            "This report is generated from simulated telemetry in a hackathon prototype "
            "environment. Anomaly scores and forecasts are prototype estimates, not certified "
            "mission analysis. Any conjunction data referenced is simulated, not a real tracked-"
            "object catalog. The system is a decision-support tool and does not autonomously "
            "control spacecraft."
        ),
    )
    store.save_report(mission_id, report)
    return report


@router.get("/{mission_id}")
def list_reports(mission_id: str):
    return store.get_reports(mission_id)
