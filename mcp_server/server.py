"""Campus Customs MCP server (FastMCP).

All shop facts and money/ticket mutations go through these tools.
Agents must not invent stock, rent, cash, or invoice data.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from db import connect, row_to_dict, rows_to_dicts

mcp = FastMCP("campus-customs")


# --- reads: clock, tickets, stock, pricing, vendors, leases, cash, invoices ---


@mcp.tool()
def get_shop_today() -> dict[str, Any]:
    """Return desk.date_today and desk notes — the shop's clock for overdue checks."""
    with connect() as conn:
        row = conn.execute("SELECT date_today, notes FROM desk LIMIT 1").fetchone()
    data = row_to_dict(row)
    if data is None:
        return {"found": False}
    return {"found": True, **data}


@mcp.tool()
def list_open_tickets() -> dict[str, Any]:
    """List every ticket with status = open (board view)."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, type, requester, subject, sku, size, qty, lease_id,
                   invoice_id, status, notes, created_at
            FROM tickets
            WHERE status = 'open'
            ORDER BY id
            """
        ).fetchall()
    return {"count": len(rows), "tickets": rows_to_dicts(rows)}


@mcp.tool()
def get_ticket(ticket_id: int) -> dict[str, Any]:
    """Load one ticket by id, including links to sku/size/qty/lease/invoice."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, type, requester, subject, sku, size, qty, lease_id,
                   invoice_id, status, notes, created_at
            FROM tickets
            WHERE id = ?
            """,
            (ticket_id,),
        ).fetchone()
    data = row_to_dict(row)
    if data is None:
        return {"found": False, "ticket_id": ticket_id}
    return {"found": True, **data}


@mcp.tool()
def get_stock_by_sku_size(sku: str, size: str) -> dict[str, Any]:
    """Look up on-hand quantity for one SKU and size from inventory."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT sku, name, size, qty, location
            FROM inventory
            WHERE sku = ? AND size = ?
            """,
            (sku, size),
        ).fetchone()
    data = row_to_dict(row)
    if data is None:
        return {"found": False, "sku": sku, "size": size}
    return {"found": True, **data}


@mcp.tool()
def get_sku_pricing(sku: str) -> dict[str, Any]:
    """Load unit_cost and list_price for one SKU from pricing."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT sku, unit_cost, list_price
            FROM pricing
            WHERE sku = ?
            """,
            (sku,),
        ).fetchone()
    data = row_to_dict(row)
    if data is None:
        return {"found": False, "sku": sku}
    return {"found": True, **data}


@mcp.tool()
def get_vendor(vendor_id: int) -> dict[str, Any]:
    """Load one vendor (name, specialty, lead_days)."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, name, specialty, lead_days
            FROM vendors
            WHERE id = ?
            """,
            (vendor_id,),
        ).fetchone()
    data = row_to_dict(row)
    if data is None:
        return {"found": False, "vendor_id": vendor_id}
    return {"found": True, **data}


@mcp.tool()
def list_vendors() -> dict[str, Any]:
    """List all vendors with specialty and lead_days."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, name, specialty, lead_days
            FROM vendors
            ORDER BY id
            """
        ).fetchall()
    return {"count": len(rows), "vendors": rows_to_dicts(rows)}


@mcp.tool()
def get_lease_details(lease_id: int) -> dict[str, Any]:
    """Load one shop lease by id (space, landlord, rent, next due)."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, space_name, landlord, monthly_rent, next_due, notes
            FROM leases
            WHERE id = ?
            """,
            (lease_id,),
        ).fetchone()
    data = row_to_dict(row)
    if data is None:
        return {"found": False, "lease_id": lease_id}
    return {"found": True, **data}


@mcp.tool()
def get_cash_balance(account: str = "checking") -> dict[str, Any]:
    """Read one cash account balance (default checking)."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT name, balance, date
            FROM cash_accounts
            WHERE name = ?
            """,
            (account,),
        ).fetchone()
    data = row_to_dict(row)
    if data is None:
        return {"found": False, "account": account}
    return {"found": True, **data}


