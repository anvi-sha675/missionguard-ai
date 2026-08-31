from __future__ import annotations
import abc
import json
import logging
import uuid
from typing import Optional

from app.schemas.models import EvidencePackage, ExplanationResponse, RecommendationCard, MissionPlanEvaluation, ConjunctionEvent
from app.core import config

logger = logging.getLogger("missionguard.granite")

GROUNDING_RULES = """You are the reasoning layer of MissionGuard AI, a spacecraft mission
decision-support system.

You are given a structured EVIDENCE PACKAGE produced by an upstream ML/statistics pipeline.

STRICT GROUNDING RULES:
- Use ONLY facts explicitly present in the EVIDENCE PACKAGE.
- Never invent telemetry values, sensor readings, object properties, orbital parameters,
  collision probabilities, covariance values, miss-distance probabilities, or mission events.
- NEVER claim that a collision is probable, likely, or has a specific probability unless an
  explicit collision probability is present in the evidence.
- A close-approach distance alone does NOT establish collision probability.
- A high relative velocity alone does NOT establish collision probability.
- Do not infer that two objects will collide from a conjunction alert.
- Treat risk_level as the classification produced by this prototype. Do not reinterpret it
  as a certified probability of collision.
- Clearly distinguish OBSERVED facts from INFERRED explanations.
- If information is missing, explicitly say that it is unavailable.
- Do not invent object size, mass, orbital path, trajectory intersection, covariance,
  uncertainty, collision probability, or impact probability.
- The conjunction data is SIMULATED and produced by a simplified screening model.
- Never issue or imply an autonomous spacecraft command.
- Recommendations must be framed as options for operator/mission-team review.
- Do not claim that an avoidance maneuver should definitely be executed.
- Do not claim that a real collision assessment has been performed.

For conjunction explanations specifically:
- State the observed closest approach distance, time to closest approach,
  relative velocity, and prototype risk classification.
- Explain that these values indicate why the prototype classified the event at that risk level,
  but do NOT convert them into a collision probability.
- State clearly that a real conjunction assessment would require authoritative tracking data,
  orbital propagation, uncertainty/covariance information, and mission-specific analysis.

Structure your answer into:
OBSERVATION
LIKELY EXPLANATION
EVIDENCE
RISK
POSSIBLE IMPACT
RECOMMENDED ACTIONS
CONFIDENCE / LIMITATIONS
"""


class GraniteProvider(abc.ABC):
    name: str

    @abc.abstractmethod
    def explain_anomaly(self, evidence: EvidencePackage) -> ExplanationResponse: ...

    @abc.abstractmethod
    def answer_copilot(self, evidence: Optional[EvidencePackage], question: str, mission_summary: str) -> str: ...

    @abc.abstractmethod
    def generate_recommendations(self, evidence: EvidencePackage) -> list[RecommendationCard]: ...

    @abc.abstractmethod
    def summarize_report(self, context: dict) -> str: ...

    @abc.abstractmethod
    def explain_mission_plan(self, evaluation: MissionPlanEvaluation) -> str: ...

    @abc.abstractmethod
    def explain_conjunction(self, event: ConjunctionEvent) -> str: ...


