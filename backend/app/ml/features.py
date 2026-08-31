"""
Feature engineering. Reused for both "training" (fitting the Isolation
Forest baseline on a normal-window) and inference (scoring new points).
"""
from __future__ import annotations
import pandas as pd
import numpy as np

RAW_PARAMS = [
    "battery_voltage", "battery_current", "power_consumption", "temperature",
    "solar_output", "signal_strength", "fuel_level", "gyro_x", "gyro_y",
    "gyro_z", "cpu_usage", "memory_usage", "radiation_level",
]


def telemetry_to_frame(points) -> pd.DataFrame:
    rows = [p.model_dump() if hasattr(p, "model_dump") else p for p in points]
    if not rows:
        return pd.DataFrame(columns=["timestamp", "mission_id", "spacecraft_id", "subsystem", *RAW_PARAMS])
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def build_features(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    feat = df.copy()
    for col in RAW_PARAMS:
        feat[f"{col}_roll_mean"] = df[col].rolling(window, min_periods=1).mean()
        feat[f"{col}_roll_std"] = df[col].rolling(window, min_periods=1).std().fillna(0.0)
        feat[f"{col}_pct_change"] = df[col].pct_change().fillna(0.0).replace([np.inf, -np.inf], 0.0)
        feat[f"{col}_rate"] = df[col].diff().fillna(0.0)

    # cross-parameter relationships
    feat["power_per_volt"] = df["power_consumption"] / df["battery_voltage"].replace(0, np.nan)
    feat["power_per_volt"] = feat["power_per_volt"].bfill().fillna(0.0)
    feat["temp_power_ratio"] = df["temperature"].diff().fillna(0.0) / (df["power_consumption"].diff().replace(0, np.nan).fillna(1.0))
    feat["temp_power_ratio"] = feat["temp_power_ratio"].replace([np.inf, -np.inf], 0.0).fillna(0.0)

    return feat


def feature_matrix(feat: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in feat.columns if c not in (
        "timestamp", "mission_id", "spacecraft_id", "subsystem"
    )]
    return feat[cols].fillna(0.0)


MODEL_PARAMS = [
    "battery_voltage", "battery_current", "power_consumption",
    "temperature", "signal_strength", "cpu_usage",
]


def model_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Compact, targeted feature set used specifically to FIT/SCORE the
    Isolation Forest anomaly model (see MODEL_PARAMS note above). The full
    `build_features`/`feature_matrix` output above is still used for the
    Telemetry Explorer's rolling-average/trend display."""
    X = pd.DataFrame(index=df.index)
    for c in MODEL_PARAMS:
        X[c] = df[c]
        X[f"{c}_rate"] = df[c].diff().fillna(0.0)
        X[f"{c}_roll_mean"] = df[c].rolling(5, min_periods=1).mean()
    return X
