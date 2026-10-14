# Campus Customs MCP server

FastMCP server that gives the shop’s agent team access to the working Campus Customs database. Every agent in this homework must call these tools instead of inventing stock, rent, cash, or invoice facts.

## Database

- Path: `data/campus_customs_new.db` (relative to the HW 5 folder)
- Working copy only. Reset by copying `data/campus_customs.db` → `data/campus_customs_new.db`.

## Tools

| Tool | Tables | Purpose |
|------|--------|---------|
| `get_shop_today` | `desk` | Shop clock (`date_today`) for overdue checks |
| `list_open_tickets` | `tickets` | Board of open tickets |
| `get_ticket` | `tickets` | One ticket with sku/size/lease/invoice links |
| `get_stock_by_sku_size` | `inventory` | On-hand qty for one SKU + size |
| `get_sku_pricing` | `pricing` | `unit_cost` / `list_price` for margin checks |
| `get_vendor` | `vendors` | One vendor (specialty, lead_days) |
| `list_vendors` | `vendors` | All vendors |
| `get_lease_details` | `leases` | Space, landlord, rent, next_due |
| `get_cash_balance` | `cash_accounts` | Available cash (default `checking`) |
| `get_invoice` | `invoices` | One vendor invoice |
| `list_open_invoices_for_vendor` | `invoices` | Open invoices + `can_ship_new_product` |
| `vendor_can_accept_order` | `vendors`, `invoices` | Shop rule: no ship with open unpaid invoice |
| `append_ticket_notes` | `tickets` | Board notes / customer drafts (no real email) |
| `update_ticket_status` | `tickets` | e.g. `open`, `waiting_approval`, `resolved`, `blocked` |
| `prepare_payment_request` | `cash_accounts`, `invoices` / `leases`, `desk` | Payment proposal; does **not** move cash |
| `execute_approved_payment` | `cash_accounts`, `payments`, `invoices`, `desk` | Pays only with human `approved_by`; refuses if cash short |
| `record_restock_plan` | `tickets`, `vendors`, `invoices`, `inventory`, `desk` | Notes a restock plan; refuses if vendor blocked |

## Connect in vibe coder

Project root configs (same `campus-customs` entry):

- `.mcp.json`
- `m.mcp.json`
- `.cursor/mcp.json`

```bash
cd mcp_server
../.venv/bin/python server.py
```

Smoke client: `../.venv/bin/python smoke_mcp_client.py` → `output/mcp_smoke.json`.
