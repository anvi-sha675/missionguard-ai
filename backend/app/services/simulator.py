from __future__ import annotations
import math
from datetime import datetime, timedelta, timezone
from typing import List
import numpy as np

from app.schemas.models import TelemetryPoint, ScenarioRequest

BASELINE = dict(
    battery_voltage=28.0, battery_current=4.5, power_consumption=120.0,
    temperature=22.0, solar_output=420.0, signal_strength=-65.0,
    fuel_level=85.0, gyro_x=0.0, gyro_y=0.0, gyro_z=0.0,
    cpu_usage=35.0, memory_usage=45.0, radiation_level=0.6,
)


def _noise(rng: np.random.Generator, scale: float) -> float:
    return float(rng.normal(0, scale))


def generate_scenario(req: ScenarioRequest) -> List[TelemetryPoint]:
    rng = np.random.default_rng(req.seed)
    n_points = max(3, (req.duration_minutes * 60) // req.interval_seconds)
    severity = req.severity / 100.0  # 0-1
    start = datetime.now(timezone.utc) - timedelta(minutes=req.duration_minutes)

    points: List[TelemetryPoint] = []

    for i in range(n_points):
        t = i / max(1, n_points - 1)  # progress 0->1 through the run
        ts = start + timedelta(seconds=i * req.interval_seconds)

        # start from baseline + small ambient noise every tick
        vals = {
            k: v + _noise(rng, abs(v) * 0.01 + 0.05) for k, v in BASELINE.items()
        }

        if req.scenario == "normal":
            pass

        elif req.scenario == "battery_degradation":
            drop = severity * 6.0 * t  # up to ~6V drop at full severity
            vals["battery_voltage"] -= drop
            vals["power_consumption"] += severity * 35 * t
            vals["battery_current"] += severity * 1.2 * t

        elif req.scenario == "thermal_anomaly":
            vals["temperature"] += severity * 28 * t
            vals["power_consumption"] += severity * 20 * t
            vals["cpu_usage"] += severity * 15 * t

        elif req.scenario == "communication_anomaly":
            vals["signal_strength"] -= severity * 25 * t
            vals["power_consumption"] += severity * 18 * t

        elif req.scenario == "sensor_anomaly":
            spike = rng.choice([0, 1], p=[0.85, 0.15])
            if spike:
                vals["gyro_x"] += _noise(rng, 1.0) * severity * 4
                vals["gyro_y"] += _noise(rng, 1.0) * severity * 4
                vals["gyro_z"] += _noise(rng, 1.0) * severity * 4

        elif req.scenario == "compound_anomaly":
            drop = severity * 5.0 * t
            vals["battery_voltage"] -= drop
            vals["power_consumption"] += severity * 30 * t
            vals["temperature"] += severity * 15 * t
            vals["signal_strength"] -= severity * 12 * t

        vals["fuel_level"] = max(0.0, BASELINE["fuel_level"] - t * 2.0)
        vals["solar_output"] = BASELINE["solar_output"] + 15 * math.sin(t * math.pi * 2) + _noise(rng, 5)
        vals["memory_usage"] = min(100.0, max(0.0, vals["memory_usage"]))
        vals["cpu_usage"] = min(100.0, max(0.0, vals["cpu_usage"]))

        points.append(TelemetryPoint(
            timestamp=ts,
            mission_id=req.mission_id,
            spacecraft_id=req.spacecraft_id,
            subsystem=_scenario_subsystem(req.scenario),
            **vals,
        ))

    return points


def _scenario_subsystem(scenario: str) -> str:
    return {
        "normal": "power",
        "battery_degradation": "power",
        "thermal_anomaly": "thermal",
        "communication_anomaly": "communication",
        "sensor_anomaly": "navigation",
        "compound_anomaly": "power",
    }.get(scenario, "power")
