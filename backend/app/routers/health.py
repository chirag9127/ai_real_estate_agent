from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "llm_provider": settings.llm_provider,
    }
