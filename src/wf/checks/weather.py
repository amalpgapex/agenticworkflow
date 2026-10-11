"""Demo named checks (FR-40..FR-43) and shared weather predicates."""

from __future__ import annotations

from typing import Any

from wf.checks.registry import register
from wf.schemas.core import CheckResult

SEVERE_WEATHER_CODES = frozenset({65, 67, 75, 82, 86, 95, 96, 97, 99})
SEVERE_WIND_KMH = 50.0
POOR_PRECIP_PROB = 60.0
POOR_WEATHER_CODE = 61
NUMERIC_TOLERANCE = 0.05
NUMERIC_FIELDS = (
    "temp_max_c",
    "temp_min_c",
    "precipitation_mm",
    "precipitation_probability_max",
    "wind_speed_max_kmh",
)


def is_severe_day(day: dict[str, Any]) -> bool:
    """Return True if the day matches the advisory `run_when` rule."""
    code = int(day.get("weather_code") or 0)
    wind = float(day.get("wind_speed_max_kmh") or 0.0)
    return code in SEVERE_WEATHER_CODES or wind >= SEVERE_WIND_KMH


def is_poor_weather_day(day: dict[str, Any]) -> bool:
    """Return True if the day must not be marked outdoor-good."""
    precip = float(day.get("precipitation_probability_max") or 0.0)
    code = int(day.get("weather_code") or 0)
    return precip >= POOR_PRECIP_PROB or code >= POOR_WEATHER_CODE


def _as_date(value: Any) -> str:
    return str(value)


@register("forecast_matches_source")
def forecast_matches_source(
    data: dict[str, Any],
    context: dict[str, Any],
    tool_trace: list[dict[str, Any]],
) -> CheckResult:
    """FR-40: every `data.days` row matches the last get_daily_forecast return."""
    del context
    last: dict[str, Any] | None = None
    for call in tool_trace:
        if call.get("tool_name") == "get_daily_forecast":
            last = call
    if last is None:
        return CheckResult(name="forecast_matches_source", passed=False, detail="no tool call")
    returned = last.get("return_value") or {}
    source_days = returned.get("days") if isinstance(returned, dict) else returned
    if not isinstance(source_days, list):
        return CheckResult(name="forecast_matches_source", passed=False, detail="tool return has no days")
    actual = data.get("days") or []
    if len(actual) != len(source_days):
        return CheckResult(
            name="forecast_matches_source",
            passed=False,
            detail=f"day count {len(actual)} != source {len(source_days)}",
        )
    for got, src in zip(actual, source_days, strict=True):
        if _as_date(got.get("date")) != _as_date(src.get("date")):
            return CheckResult(
                name="forecast_matches_source",
                passed=False,
                detail=f"date mismatch {got.get('date')} != {src.get('date')}",
            )
        for field in NUMERIC_FIELDS:
            a = float(got.get(field) or 0.0)
            b = float(src.get(field) or 0.0)
            if abs(a - b) > NUMERIC_TOLERANCE:
                return CheckResult(
                    name="forecast_matches_source",
                    passed=False,
                    detail=f"{field} {a} vs {b} on {got.get('date')}",
                )
    return CheckResult(name="forecast_matches_source", passed=True)


@register("plan_dates_match_forecast")
def plan_dates_match_forecast(
    data: dict[str, Any],
    context: dict[str, Any],
    tool_trace: list[dict[str, Any]],
) -> CheckResult:
    """FR-41: plan dates equal forecast dates, in order."""
    del tool_trace
    steps = context.get("steps") or {}
    forecast = ((steps.get("get_forecast") or {}).get("data") or {}).get("days") or []
    plan_days = data.get("days") or []
    plan_dates = [_as_date(d.get("date")) for d in plan_days]
    forecast_dates = [_as_date(d.get("date")) for d in forecast]
    if plan_dates != forecast_dates:
        return CheckResult(
            name="plan_dates_match_forecast",
            passed=False,
            detail=f"{plan_dates} != {forecast_dates}",
        )
    return CheckResult(name="plan_dates_match_forecast", passed=True)


@register("plan_respects_weather")
def plan_respects_weather(
    data: dict[str, Any],
    context: dict[str, Any],
    tool_trace: list[dict[str, Any]],
) -> CheckResult:
    """FR-42: poor-weather days are not outdoor-good and have an indoor alternative."""
    del tool_trace
    steps = context.get("steps") or {}
    forecast_days = ((steps.get("get_forecast") or {}).get("data") or {}).get("days") or []
    by_date = {_as_date(d.get("date")): d for d in forecast_days}
    failures: list[str] = []
    for plan_day in data.get("days") or []:
        key = _as_date(plan_day.get("date"))
        forecast = by_date.get(key)
        if forecast is None or not is_poor_weather_day(forecast):
            continue
        if plan_day.get("outdoor_suitability") == "good":
            failures.append(f"{key}: outdoor_suitability is good")
        if not str(plan_day.get("indoor_alternative") or "").strip():
            failures.append(f"{key}: indoor_alternative empty")
    if failures:
        return CheckResult(name="plan_respects_weather", passed=False, detail="; ".join(failures))
    return CheckResult(name="plan_respects_weather", passed=True)


@register("advisory_covers_severe_days")
def advisory_covers_severe_days(
    data: dict[str, Any],
    context: dict[str, Any],
    tool_trace: list[dict[str, Any]],
) -> CheckResult:
    """FR-43: every severe forecast day appears in the advisory."""
    del tool_trace
    steps = context.get("steps") or {}
    forecast_days = ((steps.get("get_forecast") or {}).get("data") or {}).get("days") or []
    severe = [_as_date(d.get("date")) for d in forecast_days if is_severe_day(d)]
    covered = {_as_date(d.get("date")) for d in data.get("severe_days") or []}
    missing = [d for d in severe if d not in covered]
    if missing:
        return CheckResult(
            name="advisory_covers_severe_days",
            passed=False,
            detail=f"missing {missing}",
        )
    return CheckResult(name="advisory_covers_severe_days", passed=True)
