"""Evaluator agent: judges only, never edits."""

from __future__ import annotations

import json
from typing import Any

from wf.agents.factory import build_agent, usage_limits
from wf.schemas.core import EvaluationVerdict


def build_evaluator_prompt(
    *,
    objective: str,
    rubric: list[str],
    candidate: dict[str, Any],
    check_results: list[dict[str, Any]],
) -> str:
    """Build the evaluator prompt. Instruct it to judge, not rewrite."""
    return "\n\n".join(
        [
            "Judge the candidate against the objective and rubric.",
            "Do not rewrite or edit the candidate.",
            "verdict is pass only if every rubric item is met AND every deterministic check passed.",
            f"Objective: {objective}",
            "Rubric:",
            json.dumps(rubric),
            "Deterministic check results:",
            json.dumps(check_results, default=str),
            "Candidate output:",
            json.dumps(candidate, default=str),
        ]
    )


def enforce_check_gate(verdict: EvaluationVerdict, check_results: list[dict[str, Any]]) -> EvaluationVerdict:
    """Force fail when any deterministic check failed (FR-23, AGENTS M3)."""
    failed = [c for c in check_results if not c.get("passed", False)]
    if failed and verdict.verdict == "pass":
        names = [str(c.get("name")) for c in failed]
        return EvaluationVerdict(
            verdict="fail",
            score=min(verdict.score, 0.49),
            unmet_criteria=list(dict.fromkeys([*verdict.unmet_criteria, *names])),
            feedback=verdict.feedback or f"Deterministic checks failed: {names}",
        )
    return verdict


async def run_evaluator(
    *,
    model_id: str,
    objective: str,
    rubric: list[str],
    candidate: dict[str, Any],
    check_results: list[dict[str, Any]],
) -> tuple[EvaluationVerdict, dict[str, int]]:
    """Run the evaluator with no tools."""
    agent = build_agent(
        model_id=model_id,
        instructions="You are the evaluator. Judge only. Never edit the candidate.",
        output_schema=None,
        tools=[],
        output_type=EvaluationVerdict,
    )
    prompt = build_evaluator_prompt(
        objective=objective,
        rubric=rubric,
        candidate=candidate,
        check_results=check_results,
    )
    result = await agent.run(prompt, usage_limits=usage_limits())
    raw = result.output
    verdict = raw if isinstance(raw, EvaluationVerdict) else EvaluationVerdict.model_validate(raw)
    usage = getattr(result, "usage", None)
    if callable(usage):
        usage = usage()
    usage_dict = {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
    }
    return enforce_check_gate(verdict, check_results), usage_dict
