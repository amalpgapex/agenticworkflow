"""Load and validate YAML workflow definitions."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from wf.checks.registry import check_names
from wf.definition.models import Definition, InputSpec, Step, coerce_input_value, parse_duration
from wf.errors import DefinitionError, ExpressionError
from wf.expressions.cel import compile_cel
from wf.expressions.template import interpolate, iter_placeholders
from wf.schemas.registry import get_schema

KNOWN_TOOLS = frozenset({"geocode_location", "get_daily_forecast"})
_ROOT_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)")

SITE_ROOTS: dict[str, frozenset[str]] = {
    "load": frozenset({"env", "inputs"}),
    "run_when": frozenset({"inputs", "ctx", "steps"}),
    "input": frozenset({"inputs", "ctx", "steps"}),
    "prereq": frozenset({"inputs", "ctx", "steps", "data"}),
    "required_when": frozenset({"inputs", "ctx", "steps", "system"}),
    "subject": frozenset({"inputs", "ctx", "steps"}),
}


def load_yaml(path: Path) -> Any:
    """Parse YAML with the safe loader."""
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def interpolate_env(raw: Any, extra_env: dict[str, str] | None = None) -> Any:
    """Resolve `${env.*}` (and other load-time placeholders) in the CLI."""
    from dotenv import dotenv_values

    file_env = {key: value for key, value in dotenv_values().items() if value is not None}
    env = {**file_env, **os.environ, **(extra_env or {})}
    context: dict[str, Any] = {"env": env}
    return _walk_interpolate(raw, context)


def _walk_interpolate(raw: Any, context: dict[str, Any]) -> Any:
    if isinstance(raw, str):
        if "${" not in raw:
            return raw
        return interpolate(raw, context, roots=frozenset({"env"}))
    if isinstance(raw, list):
        return [_walk_interpolate(item, context) for item in raw]
    if isinstance(raw, dict):
        return {key: _walk_interpolate(value, context) for key, value in raw.items()}
    return raw


def load_definition(
    path: Path,
    *,
    interpolate_environment: bool = True,
    extra_env: dict[str, str] | None = None,
) -> Definition:
    """Load, interpolate env, validate, and return a Definition."""
    raw = load_yaml(path)
    if not isinstance(raw, dict):
        raise DefinitionError(["root: definition must be a mapping"])
    if interpolate_environment:
        raw = interpolate_env(raw, extra_env)
    return validate_definition(raw)


def validate_definition(raw: dict[str, Any]) -> Definition:
    """Validate a raw mapping and collect every error with a YAML path."""
    errors: list[str] = []
    try:
        definition = Definition.model_validate(raw)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(part) for part in err["loc"])
            errors.append(f"{loc}: {err['msg']}")
        raise DefinitionError(errors) from exc

    _collect_semantic_errors(definition, errors)
    if errors:
        raise DefinitionError(errors)
    return definition


def _collect_semantic_errors(definition: Definition, errors: list[str]) -> None:
    seen: set[str] = set()
    for index, step in enumerate(definition.steps):
        path = f"steps[{index}]"
        if step.id in seen:
            errors.append(f"{path}.id: duplicate step id '{step.id}'")
        seen.add(step.id)
        if step.type in {"parallel", "action"}:
            errors.append(f"{path}.type: not supported in Phase 1")
        if step.executor is None and step.type == "agent":
            errors.append(f"{path}.executor: required for agent steps")
        _check_step(step, path, errors)

    from_step = definition.output.from_step
    if from_step not in seen:
        errors.append(f"output.from_step: unknown step '{from_step}'")
    _compile_site(
        definition.output.deliver.subject,
        "subject",
        "output.deliver.subject",
        errors,
        full_cel=False,
    )
    parse_duration(definition.workflow.defaults.hitl.timeout)


def _check_step(step: Step, path: str, errors: list[str]) -> None:
    if step.run_when:
        _compile_site(step.run_when, "run_when", f"{path}.run_when", errors, full_cel=True)
    for key, expr in step.input.items():
        _compile_site(expr, "input", f"{path}.input.{key}", errors, full_cel=True)
    if step.human_review:
        _compile_site(
            step.human_review.required_when,
            "required_when",
            f"{path}.human_review.required_when",
            errors,
            full_cel=True,
        )
    if step.executor:
        _check_schema(step.executor.output_schema, f"{path}.executor.output_schema", errors)
        _check_tools(step.executor.tools, f"{path}.executor.tools", errors)
        _compile_site(
            step.executor.instructions,
            "load",
            f"{path}.executor.instructions",
            errors,
            full_cel=False,
        )
    if step.evaluator:
        for i, expr in enumerate(step.evaluator.checks):
            _compile_site(expr, "prereq", f"{path}.evaluator.checks[{i}]", errors, full_cel=True)
        for i, name in enumerate(step.evaluator.named_checks):
            if name not in check_names():
                errors.append(f"{path}.evaluator.named_checks[{i}]: unknown check '{name}'")
    for i, prereq in enumerate(step.prerequisites):
        ppath = f"{path}.prerequisites[{i}]"
        _compile_site(prereq.check, "prereq", f"{ppath}.check", errors, full_cel=True)
        _check_schema(prereq.resolve.output_schema, f"{ppath}.resolve.output_schema", errors)
        _check_tools(prereq.resolve.tools, f"{ppath}.resolve.tools", errors)
        _compile_site(
            prereq.resolve.instructions,
            "load",
            f"{ppath}.resolve.instructions",
            errors,
            full_cel=False,
        )
        for j, expr in enumerate(prereq.resolve.verify):
            _compile_site(expr, "prereq", f"{ppath}.resolve.verify[{j}]", errors, full_cel=True)


def _check_schema(name: str, path: str, errors: list[str]) -> None:
    if get_schema(name) is None:
        errors.append(f"{path}: unknown schema '{name}'")


def _check_tools(tools: list[str], path: str, errors: list[str]) -> None:
    for i, tool in enumerate(tools):
        if tool not in KNOWN_TOOLS:
            errors.append(f"{path}[{i}]: unknown tool '{tool}'")


def _compile_site(
    source: str,
    site: str,
    path: str,
    errors: list[str],
    *,
    full_cel: bool,
) -> None:
    allowed = SITE_ROOTS[site]
    placeholders = list(iter_placeholders(source))
    for placeholder in placeholders:
        root = _root_of(placeholder)
        if root and root not in allowed:
            errors.append(f"{path}: placeholder root '{root}' not allowed at this site")
        try:
            compile_cel(placeholder)
        except ExpressionError as exc:
            errors.append(f"{path}: {exc}")
    if full_cel and not placeholders:
        try:
            compile_cel(source)
        except ExpressionError as exc:
            errors.append(f"{path}: {exc}")


def _root_of(expr: str) -> str | None:
    match = _ROOT_RE.match(expr.strip())
    return match.group(1) if match else None


def validate_run_inputs(definition: Definition, raw_inputs: dict[str, Any]) -> dict[str, Any]:
    """Validate and coerce run inputs against the definition (FR-03)."""
    errors: list[str] = []
    result: dict[str, Any] = {}
    specs = definition.workflow.inputs
    for name, spec in specs.items():
        if name in raw_inputs:
            try:
                value = coerce_input_value(spec, raw_inputs[name])
            except (TypeError, ValueError) as exc:
                errors.append(f"inputs.{name}: {exc}")
                continue
        elif spec.default is not None:
            value = spec.default
        elif spec.required:
            errors.append(f"inputs.{name}: required")
            continue
        else:
            continue
        bound_error = _bounds_error(name, spec, value)
        if bound_error:
            errors.append(bound_error)
        else:
            result[name] = value
    unknown = sorted(set(raw_inputs) - set(specs))
    for name in unknown:
        errors.append(f"inputs.{name}: unknown input")
    if errors:
        raise DefinitionError(errors)
    return result


def _bounds_error(name: str, spec: InputSpec, value: Any) -> str | None:
    if spec.min is not None and isinstance(value, (int, float)) and value < spec.min:
        return f"inputs.{name}: {value} is below min {spec.min}"
    if spec.max is not None and isinstance(value, (int, float)) and value > spec.max:
        return f"inputs.{name}: {value} is above max {spec.max}"
    return None
