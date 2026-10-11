"""CEL compile/evaluate helpers using cel-python (`celpy`)."""

from __future__ import annotations

from typing import Any

import celpy
from celpy.adapter import json_to_cel

from wf.errors import ExpressionError

_ENV = celpy.Environment()


def compile_cel(source: str) -> celpy.Runner:
    """Compile a CEL expression. Raise ExpressionError on syntax errors."""
    try:
        ast = _ENV.compile(source)
        return _ENV.program(ast)
    except Exception as exc:
        raise ExpressionError(f"CEL compile failed for {source!r}: {exc}") from exc


def evaluate_cel(source: str, context: dict[str, Any]) -> Any:
    """Evaluate a CEL expression against a plain-JSON context."""
    program = compile_cel(source)
    try:
        cel_context = {key: json_to_cel(value) for key, value in context.items()}
        result = program.evaluate(cel_context)
    except Exception as exc:
        raise ExpressionError(f"CEL evaluate failed for {source!r}: {exc}") from exc
    return _from_cel(result)


def _from_cel(value: Any) -> Any:
    """Convert celpy types back to plain Python JSON values."""
    if value is None:
        return None
    name = type(value).__name__
    if name == "BoolType":
        return bool(value)
    if name in {"IntType", "UintType"}:
        return int(value)
    if name == "DoubleType":
        return float(value)
    if name == "StringType":
        return str(value)
    if name == "ListType" or isinstance(value, (list, tuple)):
        return [_from_cel(item) for item in value]
    if name == "MapType" or isinstance(value, dict):
        return {str(_from_cel(key)): _from_cel(item) for key, item in value.items()}
    if isinstance(value, (bool, int, float, str)):
        return value
    return value
