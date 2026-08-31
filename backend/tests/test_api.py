import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

MISSION = "API-TEST-MISSION"
SPACECRAFT = "API-TEST-SC"


def _seed_telemetry():
    return client.post("/api/telemetry/simulate", json={
        "mission_id": MISSION, "spacecraft_id": SPACECRAFT,
        "scenario": "battery_degradation", "duration_minutes": 90,
        "severity": 75, "interval_seconds": 30, "seed": 42,
    })


def test_health_endpoint():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "explanation_provider" in r.json()


def test_telemetry_simulate_and_fetch():
    r = _seed_telemetry()
    assert r.status_code == 200
    body = r.json()
    assert body["points_generated"] > 0
    assert body["mission_id"] == MISSION

    r2 = client.get(f"/api/telemetry/{MISSION}")
    assert r2.status_code == 200
    assert len(r2.json()) > 0


def test_anomaly_list_and_detail():
    _seed_telemetry()
    r = client.get("/api/anomalies", params={"mission_id": MISSION})
    assert r.status_code == 200
    anomalies = r.json()
    assert len(anomalies) >= 1

    anomaly_id = anomalies[0]["id"]
    r2 = client.get(f"/api/anomalies/{MISSION}/{anomaly_id}")
    assert r2.status_code == 200
    detail = r2.json()
    assert "explanation" in detail
    assert "risk" in detail
    assert detail["explanation"]["observation"]


def test_anomaly_not_found_returns_404():
    r = client.get(f"/api/anomalies/{MISSION}/does-not-exist")
    assert r.status_code == 404


def test_mission_status_reflects_risk():
    _seed_telemetry()
    r = client.get(f"/api/missions/{MISSION}/status")
    assert r.status_code == 200
    body = r.json()
    assert "mission_health" in body
    assert body["risk"] is not None


def test_predictions_endpoint():
    _seed_telemetry()
    r = client.get(f"/api/predictions/{MISSION}", params={"parameter": "battery_voltage"})
    assert r.status_code == 200
    assert r.json()["sufficient_data"] is True


def test_predictions_no_telemetry_returns_404():
    r = client.get("/api/predictions/NO-SUCH-MISSION")
    assert r.status_code == 404


def test_copilot_chat_grounded():
    _seed_telemetry()
    r = client.post("/api/copilot/chat", json={
        "mission_id": MISSION, "question": "Why is the power subsystem showing abnormal behavior?",
    })
    assert r.status_code == 200
    assert len(r.json()["answer"]) > 0


def test_copilot_conjunction_question_without_screening():
    r = client.post("/api/copilot/chat", json={
        "mission_id": "MISSION-WITH-NO-CONJUNCTIONS", "question": "Are there any nearby conjunction threats?",
    })
    assert r.status_code == 200
    assert "no conjunction screening" in r.json()["answer"].lower()


def test_report_generation():
    _seed_telemetry()
    r = client.post("/api/reports/generate", params={"mission_id": MISSION})
    assert r.status_code == 200
    report = r.json()
    assert report["mission_health"] is not None
    assert "not intended" in report["limitations"].lower() or "prototype" in report["limitations"].lower()


def test_report_no_telemetry_returns_404():
    r = client.post("/api/reports/generate", params={"mission_id": "NO-SUCH-MISSION-XYZ"})
    assert r.status_code == 404


def test_mission_planner_evaluation():
    _seed_telemetry()
    r = client.post("/api/mission-planner/evaluate", json={
        "mission_id": MISSION, "spacecraft_id": SPACECRAFT, "objective": "Test pass",
        "required_power_w": 500,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["evaluation"]["overall"] in ("UNSAFE", "CONDITIONAL")
    assert len(body["narrative"]) > 0


def test_mission_planner_without_telemetry_returns_404():
    r = client.post("/api/mission-planner/evaluate", json={
        "mission_id": "NO-TELEMETRY-MISSION", "spacecraft_id": "SC-X", "objective": "Test",
    })
    assert r.status_code == 404


def test_conjunction_screening_and_explanation():
    r = client.post("/api/conjunctions/screen", params={
        "mission_id": MISSION, "spacecraft_id": SPACECRAFT, "seed": 5,
    })
    assert r.status_code == 200
    events = r.json()
    assert len(events) > 0
    assert all(e["data_source"] == "SIMULATED" for e in events)

    event_id = events[0]["id"]
    r2 = client.get(f"/api/conjunctions/{MISSION}/{event_id}/explain")
    assert r2.status_code == 200
    assert "SIMULATED" in r2.json()["explanation"]


def test_spacecraft_roster():
    r = client.get("/api/spacecraft")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_model_evaluation_returns_real_metrics():
    r = client.get("/api/models/evaluate", params={"scenario": "battery_degradation"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["results"]) == 3
    for m in body["results"]:
        assert 0 <= m["precision"] <= 1
        assert 0 <= m["recall"] <= 1


def test_full_pipeline_end_to_end():
    """Telemetry -> ML -> Risk -> Evidence -> AI provider -> Copilot -> Report,
    exercised as one continuous flow against the real running app."""
    mission = "INTEGRATION-TEST-MISSION"
    sim = client.post("/api/telemetry/simulate", json={
        "mission_id": mission, "spacecraft_id": "INT-SC", "scenario": "compound_anomaly",
        "duration_minutes": 90, "severity": 80, "interval_seconds": 30, "seed": 99,
    })
    assert sim.status_code == 200
    assert sim.json()["anomalies_detected"] >= 1

    anomalies = client.get("/api/anomalies", params={"mission_id": mission}).json()
    assert len(anomalies) >= 1

    detail = client.get(f"/api/anomalies/{mission}/{anomalies[0]['id']}").json()
    assert detail["explanation"]["provider"]

    chat = client.post("/api/copilot/chat", json={"mission_id": mission, "question": "Summarize the current mission health."})
    assert chat.status_code == 200

    report = client.post("/api/reports/generate", params={"mission_id": mission})
    assert report.status_code == 200
    assert len(report.json()["ai_explanations"]) >= 1


def test_conjunction_explain_not_found_returns_404():
    """explain_conjunction for a non-existent ID must return 404, not a
    dict-error body -- consistent with all other not-found endpoints."""
    r = client.get(f"/api/conjunctions/{MISSION}/no-such-conjunction-id/explain")
    assert r.status_code == 404
