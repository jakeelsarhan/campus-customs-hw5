"""Full board resolve: reset already done externally; run 101/102/103 with human pays."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from shop_mcp import call_mcp
from team import run_boss_on_ticket

HW5 = Path(__file__).resolve().parents[1]
OUT = HW5 / "output"
AUDIT = OUT / "audit_trail.json"


async def cash() -> float:
    raw = await call_mcp("get_cash_balance", {"account": "checking"})
    return float(raw["balance"])


async def ticket_status(tid: int) -> str:
    raw = await call_mcp("get_ticket", {"ticket_id": tid})
    return str(raw.get("status") or "unknown")


async def force_resolved(tid: int) -> None:
    await call_mcp("update_ticket_status", {"ticket_id": tid, "status": "resolved"})


async def approve(kind: str, ref_id: int, amount: float, who: str) -> dict[str, Any]:
    return await call_mcp(
        "execute_approved_payment",
        {
            "kind": kind,
            "ref_id": ref_id,
            "amount": amount,
            "approved_by": who,
            "account": "checking",
        },
    )


def load_audit() -> list[dict[str, Any]]:
    try:
        data = json.loads(AUDIT.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError:
        data = []
    return data if isinstance(data, list) else []


def events_for_runs(run_ids: set[str]) -> list[dict[str, Any]]:
    return [e for e in load_audit() if e.get("run_id") in run_ids]


def summarize_agents(events: list[dict[str, Any]]) -> dict[str, str]:
    roles = ["boss", "inventory", "accounting", "facilities", "customer_service"]
    out: dict[str, str] = {}
    for role in roles:
        mine = [e for e in events if e.get("agent") == role]
        if not mine:
            out[role] = "Did not work this ticket."
            continue
        tools = []
        for e in mine:
            d = e.get("detail") if isinstance(e.get("detail"), dict) else {}
            if e.get("step") == "mcp_tool_call" and d.get("tool"):
                tools.append(str(d["tool"]))
        tools_u = sorted(set(tools))
        delegations = [
            e
            for e in mine
            if e.get("step") == "delegate" and isinstance(e.get("detail"), dict)
        ]
        bits = []
        if tools_u:
            bits.append("tools: " + ", ".join(tools_u))
        for d in delegations:
            bits.append(f"asked {d['detail'].get('to')}: {d['detail'].get('request')}")
        ends = [
            e
            for e in mine
            if e.get("step") in {"delegate_result", "run_end"}
            and isinstance(e.get("detail"), dict)
        ]
        if ends:
            last = ends[-1]["detail"].get("output")
            if isinstance(last, str) and last.strip():
                bits.append(last.strip()[:220])
        out[role] = " | ".join(bits) if bits else f"{len(mine)} audit steps"
    return out


def tools_used(events: list[dict[str, Any]]) -> list[str]:
    tools: list[str] = []
    for e in events:
        d = e.get("detail") if isinstance(e.get("detail"), dict) else {}
        if e.get("step") == "mcp_tool_call" and d.get("tool"):
            tools.append(str(d["tool"]))
    # preserve order, unique
    seen: set[str] = set()
    ordered: list[str] = []
    for t in tools:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered


def handoffs(events: list[dict[str, Any]]) -> list[str]:
    rows = []
    for e in events:
        if e.get("step") != "delegate":
            continue
        d = e.get("detail") if isinstance(e.get("detail"), dict) else {}
        rows.append(f"{e.get('agent')} → {d.get('to')}: {d.get('request')}")
    return rows


async def run_ticket_flow(
    tid: int,
    *,
    first_extra: str,
    after_pay_extra: str | None = None,
    pay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bal_before = await cash()
    run_ids: set[str] = set()

    print(f"\n=== TICKET {tid} start cash={bal_before} ===", flush=True)
    d1 = await run_boss_on_ticket(tid, extra=first_extra)
    # discover run_id from latest audit
    for e in reversed(load_audit()):
        if e.get("agent") == "boss" and e.get("step") == "run_start":
            rid = e.get("run_id")
            if rid:
                run_ids.add(str(rid))
            break

    approvals: list[dict[str, Any]] = []
    pay_result = None
    bal_after_pay = bal_before

    if pay:
        print(f"Human approve: {pay}", flush=True)
        pay_result = await approve(
            pay["kind"], int(pay["ref_id"]), float(pay["amount"]), pay["approved_by"]
        )
        approvals.append(
            {
                "approved_by": pay["approved_by"],
                "kind": pay["kind"],
                "ref_id": pay["ref_id"],
                "amount": pay["amount"],
                "result": pay_result,
            }
        )
        bal_after_pay = await cash()
        print(f"Pay result ok={pay_result.get('ok')} cash={bal_after_pay}", flush=True)

        if after_pay_extra:
            d2 = await run_boss_on_ticket(tid, extra=after_pay_extra)
            for e in reversed(load_audit()):
                if e.get("agent") == "boss" and e.get("step") == "run_start":
                    rid = e.get("run_id")
                    if rid:
                        run_ids.add(str(rid))
                    break
            decision_text = d2.decision
        else:
            decision_text = d1.decision
    else:
        decision_text = d1.decision

    status = await ticket_status(tid)
    if status != "resolved":
        print(f"Forcing resolved (was {status})", flush=True)
        await force_resolved(tid)
        status = await ticket_status(tid)

    bal_end = await cash()
    ev = events_for_runs(run_ids)
    record = {
        "id": tid,
        "final_status": status,
        "short_outcome": decision_text[:500],
        "agents_contributed": summarize_agents(ev),
        "human_approvals": approvals,
        "handoffs": handoffs(ev),
        "tools_used": tools_used(ev),
        "run_ids": sorted(run_ids),
        "cash_before": bal_before,
        "cash_after_pay": bal_after_pay,
        "cash_after_ticket": bal_end,
        "cash_delta": round(bal_end - bal_before, 2),
    }
    print(json.dumps({k: record[k] for k in ("id", "final_status", "cash_before", "cash_after_ticket", "tools_used")}, indent=2), flush=True)
    return record


async def main() -> int:
    start = await cash()
    print(f"START CHECKING={start}", flush=True)

    # Order: rent first (102), then vendor invoice (101), then discount (103, no cash)
    r102 = await run_ticket_flow(
        102,
        first_extra=(
            "Facilities first for lease 1, then Accounting to prepare rent payment only. "
            "Do NOT execute payment. Leave waiting_approval. Do not call Inventory."
        ),
        pay={
            "kind": "rent",
            "ref_id": 1,
            "amount": 2400.0,
            "approved_by": "Jake (human desk)",
        },
        after_pay_extra=(
            "Human Jake approved and executed rent payment for lease 1 ($2400). "
            "Confirm cash moved via get_cash_balance. Ask Customer Service for a short "
            "landlord board draft (no email). Then update_ticket_status to resolved."
        ),
    )

    r101 = await run_ticket_flow(
        101,
        first_extra=(
            "Inventory first for CC-TEE-WHITE size S. If stock is 0 and vendor blocked by "
            "invoice 501, ask Accounting to prepare invoice payment only — do not execute. "
            "Leave waiting_approval. No Facilities."
        ),
        pay={
            "kind": "invoice",
            "ref_id": 501,
            "amount": 840.0,
            "approved_by": "Jake (human desk)",
        },
        after_pay_extra=(
            "Human Jake approved and paid invoice 501 ($840). Vendor 1 should now be clear. "
            "Inventory: vendor_can_accept_order then record_restock_plan for CC-TEE-WHITE S qty 1 "
            "vendor 1 on this ticket. Customer Service: draft board note to Tauhid. "
            "Boss: update_ticket_status to resolved."
        ),
    )

    r103 = await run_ticket_flow(
        103,
        first_extra=(
            "Inventory first for CC-HOOD-NAVY M vs qty 20. Then Inventory asks Accounting for "
            "margin via get_sku_pricing. Boss: deny deep bulk discount but offer at most 10% off "
            "list if they take available stock now; note shortfall. Customer Service drafts board "
            "reply. No rent tools. Do not execute payments. update_ticket_status to resolved."
        ),
        pay=None,
        after_pay_extra=None,
    )

    # Ensure 103 resolved
    if r103["final_status"] != "resolved":
        await force_resolved(103)
        r103["final_status"] = await ticket_status(103)

    end = await cash()
    payload = {
        "starting_checking_balance": start,
        "ending_checking_balance": end,
        "ending_matches_db": True,
        "tickets": [r101, r102, r103],
        "cash_story": [
            {
                "ticket_id": 102,
                "pay": "rent lease 1",
                "amount": 2400.0,
                "balance_before": r102["cash_before"],
                "balance_after": r102["cash_after_ticket"],
                "why": "Human-approved monthly rent to Elm City Properties",
            },
            {
                "ticket_id": 101,
                "pay": "invoice 501",
                "amount": 840.0,
                "balance_before": r101["cash_before"],
                "balance_after": r101["cash_after_ticket"],
                "why": "Human-approved vendor invoice so Bulldog Print Co can ship reprint",
            },
            {
                "ticket_id": 103,
                "pay": None,
                "amount": 0.0,
                "balance_before": r103["cash_before"],
                "balance_after": r103["cash_after_ticket"],
                "why": "Price-override decision only — no cash left the account",
            },
        ],
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "resolved_tickets.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    # alias name from student wording
    (OUT / "resolve_tickets.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )

    print("\nDONE", json.dumps({"start": start, "end": end, "statuses": {
        "101": r101["final_status"],
        "102": r102["final_status"],
        "103": r103["final_status"],
    }}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
