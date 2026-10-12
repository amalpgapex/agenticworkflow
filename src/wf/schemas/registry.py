"""`Name@version` → Pydantic model registry."""

from __future__ import annotations

from pydantic import BaseModel

from wf.schemas.core import EvaluationVerdict, HumanDecision
from wf.schemas.weather import ActivityPlan, ResolvedLocation, SafetyAdvisory, WeatherReport
from wf.schemas.care701b import (
    ActionResult,
    Care701bExtraction,
    CaseNoteResult,
    DocumentUploadResult,
    DuplicateCheckResult,
    LogResult,
    MemberValidationResult,
)

_REGISTRY: dict[str, type[BaseModel]] = {
    # Weather workflow schemas
    "ResolvedLocation@1": ResolvedLocation,
    "WeatherReport@1": WeatherReport,
    "SafetyAdvisory@1": SafetyAdvisory,
    "ActivityPlan@1": ActivityPlan,
    "EvaluationVerdict@1": EvaluationVerdict,
    "HumanDecision@1": HumanDecision,
    # CARE 701B workflow schemas
    "Care701bExtraction@1": Care701bExtraction,
    "MemberValidationResult@1": MemberValidationResult,
    "DuplicateCheckResult@1": DuplicateCheckResult,
    "DocumentUploadResult@1": DocumentUploadResult,
    "CaseNoteResult@1": CaseNoteResult,
    "LogResult@1": LogResult,
    "ActionResult@1": ActionResult,
}


def get_schema(name: str) -> type[BaseModel] | None:
    """Return the registered model for `Name@version`, or None."""
    return _REGISTRY.get(name)


def schema_names() -> frozenset[str]:
    """Return every registered schema key."""
    return frozenset(_REGISTRY)
