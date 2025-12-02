"""Health check endpoint."""

import logging

from fastapi import APIRouter

from app.config import get_claude_path, get_claude_version_str
from app.models import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    Returns service status and Claude Code information.
    """
    logger.debug("Health check requested")

    return HealthResponse(
        status="ok",
        claude_path=get_claude_path(),
        claude_version=get_claude_version_str(),
    )
