"""Processes list endpoint."""

import logging

from fastapi import APIRouter, Depends

from app.auth import verify_credentials
from app.models import ProcessListResponse
from app.process_manager import process_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["processes"])


@router.get("/processes", response_model=ProcessListResponse)
async def list_processes(
    username: str = Depends(verify_credentials),
) -> ProcessListResponse:
    """
    Get list of active Claude Code processes.
    Requires authentication.
    """
    logger.info(f"User {username} requested process list")

    processes = process_manager.get_active_processes()

    logger.debug(f"Returning {len(processes)} active processes")

    return ProcessListResponse(
        processes=processes,
        count=len(processes),
    )
