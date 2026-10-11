"""Envelope and HITL/eval schemas. `system` is a real field name."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ForbidModel(BaseModel):
    """Reject unknown keys."""

    model_config = ConfigDict(extra="forbid")


class CheckResult(ForbidModel):
    """One deterministic check outcome."""

    name: str
    passed: bool
    detail: str = ""


class EvaluationVerdict(ForbidModel):
    """Evaluator output (`EvaluationVerdict@1`)."""

    verdict: Literal["pass", "fail"]
    score: float
    unmet_criteria: list[str] = Field(default_factory=list)
    feedback: str = ""


class EvalResult(ForbidModel):
    """Engine-owned evaluation metadata."""

    verdict: Literal["pass", "fail", "escalated"] | None = None
    score: float = 0.0
    iterations: int = 0
    unmet_criteria: list[str] = Field(default_factory=list)
    checks: list[CheckResult] = Field(default_factory=list)


class HumanInfo(ForbidModel):
    """Engine-owned human-gate metadata."""

    required: bool = False
    decision: Literal["proceed", "proceed_modified", "redo", "stop"] | None = None
    reviewer: str = ""
    decided_at: datetime | None = None
    feedback: str = ""
    modified: bool = False
    check_warnings: list[CheckResult] = Field(default_factory=list)
    diff: dict[str, Any] | None = None


class ModelInfo(ForbidModel):
    """Model IDs used for a step."""

    executor: str = ""
    evaluator: str = ""


class UsageInfo(ForbidModel):
    """Token usage accumulated on a step."""

    input_tokens: int = 0
    output_tokens: int = 0


class SystemMeta(ForbidModel):
    """Engine-owned envelope header. Field name must be `system`."""

    run_id: str
    workflow_id: str
    definition_version: str
    step_id: str
    step_type: str = "agent"
    schema_name: str = Field(default="", alias="schema")
    status: Literal["completed", "skipped", "stopped", "failed"]
    attempt: int = 1
    eval: EvalResult = Field(default_factory=EvalResult)
    human: HumanInfo = Field(default_factory=HumanInfo)
    model: ModelInfo = Field(default_factory=ModelInfo)
    usage: UsageInfo = Field(default_factory=UsageInfo)
    artifact_uri: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Envelope(ForbidModel):
    """Persisted step result. Only the engine writes `system`."""

    system: SystemMeta
    data: dict[str, Any] = Field(default_factory=dict)


class HumanDecision(ForbidModel):
    """Temporal signal payload (`HumanDecision@1`)."""

    action: Literal["proceed", "proceed_modified", "redo", "stop"]
    reviewer: str
    attempt: int
    nonce: str
    feedback: str | None = None
    modified_data: dict[str, Any] | None = None
