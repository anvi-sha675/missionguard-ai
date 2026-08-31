from fastapi import APIRouter, HTTPException

from app.schemas.models import MissionPlanRequest
from app.services import store
from app.services.mission_planner import evaluate_mission_plan
from app.ml.features import telemetry_to_frame
from app.api.deps import provider

router = APIRouter(prefix="/mission-planner", tags=["mission-planner"])


@router.post("/evaluate")
def evaluate(req: MissionPlanRequest):
    points = store.get_telemetry(req.mission_id)
    if not points:
        raise HTTPException(404, "No telemetry for this mission yet -- generate a scenario first.")
    df = telemetry_to_frame(points)
    evaluation = evaluate_mission_plan(df, req)
    store.save_mission_plan(req.mission_id, evaluation)
    narrative = provider.explain_mission_plan(evaluation)
    return {"evaluation": evaluation, "narrative": narrative}


@router.get("/{mission_id}")
def history(mission_id: str):
    return store.get_mission_plans(mission_id)
