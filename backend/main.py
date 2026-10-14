"""Campus Customs ops API — FastAPI routes for the React desk dashboard.

Run from this folder:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from audit import AUDIT_PATH, append_event, ensure_audit_file
from llm import MODEL_NAME, MissingModelKey
from shop_mcp import call_mcp
from team import run_boss_on_ticket

HW5 = Path(__file__).resolve().parents[1]
SEED_DB = HW5 / "data" / "campus_customs.db"
WORK_DB = HW5 / "data" / "campus_customs_new.db"
TICKET_IDS = (101, 102, 103)

app = FastAPI(title="Campus Customs Ops", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunTicketBody(BaseModel):
    extra: str = Field(
        default="",
        description="Optional human instructions for this run (not an approval)",
    )


class ApprovePaymentBody(BaseModel):
    kind: Literal["invoice", "rent"]
    ref_id: int
    amount: float
    approved_by: str = Field(..., min_length=1)
    account: str = "checking"


def _ticket_row(data: dict[str, Any]) -> dict[str, Any]:
    status = str(data.get("status") or "unknown")
    # Board cares open vs resolved; also surface waiting_approval / blocked.
    if status == "resolved":
        board_state = "resolved"
    elif status == "open":
        board_state = "open"
    else:
        board_state = status
    return {
        "id": data.get("id"),
        "type": data.get("type"),
        "requester": data.get("requester"),
        "subject": data.get("subject"),
        "status": status,
        "board_state": board_state,
        "sku": data.get("sku"),
        "size": data.get("size"),
        "qty": data.get("qty"),
        "lease_id": data.get("lease_id"),
        "invoice_id": data.get("invoice_id"),
        "notes": data.get("notes"),
        "created_at": data.get("created_at"),
    }


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"ok": "true", "model": MODEL_NAME}


@app.get("/api/tickets")
async def list_tickets() -> dict[str, Any]:
    """Return the three desk tickets and whether each is open or resolved."""
    tickets: list[dict[str, Any]] = []
    for tid in TICKET_IDS:
        raw = await call_mcp("get_ticket", {"ticket_id": tid})
        if not raw.get("found"):
            continue
        tickets.append(_ticket_row(raw))
    return {"tickets": tickets}


@app.post("/api/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int, body: RunTicketBody | None = None) -> dict[str, Any]:
    """Run the agent team on one ticket (Boss + delegates via MCP)."""
    if ticket_id not in TICKET_IDS:
        raise HTTPException(status_code=404, detail=f"Unknown ticket {ticket_id}")
    extra = body.extra if body else ""
    try:
        decision = await run_boss_on_ticket(ticket_id, extra=extra)
    except MissingModelKey as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface agent errors to the board
        raise HTTPException(status_code=500, detail=f"Agent run failed: {exc}") from exc

    # Fresh ticket snapshot after the run
    raw = await call_mcp("get_ticket", {"ticket_id": ticket_id})
    ticket = _ticket_row(raw) if raw.get("found") else {"id": ticket_id}
    return {
        "ticket": ticket,
        "decision": decision.model_dump(),
        "model": MODEL_NAME,
    }


@app.get("/api/events")
async def list_events(
    limit: int = Query(default=80, ge=1, le=500),
    run_id: str | None = None,
) -> dict[str, Any]:
    """Recent agent-loop events for the board (agent, speech, tools)."""
    ensure_audit_file()
    try:
        data = json.loads(AUDIT_PATH.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="audit_trail.json is corrupt") from exc
    if not isinstance(data, list):
        raise HTTPException(status_code=500, detail="audit_trail.json must be a list")

    if run_id:
        data = [e for e in data if e.get("run_id") == run_id]

    # Newest last in file; return newest-last slice for the board to append.
    sliced = data[-limit:]
    events: list[dict[str, Any]] = []
    for row in sliced:
        detail = row.get("detail") if isinstance(row.get("detail"), dict) else {}
        step = row.get("step") or ""
        tool = None
        said = None
        if step == "mcp_tool_call":
            tool = detail.get("tool")
        elif step == "mcp_tool_result":
            tool = detail.get("tool")
        elif step == "delegate":
            said = f"Delegated to {detail.get('to')}: {detail.get('request')}"
        elif step == "delegate_result":
            said = detail.get("output")
        elif step in {"run_start", "run_end"}:
            said = detail.get("output") or detail
        else:
            said = detail.get("output") or detail

        events.append(
            {
                "time": row.get("time"),
                "run_id": row.get("run_id"),
                "agent": row.get("agent"),
                "step": step,
                "said": said,
                "tool": tool,
                "detail": detail,
            }
        )
    return {"count": len(events), "events": events}


@app.post("/api/payments/approve")
async def approve_payment(body: ApprovePaymentBody) -> dict[str, Any]:
    """Human-only cash movement. Agents prepare; this route executes via MCP."""
    approved_by = body.approved_by.strip()
    if not approved_by:
        raise HTTPException(
            status_code=400,
            detail="approved_by is required — agents cannot silently pay",
        )

    ensure_audit_file()
    append_event(
        run_id="human-approve",
        agent="human",
        step="approve_payment_request",
        detail=body.model_dump(),
    )

    result = await call_mcp(
        "execute_approved_payment",
        {
            "kind": body.kind,
            "ref_id": body.ref_id,
            "amount": body.amount,
            "approved_by": approved_by,
            "account": body.account,
        },
    )
    append_event(
        run_id="human-approve",
        agent="human",
        step="approve_payment_result",
        detail=result if isinstance(result, dict) else {"result": result},
    )

    if not isinstance(result, dict) or not result.get("ok"):
        raise HTTPException(
            status_code=400,
            detail=result if isinstance(result, dict) else {"error": str(result)},
        )

    cash = await call_mcp("get_cash_balance", {"account": body.account})
    return {"payment": result, "cash": cash}


@app.get("/api/cash")
async def cash_balance(account: str = "checking") -> dict[str, Any]:
    """Return the checking (or named) balance from cash_accounts via MCP."""
    raw = await call_mcp("get_cash_balance", {"account": account})
    if not raw.get("found"):
        raise HTTPException(status_code=404, detail=f"Account not found: {account}")
    return {
        "name": raw.get("name"),
        "balance": raw.get("balance"),
        "date": raw.get("date"),
    }


@app.post("/api/reset")
async def reset_database() -> dict[str, Any]:
    """Copy seed campus_customs.db over the working campus_customs_new.db."""
    if not SEED_DB.is_file():
        raise HTTPException(status_code=500, detail=f"Missing seed DB: {SEED_DB}")
    WORK_DB.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SEED_DB, WORK_DB)
    ensure_audit_file()
    append_event(
        run_id="system-reset",
        agent="system",
        step="db_reset",
        detail={"seed": str(SEED_DB.name), "work": str(WORK_DB.name)},
    )
    cash = await call_mcp("get_cash_balance", {"account": "checking"})
    tickets = (await list_tickets())["tickets"]
    return {
        "ok": True,
        "message": "Working database reset from seed",
        "cash": cash,
        "tickets": tickets,
    }
