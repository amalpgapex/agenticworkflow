"""Prerequisite resolver agent."""

from __future__ import annotations

from typing import Any

from wf.agents.factory import build_agent, usage_limits
from wf.agents.trace import extract_tool_trace
from wf.schemas.registry import get_schema

# Open-Meteo `name=Portugal` does not return Lisbon. Search the capital (D9, AC-02).
_ISO2_CAPITALS: dict[str, str] = {
    "AT": "Vienna",
    "AU": "Canberra",
    "BE": "Brussels",
    "BR": "Brasilia",
    "CA": "Ottawa",
    "CH": "Bern",
    "CN": "Beijing",
    "DE": "Berlin",
    "ES": "Madrid",
    "FR": "Paris",
    "GB": "London",
    "IE": "Dublin",
    "IN": "New Delhi",
    "IT": "Rome",
    "JP": "Tokyo",
    "MX": "Mexico City",
    "NL": "Amsterdam",
    "PT": "Lisbon",
    "US": "Washington",
}
_COUNTRY_CAPITALS = {
    "portugal": "Lisbon",
    "united states": "Washington",
    "united kingdom": "London",
    "france": "Paris",
    "germany": "Berlin",
    "spain": "Madrid",
    "italy": "Rome",
}

_LOCATION_FIELDS = (
    "name",
    "latitude",
    "longitude",
    "country",
    "country_code",
    "feature_code",
    "timezone",
)


def location_from_geocode(item: dict[str, Any]) -> dict[str, Any]:
    """Project a geocode hit onto `ResolvedLocation@1` fields."""
    return {
        "name": str(item.get("name") or ""),
        "latitude": float(item["latitude"]),
        "longitude": float(item["longitude"]),
        "country": str(item.get("country") or ""),
        "country_code": str(item.get("country_code") or ""),
        "feature_code": str(item.get("feature_code") or ""),
        "timezone": str(item.get("timezone") or "auto"),
    }


def country_matches(item: dict[str, Any], country: str) -> bool:
    """Return True if a geocode hit matches ISO-2 or country name (D9)."""
    needle = country.strip()
    if not needle:
        return False
    if len(needle) == 2:
        return str(item.get("country_code") or "").upper() == needle.upper()
    return str(item.get("country") or "").lower() == needle.lower()


def pplc_from_hits(hits: list[dict[str, Any]], country: str) -> dict[str, Any] | None:
    """Return the first PPLC hit for the requested country, if any."""
    for item in hits:
        if item.get("feature_code") == "PPLC" and country_matches(item, country):
            return location_from_geocode(item)
    return None


def hits_from_trace(tool_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect geocode_location return values from the tool trace."""
    hits: list[dict[str, Any]] = []
    for row in tool_trace:
        if row.get("tool_name") != "geocode_location":
            continue
        value = row.get("return_value")
        if isinstance(value, list):
            hits.extend(item for item in value if isinstance(item, dict))
        elif isinstance(value, dict) and not value.get("error"):
            hits.append(value)
    return hits


def apply_capital_rule(
    data: dict[str, Any],
    tool_trace: list[dict[str, Any]],
    inputs: dict[str, Any],
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    """When city is empty, bind a PPLC from the tool list or a deterministic geocode (D9, AC-02)."""
    city = str(inputs.get("city") or "").strip()
    country = str(inputs.get("country") or "").strip()
    if city or not country:
        return data
    chosen = pplc_from_hits(hits_from_trace(tool_trace), country)
    if chosen is not None:
        return chosen
    from wf.tools import openmeteo

    if len(country) == 2:
        name = _ISO2_CAPITALS.get(country.upper(), country)
        code: str | None = country.upper()
    else:
        name = _COUNTRY_CAPITALS.get(country.lower(), country)
        code = None
    try:
        hits = openmeteo.geocode_location(name, country_code=code, run_id=run_id)
    except Exception:  # noqa: BLE001
        return data
    return pplc_from_hits(hits, country) or data


async def run_resolver(
    *,
    model_id: str,
    instructions: str,
    output_schema: str,
    tools: list[str],
    inputs: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, int]]:
    """Run the resolver agent and return data, trace, and usage."""
    schema = get_schema(output_schema)
    if schema is None:
        raise ValueError(f"unknown schema {output_schema}")
    agent = build_agent(
        model_id=model_id,
        instructions=instructions,
        output_schema=output_schema,
        tools=tools,
    )
    result = await agent.run(
        "Resolve the prerequisite and return one matching result.",
        usage_limits=usage_limits(),
    )
    output = result.output
    data = output.model_dump(mode="json") if hasattr(output, "model_dump") else dict(output)
    messages = result.all_messages() if hasattr(result, "all_messages") else []
    usage = getattr(result, "usage", None)
    if callable(usage):
        usage = usage()
    usage_dict = {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
    }
    trace = extract_tool_trace(messages)
    data = apply_capital_rule(data, trace, inputs or {}, run_id=run_id)
    return data, trace, usage_dict
