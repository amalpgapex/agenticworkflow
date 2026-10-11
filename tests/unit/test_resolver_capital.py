"""AC-02 / D9: empty city binds a PPLC capital."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from wf.agents.resolver import apply_capital_rule

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_pplc_taken_from_tool_trace() -> None:
    data = {
        "name": "Porto",
        "latitude": 41.15,
        "longitude": -8.61,
        "country": "Portugal",
        "country_code": "PT",
        "feature_code": "PPLA",
        "timezone": "Europe/Lisbon",
    }
    lisbon = json.loads((FIXTURES / "geocode_lisbon.json").read_text())["results"][0]
    trace = [{"tool_name": "geocode_location", "args": {}, "return_value": [lisbon, data]}]
    chosen = apply_capital_rule(data, trace, {"country": "PT", "city": ""})
    assert chosen["name"] == "Lisbon"
    assert chosen["feature_code"] == "PPLC"
    assert chosen["country_code"] == "PT"


@respx.mock
def test_fallback_geocode_when_trace_has_no_pplc() -> None:
    payload = json.loads((FIXTURES / "geocode_lisbon.json").read_text())
    respx.get("https://geocoding-api.open-meteo.com/v1/search").mock(return_value=httpx.Response(200, json=payload))
    data = {
        "name": "Porto",
        "latitude": 41.15,
        "longitude": -8.61,
        "country": "Portugal",
        "country_code": "PT",
        "feature_code": "PPLA",
        "timezone": "Europe/Lisbon",
    }
    chosen = apply_capital_rule(data, [], {"country": "PT", "city": ""})
    assert chosen["feature_code"] == "PPLC"
    assert chosen["name"] == "Lisbon"


def test_city_set_leaves_agent_output() -> None:
    data = {
        "name": "Porto",
        "latitude": 41.15,
        "longitude": -8.61,
        "country": "Portugal",
        "country_code": "PT",
        "feature_code": "PPLA",
        "timezone": "Europe/Lisbon",
    }
    chosen = apply_capital_rule(data, [], {"country": "PT", "city": "Porto"})
    assert chosen["name"] == "Porto"
    assert chosen["feature_code"] == "PPLA"
