
# -*- coding: utf-8 -*-
"""
Minimal MCP Server — weather-style
Two tools that proxy GET endpoints:
- get_transformations (GET /api/transformations)
- get_transformation_details (GET /api/transformation/{key})

Transport: stdio. Do NOT print; use logging -> stderr.
"""

import os
import logging
from typing import Any, Dict, Optional
import json
import httpx
from mcp.server.fastmcp import FastMCP

# -----------------------------------------------------------------------------
# Logging (stderr-only)
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("mcp_server")

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
USER_AGENT = "catalyst-mcp/1.0"
OUTPUT_STYLE = os.getenv("OUTPUT_STYLE", "markdown").lower()

# MCP server
mcp = FastMCP("catalyst-nextgen-mcp-server")

# -----------------------------------------------------------------------------
# HTTP helper: async client + simple error handling
# -----------------------------------------------------------------------------
async def _request_json(
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    timeout_s: float = 30.0,
) -> Dict[str, Any]:
    url = f"{API_BASE}{path}"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.request(method, url, headers=headers, params=params, timeout=timeout_s)
            resp.raise_for_status()
            return {"ok": True, "data": resp.json()}
        except httpx.HTTPStatusError as e:
            log.error(f"HTTP {e.response.status_code} error on {method} {url}: {e}")
            return {"ok": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            log.error(f"Request error on {method} {url}: {e}")
            return {"ok": False, "error": str(e)}

# -----------------------------------------------------------------------------
# Tools (docstrings only)
# -----------------------------------------------------------------------------
@mcp.tool()
async def get_transformations() -> str:
    """List transformations (GET /api/transformations)."""
    result = await _request_json("GET", "/api/transformations")
    if not result.get("ok"):
        return f"ERROR_TRANSFORMATIONS:{result.get('error')}"
    formatted = json.dumps(result.get("data", {}), indent=2, ensure_ascii=False)
    return formatted


@mcp.tool()
async def get_transformation_details(transformation_key: str) -> str:
    """Get transformation details (GET /api/transformation/{key})."""
    path = f"/api/transformation/{transformation_key}"
    result = await _request_json("GET", path)
    if not result.get("ok"):
        return f"ERROR_TRANSFORMATION_DETAILS:{result.get('error')}"    
    formatted = json.dumps(result.get("data", {}), indent=2, ensure_ascii=False)
    return formatted


# -----------------------------------------------------------------------------
# Entry point — STDIO transport
# -----------------------------------------------------------------------------
def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
