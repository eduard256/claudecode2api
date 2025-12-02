"""FastAPI application entry point."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings, init_claude
from app.routes import chat, health, processes

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Initializes Claude Code on startup.
    """
    logger.info("Starting Claude Code API Gateway...")

    # Initialize Claude Code
    try:
        claude_path, claude_version = init_claude()
        logger.info(f"Claude Code ready: {claude_path} ({claude_version})")
    except SystemExit:
        logger.error("Failed to initialize Claude Code, exiting")
        raise

    settings = get_settings()
    logger.info(f"Server configured: {settings.host}:{settings.port}")
    logger.info(f"Log level: {settings.log_level}")

    yield

    logger.info("Shutting down Claude Code API Gateway...")


# Create FastAPI app
app = FastAPI(
    title="Claude Code API Gateway",
    description="API gateway for Claude Code CLI with SSE streaming",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(processes.router)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs."""
    return {
        "message": "Claude Code API Gateway",
        "docs": "/docs",
        "health": "/health",
    }
