"""Structured JSON logging. Never log prompts, outputs, tokens, or email bodies."""

from __future__ import annotations

from typing import Any

import structlog


def configure_logging() -> None:
    """Configure structlog for JSON lines."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),
        cache_logger_on_first_use=True,
    )


def bind_run(*, run_id: str, step_id: str = "", attempt: int = 0) -> None:
    """Bind run identifiers onto every subsequent log line."""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(run_id=run_id, step_id=step_id, attempt=attempt)


def get_logger() -> Any:
    """Return the package logger."""
    return structlog.get_logger("wf")