@mcp.tool()
def get_invoice(invoice_id: int) -> dict[str, Any]:
    """Load one vendor invoice by id."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, vendor_id, amount, due_date, status, description
            FROM invoices
            WHERE id = ?
            """,
            (invoice_id,),
        ).fetchone()
    data = row_to_dict(row)
    if data is None:
        return {"found": False, "invoice_id": invoice_id}
    return {"found": True, **data}


@mcp.tool()
def list_open_invoices_for_vendor(vendor_id: int) -> dict[str, Any]:
    """List open (unpaid) invoices for a vendor — blocks new shipments if any exist."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, vendor_id, amount, due_date, status, description
            FROM invoices
            WHERE vendor_id = ? AND status = 'open'
            ORDER BY due_date, id
            """,
            (vendor_id,),
        ).fetchall()
    return {
        "vendor_id": vendor_id,
        "open_count": len(rows),
        "can_ship_new_product": len(rows) == 0,
        "invoices": rows_to_dicts(rows),
    }


@mcp.tool()
def vendor_can_accept_order(vendor_id: int) -> dict[str, Any]:
    """Shop rule check: vendor may accept a new order only with zero open invoices."""
    with connect() as conn:
        vendor = conn.execute(
            """
            SELECT id, name, specialty, lead_days
            FROM vendors
            WHERE id = ?
            """,
            (vendor_id,),
        ).fetchone()
        if vendor is None:
            return {"found": False, "vendor_id": vendor_id, "allowed": False}
        open_rows = conn.execute(
            """
            SELECT id, amount, due_date, status, description
            FROM invoices
            WHERE vendor_id = ? AND status = 'open'
            """,
            (vendor_id,),
        ).fetchall()
    return {
        "found": True,
        "vendor_id": vendor_id,
        "vendor_name": vendor["name"],
        "specialty": vendor["specialty"],
        "lead_days": vendor["lead_days"],
        "open_invoice_count": len(open_rows),
        "open_invoices": rows_to_dicts(open_rows),
        "allowed": len(open_rows) == 0,
        "reason": (
            "ok"
            if len(open_rows) == 0
            else "vendor has open unpaid invoice(s); will not ship new product"
        ),
    }


# --- writes: notes, ticket status, approved payments only ---


