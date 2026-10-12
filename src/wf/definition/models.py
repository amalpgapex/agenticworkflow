"""Pydantic models for `apiVersion: wf/v1` definitions."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wf.errors import DefinitionError


class ForbidModel(BaseModel):
    """Base model that rejects unknown keys."""

    model_config = ConfigDict(extra="forbid")


class InputSpec(ForbidModel):
    """A single workflow input declaration."""

    type: Literal["string", "integer", "number", "boolean"]
    required: bool = False
    default: str | int | float | bool | None = None
    min: int | float | None = None
    max: int | float | None = None


class HitlDefaults(ForbidModel):
    """Default human-gate settings."""

    channel: Literal["email"] = "email"
    timeout: str = "72h"
    on_timeout: Literal["stop"] = "stop"

    @field_validator("timeout")
    @classmethod
    def timeout_is_duration(cls, value: str) -> str:
        parse_duration(value)
        return value


class WorkflowDefaults(ForbidModel):
    """Defaults inherited by every step unless overridden."""

    model: str | None = None
    evaluator_model: str | None = None
    max_iterations: int = 3
    hitl: HitlDefaults = Field(default_factory=HitlDefaults)
    on_exhausted: Literal["escalate_to_human", "fail"] = "escalate_to_human"


class WorkflowMeta(ForbidModel):
    """The `workflow:` block."""

    id: str
    version: str
    description: str = ""
    inputs: dict[str, InputSpec]
    defaults: WorkflowDefaults = Field(default_factory=WorkflowDefaults)
    reviewers: list[str] = Field(default_factory=list)


class ResolveConfig(ForbidModel):
    """Prerequisite resolver. Phase 1 supports `mode: agent` only."""

    mode: Literal["agent"]
    instructions: str
    tools: list[str] = Field(default_factory=list)
    output_schema: str
    verify: list[str] = Field(default_factory=list)


class Prerequisite(ForbidModel):
    """A prerequisite that may resolve missing context."""

    id: str
    check: str
    resolve: ResolveConfig
    bind: str


class ExecutorConfig(ForbidModel):
    """Executor agent configuration."""

    instructions: str
    tools: list[str] = Field(default_factory=list)
    output_schema: str


class ActionConfig(ForbidModel):
    """Action step configuration (deterministic, no LLM)."""

    tool: str = Field(description="Single tool to call directly")
    output_schema: str = Field(default="ActionResult@1", description="Schema for result")
    on_error: Literal["fail", "continue"] = Field(
        default="fail", description="Behavior on tool error"
    )


class EvaluatorConfig(ForbidModel):
    """Evaluator configuration."""

    checks: list[str] = Field(default_factory=list)
    named_checks: list[str] = Field(default_factory=list)
    rubric: list[str] = Field(default_factory=list)


class HumanReview(ForbidModel):
    """Per-step human gate."""

    required_when: str


class Step(ForbidModel):
    """One sequential agent or action step."""

    id: str
    type: Literal["agent", "parallel", "action"]
    prerequisites: list[Prerequisite] = Field(default_factory=list)
    run_when: str | None = None
    input: dict[str, str] = Field(default_factory=dict)
    executor: ExecutorConfig | None = None
    evaluator: EvaluatorConfig | None = None
    human_review: HumanReview | None = None
    action: ActionConfig | None = None  # For type: action steps

    @model_validator(mode="after")
    def validate_step_config(self) -> Step:
        """Validate that step has correct config for its type."""
        if self.type == "agent" and self.executor is None:
            raise ValueError("agent steps require an executor")
        if self.type == "action" and self.action is None:
            raise ValueError("action steps require an action config")
        if self.type == "action" and self.executor is not None:
            raise ValueError("action steps should not have an executor config")
        return self


class DeliverConfig(ForbidModel):
    """Final delivery settings."""

    to: Literal["initiator"] = "initiator"
    subject: str
    attach: bool = True
    link: Literal["presigned_s3"] = "presigned_s3"


class OutputConfig(ForbidModel):
    """Output phase configuration."""

    from_step: str
    formats: list[Literal["pdf"]]
    template: str
    deliver: DeliverConfig


class Definition(ForbidModel):
    """A complete workflow definition."""

    api_version: Literal["wf/v1"] = Field(alias="apiVersion")
    workflow: WorkflowMeta
    steps: list[Step]
    output: OutputConfig

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def parse_duration(value: str) -> timedelta:
    """Parse a HITL timeout (`72h`, `30m`, `15s`)."""
    if not value or value[-1] not in {"h", "m", "s"} or not value[:-1].isdigit():
        raise DefinitionError([f"invalid duration '{value}': use Nh, Nm, or Ns"])
    amount = int(value[:-1])
    unit = value[-1]
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "m":
        return timedelta(minutes=amount)
    return timedelta(seconds=amount)


def coerce_input_value(spec: InputSpec, raw: Any) -> Any:
    """Coerce a CLI or run input to the declared type."""
    if spec.type == "string":
        return str(raw)
    if spec.type == "integer":
        return int(raw)
    if spec.type == "number":
        return float(raw)
    if spec.type == "boolean":
        if isinstance(raw, bool):
            return raw
        text = str(raw).lower()
        if text in {"true", "1", "yes"}:
            return True
        if text in {"false", "0", "no"}:
            return False
        raise ValueError(f"cannot coerce {raw!r} to boolean")
    raise ValueError(f"unknown input type {spec.type}")
