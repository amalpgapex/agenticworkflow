"""Live Open-Meteo smoke (AC-02 / AC-03). Excluded unless `-m live`."""

from __future__ import annotations

import pytest

from wf.tools import openmeteo


@pytest.mark.live
def test_live_geocode_portugal_capital() -> None:
    """AC-02: country=PT resolves Lisbon PPLC."""
    results = openmeteo.geocode_location("Lisbon", country_code="PT", count=10)
    capitals = [r for r in results if r.get("feature_code") == "PPLC"]
    assert capitals
    assert capitals[0]["name"] == "Lisbon"
    assert capitals[0]["country_code"] == "PT"


@pytest.mark.live
def test_live_forecast_smoke() -> None:
    """AC-03 helper: a live forecast returns mapped days."""
    result = openmeteo.get_daily_forecast(38.71667, -9.13333, days=3, timezone="Europe/Lisbon")
    assert 1 <= len(result["days"]) <= 3
    assert "temp_max_c" in result["days"][0]
