from fastapi import APIRouter

from app.ml.evaluation import evaluate_detectors, evaluate_forecast

router = APIRouter(prefix="/models", tags=["model-evaluation"])


@router.get("/evaluate")
def evaluate(scenario: str = "battery_degradation", severity: int = 70, duration_minutes: int = 90):
    return evaluate_detectors(scenario=scenario, severity=severity, duration_minutes=duration_minutes)


@router.get("/evaluate-forecast")
def evaluate_forecast_route(
    scenario: str = "battery_degradation", parameter: str = "battery_voltage",
    severity: int = 70, duration_minutes: int = 90,
):
    return evaluate_forecast(scenario=scenario, parameter=parameter, severity=severity, duration_minutes=duration_minutes)
