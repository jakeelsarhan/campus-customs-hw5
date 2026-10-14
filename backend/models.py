"""Structured types for the Campus Customs ops agent team."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


AgentRole = Literal[
    "boss",
    "inventory",
    "accounting",
    "facilities",
    "customer_service",
]


class TicketSummary(BaseModel):
    """Compact ticket view for Boss triage."""

    id: int
    type: str
    requester: str
    subject: str
    status: str
    sku: str | None = None
    size: str | None = None
    qty: int | None = None
    lease_id: int | None = None
    invoice_id: int | None = None
    notes: str | None = None


class AgentStepResult(BaseModel):
    """What one specialist returns to Boss (or a peer)."""

    agent: AgentRole
    summary: str = Field(description="Plain-English outcome of this step")
    facts: dict[str, Any] = Field(default_factory=dict)
    needs_human: bool = False
    blocked: bool = False
    next_hint: str | None = None


class TeamDecision(BaseModel):
    """Boss final wrap-up for a ticket turn."""

    ticket_id: int
    status: str = Field(description="open | waiting_approval | resolved | blocked")
    decision: str
    needs_human_approval: bool = False
    human_action: str | None = None
    drafts_on_board: list[str] = Field(default_factory=list)
    agents_involved: list[AgentRole] = Field(default_factory=list)
