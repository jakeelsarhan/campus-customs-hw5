"""Shared MCP toolset — the only path from agents to shop data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic_ai.mcp import CallToolFunc, MCPToolset, ProcessToolCallback, StdioTransport
from pydantic_ai import RunContext

HW5 = Path(__file__).resolve().parents[1]
PYTHON = HW5 / ".venv" / "bin" / "python"
SERVER = HW5 / "mcp_server" / "server.py"


def make_mcp_toolset(
    process_tool_call: ProcessToolCallback | None = None,
) -> MCPToolset:
    """Stdio MCP client aimed at mcp_server/server.py (campus_customs_new.db)."""
    if not PYTHON.is_file():
        raise FileNotFoundError(f"Missing venv python: {PYTHON}")
    if not SERVER.is_file():
        raise FileNotFoundError(f"Missing MCP server: {SERVER}")
    transport = StdioTransport(
        command=str(PYTHON),
        args=[str(SERVER)],
        cwd=str(SERVER.parent),
    )
    return MCPToolset(transport, process_tool_call=process_tool_call)


async def audit_mcp_tool(
    ctx: RunContext[Any],
    call_tool: CallToolFunc,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    """Wrap every MCP tool call with an audit_trail.json append."""
    from audit import append_event

    deps = ctx.deps
    run_id = getattr(deps, "run_id", "unknown")
    agent = getattr(ctx, "agent", None)
    agent_name = getattr(agent, "name", None) or "unknown"
    append_event(
        run_id=run_id,
        agent=str(agent_name),
        step="mcp_tool_call",
        detail={"tool": tool_name, "arguments": arguments},
    )
    result = await call_tool(tool_name, arguments)
    append_event(
        run_id=run_id,
        agent=str(agent_name),
        step="mcp_tool_result",
        detail={"tool": tool_name, "result": result},
    )
    return result