class TemplateExplanationProvider(GraniteProvider):
    """Deterministic, offline stand-in for IBM Granite. Grounded strictly in
    the evidence package fields -- see module docstring."""
    name = "template-offline (Granite-interface compatible)"

    def explain_anomaly(self, evidence: EvidencePackage) -> ExplanationResponse:
        a = evidence.anomaly
        obs = "; ".join(evidence.observations) if evidence.observations else "No specific observations recorded."
        dev = evidence.historical_context.get("baseline_deviation", "deviation not computed")

        top_contrib = a.contributors[0].parameter if a.contributors else a.parameter
        likely = (
            f"The {a.subsystem} subsystem shows a {a.severity_band.lower()} anomaly centered on "
            f"{top_contrib.replace('_', ' ')}, consistent with the observed deviation ({dev}). "
            f"This pattern is most consistent with progressive subsystem degradation rather than a "
            f"single transient sensor glitch, based on the sustained trend in the supporting evidence."
        )

        risk_txt = (
            f"Overall mission risk is {evidence.risk.risk_level} (score {evidence.risk.risk_score}/100). "
            f"Contributing factors: {', '.join(evidence.risk.factors)}."
        )

        if evidence.forecast and evidence.forecast.sufficient_data and evidence.forecast.estimated_crossing_hours:
            impact = (
                f"If the current simulated trend continues unchanged, the model estimates the "
                f"{evidence.forecast.parameter.replace('_',' ')} could reach its warning threshold "
                f"in approximately {evidence.forecast.estimated_crossing_hours} hours. This is a "
                f"trend-based estimate on simulated telemetry, not a certified failure prediction."
            )
        elif evidence.forecast and evidence.forecast.sufficient_data and evidence.forecast.note:
            impact = (
                f"{evidence.forecast.note} Based on the simulated telemetry trend "
                f"({evidence.forecast.trend_per_hour:+.2f}/hour for {evidence.forecast.parameter.replace('_',' ')}), "
                f"continued degradation should be expected without intervention."
            )
        else:
            impact = "Insufficient evidence for a reliable time-to-critical-event estimate at this time."

        actions = _rule_based_actions(a.subsystem, a.severity_band)

        confidence_txt = (
            f"Model confidence: {a.confidence * 100:.0f}%, based on baseline sample size and "
            f"evidence consistency. This is a decision-support estimate, not a certified diagnosis; "
            f"operator judgement and telemetry review are required before acting."
        )

        return ExplanationResponse(
            observation=obs,
            likely_explanation=likely,
            evidence=[
                f"Anomaly score: {a.anomaly_score}/100 ({a.severity_band})",
                f"Baseline deviation: {dev}",
                *[f"{c.parameter.replace('_',' ')} contribution: {c.contribution*100:.0f}%" for c in a.contributors[:3]],
            ],
            risk=risk_txt,
            possible_impact=impact,
            recommended_actions=actions,
            confidence_limitations=confidence_txt,
            provider=self.name,
        )

    def answer_copilot(self, evidence: Optional[EvidencePackage], question: str, mission_summary: str) -> str:
        q = question.lower()
        if evidence is None:
            return (
                f"Based on current mission telemetry: {mission_summary}\n\n"
                f"I don't have a specific anomaly loaded as context for this question. "
                f"Ask about a specific alert, or open an anomaly from the Anomaly Center to give me "
                f"grounded evidence to reason from."
            )

        a = evidence.anomaly
        if "why" in q or "cause" in q or "explain" in q:
            return self.explain_anomaly(evidence).likely_explanation
        if "risk" in q or "highest risk" in q:
            return (
                f"The highest current risk is in the {a.subsystem} subsystem: "
                f"{evidence.risk.risk_level} risk (score {evidence.risk.risk_score}/100). "
                f"Factors: {', '.join(evidence.risk.factors)}."
            )
        if "evidence" in q or "support" in q:
            return "Supporting evidence: " + "; ".join(evidence.observations + [
                f"anomaly score {a.anomaly_score}/100", evidence.historical_context.get("baseline_deviation", "")
            ])
        if "changed" in q or "last" in q:
            return (
                f"In the recent window, {a.parameter.replace('_',' ')} moved into the "
                f"{a.severity_band} band with an anomaly score of {a.anomaly_score}/100. "
                f"{'; '.join(evidence.observations)}"
            )
        if "continue" in q or "happen if" in q:
            return self.explain_anomaly(evidence).possible_impact
        if "investigate" in q or "should" in q:
            actions = _rule_based_actions(a.subsystem, a.severity_band)
            return "Recommended areas to investigate: " + "; ".join(actions)
        if "summar" in q:
            return (
                f"Mission health summary: {mission_summary} Current focus: {a.subsystem} subsystem, "
                f"{a.severity_band} anomaly (score {a.anomaly_score}/100), risk level "
                f"{evidence.risk.risk_level}."
            )

        return (
            f"Regarding '{question}': the current grounded context is a {a.severity_band} anomaly in "
            f"the {a.subsystem} subsystem (score {a.anomaly_score}/100, risk {evidence.risk.risk_level}). "
            f"{'; '.join(evidence.observations)} I can go deeper on cause, risk, evidence, forecast, "
            f"or recommended actions -- just ask."
        )

    def generate_recommendations(self, evidence: EvidencePackage) -> list[RecommendationCard]:
        a = evidence.anomaly
        actions = _rule_based_actions(a.subsystem, a.severity_band)
        cards = []
        for title in actions:
            cards.append(RecommendationCard(
                id=str(uuid.uuid4())[:8],
                anomaly_id=a.id,
                title=title,
                reason=(
                    f"{a.subsystem.capitalize()} subsystem anomaly (score {a.anomaly_score}/100) "
                    f"with risk level {evidence.risk.risk_level}."
                ),
                expected_objective=_objective_for(a.subsystem),
            ))
        return cards

    def summarize_report(self, context: dict) -> str:
        health = context.get("mission_health", 0)
        n_anom = len(context.get("active_anomalies", []))
        risk = context.get("risk_level", "LOW")
        return (
            f"Mission health is currently {health}/100 with {n_anom} active anomal"
            f"{'y' if n_anom == 1 else 'ies'} and an overall risk level of {risk}. "
            f"This report summarizes simulated telemetry, ML-derived anomaly and risk scores, "
            f"and AI-generated (offline template provider) explanations. All figures are prototype "
            f"decision-support estimates on simulated data, not certified mission analysis."
        )

    def explain_mission_plan(self, evaluation: MissionPlanEvaluation) -> str:
        limiting = [c for c in evaluation.checks if c.status in ("UNSAFE", "MODERATE")]
        if not limiting:
            body = "All evaluated constraints (power, thermal, fuel, communication, attitude) are within safe margins."
        else:
            parts = "; ".join(f"{c.constraint} is {c.status}: {c.detail}" for c in limiting)
            body = f"The limiting factors are: {parts}"
        return (
            f"OBJECTIVE: {evaluation.objective}\n"
            f"FEASIBILITY: {evaluation.overall} (confidence {evaluation.confidence*100:.0f}%)\n\n"
            f"{body}\n\n"
            f"RECOMMENDATION: {evaluation.recommendation}\n\n"
            f"This is a deterministic constraint evaluation, not an autonomous go/no-go decision -- "
            f"operator approval is required before proceeding with any planned activity."
        )

    def explain_conjunction(self, event: ConjunctionEvent) -> str:
        prompt = (
            GROUNDING_RULES
            + "\n\nCONJUNCTION EVENT (SIMULATED):\n"
            + event.model_dump_json(indent=2)
            + """

    IMPORTANT:
    Do not state or imply a collision probability.
    Do not state that a collision will occur.
    Do not invent orbital trajectories, object size, mass, covariance,
    probability of collision, or impact probability.

    The explanation must remain grounded in the supplied event fields.
    """
        )

        try:
            narrative = self._call_granite(prompt)
            return f"[SIMULATED DATA] {narrative}"
        except Exception as e:
            self._fallback("explain_conjunction", e)
            narrative = TemplateExplanationProvider().explain_conjunction(event)
            return (
                "[AI service unavailable -- showing deterministic system analysis]\n\n"
                + narrative
            )


