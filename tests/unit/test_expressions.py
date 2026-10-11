"""CEL and ${...} interpolation."""

from __future__ import annotations

import pytest

from wf.errors import ExpressionError
from wf.expressions.cel import compile_cel, evaluate_cel
from wf.expressions.template import interpolate, iter_placeholders


def test_compile_and_evaluate_size() -> None:
    compile_cel("size(data.days) == inputs.days")
    result = evaluate_cel(
        "size(data.days) == inputs.days",
        {"data": {"days": [1, 2]}, "inputs": {"days": 2}},
    )
    assert result is True


def test_has_ctx_location() -> None:
    assert evaluate_cel("has(ctx.location)", {"ctx": {}}) is False
    assert evaluate_cel("has(ctx.location)", {"ctx": {"location": {"name": "Lisbon"}}}) is True


def test_exists_macro() -> None:
    days = [{"weather_code": 65, "wind_speed_max_kmh": 10.0}]
    expr = "data.days.exists(d, d.weather_code in [65, 67] || d.wind_speed_max_kmh >= 50.0)"
    assert evaluate_cel(expr, {"data": {"days": days}}) is True


def test_interpolate_env() -> None:
    text = "model=${env.WF_EXECUTOR_MODEL}"
    assert list(iter_placeholders(text)) == ["env.WF_EXECUTOR_MODEL"]
    assert interpolate(text, {"env": {"WF_EXECUTOR_MODEL": "bedrock:x"}}) == "model=bedrock:x"


def test_bad_cel_raises() -> None:
    with pytest.raises(ExpressionError):
        compile_cel("this is not @@@ cel")
