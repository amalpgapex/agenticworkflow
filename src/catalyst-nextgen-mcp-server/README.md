# Minimal MCP Server — API proxy (stdio)

This repository contains a minimal [Model Context Protocol (MCP)](https://modelcontextprotocol.io/docs/develop/build-server) server that exposes two tools which proxy GET endpoints from [InK Studio v2](https://dev.azure.com/symphonyvsts/InK_Platform/_git/deloitte-ink-genai-catalystfuture?path=/src/catalyst-nextgen-ui-poc):

- `get_transformations` → GET `/api/transformations`
- `get_transformation_details` → GET `/api/transformation/{key}`

The server is implemented with [FastMCP (Python MCP SDK)](https://github.com/modelcontextprotocol/python-sdk) and uses the **stdio transport**, following MCP’s recommended practices (no writes to stdout; use stderr for logs). 

> **Important:** This MCP Server does not execute business logic internally. It only makes HTTP requests to an external application. Therefore, the application exposing these APIs **must be running and accessible** for the MCP Server to work.

---

## Quick start

### Prerequisites
- Python 3.10+  
- The **Python MCP SDK** (FastMCP) and `httpx` installed. The official docs use `uv` to manage environments and dependencies. 

### Setup on macOS/Linux (using `uv`)

```bash
# First, install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and enter project directory
uv init catalyst-nextgen-mcp-server
cd catalyst-nextgen-mcp-server

# Initialize project and virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv add "mcp[cli]" httpx

# Create the server file
touch mcp_server.py
````

> The upstream docs demonstrate the same flow when building the tutorial “weather server” with FastMCP: [Model Context Protocol](https://modelcontextprotocol.io/docs/develop/build-server)

***

## Configuration

*   `API_BASE` — base URL of the backend that exposes `/api/transformations` (default: `http://localhost:8000`)
*   `USER_AGENT` — HTTP UA string (default: `catalyst-mcp/1.0`)
*   `OUTPUT_STYLE` — formatting style for tool outputs (`markdown` or `json`; default: `markdown`)

Set via environment variables, e.g.:

```bash
export API_BASE="http://localhost:8000"
export USER_AGENT = "catalyst-mcp/1.0"
export OUTPUT_STYLE="json"
```

***

## Run

This server uses **stdio** transport. Do not print to stdout (use `logging` → stderr).

```bash
uv run mcp_server.py
```

You can connect the server to any MCP-capable client (e.g., Claude Desktop or other clients). The FastMCP SDK handles tool schema generation from type hints and docstrings.

***

## Tools

> **Important:** This MCP Server does not execute business logic internally. It only makes HTTP requests to an external application. Ink Studio v2 **must be running and accessible** for the MCP Server to work.

### 1) `get_transformations() -> str`

Lists available transformations from PoC (`app_fastapi.py`).

*   **HTTP**: `GET /api/transformations`
*   **Returns**: Pretty-printed JSON (or Markdown, depending on `OUTPUT_STYLE`)

### 2) `get_transformation_details(transformation_key: str) -> str`

Fetches details for a specific transformation.

*   **HTTP**: `GET /api/transformation/{key}`
*   **Returns**: Pretty-printed JSON (or Markdown)

Both tools use `httpx.AsyncClient` with basic error handling and log failures to stderr (per MCP stdio guidance)

***

## Notes on transports

*   **stdio**: Client launches the server as a subprocess; server must only write valid JSON‑RPC messages to stdout; logs to stderr. [Base Protocol Transports](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
*   If you later need cross‑process or streaming support, consider **Streamable HTTP** transport (per MCP spec). [Base Protocol Transports](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)

***

## References

*   [Build an MCP server (official docs)](https://modelcontextprotocol.io/docs/develop/build-server)
*   [Transports: stdio & streamable HTTP (spec)](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
*   [Python SDK repo (FastMCP integrated)](https://github.com/modelcontextprotocol/python-sdk)
