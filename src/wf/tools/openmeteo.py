"""Open-Meteo HTTP client, WMO map, and per-run URL cache."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import httpx

from wf.config import get_settings
from wf.errors import ToolError

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO Weather interpretation codes (Open-Meteo docs).
WMO_DESCRIPTIONS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

DAILY_VARS = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
)


def cache_dir(run_id: str | None = None) -> Path:
    """Return the per-run HTTP cache directory."""
    settings = get_settings()
    rid = run_id or os.environ.get("WF_RUN_ID", "anon")
    path = Path(settings.artifact_root) / "cache" / rid
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_path(url: str, run_id: str | None = None) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_dir(run_id) / f"{digest}.json"


def fetch_json(url: str, *, run_id: str | None = None, client: httpx.Client | None = None) -> Any:
    """GET JSON, using the per-run URL cache when present."""
    path = _cache_path(url, run_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    close = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        close = True
    try:
        response = client.get(url)
    except httpx.HTTPError as exc:
        raise ToolError(f"HTTP error: {exc}") from exc
    finally:
        if close:
            client.close()
    try:
        payload = response.json()
    except ValueError as exc:
        raise ToolError(f"non-JSON response from {url}") from exc
    if response.status_code >= 400:
        raise ToolError(f"HTTP {response.status_code}: {payload}")
    if isinstance(payload, dict) and payload.get("error") is True:
        raise ToolError(str(payload.get("reason") or "Open-Meteo error"))
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def geocode_location(
    name: str,
    country_code: str | None = None,
    count: int = 10,
    *,
    run_id: str | None = None,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Search Open-Meteo geocoding and return structured results (FR-30)."""
    params: dict[str, Any] = {"name": name, "count": count, "language": "en", "format": "json"}
    if country_code:
        params["countryCode"] = country_code
    url = str(httpx.URL(GEOCODE_URL).copy_merge_params(params))
    payload = fetch_json(url, run_id=run_id, client=client)
    results = payload.get("results") or []
    mapped: list[dict[str, Any]] = []
    for item in results:
        mapped.append(
            {
                "name": item.get("name") or "",
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "country": item.get("country") or "",
                "country_code": item.get("country_code") or "",
                "feature_code": item.get("feature_code") or "",
                "timezone": item.get("timezone") or "auto",
                "population": item.get("population"),
                "admin1": item.get("admin1") or "",
            }
        )
    return mapped


def get_daily_forecast(
    latitude: float,
    longitude: float,
    days: int,
    timezone: str = "auto",
    *,
    run_id: str | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Fetch a daily forecast mapped to the WeatherReport day shape (FR-31)."""
    if days < 1 or days > 16:
        raise ToolError("days must be 1–16")
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join(DAILY_VARS),
        "forecast_days": days,
        "timezone": timezone,
    }
    url = str(httpx.URL(FORECAST_URL).copy_merge_params(params))
    payload = fetch_json(url, run_id=run_id, client=client)
    daily = payload.get("daily") or {}
    times = daily.get("time") or []
    records: list[dict[str, Any]] = []
    for index, day in enumerate(times):
        code = int((daily.get("weather_code") or [0] * len(times))[index] or 0)
        records.append(
            {
                "date": day,
                "weather_code": code,
                "weather_description": WMO_DESCRIPTIONS.get(code, f"WMO {code}"),
                "temp_max_c": float((daily.get("temperature_2m_max") or [0])[index] or 0),
                "temp_min_c": float((daily.get("temperature_2m_min") or [0])[index] or 0),
                "precipitation_mm": float((daily.get("precipitation_sum") or [0])[index] or 0),
                "precipitation_probability_max": float((daily.get("precipitation_probability_max") or [0])[index] or 0),
                "wind_speed_max_kmh": float((daily.get("wind_speed_10m_max") or [0])[index] or 0),
            }
        )
    return {
        "days": records,
        "units": payload.get("daily_units") or {},
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "timezone": payload.get("timezone") or timezone,
    }
