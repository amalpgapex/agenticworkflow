"""FR-30..FR-33 Open-Meteo client."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from wf.errors import ToolError
from wf.tools import openmeteo

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@respx.mock
def test_geocode_location_maps_fields() -> None:
    payload = json.loads((FIXTURES / "geocode_lisbon.json").read_text())
    respx.get("https://geocoding-api.open-meteo.com/v1/search").mock(return_value=httpx.Response(200, json=payload))
    results = openmeteo.geocode_location("Lisbon", country_code="PT", count=10)
    assert results[0]["feature_code"] == "PPLC"
    assert results[0]["country_code"] == "PT"


@respx.mock
def test_forecast_maps_to_schema_shape() -> None:
    payload = json.loads((FIXTURES / "forecast_lisbon.json").read_text())
    respx.get("https://api.open-meteo.com/v1/forecast").mock(return_value=httpx.Response(200, json=payload))
    result = openmeteo.get_daily_forecast(38.7, -9.1, days=2, timezone="Europe/Lisbon")
    assert len(result["days"]) == 2
    first = result["days"][0]
    assert first["temp_max_c"] == 22.1
    assert first["weather_description"] == "Clear sky"
    assert first["date"] == "2026-10-07"


@respx.mock
def test_api_error_is_tool_error() -> None:
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json={"error": True, "reason": "bad coords"})
    )
    try:
        openmeteo.get_daily_forecast(0, 0, days=1)
        raise AssertionError("expected ToolError")
    except ToolError as exc:
        assert "bad coords" in str(exc)


def test_days_bounds() -> None:
    try:
        openmeteo.get_daily_forecast(1, 1, days=20)
        raise AssertionError("expected ToolError")
    except ToolError as exc:
        assert "1–16" in str(exc)
