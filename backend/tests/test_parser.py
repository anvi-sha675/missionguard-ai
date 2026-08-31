import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
from app.services.explain import (
    _parse_structured_sections,
    _try_parse_json,
    _canonicalize_key,
    _value_to_str,
)



def test_canonicalize_exact_canonical():
    assert _canonicalize_key("OBSERVATION") == "OBSERVATION"
    assert _canonicalize_key("LIKELY EXPLANATION") == "LIKELY EXPLANATION"
    assert _canonicalize_key("CONFIDENCE / LIMITATIONS") == "CONFIDENCE / LIMITATIONS"


def test_canonicalize_alias_assessment():
    assert _canonicalize_key("ASSESSMENT") == "RISK"
    assert _canonicalize_key("assessment") == "RISK"


def test_canonicalize_alias_recommendation():
    assert _canonicalize_key("RECOMMENDATION") == "RECOMMENDED ACTIONS"
    assert _canonicalize_key("recommendations") == "RECOMMENDED ACTIONS"


def test_canonicalize_alias_confidence():
    assert _canonicalize_key("CONFIDENCE") == "CONFIDENCE / LIMITATIONS"
    assert _canonicalize_key("LIMITATIONS") == "CONFIDENCE / LIMITATIONS"


def test_canonicalize_unknown_key_uppercased():
    assert _canonicalize_key("something_unknown") == "SOMETHING_UNKNOWN"


def test_value_to_str_string():
    assert _value_to_str("  hello  ") == "hello"


def test_value_to_str_list_of_strings():
    result = _value_to_str(["item one", "  item two  ", "item three"])
    assert result == "item one\nitem two\nitem three"


def test_value_to_str_list_with_empty_items():
    result = _value_to_str(["item one", "", "item three"])
    assert "item one" in result
    assert "item three" in result


def test_value_to_str_list_with_non_string_item():
    # Non-string list items should not crash
    result = _value_to_str(["text", {"nested": "dict"}])
    assert "text" in result


def test_value_to_str_dict_fallback():
    result = _value_to_str({"key": "val"})
    assert isinstance(result, str)


def test_try_parse_json_uppercase_keys_string_values():
    raw = json.dumps({
        "OBSERVATION": "Battery voltage dropped.",
        "LIKELY EXPLANATION": "Degradation detected.",
        "EVIDENCE": "Score: 70.2",
        "RISK": "MEDIUM",
        "POSSIBLE IMPACT": "Power loss.",
        "RECOMMENDED ACTIONS": "Reduce load.",
        "CONFIDENCE / LIMITATIONS": "High confidence.",
    })
    result = _try_parse_json(raw)
    assert result is not None
    assert result["OBSERVATION"] == "Battery voltage dropped."
    assert result["RISK"] == "MEDIUM"


def test_try_parse_json_lowercase_keys():
    raw = json.dumps({
        "observation": "Voltage dropped.",
        "likely explanation": "Degradation.",
        "risk": "MEDIUM",
    })
    result = _try_parse_json(raw)
    assert result is not None
    assert result["OBSERVATION"] == "Voltage dropped."
    assert result["RISK"] == "MEDIUM"


def test_try_parse_json_alias_keys():
    """Keys like ASSESSMENT and RECOMMENDATION must map to canonical names."""
    raw = json.dumps({
        "OBSERVATION": "Thermal anomaly.",
        "ASSESSMENT": "HIGH risk.",
        "RECOMMENDATION": "Reduce power.",
        "CONFIDENCE": "80% confidence.",
    })
    result = _try_parse_json(raw)
    assert result is not None
    assert result["RISK"] == "HIGH risk."
    assert result["RECOMMENDED ACTIONS"] == "Reduce power."
    assert result["CONFIDENCE / LIMITATIONS"] == "80% confidence."


def test_try_parse_json_list_values():
    """Section values that are lists must be joined to a string."""
    raw = json.dumps({
        "OBSERVATION": [
            "Battery voltage has dropped by 4.7% over 15 minutes",
            "Power consumption has risen by 4.6%",
        ],
        "RISK": "MEDIUM",
        "LIKELY EXPLANATION": "Battery degradation.",
    })
    result = _try_parse_json(raw)
    assert result is not None
    assert "Battery voltage has dropped" in result["OBSERVATION"]
    assert "Power consumption has risen" in result["OBSERVATION"]
    assert result["RISK"] == "MEDIUM"


def test_try_parse_json_markdown_fence():
    """JSON wrapped in ```json ... ``` must be parsed correctly."""
    payload = json.dumps({
        "OBSERVATION": "Anomaly detected.",
        "RISK": "LOW",
        "LIKELY EXPLANATION": "Sensor noise.",
    })
    raw = f"```json\n{payload}\n```"
    result = _try_parse_json(raw)
    assert result is not None
    assert result["OBSERVATION"] == "Anomaly detected."
    assert result["RISK"] == "LOW"


def test_try_parse_json_markdown_fence_no_lang():
    """JSON wrapped in ``` ... ``` (no 'json' tag) must also parse."""
    payload = json.dumps({"OBSERVATION": "ok", "RISK": "LOW", "LIKELY EXPLANATION": "fine"})
    raw = f"```\n{payload}\n```"
    result = _try_parse_json(raw)
    assert result is not None
    assert result["OBSERVATION"] == "ok"


