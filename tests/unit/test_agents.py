"""M3: TestModel / FunctionModel agent factory tests."""

from __future__ import annotations

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from wf.agents.evaluator import run_evaluator
from wf.agents.executor import run_executor
from wf.agents.factory import build_agent, mcp_toolset, usage_limits
from wf.agents.resolver import run_resolver
from wf.schemas.core import EvaluationVerdict


@pytest.mark.asyncio
async def test_executor_testmodel_matches_schema() -> None:
    data, trace, usage = await run_executor(
        model_id="test",
        instructions="Return a resolved capital.",
        output_schema="ResolvedLocation@1",
        tools=[],
        step_input={"country": "PT"},
    )
    assert data["name"]
    assert "latitude" in data
    assert isinstance(trace, list)
    assert "input_tokens" in usage


@pytest.mark.asyncio
async def test_resolver_testmodel_matches_schema() -> None:
    data, _trace, _usage = await run_resolver(
        model_id="test",
        instructions="Pick the capital.",
        output_schema="ResolvedLocation@1",
        tools=[],
    )
    assert data["country_code"]
    assert data["feature_code"]


@pytest.mark.asyncio
async def test_evaluator_testmodel_returns_verdict() -> None:
    verdict, usage = await run_evaluator(
        model_id="test",
        objective="Judge the candidate.",
        rubric=["is complete"],
        candidate={"name": "Lisbon"},
        check_results=[{"name": "ok", "passed": True, "detail": ""}],
    )
    assert verdict.verdict in {"pass", "fail"}
    assert 0.0 <= verdict.score <= 1.0
    assert "output_tokens" in usage


@pytest.mark.asyncio
async def test_evaluator_functionmodel_cannot_pass_failed_checks() -> None:
    def always_pass(_messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[TextPart(content='{"verdict":"pass","score":0.99,"unmet_criteria":[],"feedback":"looks fine"}')]
        )

    agent = build_agent(
        model_id="test",
        instructions="Judge only.",
        output_schema=None,
        tools=[],
        output_type=EvaluationVerdict,
    )
    with agent.override(model=FunctionModel(always_pass)):
        result = await agent.run("judge")
    raw = result.output
    verdict = raw if isinstance(raw, EvaluationVerdict) else EvaluationVerdict.model_validate(raw)
    from wf.agents.evaluator import enforce_check_gate

    gated = enforce_check_gate(verdict, [{"name": "forecast_matches_source", "passed": False, "detail": "mismatch"}])
    assert gated.verdict == "fail"
    assert "forecast_matches_source" in gated.unmet_criteria


def test_evaluator_has_no_tools() -> None:
    agent = build_agent(
        model_id="test",
        instructions="Judge only.",
        output_schema=None,
        tools=[],
        output_type=EvaluationVerdict,
    )
    user_toolsets = getattr(agent, "_user_toolsets", [])
    assert list(user_toolsets) == []


def test_mcp_allowlist_filter() -> None:
    toolset = mcp_toolset(["geocode_location"])
    assert toolset is not None
    assert type(toolset).__name__ == "FilteredToolset"
    assert mcp_toolset([]) is None


def test_usage_limits_from_settings() -> None:
    limits = usage_limits()
    assert limits.request_limit == 20
    assert limits.total_tokens_limit == 20000


def test_testmodel_override_roundtrip() -> None:
    agent = build_agent(
        model_id="test",
        instructions="Return a location.",
        output_schema="ResolvedLocation@1",
        tools=[],
    )
    with agent.override(model=TestModel()):
        assert agent.model is not None
