import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, telemetry, anomalies, copilot, reports, spacecraft, mission_planner, ssa, evaluation
from app.core.config import CORS_ORIGINS, CORS_ALLOW_ALL

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("missionguard")

app = FastAPI(
    title="MissionGuard AI",
    description=(
        "AI-powered mission operations and decision-support platform: spacecraft health "
        "monitoring, predictive analytics, mission risk, mission planning, space situational "
        "awareness, and an evidence-grounded AI mission copilot. "
        "Prototype / hackathon build -- not flight-certified, not for autonomous spacecraft control."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if CORS_ALLOW_ALL else CORS_ORIGINS,
    allow_credentials=not CORS_ALLOW_ALL,  # wildcard + credentials is invalid per the CORS spec anyway
    allow_methods=["*"],
    allow_headers=["*"],
)

if CORS_ALLOW_ALL:
    logger.warning("CORS_ALLOW_ALL=true -- wildcard CORS is active. Do not use this in production.")


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 1)
    logger.info(f"request_id={request_id} {request.method} {request.url.path} "
                f"status={response.status_code} duration_ms={duration_ms}")
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(health.router, prefix="/api")
app.include_router(spacecraft.router, prefix="/api")
app.include_router(telemetry.router, prefix="/api")
app.include_router(anomalies.router, prefix="/api")
app.include_router(copilot.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(mission_planner.router, prefix="/api")
app.include_router(ssa.router, prefix="/api")
app.include_router(evaluation.router, prefix="/api")


@app.get("/")
def root():
    return {
        "product": "MissionGuard AI",
        "status": "operational",
        "note": "Decision-support prototype. Not flight-certified.",
    }


@app.get("/health")
def root_health():
    """Unprefixed alias of /api/health for load balancer / deployment health
    checks that expect a plain /health path."""
    return health.health()
