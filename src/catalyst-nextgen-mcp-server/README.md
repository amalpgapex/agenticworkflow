# Minimal MCP Server — API proxy (stdio)

This repository contains a minimal [Model Context Protocol (MCP)](https://modelcontextprotocol.io/docs/develop/build-server) server that exposes two tools which proxy GET endpoints from [InK Catalyst](https://dev.azure.com/symphonyvsts/InK_Platform/_git/deloitte-ink-genai-ltim):

- `get_transformations` → GET `/api/transformations`
- `get_transformation_details` → GET `/api/transformation/{key}`

The server is implemented with [FastMCP (Python MCP SDK)](https://github.com/modelcontextprotocol/python-sdk) and uses the **Streamable HTTP transport**, following MCP’s recommended practices (no writes to stdout; use stderr for logs). 

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

*   `API_BASE` — base URL of the backend that exposes `/api/transformations` (default: `http://localhost:8010`)
*   `USER_AGENT` — HTTP UA string (default: `catalyst-mcp/1.0`)
*   `OUTPUT_STYLE` — formatting style for tool outputs (`markdown` or `json`; default: `markdown`)

Set via environment variables, e.g.:

```bash
export API_BASE="http://localhost:8010"
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


### 1) Align Tools (backend :8080)

These tools proxy the `/Mapper/*` endpoints exposed by the backend service running on port 8080.  
They support **file uploads (multipart/form-data)**, **vector search**, **exact matching**, **semantic matching**, **text insights**, and **Excel generation** workflows.

#### `mapper_create_indexer(guid: str) -> str`
Creates or ensures a search index for the given process identifier.

- **HTTP**: `POST /Mapper/CreateIndexer`
- **Returns**: Index creation status and metadata

---

#### `mapper_save_embeddings(guid: str, index_name: str, records_json: str) -> str`
Generates and stores embeddings for textual records and uploads them into a search index.

- **HTTP**: `POST /Mapper/SaveEmbeddings`
- **records_json**: JSON string containing records with `row_id` and `data[]`
- **Returns**: Upload status and embedding statistics

---

#### `mapper_get_embedding_memory(...) -> str`
Retrieves semantic matches for a given row and persists results into the database.

- **HTTP**: `POST /Mapper/GetEmbeddingMemory`
- **Returns**: Mapping and similarity results

---

#### `mapper_upload_data_to_exact_match(...) -> str`
Uploads two files and performs column‑based preparation for exact matching.

- **HTTP**: `POST /Mapper/UploadDataToExactMatch`
- **Transport**: `multipart/form-data`
- **Returns**: Ingestion status

---

#### `mapper_get_exact_match_results(...) -> str`
Retrieves exact‑match results previously persisted for a given row.

- **HTTP**: `POST /Mapper/GetExactMatchResults`
- **Returns**: Exact match verdict and row mapping

---

#### `mapper_upload_data_to_match(...) -> str`
Uploads two files, performs exact matching, and prepares unmatched rows for semantic indexing.

- **HTTP**: `POST /Mapper/UploadDataToMatch`
- **Transport**: `multipart/form-data`
- **Returns**: Unmatched row identifiers

---

#### `mapper_process_upload_data_to_match(...) -> str`
Processes file uploads with explicit file IDs and persists exact match pairs.

- **HTTP**: `POST /Mapper/ProcessUploadDataToMatch`
- **Transport**: `multipart/form-data`
- **Returns**: Matched and unmatched row sets

---

#### `mapper_process_and_store_matches(...) -> str`
Executes exact‑match or semantic search flows and persists results.

- **HTTP**: `POST /Mapper/ProcessAndStoreMatches`
- **Returns**: Search type and persistence status

---

#### `mapper_process_optimal_matching(guid: str) -> str`
Performs optimal (Hungarian) matching across semantic results and exact matches.

- **HTTP**: `POST /Mapper/ProcessOptimialMatching`
- **Returns**: Final paired results

---

#### `mapper_process_text_insights(...) -> str`
Generates text insights for matched rows, including differences, summaries, and aligned text.

- **HTTP**: `POST /Mapper/ProcessTextInsights`
- **Returns**: Persisted insight generation status

---

#### `mapper_generate_file(...) -> str`
Generates a styled Excel file containing alignment, similarity, differences, and summaries.

- **HTTP**: `POST /Mapper/GenerateFile`
- **Transport**: `multipart/form-data`
- **Returns**: Local file path (`OK_SAVED:/tmp/...xlsx`)

---

#### `mapper_delete_embedding_memory(index_name: str) -> str`
Deletes a search index and its associated embedding data.

- **HTTP**: `POST /Mapper/DeleteEmbeddingMemory`

---

#### `mapper_delete_sql_records_memory(guid: str) -> str`
Deletes all SQL records associated with a given process identifier.

- **HTTP**: `POST /Mapper/DeleteSQLRecordsMemory`

---

#### `mapper_process_save_embedding(...) -> str`
Saves embeddings into Cosmos DB for later best‑pair matching.

- **HTTP**: `POST /Mapper/ProcessSaveEmbedding`

---

#### `mapper_process_best_pair_matches(...) -> str`
Computes best‑pair matches between two files using Cosmos DB embeddings.

- **HTTP**: `POST /Mapper/ProcessBestPairMatches`

---

#### `mapper_delete_cosmosdb_memory(file_id: str, file_number: str) -> str`
Deletes Cosmos DB containers or records for a given file.

- **HTTP**: `POST /Mapper/DeleteCosmosDbMemory`

---

#### `mapper_delete_containers() -> str`
Deletes all temporary Cosmos DB containers created by the Mapper workflow.

- **HTTP**: `DELETE /Mapper/DeleteContainers`

---

#### `mapper_delete_tables_data(list_of_tables_json: str = "[]") -> str`
Deletes data from all or selected SQL tables.

- **HTTP**: `DELETE /Mapper/DeleteTablesData`

---

### 2) Diff Tool

#### `differ_process_multi_column_file(row_id: str, data_json: str, enable_summary: bool = False) -> str`
Performs multi‑column text comparison and returns highlighted differences and optional summaries.

- **HTTP**: `POST /differ/processMultiColumnDifferFile`
- **data_json**: JSON string containing paired `FirstColumnValueX` / `SecondColumnValueX` values
- **Returns**: Structured difference output with optional summaries


***

## Notes on transports

*   **stdio**: Client launches the server as a subprocess; server must only write valid JSON‑RPC messages to stdout; logs to stderr. [Base Protocol Transports](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
*   If you later need cross‑process or streaming support, consider **Streamable HTTP** transport (per MCP spec). [Base Protocol Transports](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)

***

## References

*   [Build an MCP server (official docs)](https://modelcontextprotocol.io/docs/develop/build-server)
*   [Transports: stdio & streamable HTTP (spec)](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
*   [Python SDK repo (FastMCP integrated)](https://github.com/modelcontextprotocol/python-sdk)
