from __future__ import annotations
import uuid
import numpy as np

from app.schemas.models import ConjunctionEvent

OBJECT_CLASSES = ["DEBRIS", "DEBRIS", "DEBRIS", "ROCKET_BODY", "ACTIVE_SATELLITE"]

NAME_PREFIXES = {
    "DEBRIS": "DEB",
    "ROCKET_BODY": "R/B",
    "ACTIVE_SATELLITE": "SAT",
    "UNKNOWN": "OBJ",
}


def _risk_level(closest_approach_km: float, relative_velocity_km_s: float) -> str:

    if closest_approach_km < 5 or (closest_approach_km < 15 and relative_velocity_km_s > 10):
        return "HIGH"
    if closest_approach_km < 25:
        return "MEDIUM"
    return "LOW"


def generate_tracked_object_count(seed: int = 42) -> int:

    rng = np.random.default_rng(seed)
    return int(rng.integers(11000, 13500))


def generate_conjunctions(
    mission_id: str, spacecraft_id: str, n_objects: int = 6, seed: int = 7
) -> list[ConjunctionEvent]:
    rng = np.random.default_rng(seed)
    events: list[ConjunctionEvent] = []

    for i in range(n_objects):
        obj_class = rng.choice(OBJECT_CLASSES)
        object_id = f"{NAME_PREFIXES[obj_class]}-{rng.integers(1000, 9999)}"

        closest_approach_km = float(rng.exponential(scale=18) + 0.5)
        time_to_ca_hours = float(rng.uniform(0.3, 30))
        relative_velocity = float(rng.uniform(3, 14))

        risk = _risk_level(closest_approach_km, relative_velocity)

        events.append(ConjunctionEvent(
            id=str(uuid.uuid4())[:8],
            mission_id=mission_id,
            spacecraft_id=spacecraft_id,
            object_id=object_id,
            object_name=f"{object_id} ({obj_class.replace('_', ' ').title()})",
            closest_approach_km=round(closest_approach_km, 2),
            time_to_closest_approach_hours=round(time_to_ca_hours, 2),
            relative_velocity_km_s=round(relative_velocity, 2),
            risk_level=risk,
        ))

    events.sort(key=lambda e: e.time_to_closest_approach_hours)
    return events
