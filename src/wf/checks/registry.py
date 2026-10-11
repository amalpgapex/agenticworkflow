"""Name → callable registry for deterministic checks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wf.errors import CheckError
from wf.schemas.core import CheckResult

CheckFn = Callable[[dict[str, Any], dict[str, Any], list[dict[str, Any]]], CheckResult]

_REGISTRY: dict[str, CheckFn] = {}


def register(name: str) -> Callable[[CheckFn], CheckFn]:
    """Decorator that registers a named check."""

    def deco(fn: CheckFn) -> CheckFn:
        _REGISTRY[name] = fn
        return fn

    return deco


def get_check(name: str) -> CheckFn | None:
    """Return a registered check, or None."""
    return _REGISTRY.get(name)


def check_names() -> frozenset[str]:
    """Return every registered check name."""
    return frozenset(_REGISTRY)


def run_named_check(
    name: str,
    data: dict[str, Any],
    context: dict[str, Any],
    tool_trace: list[dict[str, Any]],
) -> CheckResult:
    """Run a named check or raise CheckError."""
    fn = get_check(name)
    if fn is None:
        raise CheckError(f"unknown named check {name!r}")
    return fn(data, context, tool_trace)


# Import weather checks so they self-register.
from wf.checks import weather as _weather  # noqa: E402,F401
