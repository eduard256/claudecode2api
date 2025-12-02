"""Pydantic models for request/response validation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for POST /chat endpoint."""

    # Required fields
    prompt: str = Field(..., description="User prompt message")
    cwd: str = Field(..., description="Working directory for Claude Code")

    # Model configuration
    model: str | None = Field(default="sonnet", description="Model to use (sonnet, opus, haiku, or full name)")
    fallback_model: str | None = Field(default=None, description="Fallback model when primary is overloaded")

    # Session management
    session_id: str | None = Field(default=None, description="Session ID to resume conversation")
    fork_session: bool | None = Field(default=None, description="Create new session when resuming")

    # System prompts
    system_prompt: str | None = Field(default=None, description="Replace default system prompt")
    append_system_prompt: str | None = Field(default=None, description="Append to default system prompt")

    # Tools configuration
    tools: list[str] | None = Field(default=None, description="List of tools to enable")
    allowed_tools: list[str] | None = Field(default=None, description="Whitelist of allowed tools")
    disallowed_tools: list[str] | None = Field(default=None, description="Blacklist of tools")

    # Permission mode
    permission_mode: str | None = Field(default=None, description="Permission mode (default, acceptEdits, bypassPermissions, dontAsk, plan)")

    # MCP configuration
    mcp_config: list[str] | None = Field(default=None, description="MCP config files or JSON strings")
    strict_mcp_config: bool | None = Field(default=None, description="Only use MCP servers from --mcp-config")

    # Additional settings
    settings: str | None = Field(default=None, description="Path to settings JSON or JSON string")
    add_dir: list[str] | None = Field(default=None, description="Additional directories to allow access")

    # Debug options
    debug: str | bool | None = Field(default=None, description="Enable debug mode (true, false, or category filter)")
    verbose: bool | None = Field(default=None, description="Enable verbose mode")

    # Structured output
    json_schema: dict[str, Any] | None = Field(default=None, description="JSON Schema for structured output")

    # Advanced
    agents: dict[str, Any] | None = Field(default=None, description="Custom agents definition")
    plugin_dir: list[str] | None = Field(default=None, description="Plugin directories")


class HealthResponse(BaseModel):
    """Response model for GET /health endpoint."""

    status: str
    claude_path: str
    claude_version: str


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str


class ProcessInfo(BaseModel):
    """Information about an active process."""

    process_id: str
    cwd: str
    model: str | None
    started_at: datetime
    session_id: str | None = None


class ProcessListResponse(BaseModel):
    """Response model for GET /processes endpoint."""

    processes: list[ProcessInfo]
    count: int


class CancelResponse(BaseModel):
    """Response model for DELETE /chat/{process_id}."""

    status: str
    process_id: str
