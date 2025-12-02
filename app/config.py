"""Configuration module with Claude Code auto-detection."""

import logging
import subprocess
import shutil
import sys
from functools import lru_cache

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server
    host: str = "0.0.0.0"
    port: int = 9876

    # Authentication
    auth_user: str
    auth_password: str

    # Claude Code path (auto-detected if not set)
    claude_path: str | None = None

    # Logging
    log_level: str = "DEBUG"

    # Buffer limit for subprocess (100MB)
    buffer_limit: int = 100 * 1024 * 1024

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def detect_claude_path() -> str:
    """
    Detect Claude Code CLI path using 'which claude'.
    Returns the path or exits if not found.
    """
    # First check if path is configured
    settings = get_settings()
    if settings.claude_path:
        logger.info(f"Using configured Claude path: {settings.claude_path}")
        return settings.claude_path

    # Try to find claude in PATH
    claude_path = shutil.which("claude")
    if claude_path:
        logger.info(f"Auto-detected Claude path: {claude_path}")
        return claude_path

    # Claude not found
    logger.error("Claude Code CLI not found in PATH!")
    logger.error("Please install Claude Code or set CLAUDE_PATH in .env")
    sys.exit(1)


def get_claude_version(claude_path: str) -> str:
    """
    Get Claude Code version.
    Returns version string or 'unknown' on error.
    """
    try:
        result = subprocess.run(
            [claude_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        version = result.stdout.strip()
        logger.info(f"Claude Code version: {version}")
        return version
    except Exception as e:
        logger.warning(f"Failed to get Claude version: {e}")
        return "unknown"


# Global variables set at startup
_claude_info: dict = {"path": "", "version": ""}


def init_claude() -> tuple[str, str]:
    """
    Initialize Claude Code path and version.
    Called at application startup.
    Returns (path, version) tuple.
    """
    _claude_info["path"] = detect_claude_path()
    _claude_info["version"] = get_claude_version(_claude_info["path"])

    logger.info(f"Claude Code initialized: {_claude_info['path']} ({_claude_info['version']})")

    return _claude_info["path"], _claude_info["version"]


def get_claude_path() -> str:
    """Get Claude Code path."""
    return _claude_info["path"]


def get_claude_version_str() -> str:
    """Get Claude Code version."""
    return _claude_info["version"]
