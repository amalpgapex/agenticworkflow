
# -*- coding: utf-8 -*-
"""
MCP Server — multi-API
- Transport: stdio/HTTP streaming (FastMCP).
"""

import os
import logging
from typing import Any, Dict, Optional, List, Union, Tuple
import json
import httpx
from mcp.server.fastmcp import FastMCP
import uuid
from pathlib import Path
from urllib.parse import urlencode, quote

# -----------------------------------------------------------------------------
# Logging (stderr-only)
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("mcp_server")

# -----------------------------------------------------------------------------
# Constants (multi-API)
# -----------------------------------------------------------------------------
API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
MAPPER_BASE = os.getenv("MAPPER_BASE_URL", "http://localhost:8080").rstrip("/")

USER_AGENT = "catalyst-mcp/1.0"
OUTPUT_STYLE = os.getenv("OUTPUT_STYLE", "markdown").lower()

# MCP server
mcp = FastMCP(
    "catalyst-nextgen-mcp-server",
    json_response=True,
    streamable_http_path="/mcp",
)

# -----------------------------------------------------------------------------
# Helpers multi-API
# -----------------------------------------------------------------------------
async def _request_json_base(
    base_url: str,
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    timeout_s: float = 60.0,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Generic JSON request for any base URL."""
    url = f"{base_url}{path}"
    req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.request(method, url, headers=req_headers, params=params, timeout=timeout_s)
            resp.raise_for_status()
            try:
                data = resp.json()
            except Exception:
                data = {"text": resp.text}
            return {"ok": True, "data": data}
        except httpx.HTTPStatusError as e:
            log.error(f"HTTP {e.response.status_code} error on {method} {url}: {e}")
            return {"ok": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            log.error(f"Request error on {method} {url}: {e}")
            return {"ok": False, "error": str(e)}


async def _request_json_post_base(
    base_url: str,
    path: str,
    *,
    body: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout_s: float = 60.0,
) -> Dict[str, Any]:
    """Generic POST JSON for any base URL."""
    url = f"{base_url}{path}"
    req_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if headers:
        req_headers.update(headers)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, headers=req_headers, json=body, timeout=timeout_s)
            resp.raise_for_status()
            try:
                data = resp.json()
            except Exception:
                data = {"text": resp.text}
            return {"ok": True, "data": data}
        except httpx.HTTPStatusError as e:
            log.error(f"HTTP {e.response.status_code} error on POST {url}: {e}")
            return {"ok": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            log.error(f"Request error on POST {url}: {e}")
            return {"ok": False, "error": str(e)}


async def _request_json(method: str, path: str, *, params: Optional[Dict[str, Any]] = None, timeout_s: float = 60.0) -> Dict[str, Any]:
    return await _request_json_base(API_BASE, method, path, params=params, timeout_s=timeout_s)

async def _request_json_post(path: str, *, body: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout_s: float = 60.0) -> Dict[str, Any]:
    return await _request_json_post_base(API_BASE, path, body=body, headers=headers, timeout_s=timeout_s)


async def _request_multipart_base(
    base_url: str,
    path: str,
    *,
    form_fields: Dict[str, Any],
    file_fields: Dict[str, Union[str, Tuple[str, bytes, str]]],  # name -> (filename, bytes, content_type) | filepath str
    method: str = "POST",
    headers: Optional[Dict[str, str]] = None,
    timeout_s: float = 180.0,
) -> Dict[str, Any]:
    url = f"{base_url}{path}"

    files = []
    for field_name, val in file_fields.items():
        if isinstance(val, str):
            p = Path(val)
            if not p.exists():
                return {"ok": False, "data": None, "error": f"FileNotFound:{val}"}
            # naive content-type
            ct = "application/octet-stream"
            if p.suffix.lower() in {".xlsx", ".xlsm", ".xltx", ".xltm", ".xls"}:
                ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif p.suffix.lower() == ".csv":
                ct = "text/csv"
            files.append((field_name, (p.name, p.read_bytes(), ct)))
        else:
            files.append((field_name, val))  # (filename, bytes, content_type)

    data = {}
    for k, v in form_fields.items():
        if isinstance(v, (list, dict)):
            data[k] = json.dumps(v, ensure_ascii=False)
        else:
            data[k] = "" if v is None else str(v)

    req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        try:
            resp = await client.request(method.upper(), url, data=data, files=files, headers=req_headers)
            resp.raise_for_status()
            try:
                payload = resp.json()
            except Exception:
                payload = {"text": resp.text}
            return {"ok": True, "data": payload}
        except httpx.HTTPStatusError as e:
            log.error(f"HTTP {e.response.status_code} error on {method} {url}: {e}")
            return {"ok": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            log.error(f"Multipart error on {method} {url}: {e}")
            return {"ok": False, "error": str(e)}


async def _download_to_tmp_base(
    base_url: str,
    method: str,
    path: str,
    *,
    form_fields: Optional[Dict[str, Any]] = None,
    file_fields: Optional[Dict[str, Union[str, Tuple[str, bytes, str]]]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    filename_hint: str = "download.bin",
    timeout_s: float = 300.0,
) -> Dict[str, Any]:
    url = f"{base_url}{path}"
    tmp_dir = Path("/tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    out_path = tmp_dir / f"{Path(filename_hint).stem}_{uuid.uuid4().hex}{Path(filename_hint).suffix}"

    req_kwargs: Dict[str, Any] = {"headers": {"User-Agent": USER_AGENT}}
    if json_body is not None:
        req_kwargs["json"] = json_body

    if form_fields is not None or file_fields is not None:
        files = []
        data = {}
        if file_fields:
            for field_name, val in file_fields.items():
                if isinstance(val, str):
                    p = Path(val)
                    if not p.exists():
                        return {"ok": False, "error": f"FileNotFound:{val}"}
                    ct = "application/octet-stream"
                    if p.suffix.lower() in {".xlsx", ".xlsm", ".xltx", ".xltm", ".xls"}:
                        ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    elif p.suffix.lower() == ".csv":
                        ct = "text/csv"
                    files.append((field_name, (p.name, p.read_bytes(), ct)))
                else:
                    files.append((field_name, val))
        if form_fields:
            for k, v in form_fields.items():
                data[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else ("" if v is None else str(v))
        req_kwargs["data"] = data
        req_kwargs["files"] = files

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            async with client.stream(method.upper(), url, **req_kwargs) as resp:
                resp.raise_for_status()
                with out_path.open("wb") as f:
                    async for chunk in resp.aiter_bytes():
                        f.write(chunk)
        return {"ok": True, "data": {"file_path": str(out_path)}}
    except httpx.HTTPStatusError as e:
        try:
            txt = e.response.text
        except Exception:
            txt = str(e)
        return {"ok": False, "error": f"HTTP {e.response.status_code}: {txt}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def _sse_get_events(url: str, *, timeout_s: float = 180.0) -> Dict[str, Any]:
    headers = {"Accept": "text/event-stream", "User-Agent": USER_AGENT}
    events: list = []
    final_text: str = ""

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        async with client.stream("GET", url, headers=headers) as r:
            r.raise_for_status()
            buf: list[str] = []
            async for line in r.aiter_lines():
                if line == "":
                    if not buf:
                        continue
                    data_lines = [l[5:].lstrip() for l in buf if l.startswith("data:")]
                    buf.clear()
                    if not data_lines:
                        continue
                    data_raw = "\n".join(data_lines)
                    try:
                        evt = json.loads(data_raw)
                    except Exception:
                        evt = {"type": "raw", "data": data_raw}
                    events.append(evt)
                    if isinstance(evt, dict) and evt.get("type") == "stream":
                        t = evt.get("text", "")
                        if isinstance(t, str):
                            final_text += t
                    continue
                buf.append(line)

    return {"events": events, "finalText": final_text}


# -----------------------------------------------------------------------------
# Tools PoC
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


@mcp.tool()
async def stream_transformation_via_rest(
    transformation_key: str,
    start_from_step: int = 0,
    edited_output: str = "",
    options_json: str = "",
) -> str:
    """Stream transformation (GET /api/stream/{transformation_key}) and return collected events as JSON."""
    qs = {"start_from_step": start_from_step, "edited_output": edited_output or ""}
    if options_json:
        qs["options"] = options_json
    url = f"{API_BASE}/api/stream/{quote(transformation_key)}?{urlencode(qs)}"
    try:
        data = await _sse_get_events(url)
    except httpx.HTTPStatusError as e:
        return f"ERROR_STREAM:HTTP {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"ERROR_STREAM:{e}"
    formatted = json.dumps(data, indent=2, ensure_ascii=False)
    return formatted


@mcp.tool()
async def get_audio_file(filename: str) -> str:
    """Retrieve generated audio file as a URL."""
    return f"/api/audio/{filename}"


@mcp.tool()
async def list_registered_tools_rest() -> str:
    """List registered tools (GET /api/tools)."""
    result = await _request_json("GET", "/api/tools")
    if not result.get("ok"):
        return f"ERROR_TOOLS:{result.get('error')}"
    formatted = json.dumps(result.get("data", {}), indent=2, ensure_ascii=False)
    return formatted


@mcp.tool()
async def execute_tool_via_rest(payload: Dict[str, Any]) -> str:
    """Execute tool via REST (POST /api/tool/execute)."""
    if not isinstance(payload, dict):
        return "ERROR_TOOL_EXECUTE:Payload must be a JSON object"
    key = payload.get("key")
    name = payload.get("name")
    arguments = payload.get("arguments", {})
    tool_call_id = payload.get("tool_call_id")
    if not key and not name:
        return "ERROR_TOOL_EXECUTE:Missing 'key' or 'name'"
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return "ERROR_TOOL_EXECUTE:'arguments' must be an object"
    body: Dict[str, Any] = {"key": key, "name": name, "arguments": arguments, "tool_call_id": tool_call_id}
    rid = str(uuid.uuid4())
    headers = {"x-request-id": rid}
    result = await _request_json_post("/api/tool/execute", body=body, headers=headers)
    if not result.get("ok"):
        return f"ERROR_TOOL_EXECUTE:{result.get('error')}"
    return json.dumps(result.get("data", {}), indent=2, ensure_ascii=False)


@mcp.tool()
async def generate_podcast(text: str, voice: str = "alloy") -> str:
    """Generate podcast audio via backend FastAPI."""
    payload = {"name": "podcast_generator", "arguments": {"text": text, "voice": voice}}
    result = await _request_json_post("/api/tool/execute", body=payload)
    if not result.get("ok"):
        return json.dumps({"ok": False, "error": result.get("error")}, ensure_ascii=False)
    return json.dumps(result["data"], ensure_ascii=False)


@mcp.tool()
async def custom_prompt(
    prompt: str,
    document_content: str = "",
    previous_output: str = "",
    template_variables_json: str = "",
    user_options_json: str = "",
    labeled_documents_json: str = "",
    step_history_json: str = ""
) -> str:
    """Proxy for LLM prompt (POST /api/tool/execute, 'llm_prompt')."""
    if not isinstance(prompt, str) or not prompt.strip():
        return json.dumps({"ok": False, "error": "custom_prompt: 'prompt' is required and cannot be empty"}, ensure_ascii=False, indent=2)

    def _safe_parse_json(raw: str, fallback):
        if not raw:
            return fallback
        try:
            return json.loads(raw)
        except Exception:
            return fallback

    template_variables = _safe_parse_json(template_variables_json, [])
    user_options       = _safe_parse_json(user_options_json, {})
    labeled_documents  = _safe_parse_json(labeled_documents_json, {})
    step_history       = _safe_parse_json(step_history_json, [])

    final_prompt = prompt
    if document_content and "{document_content}" not in final_prompt:
        final_prompt = f"{final_prompt}\n\n{document_content}"
    if previous_output and "{previous_output}" not in final_prompt:
        final_prompt = f"{final_prompt}\n\n{previous_output}"

    payload = {
        "name": "llm_prompt",
        "arguments": {
            "prompt": final_prompt,
            "document_content": document_content or "",
            "previous_output": previous_output or "",
            "template_variables": template_variables,
            "user_options": user_options,
            "labeled_documents": labeled_documents,
            "step_history": step_history
        }
    }

    result = await _request_json_post("/api/tool/execute", body=payload)
    if not result.get("ok"):
        return json.dumps({"ok": False, "error": result.get("error")}, ensure_ascii=False, indent=2)
    return json.dumps(result.get("data", {}), ensure_ascii=False, indent=2)


# -----------------------------------------------------------------------------
# Align Tools
# -----------------------------------------------------------------------------
def _fmt_ok(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)

def _maybe_parse_json(raw: Union[str, List, Dict]) -> Union[List, Dict]:
    if isinstance(raw, (list, dict)):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except Exception:
            pass
    return raw

@mcp.tool()
async def mapper_create_indexer(guid: str) -> str:
    """Mapper: Create indexer (POST /Mapper/CreateIndexer)."""
    payload = {"guid": guid}
    result = await _request_json_post_base(MAPPER_BASE, "/Mapper/CreateIndexer", body=payload)
    if not result.get("ok"):
        return f"ERROR_CREATE_INDEXER:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_save_embeddings(guid: str, index_name: str, records_json: str) -> str:
    """
    Mapper: Save embeddings (POST /Mapper/SaveEmbeddings).
    records_json: JSON string [{"row_id":..., "data":[...]}]
    """
    records = _maybe_parse_json(records_json) or []
    payload = {"guid": guid, "indexName": index_name, "records": records}
    result = await _request_json_post_base(MAPPER_BASE, "/Mapper/SaveEmbeddings", body=payload, timeout_s=300.0)
    if not result.get("ok"):
        return f"ERROR_SAVE_EMBEDDINGS:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_get_embedding_memory(
    guid: str,
    row_id: str,
    source_cols: str,
    destination_cols: str,
    index_name: str,
    with_summary_similarity_differences: bool = False,
    no_of_mappings: str = "1",
    list_source_columns_data_json: str = "[]",
) -> str:
    """Mapper: GetEmbeddingMemory (POST /Mapper/GetEmbeddingMemory)."""
    list_src = _maybe_parse_json(list_source_columns_data_json) or []
    payload = {
        "guid": guid,
        "rowId": str(row_id),
        "sourceFileColumnName": source_cols,
        "destinationFileColumnName": destination_cols,
        "indexName": index_name,
        "withSummarySimilarityDifferences": bool(with_summary_similarity_differences),
        "noOfMappings": str(no_of_mappings),
        "listSourceColumnsData": list_src,
    }
    result = await _request_json_post_base(MAPPER_BASE, "/Mapper/GetEmbeddingMemory", body=payload, timeout_s=300.0)
    if not result.get("ok"):
        return f"ERROR_GET_EMBEDDING_MEMORY:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_upload_data_to_exact_match(
    source_file_path: str,
    destination_file_path: str,
    guid: str,
    source_cols: str,
    destination_cols: str,
) -> str:
    """Mapper: UploadDataToExactMatch (multipart, POST /Mapper/UploadDataToExactMatch)."""
    form_fields = {"guid": guid, "sourceFileColumnName": source_cols, "destinationFileColumnName": destination_cols}
    file_fields = {"sourceFile": source_file_path, "destinationFile": destination_file_path}
    result = await _request_multipart_base(MAPPER_BASE, "/Mapper/UploadDataToExactMatch", form_fields=form_fields, file_fields=file_fields)
    if not result.get("ok"):
        return f"ERROR_UPLOAD_EXACT_MATCH:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_get_exact_match_results(
    guid: str,
    row_id: str,
    list_source_columns_data_json: str,
    ignore_case: int = 0,
) -> str:
    """Mapper: GetExactMatchResults (POST /Mapper/GetExactMatchResults)."""
    list_src = _maybe_parse_json(list_source_columns_data_json) or []
    payload = {"guid": guid, "rowId": str(row_id), "listSourceColumnsData": list_src, "ignoreCase": int(ignore_case)}
    result = await _request_json_post_base(MAPPER_BASE, "/Mapper/GetExactMatchResults", body=payload)
    if not result.get("ok"):
        return f"ERROR_GET_EXACT_MATCH_RESULTS:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_upload_data_to_match(
    source_file_path: str,
    destination_file_path: str,
    guid: str,
    source_cols: str,
    destination_cols: str,
    ignore_case: int = 0,
) -> str:
    """Mapper: UploadDataToMatch (multipart, POST /Mapper/UploadDataToMatch)."""
    form_fields = {
        "guid": guid,
        "sourceFileColumnName": source_cols,
        "destinationFileColumnName": destination_cols,
        "ignoreCase": int(ignore_case),
    }
    file_fields = {"sourceFile": source_file_path, "destinationFile": destination_file_path}
    result = await _request_multipart_base(MAPPER_BASE, "/Mapper/UploadDataToMatch", form_fields=form_fields, file_fields=file_fields)
    if not result.get("ok"):
        return f"ERROR_UPLOAD_DATA_TO_MATCH:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_process_upload_data_to_match(
    file1_path: str,
    file2_path: str,
    guid: str,
    file_1_columns: str,
    file_2_columns: str,
    file_1_id: str,
    file_2_id: str,
) -> str:
    """Mapper: ProcessUploadDataToMatch (multipart, POST /Mapper/ProcessUploadDataToMatch)."""
    form_fields = {
        "guid": guid,
        "file_1_columns": file_1_columns,
        "file_2_columns": file_2_columns,
        "file_1_Id": str(file_1_id),
        "file_2_Id": str(file_2_id),
    }
    file_fields = {"file1": file1_path, "file2": file2_path}
    result = await _request_multipart_base(MAPPER_BASE, "/Mapper/ProcessUploadDataToMatch", form_fields=form_fields, file_fields=file_fields, timeout_s=600.0)
    if not result.get("ok"):
        return f"ERROR_PROCESS_UPLOAD_DATA_TO_MATCH:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_process_and_store_matches(
    guid: str,
    list_source_columns_data_json: str,
    number_of_rows: int,
    row_id: str,
    index_name: str,
) -> str:
    """Mapper: ProcessAndStoreMatches (POST /Mapper/ProcessAndStoreMatches)."""
    list_src = _maybe_parse_json(list_source_columns_data_json) or []
    payload = {
        "guid": guid,
        "listSourceColumnsData": list_src,
        "numberOfRows": int(number_of_rows),
        "rowId": str(row_id),
        "indexName": index_name,
    }
    result = await _request_json_post_base(MAPPER_BASE, "/Mapper/ProcessAndStoreMatches", body=payload, timeout_s=300.0)
    if not result.get("ok"):
        return f"ERROR_PROCESS_AND_STORE_MATCHES:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_process_optimal_matching(guid: str) -> str:
    """Mapper: ProcessOptimialMatching (POST /Mapper/ProcessOptimialMatching)."""
    payload = {"guid": guid}
    result = await _request_json_post_base(MAPPER_BASE, "/Mapper/ProcessOptimialMatching", body=payload, timeout_s=600.0)
    if not result.get("ok"):
        return f"ERROR_PROCESS_OPTIMIAL_MATCHING:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_process_text_insights(
    guid: str,
    row_id: str,
    with_difference: bool,
    with_summary_similarity: bool,
    with_mapped_text: bool,
    source_cols: str,
    destination_cols: str,
) -> str:
    """Mapper: ProcessTextInsights (POST /Mapper/ProcessTextInsights)."""
    payload = {
        "guid": guid,
        "rowId": str(row_id),
        "withDifference": bool(with_difference),
        "withSummarySimilarity": bool(with_summary_similarity),
        "withMappedText": bool(with_mapped_text),
        "SourceFileColumnName": source_cols,
        "DestinationFileColumnName": destination_cols,
    }
    result = await _request_json_post_base(MAPPER_BASE, "/Mapper/ProcessTextInsights", body=payload, timeout_s=300.0)
    if not result.get("ok"):
        return f"ERROR_PROCESS_TEXT_INSIGHTS:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_generate_file(
    source_file_path: str,
    destination_file_path: str,
    guid: str,
    feature: int,
    source_cols: str,
    destination_cols: str,
    add_ons_list_csv: str,
    sheet_info: str = "string",
) -> str:
    """
    Mapper: GenerateFile (multipart, POST /Mapper/GenerateFile).
    Download Excel files in /tmp and show: 'OK_SAVED:/tmp/file.xlsx'.
    """
    form_fields = {
        "guid": guid,
        "feature": int(feature),
        "sourceFileColumnName": source_cols,
        "destinationFileColumnName": destination_cols,
        "addOnsList": add_ons_list_csv,
        "sheetInfo": sheet_info or "string",
    }
    file_fields = {"sourceFile": source_file_path, "destinationFile": destination_file_path}
    result = await _download_to_tmp_base(MAPPER_BASE, "POST", "/Mapper/GenerateFile", form_fields=form_fields, file_fields=file_fields, filename_hint="ContentMapper.xlsx", timeout_s=900.0)
    if not result.get("ok"):
        return f"ERROR_GENERATE_FILE:{result.get('error')}"
    return f"OK_SAVED:{result['data']['file_path']}"

@mcp.tool()
async def mapper_delete_embedding_memory(index_name: str) -> str:
    """Mapper: DeleteEmbeddingMemory (POST /Mapper/DeleteEmbeddingMemory)."""
    payload = {"indexName": index_name}
    result = await _request_json_post_base(MAPPER_BASE, "/Mapper/DeleteEmbeddingMemory", body=payload)
    if not result.get("ok"):
        return f"ERROR_DELETE_EMBEDDING_MEMORY:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_delete_sql_records_memory(guid: str) -> str:
    """Mapper: DeleteSQLRecordsMemory (POST /Mapper/DeleteSQLRecordsMemory)."""
    payload = {"guid": guid}
    result = await _request_json_post_base(MAPPER_BASE, "/Mapper/DeleteSQLRecordsMemory", body=payload)
    if not result.get("ok"):
        return f"ERROR_DELETE_SQL_RECORDS_MEMORY:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_process_save_embedding(file_id: str, file_number: str, records_json: str) -> str:
    """Mapper: ProcessSaveEmbedding (POST /Mapper/ProcessSaveEmbedding)."""
    records = _maybe_parse_json(records_json) or []
    payload = {"file_id": file_id, "file_number": str(file_number), "records": records}
    result = await _request_json_post_base(MAPPER_BASE, "/Mapper/ProcessSaveEmbedding", body=payload, timeout_s=600.0)
    if not result.get("ok"):
        return f"ERROR_PROCESS_SAVE_EMBEDDING:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_process_best_pair_matches(file_1_id: str, file_2_id: str, guid: str) -> str:
    """Mapper: ProcessBestPairMatches (POST /Mapper/ProcessBestPairMatches)."""
    payload = {"file_1_id": file_1_id, "file_2_id": file_2_id, "guid": guid}
    result = await _request_json_post_base(MAPPER_BASE, "/Mapper/ProcessBestPairMatches", body=payload, timeout_s=900.0)
    if not result.get("ok"):
        return f"ERROR_PROCESS_BEST_PAIR_MATCHES:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_delete_cosmosdb_memory(file_id: str, file_number: str) -> str:
    """Mapper: DeleteCosmosDbMemory (POST /Mapper/DeleteCosmosDbMemory)."""
    payload = {"file_id": file_id, "file_number": str(file_number)}
    result = await _request_json_post_base(MAPPER_BASE, "/Mapper/DeleteCosmosDbMemory", body=payload)
    if not result.get("ok"):
        return f"ERROR_DELETE_COSMOSDB_MEMORY:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_delete_containers() -> str:
    """Mapper: DeleteContainers (DELETE /Mapper/DeleteContainers)."""
    result = await _request_json_base(MAPPER_BASE, "DELETE", "/Mapper/DeleteContainers")
    if not result.get("ok"):
        return f"ERROR_DELETE_CONTAINERS:{result.get('error')}"
    return _fmt_ok(result["data"])

@mcp.tool()
async def mapper_delete_tables_data(list_of_tables_json: str = "[]") -> str:
    """Mapper: DeleteTablesData (DELETE /Mapper/DeleteTablesData)."""
    list_of_tables = _maybe_parse_json(list_of_tables_json) or []
    payload = {"ListOfTables": list_of_tables}
    result = await _request_json_post_base(MAPPER_BASE, "/Mapper/DeleteTablesData", body=payload) 
    if not result.get("ok"):
        return f"ERROR_DELETE_TABLES_DATA:{result.get('error')}"
    return _fmt_ok(result["data"])




@mcp.tool()
async def differ_process_multi_column_file(
    row_id: str,
    data_json: str,
    enable_summary: bool = False,
) -> str:
    """
    Differ: Process multi-column differ
    POST /differ/processMultiColumnDifferFile

    IMPORTANT CONTRACT:
    - 'data' MUST be a JSON array of objects.
    - Each object represents ONE independent comparison.
    - Each object MUST contain a PAIR of values:
          FirstColumnValueX  +  SecondColumnValueX
      where X is a numeric suffix (1, 2, 3, ...).
    - Objects are NOT compared against each other.
    - Differences are computed BETWEEN the paired values
      inside the SAME object.

    MCP Inspector usage:
    - data_json MUST be a STRING containing valid JSON.

    Example data_json:
    [
      {
        "FirstColumnValue1": "Text before",
        "SecondColumnValue1": "Text after"
      }
    ]
    """

    # 1) Parse JSON safely
    try:
        data = json.loads(data_json) if data_json else []
    except Exception as e:
        return f"ERROR_DIFFER_INVALID_JSON:{e}"

    # 2) Validate structure
    if not isinstance(data, list):
        return "ERROR_DIFFER_DATA_FORMAT:data must be a JSON array"

    if not data:
        return "ERROR_DIFFER_EMPTY_DATA:data array cannot be empty"

    # Optional: soft validation to catch common mistakes early
    for idx, obj in enumerate(data):
        if not isinstance(obj, dict):
            return f"ERROR_DIFFER_DATA_ITEM_{idx}:each item must be an object"
        first_keys = [k for k in obj.keys() if k.startswith("First")]
        second_keys = [k for k in obj.keys() if k.startswith("Second")]
        if not first_keys or not second_keys:
            return (
                f"ERROR_DIFFER_DATA_ITEM_{idx}:"
                "each object must contain FirstColumnValueX and SecondColumnValueX"
            )

    # 3) Build payload exactly as backend expects
    payload = {
        "RowId": row_id,
        "EnableSummary": bool(enable_summary),
        "data": data,
    }

    # 4) Call backend (8080)
    result = await _request_json_post_base(
        MAPPER_BASE,
        "/differ/processMultiColumnDifferFile",
        body=payload,
        timeout_s=300.0,
    )

    if not result.get("ok"):
        return f"ERROR_DIFFER_PROCESS:{result.get('error')}"

    # 5) Return backend response verbatim (Inspector‑friendly)
    return json.dumps(result.get("data", {}), indent=2, ensure_ascii=False)


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
app = mcp.streamable_http_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mcp_server:app", host="127.0.0.1", port=8010, reload=False)
