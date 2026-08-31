import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.explain import get_provider, WatsonxGraniteProvider, TemplateExplanationProvider
from app.core import config
from app.schemas.models import ScenarioRequest
from app.services.simulator import generate_scenario
from app.services import pipeline
from app.services.evidence import build_evidence


@pytest.fixture(autouse=True)
def fake_watsonx_credentials(monkeypatch):

    monkeypatch.setattr(config, "EXPLANATION_PROVIDER", "watsonx")
    monkeypatch.setattr(config, "GRANITE_API_KEY", "test-key-not-real")
    monkeypatch.setattr(config, "GRANITE_PROJECT_ID", "test-project-not-real")
    from app.services.explain import WatsonxGraniteProvider
    monkeypatch.setattr(WatsonxGraniteProvider, "_get_iam_token",
                        lambda self: "test-iam-token-not-real")


@pytest.fixture
def evidence():
    req = ScenarioRequest(mission_id="T", spacecraft_id="T-1", scenario="battery_degradation",
                           duration_minutes=90, severity=75, interval_seconds=30, seed=42)
    points = generate_scenario(req)
    df, anomalies = pipeline.analyze_run(points)
    assert anomalies, "test fixture requires a detected anomaly"
    forecast = pipeline.forecast_for_anomaly(df, anomalies[-1])
    risk = pipeline.risk_for_run(df, anomalies, forecast)
    return build_evidence(df, anomalies[-1], forecast, risk)


def test_watsonx_provider_selected_when_credentials_present():
    provider = get_provider()
    assert isinstance(provider, WatsonxGraniteProvider)


def test_explain_anomaly_falls_back_cleanly_on_network_failure(evidence):
    provider = WatsonxGraniteProvider()
    result = provider.explain_anomaly(evidence)
    # must not crash, must return a real ExplanationResponse
    assert result.observation
    assert result.likely_explanation
    # must be honestly labeled as a fallback, never claimed as real Granite output
    assert "fallback" in result.provider.lower()
    assert "watsonx" in result.provider.lower()


def test_answer_copilot_falls_back_with_visible_notice(evidence):
    provider = WatsonxGraniteProvider()
    answer = provider.answer_copilot(evidence, "why is this happening", "test summary")
    assert "AI service unavailable" in answer
    assert len(answer) > len("[AI service unavailable -- showing deterministic system analysis]")


def test_summarize_report_falls_back_with_visible_notice():
    provider = WatsonxGraniteProvider()
    summary = provider.summarize_report({"mission_health": 62.0, "active_anomalies": [], "risk_level": "MEDIUM"})
    assert "AI service unavailable" in summary


def test_fallback_never_silently_impersonates_granite(evidence):
    """The single most important safety property in this whole module: a
    fallback response must always be distinguishable from a real one."""
    provider = WatsonxGraniteProvider()
    result = provider.explain_anomaly(evidence)
    template_direct = TemplateExplanationProvider().explain_anomaly(evidence)
    # content matches the template provider's output...
    assert result.observation == template_direct.observation
    # ...but the provider label does NOT claim to be plain "ibm-granite"
    assert result.provider != WatsonxGraniteProvider.name


# ------------------------------------------------ malformed/empty responses
def test_malformed_json_response_falls_back(monkeypatch, evidence):
    """Simulates Granite returning non-JSON (e.g. an HTML error page from a
    misconfigured gateway) and proves it doesn't crash the app."""
    import urllib.request

    class FakeResp:
        def read(self):
            return b"<html>not json</html>"
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: FakeResp())
    provider = WatsonxGraniteProvider()
    result = provider.explain_anomaly(evidence)
    assert "fallback" in result.provider.lower()


def test_empty_choices_response_falls_back(monkeypatch, evidence):
    """Simulates a well-formed but empty Granite chat response (choices: [])."""
    import urllib.request

    class FakeResp:
        def read(self):
            return json.dumps({"choices": []}).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: FakeResp())
    provider = WatsonxGraniteProvider()
    result = provider.explain_anomaly(evidence)
    assert "fallback" in result.provider.lower()


def test_empty_message_content_falls_back(monkeypatch, evidence):
    """Simulates a Granite chat response with blank message content."""
    import urllib.request

    class FakeResp:
        def read(self):
            return json.dumps({"choices": [{"message": {"role": "assistant", "content": "   "}}]}).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: FakeResp())
    provider = WatsonxGraniteProvider()
    result = provider.explain_anomaly(evidence)
    assert "fallback" in result.provider.lower()