def _rule_based_actions(subsystem: str, severity_band: str) -> list[str]:
    base = {
        "power": [
            "Enter low-power operating mode to reduce battery drain",
            "Review non-essential load shedding candidates",
            "Cross-check solar panel orientation and charging telemetry",
        ],
        "thermal": [
            "Increase thermal control system duty cycle",
            "Review recent power draw contributing to heat generation",
            "Reduce compute-intensive onboard tasks temporarily",
        ],
        "communication": [
            "Schedule a link-budget check at next ground station pass",
            "Reduce transmit power to conserve energy if signal quality allows",
            "Verify antenna pointing and attitude telemetry",
        ],
        "navigation": [
            "Cross-validate gyro readings against redundant sensors",
            "Flag attitude control system for engineering review",
            "Hold non-critical maneuvers pending sensor validation",
        ],
    }.get(subsystem, ["Flag subsystem for engineering review", "Increase telemetry sampling rate"])

    if severity_band == "CRITICAL":
        base = ["Escalate to mission engineering team immediately"] + base
    return base[:4]


def _objective_for(subsystem: str) -> str:
    return {
        "power": "Reduce power demand and preserve battery capacity.",
        "thermal": "Bring subsystem temperature back within nominal range.",
        "communication": "Restore reliable link margin.",
        "navigation": "Restore confidence in attitude/orientation data.",
    }.get(subsystem, "Reduce anomaly severity and restore nominal operation.")