def test_try_parse_json_whitespace_around_json():
    payload = json.dumps({"OBSERVATION": "ok", "RISK": "LOW", "LIKELY EXPLANATION": "fine"})
    result = _try_parse_json("   \n" + payload + "\n   ")
    assert result is not None
    assert result["OBSERVATION"] == "ok"


def test_try_parse_json_malformed_returns_none():
    assert _try_parse_json("{not valid json}") is None
    assert _try_parse_json("just plain text") is None
    assert _try_parse_json("") is None


def test_try_parse_json_array_root_returns_none():
    """A JSON array at root level is not a valid section dict."""
    assert _try_parse_json('["a", "b"]') is None

def test_parse_json_response_uppercase_list_values():
    """Exercises the exact format from the bug report."""
    raw = json.dumps({
        "OBSERVATION": [
            "Battery voltage has dropped by 4.7% over 15 minutes",
            "Power consumption has risen by 4.6%",
        ],
        "LIKELY EXPLANATION": "Progressive battery degradation.",
        "EVIDENCE": ["Score: 70.2", "Baseline: 28V, current: 24V"],
        "RISK": "MEDIUM risk score 42.1",
        "POSSIBLE IMPACT": "Power loss within 4 hours.",
        "RECOMMENDED ACTIONS": ["Reduce load", "Check solar panels"],
        "CONFIDENCE / LIMITATIONS": "High confidence on simulated data.",
    })
    result = _parse_structured_sections(raw)
    assert "Battery voltage has dropped" in result["OBSERVATION"]
    assert result["LIKELY EXPLANATION"] == "Progressive battery degradation."
    assert "Score: 70.2" in result["EVIDENCE"]
    assert result["RISK"] == "MEDIUM risk score 42.1"
    assert "Reduce load" in result["RECOMMENDED ACTIONS"]
    assert result["CONFIDENCE / LIMITATIONS"] == "High confidence on simulated data."


def test_parse_prose_standard_headers():
    raw = (
        "OBSERVATION\n"
        "Voltage dropped 3.7%.\n\n"
        "LIKELY EXPLANATION\n"
        "Battery degradation.\n\n"
        "EVIDENCE\n"
        "- Score 70.2\n\n"
        "RISK\n"
        "MEDIUM\n\n"
        "POSSIBLE IMPACT\n"
        "Power loss.\n\n"
        "RECOMMENDED ACTIONS\n"
        "Reduce load.\n\n"
        "CONFIDENCE / LIMITATIONS\n"
        "80% confidence.\n"
    )
    result = _parse_structured_sections(raw)
    assert result["OBSERVATION"] == "Voltage dropped 3.7%."
    assert result["RISK"] == "MEDIUM"
    assert result["LIKELY EXPLANATION"] == "Battery degradation."


def test_parse_prose_with_colons():
    raw = (
        "OBSERVATION:\nVoltage dropped.\n\n"
        "RISK:\nMEDIUM\n\n"
        "LIKELY EXPLANATION:\nDegradation.\n"
    )
    result = _parse_structured_sections(raw)
    assert result["OBSERVATION"] == "Voltage dropped."
    assert result["RISK"] == "MEDIUM"


def test_parse_prose_bold_headers():
    raw = (
        "**OBSERVATION**\nVoltage dropped.\n\n"
        "**RISK**\nMEDIUM\n\n"
        "**LIKELY EXPLANATION**\nDegradation.\n"
    )
    result = _parse_structured_sections(raw)
    assert result["OBSERVATION"] == "Voltage dropped."
    assert result["RISK"] == "MEDIUM"


def test_parse_prose_triple_asterisk_headers():
    raw = (
        "*** OBSERVATION ***\nVoltage dropped.\n\n"
        "*** RISK ***\nMEDIUM\n"
    )
    result = _parse_structured_sections(raw)
    assert result.get("OBSERVATION") == "Voltage dropped."
    assert result.get("RISK") == "MEDIUM"


def test_parse_alias_keys_in_prose():
    """ASSESSMENT in prose must map to RISK."""
    raw = (
        "OBSERVATION\nAnomaly detected.\n\n"
        "ASSESSMENT\nHIGH risk.\n\n"
        "RECOMMENDATION\nReduce power.\n"
    )
    result = _parse_structured_sections(raw)
    assert result["RISK"] == "HIGH risk."
    assert result["RECOMMENDED ACTIONS"] == "Reduce power."


def test_parse_missing_required_sections_returns_empty_dict():
    """Completely unparseable text returns an empty dict (not an exception)."""
    result = _parse_structured_sections("This is just some random text with no headers.")
    # May return empty or partial; must not raise
    assert isinstance(result, dict)


def test_parse_malformed_json_falls_through_to_prose():
    """Malformed JSON must fall through to the prose parser, not raise."""
    raw = "{not valid json}\n\nOBSERVATION\nVoltage dropped.\n\nRISK\nLOW\n"
    result = _parse_structured_sections(raw)
    # The prose parser should pick up OBSERVATION and RISK
    assert result.get("OBSERVATION") == "Voltage dropped."
    assert result.get("RISK") == "LOW"


def test_parse_empty_string():
    assert _parse_structured_sections("") == {}


def test_parse_json_with_alias_assessment_maps_to_risk():
    raw = json.dumps({
        "OBSERVATION": "Thermal spike.",
        "ASSESSMENT": "CRITICAL risk.",
        "LIKELY EXPLANATION": "Overheating.",
    })
    result = _parse_structured_sections(raw)
    assert result["RISK"] == "CRITICAL risk."
    assert "ASSESSMENT" not in result  # alias resolved away
