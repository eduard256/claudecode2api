"""Chat endpoint with SSE streaming."""

import json
import logging
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.auth import verify_credentials
from app.models import ChatRequest, CancelResponse, ErrorResponse
from app.process_manager import process_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


async def generate_sse(
    stream: AsyncGenerator[str, None],
    process_id: str,
) -> AsyncGenerator[dict, None]:
    """
    Generate SSE events from Claude Code stream.
    Yields raw JSON lines as 'message' events.
    """
    try:
        async for line in stream:
            yield {
                "event": "message",
                "data": line,
            }

        # Send done event
        yield {
            "event": "done",
            "data": json.dumps({"process_id": process_id}),
        }

    except Exception as e:
        logger.error(f"Error in SSE stream: {e}")
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e)}),
        }


@router.post("/chat")
async def chat(
    request: ChatRequest,
    username: str = Depends(verify_credentials),
):
    """
    Start Claude Code with SSE streaming.

    - **prompt**: User prompt message (required)
    - **cwd**: Working directory for Claude Code (required)
    - **model**: Model to use (default: sonnet)
    - **session_id**: Session ID to resume conversation

    Returns SSE stream with raw JSON from Claude Code.
    Header X-Process-ID contains the process ID for cancellation.
    """
    logger.info(f"Chat request from user {username}")
    logger.debug(f"Request: cwd={request.cwd}, model={request.model}, session_id={request.session_id}")
    logger.debug(f"Prompt length: {len(request.prompt)} chars")

    # Validate cwd
    cwd_path = Path(request.cwd)

    if not cwd_path.exists():
        logger.error(f"Directory does not exist: {request.cwd}")
        raise HTTPException(
            status_code=400,
            detail=f"Directory does not exist: {request.cwd}",
        )

    if not cwd_path.is_dir():
        logger.error(f"Path is not a directory: {request.cwd}")
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a directory: {request.cwd}",
        )

    # Start process
    process_id, stream = await process_manager.start_process(request)

    logger.info(f"Started process {process_id} for user {username}")

    # Return SSE response
    return EventSourceResponse(
        generate_sse(stream, process_id),
        headers={
            "X-Process-ID": process_id,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx/traefik
        },
    )


@router.delete(
    "/chat/{process_id}",
    response_model=CancelResponse,
    responses={404: {"model": ErrorResponse}},
)
async def cancel_chat(
    process_id: str,
    username: str = Depends(verify_credentials),
):
    """
    Cancel a running Claude Code process.

    - **process_id**: Process ID from X-Process-ID header
    """
    logger.info(f"Cancel request from user {username} for process {process_id}")

    success = await process_manager.kill_process(process_id)

    if not success:
        logger.warning(f"Process not found: {process_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Process not found: {process_id}",
        )

    logger.info(f"Process {process_id} cancelled successfully")

    return CancelResponse(
        status="cancelled",
        process_id=process_id,
    )