class WatsonxGraniteProvider(GraniteProvider):
    name = "ibm-granite (watsonx.ai)"

    # Class-level token cache shared across all method calls within one process.
    _iam_token: str | None = None
    _iam_token_expiry: float = 0.0   # Unix timestamp; 0 means "never fetched"

    def __init__(self):
        if not (config.GRANITE_API_KEY and config.GRANITE_PROJECT_ID):
            raise RuntimeError(
                "GRANITE_API_KEY / GRANITE_PROJECT_ID not configured. "
                "Set EXPLANATION_PROVIDER=template to run without live Granite access."
            )

    def _get_iam_token(self) -> str:
        
        import urllib.request
        import urllib.error
        import urllib.parse
        import time

        now = time.time()
        if self._iam_token and now < self.__class__._iam_token_expiry - 60:
            return self._iam_token

        body = urllib.parse.urlencode({
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": config.GRANITE_API_KEY,
        }).encode()

        req = urllib.request.Request(
            "https://iam.cloud.ibm.com/identity/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        # IAM endpoint is fast; 30 s is ample.
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        token = data.get("access_token")
        if not token:
            raise ValueError("IAM token exchange returned no access_token")

        expires_in = int(data.get("expires_in", 3600))
        self.__class__._iam_token = token
        self.__class__._iam_token_expiry = now + expires_in
        return token

    def _call_granite(self, prompt: str, retries: int = 1) -> str:
        
        import urllib.request
        import urllib.error
        import time

        bearer = self._get_iam_token()

        parts = prompt.split("\n\n", 1)
        system_text = parts[0].strip()
        user_text = parts[1].strip() if len(parts) > 1 else prompt.strip()

        body = json.dumps({
            "model_id": config.GRANITE_MODEL_ID,
            "messages": [
                {"role": "system", "content": system_text},
                {"role": "user",   "content": user_text},
            ],
            "project_id": config.GRANITE_PROJECT_ID,
            "parameters": {"max_new_tokens": 600, "temperature": 0.2},
        }).encode()
        req = urllib.request.Request(
            f"{config.GRANITE_URL}/ml/v1/text/chat?version=2024-05-01",
            data=body,
            headers={
                "Authorization": f"Bearer {bearer}",
                "Content-Type": "application/json",
            },
        )

        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=config.GRANITE_TIMEOUT_SECONDS) as resp:
                    raw_body = resp.read()
                break
            except (urllib.error.URLError, TimeoutError) as e:

                last_exc = e
                is_client_error = isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500
                if is_client_error or attempt == retries:
                    raise
                time.sleep(0.5 * (attempt + 1))
        else:
            raise last_exc  # pragma: no cover -- unreachable, loop always breaks or raises

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Granite returned a non-JSON response: {e}") from e

        # Chat completions response: choices[0].message.content
        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            raise ValueError(f"Granite chat response missing/empty 'choices': {data!r}"[:200])

        text = choices[0].get("message", {}).get("content")
        if not text or not text.strip():
            raise ValueError("Granite returned an empty message content")

        return text

    def _fallback(self, method_name: str, exc: Exception):

        logger.warning(
            f"granite_call_failed method={method_name} error={type(exc).__name__}: {exc} "
            f"-- falling back to offline template provider"
        )

    def _fallback_parse(self, method_name: str, raw: str):

        logger.warning(
            f"granite_parse_failed method={method_name} "
            f"raw_preview={repr(raw[:120])} "
            f"-- sections missing or empty, falling back to offline template provider"
        )

    def explain_anomaly(self, evidence: EvidencePackage) -> ExplanationResponse:
        prompt = GROUNDING_RULES + "\n\nEVIDENCE PACKAGE:\n" + evidence.model_dump_json(indent=2)
        try:
            raw = self._call_granite(prompt)
            parsed = _parse_structured_sections(raw)
            has_content = (
                parsed.get("OBSERVATION")
                or parsed.get("LIKELY EXPLANATION")
                or parsed.get("RISK")
            )
            if not has_content:
                self._fallback_parse("explain_anomaly", raw)
                result = TemplateExplanationProvider().explain_anomaly(evidence)
                result.provider = (
                    f"{TemplateExplanationProvider.name} "
                    f"(fallback -- granite response could not be parsed)"
                )
                return result

            def _lines(text: str) -> list[str]:
                return [s.strip("- ").strip() for s in text.split("\n") if s.strip()]

            response = ExplanationResponse(
                observation=parsed.get("OBSERVATION", ""),
                likely_explanation=parsed.get("LIKELY EXPLANATION", ""),
                evidence=_lines(parsed.get("EVIDENCE", "")),
                risk=parsed.get("RISK", ""),
                possible_impact=parsed.get("POSSIBLE IMPACT", ""),
                recommended_actions=_lines(parsed.get("RECOMMENDED ACTIONS", "")),
                confidence_limitations=parsed.get("CONFIDENCE / LIMITATIONS", ""),
                provider=self.name,
            )
            logger.info(
                f"granite_explanation_success method=explain_anomaly "
                f"sections={sorted(parsed.keys())} "
                f"anomaly_id={evidence.anomaly.id}"
            )
            return response
        except Exception as e:
            self._fallback("explain_anomaly", e)
            result = TemplateExplanationProvider().explain_anomaly(evidence)
            result.provider = f"{TemplateExplanationProvider.name} (fallback -- watsonx unavailable: {type(e).__name__})"
            return result

    def answer_copilot(self, evidence, question, mission_summary):
        prompt = GROUNDING_RULES + f"\n\nMISSION SUMMARY:\n{mission_summary}\n\nQUESTION:\n{question}"
        if evidence:
            prompt += "\n\nEVIDENCE:\n" + evidence.model_dump_json(indent=2)
        try:
            return self._call_granite(prompt)
        except Exception as e:
            self._fallback("answer_copilot", e)
            answer = TemplateExplanationProvider().answer_copilot(evidence, question, mission_summary)
            return f"[AI service unavailable -- showing deterministic system analysis]\n\n{answer}"

    def generate_recommendations(self, evidence):
        return TemplateExplanationProvider().generate_recommendations(evidence)

    def summarize_report(self, context):
        prompt = GROUNDING_RULES + "\n\nREPORT CONTEXT:\n" + json.dumps(context, default=str)
        try:
            return self._call_granite(prompt)
        except Exception as e:
            self._fallback("summarize_report", e)
            summary = TemplateExplanationProvider().summarize_report(context)
            return f"[AI service unavailable -- showing deterministic system analysis] {summary}"

    def explain_mission_plan(self, evaluation: MissionPlanEvaluation) -> str:
        prompt = GROUNDING_RULES + "\n\nMISSION PLAN EVALUATION:\n" + evaluation.model_dump_json(indent=2)
        try:
            return self._call_granite(prompt)
        except Exception as e:
            self._fallback("explain_mission_plan", e)
            narrative = TemplateExplanationProvider().explain_mission_plan(evaluation)
            return f"[AI service unavailable -- showing deterministic system analysis]\n\n{narrative}"

    def explain_conjunction(self, event: ConjunctionEvent) -> str:
        prompt = GROUNDING_RULES + "\n\nCONJUNCTION EVENT (SIMULATED):\n" + event.model_dump_json(indent=2)
        try:
            narrative = self._call_granite(prompt)
            return f"[SIMULATED DATA] {narrative}"
        except Exception as e:
            self._fallback("explain_conjunction", e)
            narrative = TemplateExplanationProvider().explain_conjunction(event)
            return f"[AI service unavailable -- showing deterministic system analysis]\n\n{narrative}"


