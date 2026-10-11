"""Extract tool-call traces from Pydantic AI messages."""

from __future__ import annotations

import json
from typing import Any


def extract_tool_trace(messages: list[Any]) -> list[dict[str, Any]]:
    """Return `{tool_name, args, return_value}` rows from agent messages (FR-24)."""
    pending: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for message in messages:
        kind = type(message).__name__
        parts = getattr(message, "parts", None) or []
        for part in parts:
            part_kind = type(part).__name__
            name = getattr(part, "tool_name", None) or getattr(part, "name", None)
            args = getattr(part, "args", None)
            tool_call_id = getattr(part, "tool_call_id", None) or getattr(part, "id", None)
            content = getattr(part, "content", None)
            if "ToolCall" in part_kind or (name and args is not None and "Return" not in part_kind):
                parsed_args = args
                if isinstance(args, str):
                    try:
                        parsed_args = json.loads(args)
                    except json.JSONDecodeError:
                        parsed_args = args
                record = {"tool_name": name or "", "args": parsed_args, "return_value": None}
                if tool_call_id:
                    pending[str(tool_call_id)] = record
                rows.append(record)
            elif "ToolReturn" in part_kind or (name and content is not None and "ToolCall" not in part_kind):
                value = content
                if isinstance(content, str):
                    try:
                        value = json.loads(content)
                    except json.JSONDecodeError:
                        value = content
                if tool_call_id and str(tool_call_id) in pending:
                    pending[str(tool_call_id)]["return_value"] = value
                elif rows:
                    rows[-1]["return_value"] = value
        del kind
    return rows
