from __future__ import annotations
from typing import Dict, List
import threading

_lock = threading.Lock()

telemetry: Dict[str, list] = {}          # mission_id -> [TelemetryPoint]
anomalies: Dict[str, list] = {}          # mission_id -> [Anomaly]
recommendations: Dict[str, list] = {}    # mission_id -> [RecommendationCard]
reports: Dict[str, list] = {}            # mission_id -> [MissionReport]
audit_log: List[dict] = []
copilot_history: Dict[str, list] = {}    # mission_id -> [CopilotMessage]
spacecraft_registry: Dict[str, dict] = {}  # spacecraft_id -> Spacecraft-shaped dict
mission_plans: Dict[str, list] = {}      # mission_id -> [MissionPlanEvaluation]
conjunctions: Dict[str, list] = {}       # mission_id -> [ConjunctionEvent]

spacecraft_registry.update({
    "SC-001": {"spacecraft_id": "SC-001", "mission_id": "MISSION-001", "name": "Aurora-1", "status": "STANDBY", "health": 100.0},
    "SC-002": {"spacecraft_id": "SC-002", "mission_id": "MISSION-002", "name": "Meridian-2", "status": "STANDBY", "health": 100.0},
    "SC-003": {"spacecraft_id": "SC-003", "mission_id": "MISSION-003", "name": "Horizon-3", "status": "STANDBY", "health": 100.0},
})


def log_audit(event: str, **fields):
    import datetime
    with _lock:
        audit_log.append({"event": event, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), **fields})


def save_telemetry(mission_id: str, points: list):
    with _lock:
        telemetry.setdefault(mission_id, [])
        telemetry[mission_id] = points  # latest scenario run replaces prior demo run
    log_audit("telemetry_ingested", mission_id=mission_id, count=len(points))


def get_telemetry(mission_id: str) -> list:
    return telemetry.get(mission_id, [])


def save_anomalies(mission_id: str, items: list):
    with _lock:
        anomalies[mission_id] = items
    log_audit("anomalies_created", mission_id=mission_id, count=len(items))


def get_anomalies(mission_id: str) -> list:
    return anomalies.get(mission_id, [])


def get_anomaly(mission_id: str, anomaly_id: str):
    return next((a for a in get_anomalies(mission_id) if a.id == anomaly_id), None)


def update_anomaly_status(mission_id: str, anomaly_id: str, status: str) -> bool:
    for a in anomalies.get(mission_id, []):
        if a.id == anomaly_id:
            a.status = status
            log_audit("anomaly_status_updated", mission_id=mission_id, anomaly_id=anomaly_id, status=status)
            return True
    return False


def save_recommendations(mission_id: str, cards: list):
    with _lock:
        recommendations.setdefault(mission_id, [])
        recommendations[mission_id].extend(cards)
    log_audit("recommendations_generated", mission_id=mission_id, count=len(cards))


def get_recommendations(mission_id: str) -> list:
    return recommendations.get(mission_id, [])


def save_report(mission_id: str, report):
    with _lock:
        reports.setdefault(mission_id, [])
        reports[mission_id].append(report)
    log_audit("report_generated", mission_id=mission_id, report_id=report.id)


def get_reports(mission_id: str) -> list:
    return reports.get(mission_id, [])


def append_copilot(mission_id: str, message):
    copilot_history.setdefault(mission_id, [])
    copilot_history[mission_id].append(message)


def get_copilot_history(mission_id: str) -> list:
    return copilot_history.get(mission_id, [])


def list_spacecraft() -> list:
    return list(spacecraft_registry.values())


def get_spacecraft(spacecraft_id: str) -> dict | None:
    return spacecraft_registry.get(spacecraft_id)


def upsert_spacecraft(spacecraft_id: str, **fields):
    entry = spacecraft_registry.setdefault(spacecraft_id, {"spacecraft_id": spacecraft_id})
    entry.update(fields)
    log_audit("spacecraft_updated", spacecraft_id=spacecraft_id, **fields)


def save_mission_plan(mission_id: str, evaluation):
    with _lock:
        mission_plans.setdefault(mission_id, [])
        mission_plans[mission_id].append(evaluation)
    log_audit("mission_plan_evaluated", mission_id=mission_id, overall=evaluation.overall)


def get_mission_plans(mission_id: str) -> list:
    return mission_plans.get(mission_id, [])


def save_conjunctions(mission_id: str, events: list):
    with _lock:
        conjunctions[mission_id] = events
    log_audit("conjunctions_screened", mission_id=mission_id, count=len(events))


def get_conjunctions(mission_id: str) -> list:
    return conjunctions.get(mission_id, [])
