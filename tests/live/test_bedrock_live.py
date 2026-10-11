"""Live Bedrock smoke (M3). Excluded unless `-m live`."""

from __future__ import annotations

import pytest

from wf.config import get_settings


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_bedrock_executor_smoke() -> None:
    """One live Bedrock call succeeds when credentials and model access exist."""
    from pydantic_ai import Agent

    settings = get_settings()
    agent = Agent(settings.wf_executor_model, instructions="Reply with the word pong only.")
    result = await agent.run("ping")
    assert result.output
