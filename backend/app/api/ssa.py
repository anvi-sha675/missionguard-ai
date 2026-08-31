from fastapi import APIRouter, HTTPException

from app.services import store, ssa
from app.api.deps import provider

router = APIRouter(tags=["space-situational-awareness"])


@router.get("/space-objects/summary")
def summary():
    """SIMULATED catalog summary figures -- see app/services/ssa.py docstring."""
    return {
        "tracked_objects": ssa.generate_tracked_object_count(),
        "data_source": "SIMULATED",
    }


@router.post("/conjunctions/screen")
def screen(mission_id: str, spacecraft_id: str, seed: int = 7):
    events = ssa.generate_conjunctions(mission_id, spacecraft_id, seed=seed)
    store.save_conjunctions(mission_id, events)
    return events


@router.get("/conjunctions")
def list_conjunctions(mission_id: str):
    return store.get_conjunctions(mission_id)


@router.get("/conjunctions/{mission_id}/{conjunction_id}/explain")
def explain_conjunction(mission_id: str, conjunction_id: str):
    events = store.get_conjunctions(mission_id)
    event = next((e for e in events if e.id == conjunction_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Conjunction event not found")
    return {"explanation": provider.explain_conjunction(event)}
