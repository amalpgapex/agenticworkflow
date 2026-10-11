"""Build Pydantic AI agents from step config."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from wf.config import Settings, get_settings
from wf.schemas.registry import get_schema


def resolve_model_id(configured: str | None, fallback: str) -> str:
    """Return the step override or the configured default."""
    return configured or fallback


def usage_limits(settings: Settings | None = None) -> Any:
    """Build Pydantic AI usage limits from config (FR-26)."""
    settings = settings or get_settings()
    try:
        from pydantic_ai.settings import UsageLimits
    except ImportError:  # pragma: no cover - API rename
        from pydantic_ai.usage import UsageLimits  # type: ignore[attr-defined]
    return UsageLimits(
        request_limit=settings.wf_agent_max_requests,
        total_tokens_limit=settings.wf_agent_max_tokens,
    )


def mcp_toolset(allowlist: Sequence[str]) -> Any | None:
    """Return a filtered MCP stdio toolset, or None if the allowlist is empty."""
    if not allowlist:
        return None
    allowed = set(allowlist)
    from fastmcp.client.transports import StdioTransport
    from pydantic_ai.mcp import MCPToolset

    env = {key: value for key, value in os.environ.items() if value is not None}
    env["PYTHONUNBUFFERED"] = "1"
    server = MCPToolset(
        StdioTransport(
            command=sys.executable,
            args=["-m", "wf.tools.mcp_weather_server"],
            cwd=str(Path.cwd()),
            env=env,
            keep_alive=False,
        )
    )
    return server.filtered(lambda _ctx, tool: getattr(tool, "name", "") in allowed)


def build_agent(
    *,
    model_id: str,
    instructions: str,
    output_schema: str | None,
    tools: Sequence[str],
    output_type: type[BaseModel] | None = None,
) -> Any:
    """Construct a Pydantic AI Agent (FR-20, FR-21)."""
    from pydantic_ai import Agent

    model_cls = output_type
    if model_cls is None and output_schema:
        model_cls = get_schema(output_schema)
    toolset = mcp_toolset(tools)
    kwargs: dict[str, Any] = {
        "model": model_id,
        "instructions": instructions,
    }
    if model_cls is not None:
        kwargs["output_type"] = model_cls
    if toolset is not None:
        kwargs["toolsets"] = [toolset]
    return Agent(**kwargs)
