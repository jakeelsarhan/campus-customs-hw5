"""Call each Campus Customs MCP tool over stdio (same path Cursor uses)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv" / "bin" / "python"
SERVER = ROOT / "mcp_server" / "server.py"


async def call_tool(session: ClientSession, name: str, arguments: dict) -> object:
    result = await session.call_tool(name, arguments)
    # Prefer structured content when present; else parse text content.
    if getattr(result, "structuredContent", None) is not None:
        return result.structuredContent
    chunks: list[object] = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text is None:
            chunks.append(block.model_dump() if hasattr(block, "model_dump") else str(block))
            continue
        try:
            chunks.append(json.loads(text))
        except json.JSONDecodeError:
            chunks.append(text)
    if len(chunks) == 1:
        return chunks[0]
    return chunks


async def main() -> int:
    params = StdioServerParameters(
        command=str(PYTHON),
        args=[str(SERVER)],
        cwd=str(SERVER.parent),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = sorted(t.name for t in tools.tools)

            cases = [
                {
                    "prompt": "Call get_stock_by_sku_size for SKU CC-TEE-WHITE size S (ticket 101).",
                    "tool": "get_stock_by_sku_size",
                    "arguments": {"sku": "CC-TEE-WHITE", "size": "S"},
                },
                {
                    "prompt": "Call get_lease_details for lease_id 1 (ticket 102).",
                    "tool": "get_lease_details",
                    "arguments": {"lease_id": 1},
                },
                {
                    "prompt": "Call get_sku_pricing for SKU CC-HOOD-NAVY (ticket 103).",
                    "tool": "get_sku_pricing",
                    "arguments": {"sku": "CC-HOOD-NAVY"},
                },
            ]

            evidence = []
            for case in cases:
                output = await call_tool(session, case["tool"], case["arguments"])
                evidence.append(
                    {
                        "prompt": case["prompt"],
                        "tool": case["tool"],
                        "arguments": case["arguments"],
                        "output": output,
                    }
                )

            payload = {
                "mcp_config": ".mcp.json (also m.mcp.json and .cursor/mcp.json)",
                "server": "campus-customs",
                "tools_listed": tool_names,
                "tests": evidence,
            }
            out_path = ROOT / "output" / "mcp_smoke.json"
            out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(payload, indent=2))
            print(f"\nWrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
