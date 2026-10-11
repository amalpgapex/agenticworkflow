"""Executor agent runner."""

from __future__ import annotations

import json
from typing import Any

from wf.agents.factory import build_agent, usage_limits
from wf.agents.trace import extract_tool_trace
from wf.config import get_settings
from wf.schemas.registry import get_schema


def build_executor_prompt(
    instructions: str,
    step_input: dict[str, Any],
    *,
    previous_output: dict[str, Any] | None = None,
    failed_checks: list[dict[str, Any]] | None = None,
    evaluator_feedback: str | None = None,
    human_feedback: str | None = None,
) -> str:
    """Assemble the executor user prompt in the documented order."""
    parts = [instructions, "Input JSON:", json.dumps(step_input, default=str)]
    if previous_output is not None:
        parts.extend(["Previous output:", json.dumps(previous_output, default=str)])
    if failed_checks:
        parts.extend(["Failed checks:", json.dumps(failed_checks, default=str)])
    if evaluator_feedback:
        parts.extend(["Evaluator feedback:", evaluator_feedback])
    if human_feedback:
        parts.extend(["Human feedback:", human_feedback])
    return "\n\n".join(parts)


async def run_executor(
    *,
    model_id: str,
    instructions: str,
    output_schema: str,
    tools: list[str],
    step_input: dict[str, Any],
    previous_output: dict[str, Any] | None = None,
    failed_checks: list[dict[str, Any]] | None = None,
    evaluator_feedback: str | None = None,
    human_feedback: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, int]]:
    """Run the executor and return data, tool trace, and usage."""
    get_settings()
    schema = get_schema(output_schema)
    if schema is None:
        raise ValueError(f"unknown schema {output_schema}")
    agent = build_agent(
        model_id=model_id,
        instructions="You are the executor. Produce output that matches the schema.",
        output_schema=output_schema,
        tools=tools,
    )
    prompt = build_executor_prompt(
        instructions,
        step_input,
        previous_output=previous_output,
        failed_checks=failed_checks,
        evaluator_feedback=evaluator_feedback,
        human_feedback=human_feedback,
    )
    result = await agent.run(prompt, usage_limits=usage_limits())
    output = result.output
    data = output.model_dump(mode="json") if hasattr(output, "model_dump") else dict(output)
    messages = result.all_messages() if hasattr(result, "all_messages") else []
    usage = _usage_dict(result)
    return data, extract_tool_trace(messages), usage


def _usage_dict(result: Any) -> dict[str, int]:
    usage = getattr(result, "usage", None)
    if callable(usage):
        usage = usage()
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
    }
