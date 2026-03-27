"""Observatory API — FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from holus.api.routes import (
    agents,
    alerts,
    config,
    content,
    evaluations,
    health,
    improvement,
    ingest,
    knowledge,
    results,
    telegram_gate,
    trajectory,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Log resolved data source paths on startup."""
    from holus.api.routes.evaluations import EVAL_HISTORY_PATH
    from holus.api.routes.health import (
        AGENTS_YAML,
        CONTENT_QUEUE_DIR,
        GUARDRAILS_YAML,
    )
    from holus.api.routes.knowledge import KNOWLEDGE_DIR
    from holus.api.routes.trajectory import TRAJECTORY_PATH

    logger.info("Observatory API starting up")
    logger.info("  trajectory.jsonl:    %s (exists=%s)", TRAJECTORY_PATH, TRAJECTORY_PATH.exists())
    logger.info(
        "  eval_history.jsonl:  %s (exists=%s)", EVAL_HISTORY_PATH, EVAL_HISTORY_PATH.exists()
    )
    logger.info("  AGENTS.yaml:         %s (exists=%s)", AGENTS_YAML, AGENTS_YAML.exists())
    logger.info(
        "  content-queue/:      %s (exists=%s)", CONTENT_QUEUE_DIR, CONTENT_QUEUE_DIR.exists()
    )
    logger.info("  knowledge/current/:  %s (exists=%s)", KNOWLEDGE_DIR, KNOWLEDGE_DIR.exists())
    logger.info("  guardrails.yaml:     %s (exists=%s)", GUARDRAILS_YAML, GUARDRAILS_YAML.exists())

    yield

    logger.info("Observatory API shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Holus Observatory API",
        description="Read-only API serving Holus system data for the Observatory dashboard.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS — allow both Next.js (3000) and SvelteKit/Vite (5173) dev servers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_methods=["GET", "PATCH", "PUT", "POST", "DELETE"],
        allow_headers=["*"],
    )

    # Mount all route groups under /api/v1
    prefix = "/api/v1"
    app.include_router(agents.router, prefix=prefix)
    app.include_router(alerts.router, prefix=prefix)
    app.include_router(config.router, prefix=prefix)
    app.include_router(trajectory.router, prefix=prefix)
    app.include_router(content.router, prefix=prefix)
    app.include_router(evaluations.router, prefix=prefix)
    app.include_router(knowledge.router, prefix=prefix)
    app.include_router(health.router, prefix=prefix)
    app.include_router(results.router, prefix=prefix)
    app.include_router(improvement.router, prefix=prefix)
    app.include_router(telegram_gate.router)  # prefix already set in router
    app.include_router(ingest.router)  # prefix already set in router

    return app


app = create_app()