_CANONICAL = [
    "OBSERVATION",
    "LIKELY EXPLANATION",
    "EVIDENCE",
    "RISK",
    "POSSIBLE IMPACT",
    "RECOMMENDED ACTIONS",
    "CONFIDENCE / LIMITATIONS",
]

_ALIASES: dict[str, str] = {
    # LIKELY EXPLANATION variants
    "EXPLANATION": "LIKELY EXPLANATION",
    "LIKELY_EXPLANATION": "LIKELY EXPLANATION",
    # EVIDENCE variants
    "SUPPORTING EVIDENCE": "EVIDENCE",
    # RISK variants
    "ASSESSMENT": "RISK",
    "RISK ASSESSMENT": "RISK",
    # POSSIBLE IMPACT variants
    "IMPACT": "POSSIBLE IMPACT",
    "POTENTIAL IMPACT": "POSSIBLE IMPACT",
    # RECOMMENDED ACTIONS variants
    "RECOMMENDATION": "RECOMMENDED ACTIONS",
    "RECOMMENDATIONS": "RECOMMENDED ACTIONS",
    "RECOMMENDED ACTION": "RECOMMENDED ACTIONS",
    "ACTIONS": "RECOMMENDED ACTIONS",
    # CONFIDENCE / LIMITATIONS variants
    "CONFIDENCE": "CONFIDENCE / LIMITATIONS",
    "LIMITATIONS": "CONFIDENCE / LIMITATIONS",
    "CONFIDENCE/LIMITATIONS": "CONFIDENCE / LIMITATIONS",
    "CONFIDENCE AND LIMITATIONS": "CONFIDENCE / LIMITATIONS",
}


