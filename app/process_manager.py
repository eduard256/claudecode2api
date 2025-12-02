"""Process manager for tracking and controlling Claude Code subprocesses."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncGenerator

from app.claude import run_claude
from app.models import ChatRequest, ProcessInfo

logger = logging.getLogger(__name__)


@dataclass
class ManagedProcess:
    """Internal representation of a managed process."""

    process_id: str
    task: asyncio.Task
    cwd: str
    model: str | None
    started_at: datetime
    session_id: str | None = None
    _cancelled: bool = field(default=False, repr=False)


class ProcessManager:
    """
    Manager for Claude Code subprocess lifecycle.
    Thread-safe for use with asyncio.
    """

    def __init__(self):
        self._processes: dict[str, ManagedProcess] = {}
        self._lock = asyncio.Lock()

    async def start_process(
        self,
        request: ChatRequest,
    ) -> tuple[str, AsyncGenerator[str, None]]:
        """
        Start a new Claude Code process.
        Returns (process_id, stream_generator).
        """
        process_id = str(uuid.uuid4())

        logger.info(f"Starting process {process_id} in {request.cwd}")

        # Create the stream generator
        async def wrapped_stream() -> AsyncGenerator[str, None]:
            try:
                async for line in run_claude(request):
                    # Update session_id from first system message if available
                    if '"type":"system"' in line and '"session_id"' in line:
                        try:
                            import json
                            data = json.loads(line)
                            if data.get("session_id"):
                                async with self._lock:
                                    if process_id in self._processes:
                                        self._processes[process_id].session_id = data["session_id"]
                                        logger.debug(f"Process {process_id} session_id: {data['session_id']}")
                        except:
                            pass
                    yield line
            finally:
                # Cleanup when stream ends
                await self._cleanup_process(process_id)

        # Create task placeholder (will be set by caller)
        managed = ManagedProcess(
            process_id=process_id,
            task=None,  # type: ignore
            cwd=request.cwd,
            model=request.model,
            started_at=datetime.utcnow(),
            session_id=request.session_id,
        )

        async with self._lock:
            self._processes[process_id] = managed

        logger.info(f"Process {process_id} registered, total active: {len(self._processes)}")

        return process_id, wrapped_stream()

    async def kill_process(self, process_id: str) -> bool:
        """
        Kill a process by its ID.
        Returns True if process was found and killed, False otherwise.
        """
        async with self._lock:
            managed = self._processes.get(process_id)
            if not managed:
                logger.warning(f"Process {process_id} not found")
                return False

            if managed._cancelled:
                logger.debug(f"Process {process_id} already cancelled")
                return True

            managed._cancelled = True

        logger.info(f"Cancelling process {process_id}")

        if managed.task and not managed.task.done():
            managed.task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(managed.task), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        await self._cleanup_process(process_id)
        return True

    async def _cleanup_process(self, process_id: str) -> None:
        """Remove process from tracking."""
        async with self._lock:
            if process_id in self._processes:
                del self._processes[process_id]
                logger.info(f"Process {process_id} cleaned up, remaining: {len(self._processes)}")

    def get_active_processes(self) -> list[ProcessInfo]:
        """Get list of all active processes."""
        processes = []
        for managed in self._processes.values():
            processes.append(
                ProcessInfo(
                    process_id=managed.process_id,
                    cwd=managed.cwd,
                    model=managed.model,
                    started_at=managed.started_at,
                    session_id=managed.session_id,
                )
            )
        return processes

    @property
    def active_count(self) -> int:
        """Get count of active processes."""
        return len(self._processes)


# Global process manager instance
process_manager = ProcessManager()
