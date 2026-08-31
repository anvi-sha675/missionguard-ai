from fastapi import APIRouter

from app.schemas.models import CopilotRequest, CopilotMessage
from app.services import store, copilot_tools
from app.api.deps import provider

router = APIRouter(prefix="/copilot", tags=["copilot"])


def _route_question(mission_id: str, question: str, context_anomaly_id: str | None) -> tuple[str, dict | None]:
    q = question.lower()

    if "conjunction" in q or "debris" in q or "collision" in q:
        events = store.get_conjunctions(mission_id)
        if not events:
            return ("No conjunction screening has been run for this mission yet. Open Space Situational "
                    "Awareness to run a screening.", None)
        worst = sorted(events, key=lambda e: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[e.risk_level])[0]
        return (provider.explain_conjunction(worst), None)

    if "maneuver" in q or "mission plan" in q or "feasib" in q or "can we perform" in q:
        plan = copilot_tools.get_mission_plan(mission_id)
        if not plan:
            return ("No mission plan has been evaluated for this mission yet. Open Mission Planner to "
                    "evaluate a proposed activity.", None)
        return (f"Most recent plan evaluation — '{plan['objective']}': {plan['overall']}. {plan['recommendation']}", None)

    # default: fall through to evidence-grounded anomaly Q&A (existing behavior)
    evidence = None
    anomalies = store.get_anomalies(mission_id)
    from app.services.pipeline import forecast_for_anomaly, risk_for_run
    from app.services.evidence import build_evidence
    from app.ml.features import telemetry_to_frame

    points = store.get_telemetry(mission_id)
    if points:
        df = telemetry_to_frame(points)
        target = None
        if context_anomaly_id:
            target = store.get_anomaly(mission_id, context_anomaly_id)
        elif anomalies:
            target = sorted(anomalies, key=lambda a: a.anomaly_score, reverse=True)[0]
        if target:
            forecast = forecast_for_anomaly(df, target)
            risk = risk_for_run(df, anomalies, forecast)
            evidence = build_evidence(df, target, forecast, risk)

    mission_summary = f"{len(anomalies)} active anomaly(ies) tracked for {mission_id}."
    answer = provider.answer_copilot(evidence, question, mission_summary)
    return (answer, {"anomaly_id": evidence.anomaly.id} if evidence else None)


@router.post("/chat")
def copilot_chat(req: CopilotRequest):
    answer, meta = _route_question(req.mission_id, req.question, req.context_anomaly_id)

    store.append_copilot(req.mission_id, CopilotMessage(role="user", content=req.question, context_anomaly_id=req.context_anomaly_id))
    store.append_copilot(req.mission_id, CopilotMessage(role="assistant", content=answer, context_anomaly_id=req.context_anomaly_id))

    return {"answer": answer, "context_anomaly_id": (meta or {}).get("anomaly_id")}


@router.get("/history")
def copilot_history(mission_id: str):
    return store.get_copilot_history(mission_id)
