from __future__ import annotations
from typing import List
import pandas as pd

from app.schemas.models import MissionPlanRequest, MissionPlanEvaluation, ConstraintCheck
from app.ml.forecasting import forecast_parameter


def _predict_at(df: pd.DataFrame, parameter: str, minutes_ahead: float) -> float | None:
    fc = forecast_parameter(df, parameter)
    if not fc.sufficient_data:
        return None
    return fc.current_value + fc.trend_per_hour * (minutes_ahead / 60.0)


def evaluate_mission_plan(df: pd.DataFrame, req: MissionPlanRequest) -> MissionPlanEvaluation:
    checks: List[ConstraintCheck] = []
    evidence: List[str] = []
    activity_end = req.start_in_minutes + req.duration_minutes

    # --- power ---
    predicted_power = _predict_at(df, "power_consumption", activity_end)
    current_power = float(df["power_consumption"].iloc[-1])
    if predicted_power is None:
        checks.append(ConstraintCheck(constraint="Power", status="UNKNOWN",
                                       detail="Insufficient telemetry history to project power margin."))
    else:
        # prototype fixed bus power budget the activity load draws against
        bus_budget_w = 250.0
        spare = max(0.0, bus_budget_w - predicted_power - req.required_power_w)
        status = "SAFE" if spare > 40 else "MODERATE" if spare > 0 else "UNSAFE"
        checks.append(ConstraintCheck(
            constraint="Power", status=status,
            detail=f"Projected power draw {predicted_power:.1f}W + activity load {req.required_power_w:.1f}W "
                   f"against a {bus_budget_w:.0f}W prototype bus budget (spare ~{spare:.1f}W).",
        ))
        evidence.append(f"Current power consumption: {current_power:.1f}W")

    # --- thermal ---
    predicted_temp = _predict_at(df, "temperature", activity_end)
    if predicted_temp is None:
        checks.append(ConstraintCheck(constraint="Thermal", status="UNKNOWN",
                                       detail="Insufficient telemetry history to project temperature."))
    else:
        margin = req.max_temperature_c - predicted_temp
        status = "SAFE" if margin > 8 else "MODERATE" if margin > 0 else "UNSAFE"
        checks.append(ConstraintCheck(
            constraint="Thermal", status=status,
            detail=f"Projected temperature at activity end: {predicted_temp:.1f}\u00b0C "
                   f"against a {req.max_temperature_c:.0f}\u00b0C constraint.",
        ))
        evidence.append(f"Current temperature: {float(df['temperature'].iloc[-1]):.1f}\u00b0C")

    # --- fuel ---
    current_fuel = float(df["fuel_level"].iloc[-1])
    fuel_status = "SAFE" if current_fuel > req.min_fuel_pct + 10 else "MODERATE" if current_fuel > req.min_fuel_pct else "UNSAFE"
    checks.append(ConstraintCheck(
        constraint="Fuel", status=fuel_status,
        detail=f"Current fuel level {current_fuel:.1f}% against a {req.min_fuel_pct:.1f}% minimum.",
    ))
    evidence.append(f"Current fuel level: {current_fuel:.1f}%")

    # --- communication ---
    if req.requires_communication:
        signal = float(df["signal_strength"].iloc[-1])
        comms_status = "SAFE" if signal > -80 else "MODERATE" if signal > -90 else "UNSAFE"
        checks.append(ConstraintCheck(
            constraint="Communication", status=comms_status,
            detail=f"Current signal strength {signal:.1f}dBm; activity requires an active communication link.",
        ))
        evidence.append(f"Current signal strength: {signal:.1f}dBm")
    else:
        checks.append(ConstraintCheck(constraint="Communication", status="SAFE", detail="Not required for this activity."))

    # --- attitude ---
    if req.requires_attitude_maneuver:
        gyro_mag = float((df[["gyro_x", "gyro_y", "gyro_z"]].iloc[-1] ** 2).sum() ** 0.5)
        attitude_status = "SAFE" if gyro_mag < 0.05 else "MODERATE" if gyro_mag < 0.15 else "UNSAFE"
        checks.append(ConstraintCheck(
            constraint="Attitude", status=attitude_status,
            detail=f"Current gyro magnitude {gyro_mag:.3f} rad/s; activity requires an attitude maneuver.",
        ))
        evidence.append(f"Current gyro magnitude: {gyro_mag:.3f} rad/s")
    else:
        checks.append(ConstraintCheck(constraint="Attitude", status="SAFE", detail="No maneuver required for this activity."))

    # --- overall ---
    statuses = [c.status for c in checks]
    if "UNSAFE" in statuses:
        overall = "UNSAFE"
    elif "MODERATE" in statuses or "UNKNOWN" in statuses:
        overall = "CONDITIONAL"
    else:
        overall = "SAFE"

    worst = next((c for c in checks if c.status == "UNSAFE"), None) or next((c for c in checks if c.status == "MODERATE"), None)
    if overall == "SAFE":
        recommendation = "All evaluated constraints are within safe margins. Proceed pending final operator sign-off."
    elif worst is not None:
        recommendation = (
            f"{worst.constraint} margin is the limiting factor ({worst.detail}) Consider delaying the activity, "
            f"reducing its scope, or addressing the {worst.constraint.lower()} constraint before proceeding."
        )
    else:
        recommendation = "One or more constraints could not be evaluated; gather more telemetry before proceeding."

    known = sum(1 for c in checks if c.status != "UNKNOWN")
    confidence = round(0.5 + 0.4 * (known / max(1, len(checks))), 2)

    return MissionPlanEvaluation(
        mission_id=req.mission_id,
        spacecraft_id=req.spacecraft_id,
        objective=req.objective,
        checks=checks,
        overall=overall,
        recommendation=recommendation,
        confidence=confidence,
        evidence=evidence,
    )
