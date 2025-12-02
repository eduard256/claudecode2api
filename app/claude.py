"""Claude Code subprocess runner."""

import asyncio
import json
import logging
import os
from typing import AsyncGenerator

from app.config import get_claude_path, get_settings
from app.models import ChatRequest

logger = logging.getLogger(__name__)


def build_command(request: ChatRequest) -> list[str]:
    """
    Build Claude Code CLI command from request parameters.
    Always includes: --dangerously-skip-permissions, --verbose, --output-format stream-json
    """
    cmd = [get_claude_path()]

    # Always required flags
    cmd.extend(["--dangerously-skip-permissions"])
    cmd.extend(["--verbose"])
    cmd.extend(["--output-format", "stream-json"])

    # Model
    if request.model:
        cmd.extend(["--model", request.model])

    # Session resume
    if request.session_id:
        cmd.extend(["--resume", request.session_id])

    # Fork session
    if request.fork_session:
        cmd.append("--fork-session")

    # Fallback model
    if request.fallback_model:
        cmd.extend(["--fallback-model", request.fallback_model])

    # System prompts
    if request.system_prompt:
        cmd.extend(["--system-prompt", request.system_prompt])
    if request.append_system_prompt:
        cmd.extend(["--append-system-prompt", request.append_system_prompt])

    # Tools configuration
    if request.tools is not None:
        cmd.extend(["--tools", ",".join(request.tools)])
    if request.allowed_tools:
        cmd.extend(["--allowed-tools"] + request.allowed_tools)
    if request.disallowed_tools:
        cmd.extend(["--disallowed-tools"] + request.disallowed_tools)

    # Permission mode
    if request.permission_mode:
        cmd.extend(["--permission-mode", request.permission_mode])

    # MCP configuration
    if request.mcp_config:
        cmd.extend(["--mcp-config"] + request.mcp_config)
    if request.strict_mcp_config:
        cmd.append("--strict-mcp-config")

    # Settings
    if request.settings:
        cmd.extend(["--settings", request.settings])

    # Additional directories
    if request.add_dir:
        cmd.extend(["--add-dir"] + request.add_dir)

    # Debug options
    if request.debug is not None:
        if isinstance(request.debug, bool):
            if request.debug:
                cmd.append("--debug")
        else:
            cmd.extend(["--debug", request.debug])

    if request.verbose:
        # Already added above, but keeping for explicit request
        pass

    # JSON Schema
    if request.json_schema:
        cmd.extend(["--json-schema", json.dumps(request.json_schema)])

    # Agents
    if request.agents:
        cmd.extend(["--agents", json.dumps(request.agents)])

    # Plugin directories
    if request.plugin_dir:
        cmd.extend(["--plugin-dir"] + request.plugin_dir)

    # Prompt (must be last with -p flag)
    cmd.extend(["-p", request.prompt])

    return cmd


async def run_claude(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Run Claude Code subprocess and yield output lines.
    Yields raw JSON lines from Claude Code stdout.
    """
    settings = get_settings()
    cmd = build_command(request)

    # Log command (hide prompt for brevity)
    cmd_display = cmd.copy()
    prompt_idx = cmd_display.index("-p")
    cmd_display[prompt_idx + 1] = f"<prompt: {len(request.prompt)} chars>"
    logger.info(f"Running Claude: {' '.join(cmd_display)}")
    logger.debug(f"Working directory: {request.cwd}")

    # Start subprocess with large buffer
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=request.cwd,
        env=os.environ.copy(),
        limit=settings.buffer_limit,
    )

    logger.info(f"Claude subprocess started with PID: {process.pid}")

    # Read stdout line by line
    try:
        while True:
            line = await process.stdout.readline()
            if not line:
                break

            decoded = line.decode("utf-8", errors="ignore").rstrip()
            if decoded:
                logger.debug(f"Claude output: {decoded[:200]}{'...' if len(decoded) > 200 else ''}")
                yield decoded

    except asyncio.CancelledError:
        logger.warning(f"Claude subprocess cancelled, terminating PID: {process.pid}")
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning(f"Force killing PID: {process.pid}")
            process.kill()
        raise

    except Exception as e:
        logger.error(f"Error reading Claude output: {e}")
        raise

    finally:
        # Wait for process to complete
        return_code = await process.wait()
        logger.info(f"Claude subprocess finished with code: {return_code}")

        # Log stderr if any
        if process.stderr:
            stderr = await process.stderr.read()
            if stderr:
                stderr_text = stderr.decode("utf-8", errors="ignore")
                logger.warning(f"Claude stderr: {stderr_text[:500]}")
