"""MCP stdio server exposing geocode_location and get_daily_forecast."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from wf.errors import ToolError
from wf.tools import openmeteo

mcp = MCPServer(name="wf-weather", log_level="ERROR")


@mcp.tool()
def geocode_location(
    name: str,
    country_code: str | None = None,
    count: int = 10,
) -> list[dict[str, Any]]:
    """Search Open-Meteo geocoding. Prefer country_code when the country is ISO-2."""
    try:
        return openmeteo.geocode_location(name, country_code=country_code, count=count)
    except ToolError as exc:
        return {"error": True, "reason": str(exc)}  # type: ignore[return-value]


@mcp.tool()
def get_daily_forecast(
    latitude: float,
    longitude: float,
    days: int,
    timezone: str = "auto",
) -> dict[str, Any]:
    """Daily forecast mapped to the WeatherReport day shape. days must be 1-16."""
    try:
        return openmeteo.get_daily_forecast(latitude, longitude, days, timezone=timezone)
    except ToolError as exc:
        return {"error": True, "reason": str(exc)}


def main() -> None:
    """Stdio entry point for the MCP weather server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
