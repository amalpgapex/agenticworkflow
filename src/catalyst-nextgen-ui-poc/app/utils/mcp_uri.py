
# app/utils/mcp_uri.py
from urllib.parse import urlparse

def build_mcp_uri(mcp_base_url: str, skill_id: str, logical_name: str | None = None) -> str:

    """
    Generates the MCP URI for a skill.

    - If logical_name is defined (recommended for stability and portability):
        mcp://<logical-name>/tools/<skillId>

    - If not defined (derived from the current MCP base URL, useful for local/dev environments):
        mcp://<host>:<port><path>/tools/<skillId>
        Example: mcp://localhost:8000/mcp/tools/diff-documents
    """

    if logical_name:
        return f"mcp://{logical_name}/tools/{skill_id}"

    parsed = urlparse(mcp_base_url)
    host_port = parsed.netloc or "localhost"
    base_path = parsed.path.rstrip("/") or "/mcp"
    return f"mcp://{host_port}{base_path}/tools/{skill_id}"