def _canonicalize_key(raw_key: str) -> str:
    upper = raw_key.strip().upper()
    if upper in _ALIASES:
        return _ALIASES[upper]
    # Check canonical list directly (handles exact matches)
    for c in _CANONICAL:
        if upper == c:
            return c
    return upper


def _value_to_str(value) -> str:

    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item.strip())
            else:
                import json as _json
                parts.append(_json.dumps(item))
        return "\n".join(p for p in parts if p)
    import json as _json
    return _json.dumps(value)


def _try_parse_json(text: str) -> dict | None:

    import json as _json
    import re as _re

    fenced = _re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, _re.DOTALL)
    candidates = []
    if fenced:
        candidates.append(fenced.group(1))
    candidates.append(text.strip())

    for candidate in candidates:
        # Fast reject non-JSON-object-looking strings
        if not candidate.startswith("{"):
            continue
        try:
            obj = _json.loads(candidate)
        except (_json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        # Normalise keys to canonical names
        normalised: dict[str, str] = {}
        for k, v in obj.items():
            canonical = _canonicalize_key(k)
            normalised[canonical] = _value_to_str(v)
        return normalised

    return None


def _parse_structured_sections(raw: str) -> dict:

    import re

    # --- Strategy 1: JSON ---
    json_result = _try_parse_json(raw)
    if json_result is not None:
        return json_result

    # --- Strategy 2: prose section headers ---

    all_header_names = list(_CANONICAL) + list(_ALIASES.keys())
    pattern = (
        r"(?:^|\n)"                          # start or newline before header
        r"\*{0,3}\s*"                        # optional leading asterisks/spaces
        r"("
        + "|".join(re.escape(h) for h in sorted(all_header_names, key=len, reverse=True))
        + r")"
        r"\s*\*{0,3}"                        # optional trailing asterisks/spaces
        r"\s*:?\s*\n?"                       # optional colon + whitespace
    )
    parts = re.split(pattern, raw, flags=re.IGNORECASE)
    result: dict[str, str] = {}
    for i in range(1, len(parts) - 1, 2):
        canonical = _canonicalize_key(parts[i])
        text_value = parts[i + 1].strip()
        # Later occurrence of the same section wins (some models repeat headers)
        result[canonical] = text_value
    return result


def get_provider() -> GraniteProvider:
    if config.EXPLANATION_PROVIDER == "watsonx":
        try:
            return WatsonxGraniteProvider()
        except RuntimeError as e:
            logger.warning(f"watsonx provider unavailable at startup ({e}); using offline template provider")
    return TemplateExplanationProvider()
