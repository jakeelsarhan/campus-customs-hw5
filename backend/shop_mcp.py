"""Call Campus Customs MCP tools from the FastAPI layer (no second DB tools)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

HW5 = Path(__file__).resolve().parents[1]
MCP_DIR = HW5 / "mcp_server"
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

from server import mcp  # noqa: E402  (FastMCP app with all shop tools)


def _unwrap(result: Any) -> Any:
    """FastMCP.call_tool returns (content_blocks, structured) or structured alone."""
    if isinstance(result, tuple) and len(result) == 2:
        _blocks, structured = result
        if structured is not None:
            return structured
        return _blocks
    return result


async def call_mcp(tool: str, arguments: dict[str, Any] | None = None) -> Any:
    raw = await mcp.call_tool(tool, arguments or {})
    return _unwrap(raw)
