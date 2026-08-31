from __future__ import annotations
from typing import List, Dict
from app.schemas.models import RiskAssessment, Forecast
from app.core.config import SUBSYSTEM_CRITICALITY


def _level(score: float) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def compute_risk(
    mission_id: str, spacecraft_id: str,
    subsystem_scores: Dict[str, float],
    forecast: Forecast | None,
) -> RiskAssessment:

    breakdown: Dict[str, Dict[str, float]] = {}
    weighted_total = 0.0
    weight_sum = 0.0
    factors: List[str] = []

    for subsystem, anomaly_score in subsystem_scores.items():
        criticality = SUBSYSTEM_CRITICALITY.get(subsystem, 0.5)
        trend_component = 0.0
        if forecast and forecast.sufficient_data and forecast.estimated_crossing_hours is not None:
            # closer crossing => higher trend severity, saturating at 24h horizon
            trend_component = max(0.0, 1 - min(forecast.estimated_crossing_hours, 24) / 24) * 100

        subsystem_risk = 0.6 * anomaly_score + 0.4 * trend_component
        weighted = subsystem_risk * criticality
        breakdown[subsystem] = {
            "anomaly_score": round(anomaly_score, 1),
            "trend_component": round(trend_component, 1),
            "criticality": criticality,
            "subsystem_risk": round(subsystem_risk, 1),
        }
        weighted_total += weighted
        weight_sum += criticality

        if anomaly_score >= 60:
            factors.append(f"elevated anomaly severity in {subsystem} subsystem")
        if trend_component >= 40:
            factors.append(f"degrading trend in {subsystem} subsystem approaching threshold")

    overall = round(weighted_total / weight_sum, 1) if weight_sum else 0.0
    if not factors:
        factors.append("no significant risk factors detected in current window")

    return RiskAssessment(
        mission_id=mission_id,
        spacecraft_id=spacecraft_id,
        risk_level=_level(overall),
        risk_score=overall,
        factors=factors,
        subsystem_breakdown=breakdown,
    )
