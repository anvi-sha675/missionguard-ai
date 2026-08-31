import os
from pathlib import Path
from dotenv import load_dotenv

_env_file = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_file, override=False)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "missionguard")

# "watsonx" (real Granite call) or "template" (offline, deterministic, demo-safe)
EXPLANATION_PROVIDER = os.getenv("EXPLANATION_PROVIDER", "template")

GRANITE_API_KEY = os.getenv("GRANITE_API_KEY", "")
GRANITE_PROJECT_ID = os.getenv("GRANITE_PROJECT_ID", "")
GRANITE_URL = os.getenv("GRANITE_URL", "https://us-south.ml.cloud.ibm.com")
GRANITE_MODEL_ID = os.getenv("GRANITE_MODEL_ID", "ibm/granite-3-8b-instruct")
GRANITE_TIMEOUT_SECONDS = int(os.getenv("GRANITE_TIMEOUT_SECONDS", "20"))

# Anomaly score bands -- PROTOTYPE THRESHOLDS ONLY, not certification standards
ANOMALY_BANDS = {
    "NORMAL": (0, 30),
    "LOW": (31, 60),
    "WARNING": (61, 80),
    "CRITICAL": (81, 100),
}

# Subsystem criticality weights used by the risk engine (0-1)
SUBSYSTEM_CRITICALITY = {
    "power": 1.0,
    "thermal": 0.8,
    "communication": 0.7,
    "navigation": 0.9,
    "propulsion": 0.85,
    "onboard_compute": 0.6,
}

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
CORS_ALLOW_ALL = os.getenv("CORS_ALLOW_ALL", "false").lower() == "true"

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
