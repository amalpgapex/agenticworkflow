"""MCP stdio server exposing TrueCare stub tools for CARE 701B workflow."""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.server.mcpserver import MCPServer

from wf.tools.truecare import (
    CaseNoteInput,
    DocumentSearchInput,
    DocumentUploadInput,
    MemberLookupInput,
    S3LogInput,
    TextractExtractInput,
    s3_append_log,
    s3_get_object,
    textract_extract_form,
    truecare_create_case_note,
    truecare_document_search,
    truecare_document_upload,
    truecare_member_lookup,
)

mcp = MCPServer(name="wf-truecare", log_level="ERROR")


def _run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@mcp.tool()
def textract_extract_form_tool(
    file_key: str,
    bucket: str = "care701b-intake",
) -> dict[str, Any]:
    """
    Extract fields from a CARE 701B PDF using AWS Textract.
    
    Returns member_ssn, member_name, member_dob, document_date, 
    initial_checkbox_checked, and confidence_scores for each field.
    """
    try:
        input_data = TextractExtractInput(file_key=file_key, bucket=bucket)
        result = _run_async(textract_extract_form(input_data))
        return result.model_dump()
    except Exception as exc:
        return {"error": True, "reason": str(exc)}


@mcp.tool()
def truecare_member_lookup_tool(
    ssn: str,
    name: str,
    dob: str,
) -> dict[str, Any]:
    """
    Look up a member in TrueCare by SSN, name, and date of birth.
    
    Returns member_found (bool), member_id (if found), and match_type.
    """
    try:
        input_data = MemberLookupInput(ssn=ssn, name=name, dob=dob)
        result = _run_async(truecare_member_lookup(input_data))
        return result.model_dump()
    except Exception as exc:
        return {"error": True, "reason": str(exc)}


@mcp.tool()
def truecare_document_search_tool(
    member_id: str,
    document_date: str,
    lookback_months: int = 12,
) -> dict[str, Any]:
    """
    Search for duplicate documents in TrueCare within a lookback window.
    
    Returns is_duplicate (bool) and list of matching documents.
    """
    try:
        input_data = DocumentSearchInput(
            member_id=member_id,
            document_date=document_date,
            lookback_months=lookback_months,
        )
        result = _run_async(truecare_document_search(input_data))
        return result.model_dump()
    except Exception as exc:
        return {"error": True, "reason": str(exc)}


@mcp.tool()
def truecare_document_upload_tool(
    member_id: str,
    file_key: str,
    document_date: str,
    document_type: str = "CARE-701B",
) -> dict[str, Any]:
    """
    Upload a document to TrueCare and attach it to a member record.
    
    Returns upload_success (bool), document_id, and attachment_confirmed.
    """
    try:
        input_data = DocumentUploadInput(
            member_id=member_id,
            file_key=file_key,
            document_date=document_date,
            document_type=document_type,
        )
        result = _run_async(truecare_document_upload(input_data))
        return result.model_dump()
    except Exception as exc:
        return {"error": True, "reason": str(exc)}


@mcp.tool()
def truecare_create_case_note_tool(
    member_id: str,
    document_id: str,
    note_template: str = "CARE-701B-STANDARD",
    fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a case note in TrueCare for a member.
    
    Returns note_created (bool), note_id, and note_content.
    """
    try:
        input_data = CaseNoteInput(
            member_id=member_id,
            document_id=document_id,
            note_template=note_template,
            fields=fields or {},
        )
        result = _run_async(truecare_create_case_note(input_data))
        return result.model_dump()
    except Exception as exc:
        return {"error": True, "reason": str(exc)}


@mcp.tool()
def s3_append_log_tool(
    batch_id: str,
    entry: dict[str, Any],
    log_bucket: str = "care701b-logs",
) -> dict[str, Any]:
    """
    Append a PHI-compliant log entry to S3.
    
    Returns log_written (bool) and log_key.
    """
    try:
        input_data = S3LogInput(batch_id=batch_id, entry=entry, log_bucket=log_bucket)
        result = _run_async(s3_append_log(input_data))
        return result.model_dump()
    except Exception as exc:
        return {"error": True, "reason": str(exc)}


@mcp.tool()
def s3_get_object_tool(
    bucket: str,
    key: str,
) -> dict[str, Any]:
    """
    Retrieve an object from S3.
    
    Returns object metadata and content.
    """
    try:
        result = _run_async(s3_get_object(bucket, key))
        # Don't include binary content in response
        result.pop("content", None)
        return result
    except Exception as exc:
        return {"error": True, "reason": str(exc)}


def main() -> None:
    """Stdio entry point for the MCP TrueCare server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
