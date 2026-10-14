"""Campus Customs multi-agent ops team (PydanticAI).

Five roles with full connectivity: any agent may ask any other for help.
Shop facts go through the MCP toolset only — no parallel SQLite tools layer.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPToolset

from audit import append_event, ensure_audit_file
from llm import MAX_DELEGATION_DEPTH, MODEL_NAME, TEAM_LIMITS, make_model
from mcp_access import audit_mcp_tool, make_mcp_toolset
from models import AgentRole, TeamDecision

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

BACKEND = Path(__file__).resolve().parent
PROMPTS = BACKEND / "prompts"

PeerName = Literal[
    "boss",
    "inventory",
    "accounting",
    "facilities",
    "customer_service",
]


@dataclass
class TeamDeps:
    """Shared run state for the whole agent team."""

    run_id: str
    ticket_id: int | None = None
    depth: int = 0
    max_depth: int = MAX_DELEGATION_DEPTH
    agents_involved: list[str] = field(default_factory=list)

    def child(self) -> TeamDeps:
        return TeamDeps(
            run_id=self.run_id,
            ticket_id=self.ticket_id,
            depth=self.depth + 1,
            max_depth=self.max_depth,
            agents_involved=list(self.agents_involved),
        )


def _load_prompt(name: str) -> str:
    path = PROMPTS / f"{name}.md"
    return path.read_text(encoding="utf-8")


def _note(deps: TeamDeps, agent: str, step: str, detail: Any) -> None:
    if agent not in deps.agents_involved:
        deps.agents_involved.append(agent)
    append_event(run_id=deps.run_id, agent=agent, step=step, detail=detail)


def _build_agent(role: AgentRole, mcp_toolset: MCPToolset) -> Agent[TeamDeps, str]:
    return Agent(
        make_model(),
        deps_type=TeamDeps,
        system_prompt=_load_prompt(role),
        toolsets=[mcp_toolset],
        name=role,
        # gpt-6-luna rejects function tools unless reasoning is off
        # on the chat.completions path Portkey exposes.
        model_settings={
            "temperature": 0,
            "thinking": False,
            "openai_reasoning_effort": "none",
        },
    )


# MCP toolset + agents are created once per process.
# Shop facts only through MCP; each call is appended to output/audit_trail.json.
_mcp_toolset = make_mcp_toolset(process_tool_call=audit_mcp_tool)

boss_agent: Agent[TeamDeps, str] = _build_agent("boss", _mcp_toolset)
inventory_agent: Agent[TeamDeps, str] = _build_agent("inventory", _mcp_toolset)
accounting_agent: Agent[TeamDeps, str] = _build_agent("accounting", _mcp_toolset)
facilities_agent: Agent[TeamDeps, str] = _build_agent("facilities", _mcp_toolset)
customer_service_agent: Agent[TeamDeps, str] = _build_agent(
    "customer_service", _mcp_toolset
)

_AGENTS: dict[PeerName, Agent[TeamDeps, str]] = {
    "boss": boss_agent,
    "inventory": inventory_agent,
    "accounting": accounting_agent,
    "facilities": facilities_agent,
    "customer_service": customer_service_agent,
}


async def _delegate(
    ctx: RunContext[TeamDeps],
    from_agent: PeerName,
    to_agent: PeerName,
    request: str,
) -> str:
    """Ask another agent for help. Depth-capped to control tokens."""
    if from_agent == to_agent:
        return f"Cannot delegate to yourself ({from_agent})."
    if ctx.deps.depth >= ctx.deps.max_depth:
        return (
            f"Delegation depth limit ({ctx.deps.max_depth}) reached; "
            f"handle '{request}' with MCP tools you have, or return to Boss."
        )
    _note(
        ctx.deps,
        from_agent,
        "delegate",
        {"to": to_agent, "request": request, "depth": ctx.deps.depth},
    )
    child = ctx.deps.child()
    peer = _AGENTS[to_agent]
    result = await peer.run(
        request,
        deps=child,
        usage_limits=TEAM_LIMITS,
    )
    text = result.output if isinstance(result.output, str) else str(result.output)
    # Merge involvement upward
    for name in child.agents_involved:
        if name not in ctx.deps.agents_involved:
            ctx.deps.agents_involved.append(name)
    _note(
        ctx.deps,
        to_agent,
        "delegate_result",
        {"from": from_agent, "output": text},
    )
    return text


def _register_peers(agent: Agent[TeamDeps, str], self_name: PeerName) -> None:
    peers = [p for p in _AGENTS if p != self_name]

    async def ask_boss(ctx: RunContext[TeamDeps], request: str) -> str:
        """Ask Boss for a final call or priority decision."""
        return await _delegate(ctx, self_name, "boss", request)

    async def ask_inventory(ctx: RunContext[TeamDeps], request: str) -> str:
        """Ask Inventory about stock, shortfalls, or vendor restock."""
        return await _delegate(ctx, self_name, "inventory", request)

    async def ask_accounting(ctx: RunContext[TeamDeps], request: str) -> str:
        """Ask Accounting about cash, invoices, margins, or payment prep."""
        return await _delegate(ctx, self_name, "accounting", request)

    async def ask_facilities(ctx: RunContext[TeamDeps], request: str) -> str:
        """Ask Facilities about leases, rent due dates, or space facts."""
        return await _delegate(ctx, self_name, "facilities", request)

    async def ask_customer_service(ctx: RunContext[TeamDeps], request: str) -> str:
        """Ask Customer Service to draft a board message (no real email)."""
        return await _delegate(ctx, self_name, "customer_service", request)

    mapping = {
        "boss": ask_boss,
        "inventory": ask_inventory,
        "accounting": ask_accounting,
        "facilities": ask_facilities,
        "customer_service": ask_customer_service,
    }
    for peer in peers:
        agent.tool(mapping[peer])


for _name, _agent in _AGENTS.items():
    _register_peers(_agent, _name)


async def run_boss_on_ticket(ticket_id: int, extra: str = "") -> TeamDecision:
    """Entry point: Boss works one ticket, delegating as needed."""
    ensure_audit_file()
    run_id = uuid.uuid4().hex[:12]
    deps = TeamDeps(run_id=run_id, ticket_id=ticket_id)
    _note(deps, "boss", "run_start", {"ticket_id": ticket_id, "model": MODEL_NAME})

    prompt = (
        f"Work ticket {ticket_id} end-to-end for this turn. "
        "Use MCP tools for all shop facts. Delegate to teammates as needed. "
        "Do not execute any payment unless a human already provided approved_by "
        "in this message. If payment is required, prepare it and leave the ticket "
        "waiting_approval.\n"
    )
    if extra.strip():
        prompt += f"\nAdditional human instructions:\n{extra.strip()}\n"

    async with _mcp_toolset:
        result = await boss_agent.run(
            prompt,
            deps=deps,
            usage_limits=TEAM_LIMITS,
        )

    output = result.output if isinstance(result.output, str) else str(result.output)
    _note(
        deps,
        "boss",
        "run_end",
        {
            "ticket_id": ticket_id,
            "output": output,
            "agents_involved": deps.agents_involved,
        },
    )

    # Lightweight structured wrap for callers / later FastAPI layer
    lowered = output.lower()
    needs_human = "waiting_approval" in lowered or "human approval" in lowered
    status = "waiting_approval" if needs_human else "open"
    if "resolved" in lowered and not needs_human:
        status = "resolved"
    if "blocked" in lowered and not needs_human:
        status = "blocked"

    return TeamDecision(
        ticket_id=ticket_id,
        status=status,
        decision=output,
        needs_human_approval=needs_human,
        human_action="Provide approved_by for prepared payment" if needs_human else None,
        agents_involved=[a for a in deps.agents_involved if a in _AGENTS],  # type: ignore[misc]
    )


def model_name() -> str:
    return MODEL_NAME
