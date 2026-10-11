"""Evaluator cannot pass when checks failed."""

from __future__ import annotations

from wf.agents.evaluator import enforce_check_gate
from wf.schemas.core import EvaluationVerdict


def test_enforce_check_gate_overrides_pass() -> None:
    verdict = EvaluationVerdict(verdict="pass", score=0.9, unmet_criteria=[], feedback="ok")
    gated = enforce_check_gate(
        verdict,
        [{"name": "forecast_matches_source", "passed": False, "detail": "x"}],
    )
    assert gated.verdict == "fail"
    assert "forecast_matches_source" in gated.unmet_criteria
