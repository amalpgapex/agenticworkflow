
# app/utils/skill_descriptor_auto.py
from typing import Any, Dict, Optional
import re

from config import MCP_BASE_URL, MCP_LOGICAL_NAME
from app.utils.mcp_uri import build_mcp_uri

DOC_DIRECTIVE_PATTERNS = {
    "files": re.compile(r"^@files:\s*(.+)$", re.IGNORECASE),
    "inputs": re.compile(r"^@inputs:\s*(.+)$", re.IGNORECASE),
    "output": re.compile(r"^@output:\s*(.+)$", re.IGNORECASE),
    "prompt": re.compile(r"^@prompt:\s*(.+)$", re.IGNORECASE),
    "type": re.compile(r"^@type:\s*(.+)$", re.IGNORECASE),
    "name": re.compile(r"^@name:\s*(.+)$", re.IGNORECASE),
}

def _parse_doc_directives(doc: Optional[str]) -> Dict[str, Any]:
    """
    Optional docstring directives:
      @name: Excel Column Alignment
      @type: processing
      @files: min=2 max=2 exact=2 desc=Exactly 2 Excel files required
      @inputs: file1_path|xlsx,xls; file2_path|xlsx,xls; user_options|json
      @output: json; guarantees: Pairs aligned semantically|Similarity statistics included
      @prompt: false
    """
    hints: Dict[str, Any] = {}
    if not doc:
        return hints

    # Normalize lines and match each directive by pattern
    lines = [l.strip() for l in doc.splitlines() if l.strip()]
    for line in lines:
        for key, pattern in DOC_DIRECTIVE_PATTERNS.items():
            m = pattern.match(line)
            if not m:
                continue
            val = m.group(1).strip()

            if key == "name":
                hints["skillName"] = val
            elif key == "type":
                hints["skillType"] = val
            elif key == "prompt":
                # Normalize truthy values: true/1/yes/y
                hints["requiresPrompt"] = val.lower() in ("true", "1", "yes", "y")
            elif key == "files":
                # Build inputFileRequirements from tokens: min, max, exact, desc
                req: Dict[str, Any] = {}
                for token in re.split(r"\s+", val):
                    if "=" in token:
                        k, v = token.split("=", 1)
                        k = k.strip().lower()
                        v = v.strip()
                        if k in ("min", "minfiles"):
                            req["minFiles"] = int(v)
                        elif k in ("max", "maxfiles"):
                            req["maxFiles"] = int(v)
                        elif k in ("exact", "exactfiles"):
                            req["exactFiles"] = int(v)
                        elif k in ("desc", "description"):
                            req["description"] = v
                hints["inputFileRequirements"] = req
            elif key == "inputs":
                # Build entryCriteria.requiredInputs and entryCriteria.inputFormats
                required: list[str] = []
                formats: set[str] = set()
                for part in val.split(";"):
                    part = part.strip()
                    if not part:
                        continue
                    if "|" in part:
                        nm, fmts = part.split("|", 1)
                        required.append(nm.strip())
                        for f in fmts.split(","):
                            f = f.strip()
                            if f:
                                formats.add(f)
                    else:
                        required.append(part)
                hints["entryCriteria"] = {
                    "requiredInputs": required or ["document"],
                    "inputFormats": sorted(list(formats)) or ["*"]
                }
            elif key == "output":
                # Build exitCriteria.outputFormat and exitCriteria.guarantees
                output_format = "txt"
                guarantees: list[str] = []
                parts = [p.strip() for p in val.split(";") if p.strip()]
                for p in parts:
                    if p.lower().startswith("guarantees:"):
                        gs = p.split(":", 1)[1]
                        guarantees = [g.strip() for g in gs.split("|") if g.strip()]
                    else:
                        output_format = p
                hints["exitCriteria"] = {
                    "outputFormat": output_format or "txt",
                    "guarantees": guarantees
                }

    return hints


def build_skill_descriptor_for(instance: Any) -> Dict[str, Any]:
    """Auto-generates the skill descriptor from the instance + docstring + defaults."""
    # Resolve skillId from instance attributes, falling back to class name
    skill_id = (
        getattr(instance, "NAME", None)
        or getattr(instance, "name", None)
        or instance.__class__.__name__.replace("Tool", "").lower()
    )
    # Resolve skillName from instance attributes, falling back to a titled skill_id
    skill_name = (
        getattr(instance, "DISPLAY_NAME", None)
        or getattr(instance, "display_name", None)
        or str(skill_id).replace("-", " ").title()
    )
    # Resolve skillType from instance or default to "processing"
    skill_type = getattr(instance, "SKILL_TYPE", "processing")

    # Parse optional docstring directives
    doc = getattr(instance, "__doc__", None)
    hints = _parse_doc_directives(doc)

    # Default descriptor values (overridden by hints when present)
    input_file_reqs = {"minFiles": 1, "maxFiles": 1, "exactFiles": 1, "description": "One input required"}
    entry_criteria = {"requiredInputs": ["document"], "inputFormats": ["*"]}
    exit_criteria = {"outputFormat": "txt", "guarantees": []}
    requires_prompt = False

    if hints.get("inputFileRequirements"): input_file_reqs.update(hints["inputFileRequirements"])
    if hints.get("entryCriteria"):         entry_criteria.update(hints["entryCriteria"])
    if hints.get("exitCriteria"):          exit_criteria.update(hints["exitCriteria"])
    if "requiresPrompt" in hints:          requires_prompt = hints["requiresPrompt"]
    skill_name = hints.get("skillName", skill_name)
    skill_type = hints.get("skillType", skill_type)

    # Build the final descriptor including an MCP URI and the execution endpoint
    return {
        "skillId": str(skill_id),
        "skillName": str(skill_name),
        "skillType": str(skill_type),
        "mcpUri": build_mcp_uri(MCP_BASE_URL, str(skill_id), logical_name=MCP_LOGICAL_NAME),
        "inputFileRequirements": input_file_reqs,
        "entryCriteria": entry_criteria,
        "exitCriteria": exit_criteria,
        "requiresPrompt": requires_prompt,
        "executionEndpoint": "/api/tool/execute",
    }
