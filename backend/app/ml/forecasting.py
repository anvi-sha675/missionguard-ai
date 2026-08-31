from __future__ import annotations
import numpy as np
import pandas as pd
from app.schemas.models import Forecast

WARNING_THRESHOLDS = {
    "battery_voltage": 25.0,
    "temperature": 45.0,
    "signal_strength": -85.0,
    "fuel_level": 15.0,
}
# direction: does crossing mean the value falls below (-1) or rises above (+1) the threshold
DIRECTION = {
    "battery_voltage": -1, "temperature": +1, "signal_strength": -1, "fuel_level": -1,
}

MIN_POINTS = 6


def forecast_parameter(df: pd.DataFrame, parameter: str) -> Forecast:
    if parameter not in df.columns:
        return Forecast(parameter=parameter, current_value=0, trend_per_hour=0,
                         sufficient_data=False, note="Unknown parameter.")

    series = df[["timestamp", parameter]].dropna()
    current_value = float(series[parameter].iloc[-1])

    if len(series) < MIN_POINTS:
        return Forecast(
            parameter=parameter, current_value=current_value, trend_per_hour=0.0,
            sufficient_data=False,
            note="Insufficient historical data for reliable forecasting.",
        )

    t0 = series["timestamp"].iloc[0]
    hours = (series["timestamp"] - t0).dt.total_seconds() / 3600.0
    y = series[parameter].values
    x = hours.values

    # simple linear regression (least squares)
    A = np.vstack([x, np.ones_like(x)]).T
    slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]

    threshold = WARNING_THRESHOLDS.get(parameter)
    direction = DIRECTION.get(parameter, -1)

    crossing_hours = None
    note = None
    if threshold is not None:
        moving_toward_threshold = (slope * direction) > 0
        if abs(slope) < 1e-4 or not moving_toward_threshold:
            note = "Trend is flat or moving away from the warning threshold."
        else:
            last_t = x[-1]
            # solve slope*t + intercept = threshold for t, relative to now
            t_cross = (threshold - intercept) / slope
            delta = t_cross - last_t
            if delta > 0:
                crossing_hours = round(float(delta), 2)
            else:
                note = "Trend suggests threshold was already crossed within the observed window."

    return Forecast(
        parameter=parameter,
        current_value=round(current_value, 3),
        trend_per_hour=round(float(slope), 4),
        threshold=threshold,
        estimated_crossing_hours=crossing_hours,
        sufficient_data=True,
        note=note,
    )
