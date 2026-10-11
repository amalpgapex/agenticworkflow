"""FR-40..FR-43 named checks."""

from __future__ import annotations

from wf.checks.registry import run_named_check
from wf.checks.weather import is_poor_weather_day, is_severe_day


def test_severe_and_poor_rules_differ() -> None:
    mild_rain = {"weather_code": 61, "wind_speed_max_kmh": 10, "precipitation_probability_max": 40}
    assert is_poor_weather_day(mild_rain) is True
    assert is_severe_day(mild_rain) is False


def test_forecast_matches_source() -> None:
    day = {
        "date": "2026-10-07",
        "weather_code": 0,
        "weather_description": "Clear sky",
        "temp_max_c": 20.0,
        "temp_min_c": 10.0,
        "precipitation_mm": 0.0,
        "precipitation_probability_max": 5.0,
        "wind_speed_max_kmh": 12.0,
    }
    data = {"days": [day]}
    trace = [{"tool_name": "get_daily_forecast", "args": {}, "return_value": {"days": [day]}}]
    result = run_named_check("forecast_matches_source", data, {}, trace)
    assert result.passed is True
    mismatch = {**day, "temp_max_c": 30.0}
    failed = run_named_check(
        "forecast_matches_source",
        {"days": [mismatch]},
        {},
        trace,
    )
    assert failed.passed is False


def test_plan_dates_and_weather() -> None:
    forecast = {
        "data": {
            "days": [
                {
                    "date": "2026-10-07",
                    "weather_code": 65,
                    "precipitation_probability_max": 80,
                    "wind_speed_max_kmh": 10,
                }
            ]
        }
    }
    context = {"steps": {"get_forecast": forecast}}
    plan = {
        "days": [
            {
                "date": "2026-10-07",
                "outdoor_suitability": "poor",
                "indoor_alternative": "museum",
            }
        ]
    }
    assert run_named_check("plan_dates_match_forecast", plan, context, []).passed
    assert run_named_check("plan_respects_weather", plan, context, []).passed
    bad = {
        "days": [
            {
                "date": "2026-10-07",
                "outdoor_suitability": "good",
                "indoor_alternative": "",
            }
        ]
    }
    assert run_named_check("plan_respects_weather", bad, context, []).passed is False


def test_advisory_covers_severe_days() -> None:
    context = {
        "steps": {
            "get_forecast": {
                "data": {
                    "days": [
                        {"date": "2026-10-07", "weather_code": 95, "wind_speed_max_kmh": 10},
                        {"date": "2026-10-08", "weather_code": 0, "wind_speed_max_kmh": 5},
                    ]
                }
            }
        }
    }
    ok = {"severe_days": [{"date": "2026-10-07", "hazards": ["thunder"], "advice": "stay in"}]}
    assert run_named_check("advisory_covers_severe_days", ok, context, []).passed
    missing = {"severe_days": []}
    assert run_named_check("advisory_covers_severe_days", missing, context, []).passed is False
