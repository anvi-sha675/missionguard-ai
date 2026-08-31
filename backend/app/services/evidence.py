from __future__ import annotations
import pandas as pd

from app.schemas.models import Anomaly, EvidencePackage, Forecast, RiskAssessment


def build_evidence(
    df: pd.DataFrame,
    anomaly: Anomaly,
    forecast: Forecast | None,
    risk: RiskAssessment,
) -> EvidencePackage:
    
    window = df.tail(min(len(df), 20))
    baseline = df.head(max(5, len(df) // 3))

    observations = list(anomaly.observations)
    historical_context = {}
    if anomaly.parameter in df.columns:
        mu = baseline[anomaly.parameter].mean()
        sigma = baseline[anomaly.parameter].std() or 1e-6
        current = window[anomaly.parameter].iloc[-1]
        z = (current - mu) / sigma
        historical_context["baseline_deviation"] = f"{z:.1f} standard deviations from baseline"
        historical_context["baseline_mean"] = f"{mu:.2f}"
        historical_context["current_value"] = f"{current:.2f}"

    return EvidencePackage(
        mission_id=anomaly.mission_id,
        spacecraft_id=anomaly.spacecraft_id,
        anomaly=anomaly,
        observations=observations,
        historical_context=historical_context,
        forecast=forecast,
        risk=risk,
    )
