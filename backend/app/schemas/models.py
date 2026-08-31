from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Literal
from pydantic import BaseModel, Field


class TelemetryPoint(BaseModel):
    timestamp: datetime
    mission_id: str
    spacecraft_id: str
    subsystem: str
    battery_voltage: float
    battery_current: float
    power_consumption: float
    temperature: float
    solar_output: float
    signal_strength: float
    fuel_level: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    cpu_usage: float
    memory_usage: float
    radiation_level: float


class ScenarioRequest(BaseModel):
    mission_id: str = "MISSION-001"
    spacecraft_id: str = "SC-001"
    scenario: Literal[
        "normal", "battery_degradation", "thermal_anomaly",
        "communication_anomaly", "sensor_anomaly", "compound_anomaly"
    ] = "normal"
    duration_minutes: int = Field(60, ge=5, le=1440)
    severity: int = Field(60, ge=1, le=100)
    interval_seconds: int = Field(30, ge=5, le=300)
    seed: Optional[int] = 42


class AnomalyContributor(BaseModel):
    parameter: str
    contribution: float  # 0-1 relative contribution


class Anomaly(BaseModel):
    id: str
    mission_id: str
    spacecraft_id: str
    subsystem: str
    parameter: str
    timestamp: datetime
    anomaly_score: float
    severity_band: Literal["NORMAL", "LOW", "WARNING", "CRITICAL"]
    confidence: float
    observations: List[str]
    contributors: List[AnomalyContributor]
    status: Literal["NEW", "INVESTIGATING", "ACKNOWLEDGED", "MONITORING", "RESOLVED"] = "NEW"


class Forecast(BaseModel):
    parameter: str
    current_value: float
    trend_per_hour: float
    threshold: Optional[float] = None
    estimated_crossing_hours: Optional[float] = None
    sufficient_data: bool
    note: Optional[str] = None


class RiskAssessment(BaseModel):
    mission_id: str
    spacecraft_id: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    risk_score: float
    factors: List[str]
    subsystem_breakdown: Dict[str, Dict[str, float]]


class EvidencePackage(BaseModel):
    mission_id: str
    spacecraft_id: str
    anomaly: Anomaly
    observations: List[str]
    historical_context: Dict[str, str]
    forecast: Optional[Forecast]
    risk: RiskAssessment


class ExplanationResponse(BaseModel):
    observation: str
    likely_explanation: str
    evidence: List[str]
    risk: str
    possible_impact: str
    recommended_actions: List[str]
    confidence_limitations: str
    provider: str


class RecommendationCard(BaseModel):
    id: str
    anomaly_id: str
    title: str
    reason: str
    expected_objective: str
    requires_operator_validation: bool = True
    status: Literal["PROPOSED", "ACCEPTED_FOR_REVIEW", "DISMISSED"] = "PROPOSED"


class CopilotMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    context_anomaly_id: Optional[str] = None


class CopilotRequest(BaseModel):
    mission_id: str
    question: str
    context_anomaly_id: Optional[str] = None


class MissionReport(BaseModel):
    id: str
    mission_id: str
    generated_at: datetime
    executive_summary: str
    mission_health: float
    active_anomalies: List[Anomaly]
    subsystem_status: Dict[str, str]
    risk_assessment: RiskAssessment
    forecasts: List[Forecast]
    ai_explanations: List[str]
    recommended_actions: List[str]
    limitations: str


# ---------------------------------------------------------------- spacecraft
class Spacecraft(BaseModel):
    spacecraft_id: str
    mission_id: str
    name: str
    status: Literal["HEALTHY", "WARNING", "CRITICAL", "STANDBY"] = "STANDBY"
    health: float = 100.0


# ------------------------------------------------------------ mission planner
class MissionPlanRequest(BaseModel):
    mission_id: str
    spacecraft_id: str
    objective: str
    start_in_minutes: float = Field(0, ge=0, description="minutes from now the activity would start")
    duration_minutes: float = Field(15, gt=0)
    required_power_w: float = Field(100, ge=0)
    requires_communication: bool = False
    requires_attitude_maneuver: bool = False
    min_fuel_pct: float = Field(5.0, ge=0)
    max_temperature_c: float = Field(50.0)


class ConstraintCheck(BaseModel):
    constraint: str
    status: Literal["SAFE", "MODERATE", "UNSAFE", "UNKNOWN"]
    detail: str


class MissionPlanEvaluation(BaseModel):
    mission_id: str
    spacecraft_id: str
    objective: str
    checks: List[ConstraintCheck]
    overall: Literal["SAFE", "CONDITIONAL", "UNSAFE"]
    recommendation: str
    confidence: float
    evidence: List[str]


# ------------------------------------------------ space situational awareness
class SpaceObject(BaseModel):
    object_id: str
    name: str
    classification: Literal["DEBRIS", "ACTIVE_SATELLITE", "ROCKET_BODY", "UNKNOWN"]
    altitude_km: float
    inclination_deg: float


class ConjunctionEvent(BaseModel):
    id: str
    mission_id: str
    spacecraft_id: str
    object_id: str
    object_name: str
    closest_approach_km: float
    time_to_closest_approach_hours: float
    relative_velocity_km_s: float
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    data_source: Literal["SIMULATED"] = "SIMULATED"


# ------------------------------------------------------------ model evaluation
class DetectorMetrics(BaseModel):
    detector: str
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    detection_latency_points: Optional[float] = None
    n_eval_points: int
    n_true_anomalies: int


class EvaluationReport(BaseModel):
    scenario: str
    generated_at: datetime
    results: List[DetectorMetrics]
    note: str