@mcp.tool()
def append_ticket_notes(ticket_id: int, note: str) -> dict[str, Any]:
    """Append a note / customer draft to a ticket. Does not email anyone."""
    note = (note or "").strip()
    if not note:
        return {"ok": False, "error": "note is empty"}
    with connect() as conn:
        row = conn.execute(
            "SELECT id, notes FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
        if row is None:
            return {"ok": False, "error": "ticket not found", "ticket_id": ticket_id}
        prior = row["notes"] or ""
        updated = f"{prior}\n{note}".strip() if prior else note
        conn.execute(
            "UPDATE tickets SET notes = ? WHERE id = ?",
            (updated, ticket_id),
        )
        conn.commit()
    return {"ok": True, "ticket_id": ticket_id, "notes": updated}


@mcp.tool()
def update_ticket_status(ticket_id: int, status: str) -> dict[str, Any]:
    """Set ticket status (e.g. open, waiting_approval, resolved)."""
    status = (status or "").strip().lower()
    allowed = {"open", "waiting_approval", "resolved", "blocked"}
    if status not in allowed:
        return {
            "ok": False,
            "error": f"status must be one of {sorted(allowed)}",
            "ticket_id": ticket_id,
        }
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
        if row is None:
            return {"ok": False, "error": "ticket not found", "ticket_id": ticket_id}
        conn.execute(
            "UPDATE tickets SET status = ? WHERE id = ?",
            (status, ticket_id),
        )
        conn.commit()
    return {"ok": True, "ticket_id": ticket_id, "status": status}


@mcp.tool()
def prepare_payment_request(
    kind: str,
    ref_id: int,
    amount: float,
    account: str = "checking",
) -> dict[str, Any]:
    """Build a payment proposal for human approval. Does not move cash.

    kind: 'invoice' (ref_id = invoice id) or 'rent' (ref_id = lease id).
    """
    kind = (kind or "").strip().lower()
    if kind not in {"invoice", "rent"}:
        return {"ok": False, "error": "kind must be 'invoice' or 'rent'"}
    if amount <= 0:
        return {"ok": False, "error": "amount must be positive"}

    with connect() as conn:
        cash = conn.execute(
            "SELECT name, balance, date FROM cash_accounts WHERE name = ?",
            (account,),
        ).fetchone()
        if cash is None:
            return {"ok": False, "error": f"unknown account {account}"}
        desk = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
        today = desk["date_today"] if desk else None

        detail: dict[str, Any]
        if kind == "invoice":
            inv = conn.execute(
                """
                SELECT id, vendor_id, amount, due_date, status, description
                FROM invoices WHERE id = ?
                """,
                (ref_id,),
            ).fetchone()
            if inv is None:
                return {"ok": False, "error": "invoice not found", "ref_id": ref_id}
            detail = row_to_dict(inv) or {}
            if abs(float(inv["amount"]) - float(amount)) > 0.001:
                return {
                    "ok": False,
                    "error": "amount does not match invoice.amount",
                    "invoice_amount": inv["amount"],
                    "requested_amount": amount,
                }
            if inv["status"] != "open":
                return {
                    "ok": False,
                    "error": f"invoice status is {inv['status']}, not open",
                }
        else:
            lease = conn.execute(
                """
                SELECT id, space_name, landlord, monthly_rent, next_due, notes
                FROM leases WHERE id = ?
                """,
                (ref_id,),
            ).fetchone()
            if lease is None:
                return {"ok": False, "error": "lease not found", "ref_id": ref_id}
            detail = row_to_dict(lease) or {}
            if abs(float(lease["monthly_rent"]) - float(amount)) > 0.001:
                return {
                    "ok": False,
                    "error": "amount does not match lease.monthly_rent",
                    "monthly_rent": lease["monthly_rent"],
                    "requested_amount": amount,
                }

        affordable = float(cash["balance"]) >= float(amount)
    return {
        "ok": True,
        "needs_human_approval": True,
        "kind": kind,
        "ref_id": ref_id,
        "amount": amount,
        "account": account,
        "cash_balance": cash["balance"],
        "affordable": affordable,
        "shop_today": today,
        "detail": detail,
        "instruction": (
            "Call execute_approved_payment only after a human sets approved_by. "
            "Do not invent an approver name."
        ),
    }


@mcp.tool()
def execute_approved_payment(
    kind: str,
    ref_id: int,
    amount: float,
    approved_by: str,
    account: str = "checking",
) -> dict[str, Any]:
    """Pay an invoice or rent after human approval. Refuses without approved_by or cash.

    Updates cash_accounts (no negative balances), inserts payments, and marks
    invoices paid when kind='invoice'. Cash only goes out — no revenue credit.
    """
    kind = (kind or "").strip().lower()
    approved_by = (approved_by or "").strip()
    if kind not in {"invoice", "rent"}:
        return {"ok": False, "error": "kind must be 'invoice' or 'rent'"}
    if not approved_by:
        return {
            "ok": False,
            "error": "human approval required: approved_by cannot be empty",
        }
    if amount <= 0:
        return {"ok": False, "error": "amount must be positive"}

    with connect() as conn:
        desk = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
        today = desk["date_today"] if desk else None
        cash = conn.execute(
            "SELECT name, balance, date FROM cash_accounts WHERE name = ?",
            (account,),
        ).fetchone()
        if cash is None:
            return {"ok": False, "error": f"unknown account {account}"}
        if float(cash["balance"]) < float(amount):
            return {
                "ok": False,
                "error": "insufficient cash; payment refused (no negative balances)",
                "balance": cash["balance"],
                "amount": amount,
            }

        if kind == "invoice":
            inv = conn.execute(
                "SELECT id, amount, status FROM invoices WHERE id = ?",
                (ref_id,),
            ).fetchone()
            if inv is None:
                return {"ok": False, "error": "invoice not found", "ref_id": ref_id}
            if inv["status"] != "open":
                return {"ok": False, "error": f"invoice already {inv['status']}"}
            if abs(float(inv["amount"]) - float(amount)) > 0.001:
                return {
                    "ok": False,
                    "error": "amount does not match invoice.amount",
                    "invoice_amount": inv["amount"],
                }
        else:
            lease = conn.execute(
                "SELECT id, monthly_rent FROM leases WHERE id = ?",
                (ref_id,),
            ).fetchone()
            if lease is None:
                return {"ok": False, "error": "lease not found", "ref_id": ref_id}
            if abs(float(lease["monthly_rent"]) - float(amount)) > 0.001:
                return {
                    "ok": False,
                    "error": "amount does not match lease.monthly_rent",
                    "monthly_rent": lease["monthly_rent"],
                }

        new_balance = float(cash["balance"]) - float(amount)
        conn.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
            (new_balance, today or cash["date"], account),
        )
        cur = conn.execute(
            """
            INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (kind, ref_id, amount, account, today, approved_by),
        )
        payment_id = cur.lastrowid
        if kind == "invoice":
            conn.execute(
                "UPDATE invoices SET status = 'paid' WHERE id = ?",
                (ref_id,),
            )
        conn.commit()

    return {
        "ok": True,
        "payment_id": payment_id,
        "kind": kind,
        "ref_id": ref_id,
        "amount": amount,
        "account": account,
        "approved_by": approved_by,
        "paid_at": today,
        "new_balance": new_balance,
    }


@mcp.tool()
def record_restock_plan(
    sku: str,
    size: str,
    qty: int,
    vendor_id: int,
    ticket_id: int,
) -> dict[str, Any]:
    """Record a restock plan on the ticket after vendor-can-ship checks.

    Does not invent stock or call real vendors. Refuses if the vendor has an
    open unpaid invoice. Does not change inventory qty (goods have not arrived).
    """
    if qty <= 0:
        return {"ok": False, "error": "qty must be positive"}
    with connect() as conn:
        vendor = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?",
            (vendor_id,),
        ).fetchone()
        if vendor is None:
            return {"ok": False, "error": "vendor not found", "vendor_id": vendor_id}
        open_inv = conn.execute(
            """
            SELECT id FROM invoices
            WHERE vendor_id = ? AND status = 'open'
            """,
            (vendor_id,),
        ).fetchall()
        if open_inv:
            return {
                "ok": False,
                "error": "vendor will not ship while they have an open unpaid invoice",
                "vendor_id": vendor_id,
                "open_invoice_ids": [r["id"] for r in open_inv],
            }
        stock = conn.execute(
            """
            SELECT sku, name, size, qty FROM inventory
            WHERE sku = ? AND size = ?
            """,
            (sku, size),
        ).fetchone()
        ticket = conn.execute(
            "SELECT id, notes FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
        if ticket is None:
            return {"ok": False, "error": "ticket not found", "ticket_id": ticket_id}
        desk = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
        today = desk["date_today"] if desk else "?"
        plan = (
            f"[restock_plan {today}] sku={sku} size={size} qty={qty} "
            f"vendor_id={vendor_id} ({vendor['name']}) lead_days={vendor['lead_days']} "
            f"on_hand={stock['qty'] if stock else 'missing'}"
        )
        prior = ticket["notes"] or ""
        updated = f"{prior}\n{plan}".strip() if prior else plan
        conn.execute(
            "UPDATE tickets SET notes = ? WHERE id = ?",
            (updated, ticket_id),
        )
        conn.commit()
    return {
        "ok": True,
        "ticket_id": ticket_id,
        "plan": plan,
        "vendor_name": vendor["name"],
        "lead_days": vendor["lead_days"],
    }


if __name__ == "__main__":
    mcp.run()
