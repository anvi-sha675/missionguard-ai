from fastapi import APIRouter
from app.api.deps import provider
from app.core import config

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {
        "status": "ok",
        "explanation_provider": provider.name,
        # True when both secrets are present in the environment; does NOT
        # expose the key values -- only their presence is reported.
        "granite_configured": bool(config.GRANITE_API_KEY and config.GRANITE_PROJECT_ID),
    }