def test_client_error_does_not_retry(monkeypatch):
    """A 4xx (bad API key / bad request) should fail fast, not burn demo
    seconds retrying something that can never succeed."""
    import urllib.request
    import urllib.error

    call_count = {"n": 0}

    def fake_urlopen(*a, **k):
        call_count["n"] += 1
        raise urllib.error.HTTPError("http://x", 401, "Unauthorized", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    provider = WatsonxGraniteProvider()
    with pytest.raises(urllib.error.HTTPError):
        provider._call_granite("test prompt")
    assert call_count["n"] == 1  # no retry on a 4xx


def test_transient_error_does_retry(monkeypatch):
    """A generic connection failure should be retried once before giving up."""
    import urllib.request
    import urllib.error

    call_count = {"n": 0}

    def fake_urlopen(*a, **k):
        call_count["n"] += 1
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    provider = WatsonxGraniteProvider()
    with pytest.raises(urllib.error.URLError):
        provider._call_granite("test prompt", retries=1)
    assert call_count["n"] == 2  # original attempt + 1 retry


# ------------------------------------------------ parser safety
def test_realistic_granite_response_parses_correctly(monkeypatch, evidence):
    """A well-formed Granite-3-8b-instruct response (realistic section headers
    and content) must parse into a valid ExplanationResponse with non-empty
    critical fields -- no fallback should be triggered."""
    import urllib.request

    REALISTIC_RESPONSE = (
        "OBSERVATION:\n"
        "Battery voltage has declined steadily over the past 60 minutes, "
        "falling from 28.0V to 22.4V. Power consumption has risen concurrently.\n\n"
        "LIKELY EXPLANATION:\n"
        "Progressive battery cell degradation consistent with end-of-life capacity loss. "
        "The simultaneous rise in current draw and consumption suggests the battery is "
        "being over-discharged to compensate for lost capacity.\n\n"
        "EVIDENCE:\n"
        "- Battery voltage: 22.4V (baseline 28.0V, deviation -2.1 standard deviations)\n"
        "- Power consumption: 155W (up from baseline 120W)\n"
        "- Battery current: 5.7A (elevated)\n\n"
        "RISK:\n"
        "Overall mission risk is HIGH. Power subsystem degradation is the primary factor.\n\n"
        "POSSIBLE IMPACT:\n"
        "If the current trend continues, voltage may cross the 25V warning threshold "
        "within approximately 4 hours, triggering safe-mode entry.\n\n"
        "RECOMMENDED ACTIONS:\n"
        "- Enter low-power operating mode to reduce battery drain\n"
        "- Review non-essential load shedding candidates\n"
        "- Cross-check solar panel orientation and charging telemetry\n\n"
        "CONFIDENCE / LIMITATIONS:\n"
        "Confidence: 82%. Based on simulated telemetry; operator review required before action."
    )

    class FakeResp:
        def read(self):
            import json as _json
            return _json.dumps({"choices": [{"message": {"role": "assistant", "content": REALISTIC_RESPONSE}}]}).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: FakeResp())
    provider = WatsonxGraniteProvider()
    result = provider.explain_anomaly(evidence)

    # All three critical fields must be populated -- no silent blanks
    assert result.observation, "OBSERVATION must not be empty"
    assert result.likely_explanation, "LIKELY EXPLANATION must not be empty"
    assert result.risk, "RISK must not be empty"
    # Should be credited to the real Granite provider, not a fallback
    assert "fallback" not in result.provider.lower()
    assert "ibm-granite" in result.provider.lower()


def test_unparseable_granite_response_falls_back_with_parse_label(monkeypatch, evidence):
    """A successful HTTP call that returns a response whose structure the parser
    cannot map to any known section headers must fall back to the template
    provider and be labeled as a parse failure, not a network failure."""
    import urllib.request

    UNPARSEABLE_RESPONSE = (
        "Sure! Here is my analysis of the spacecraft situation you have described. "
        "The battery appears to be experiencing some issues. "
        "You should probably look into it soon. "
        "Let me know if you need more help!"
    )

    class FakeResp:
        def read(self):
            import json as _json
            return _json.dumps({"choices": [{"message": {"role": "assistant", "content": UNPARSEABLE_RESPONSE}}]}).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: FakeResp())
    provider = WatsonxGraniteProvider()
    result = provider.explain_anomaly(evidence)

    # Must fall back cleanly -- non-empty content from the template
    assert result.observation, "fallback must populate observation"
    assert result.likely_explanation, "fallback must populate explanation"
    # Must be labeled as a parse fallback, not a network failure
    assert "fallback" in result.provider.lower()
    assert "parsed" in result.provider.lower()
    # Must not claim to be live Granite output
    assert result.provider != WatsonxGraniteProvider.name
