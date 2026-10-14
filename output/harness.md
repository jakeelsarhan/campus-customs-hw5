# Campus Customs — harness notes

Working database for agents/tools: `data/campus_customs_new.db` (copy of the seed).  
Untouched reset seed: `data/campus_customs.db`.  
Shop “today” from seed: `desk.date_today` = **2026-08-31**.

---

## Tables

### `desk`

| Field | Why it matters |
|-------|----------------|
| `date_today` | Shop clock. Agents use this (not the real calendar) for overdue rent/invoices and lead-time math. |
| `notes` | Free-text desk memo; optional context for ops. |

**For agents:** Every overdue / due-soon judgment starts here.

### `tickets`

| Field | Why it matters |
|-------|----------------|
| `id` | Ticket key on the board (101, 102, 103 open in seed). |
| `type` | Routes work (`customer_order`, `rent_notice`, `price_override`, …). |
| `requester` | Who opened it (customer, landlord, org). |
| `subject` | Short title for the board / Boss triage. |
| `sku`, `size`, `qty` | Product ask when the ticket is inventory- or price-related. |
| `lease_id` | Link to `leases` for rent/facilities tickets. |
| `invoice_id` | Link to `invoices` when a vendor bill is in play. |
| `status` | `open` / resolved; agents update this as work finishes. |
| `notes` | Human-readable detail (drafts stay here; no real email). |
| `created_at` | When the ticket landed. |

**For agents:** Boss reads these; other agents resolve them by walking the foreign keys into inventory, leases, invoices, pricing.

### `inventory`

| Field | Why it matters |
|-------|----------------|
| `sku` | Product id (with `size` forms the PK). |
| `name` | Display name for drafts and board notes. |
| `size` | Size dimension of stock. |
| `qty` | On-hand count; shortfalls drive restock / vendor work. |
| `location` | Aisle / bin for shop floor context. |

**For agents:** Inventory agent checks stock by SKU+size before fulfilling orders or quoting bulk.

### `pricing`

| Field | Why it matters |
|-------|----------------|
| `sku` | Product priced. |
| `unit_cost` | Cost basis for margin checks. |
| `list_price` | Sticker price before any override/discount. |

**For agents:** Accounting (and Boss) need cost vs list to judge discount / PO economics.

### `vendors`

| Field | Why it matters |
|-------|----------------|
| `id` | Vendor key; invoices point here. |
| `name` | Who would reprint / restock. |
| `specialty` | What they can supply (apparel, mugs, courier). |
| `lead_days` | How long until new stock can arrive (from this table only). |

**For agents:** Inventory picks a vendor by specialty + lead time; rule: no new ship while that vendor has an open unpaid invoice.

### `leases`

| Field | Why it matters |
|-------|----------------|
| `id` | Lease key; tickets may set `lease_id`. |
| `space_name` | Which space the rent covers. |
| `landlord` | Payee / facilities contact. |
| `monthly_rent` | Amount Facilities / Accounting prepare for approval. |
| `next_due` | Compared to `desk.date_today` for due/overdue. |
| `notes` | Lease caveats. |

**For agents:** Facilities owns the space side; Accounting prepares the rent payment for human approval.

### `cash_accounts`

| Field | Why it matters |
|-------|----------------|
| `name` | Account id (seed: `checking`). |
| `balance` | Available cash; pay tool must refuse if amount > balance (no negatives). |
| `date` | Balance-as-of date aligned with shop time. |

**For agents:** Accounting gates every outflow. Cash only goes out in this homework (no revenue modeled).

### `payments`

| Field | Why it matters |
|-------|----------------|
| `id` | Payment record id. |
| `kind` | What was paid (rent, invoice, …). |
| `ref_id` | Points at lease / invoice / related row. |
| `amount` | Cash leaving the account. |
| `account` | Which `cash_accounts.name` was debited. |
| `paid_at` | When paid (shop time). |
| `approved_by` | Human approver — required; no silent pays. |

**For agents:** Empty in the seed. Tools append rows only after human approval and a successful cash check.

### `invoices`

| Field | Why it matters |
|-------|----------------|
| `id` | Invoice key; tickets may set `invoice_id`. |
| `vendor_id` | Which vendor is owed (`vendors`). |
| `amount` | Dollars due. |
| `due_date` | Overdue if before `desk.date_today`. |
| `status` | e.g. `open` until paid. |
| `description` | What the bill covers (e.g. rush reprint). |

**For agents:** Accounting prepares payment; an open unpaid invoice blocks that vendor from shipping new product.

---

## Three open tickets (how they link)

Shop today: **2026-08-31**. Checking balance: **$3,400**.

### Ticket 101 — `customer_order` (Tauhid Zaman / Bulldog tee)

- Asks for `sku=CC-TEE-WHITE`, `size=S`, `qty=1`.
- Inventory: Classic Bulldog Tee size S has **`qty=0`** → shortfall; cannot fulfill from stock.
- Linked `invoice_id=501`: Bulldog Print Co (`vendors.id=1`) owes an **open** rush-reprint invoice for CC-TEE-WHITE S, **$840**, due **2026-08-28** → **past due** vs desk today.
- Rule conflict for restock: vendor lead_days=5, but they **will not ship** while invoice 501 is open unpaid.
- Pricing for the SKU: cost $8 / list $28 (margin context if Accounting is involved).
- Agents in play: Inventory (stock + vendor), Accounting (pay invoice with human approval, cash check), Boss (order of ops), Customer Service (draft reply — stay on the board).

### Ticket 102 — `rent_notice` (Elm City Properties / Rent due)

- Linked `lease_id=1`: Chapel Street shop, landlord Elm City Properties, **$2,400**/mo, `next_due=2026-09-02` (due in 2 days; not overdue yet).
- Notes say rent due in 2 days — matches lease vs desk date.
- Cash: $3,400 ≥ $2,400, so a rent pay is affordable **after** human approval; paying this first still leaves $1,000 before invoice 501 ($840).
- Agents in play: Facilities (lease/rent facts), Accounting (prepare payment), Boss (approve path), Customer Service / board draft only (no real landlord email).

### Ticket 103 — `price_override` (Yale AI Club / Bulk hoodie discount)

- Asks for `sku=CC-HOOD-NAVY`, `size=M`, `qty=20`, bulk discount.
- Inventory: size M has **`qty=8`** → short by 12; need restock path and/or partial plan.
- Pricing: cost $22 / list $58 → Accounting checks margin on any discount; Boss makes the final call.
- No `lease_id` / `invoice_id` on this ticket; vendors for apparel reprint is Bulldog Print Co (same open invoice issue as 101 if they are the restock source).
- Agents in play: Inventory, Accounting, Boss, Customer Service (draft to the club).

---

## Reset note

Before a full ticket-resolving run, copy `campus_customs.db` → `campus_customs_new.db` again so tools start from seed values.

---

## MCP tools (Problem 3)

Server lives in `mcp_server/` (FastMCP). It only reads `data/campus_customs_new.db` — no invented rows.

### `get_stock_by_sku_size(sku, size)`

| | |
|--|--|
| **Table** | `inventory` |
| **Ticket** | **101** (`customer_order` for `CC-TEE-WHITE` / `S`) |
| **Why this tool** | Ticket 101 is a size-S tee order; this tool returns the real `qty` for that SKU/size (seed: **0**), so Inventory/Boss know the order cannot ship from stock and must treat restock as blocked until related vendor work is handled. |

### `get_lease_details(lease_id)`

| | |
|--|--|
| **Table** | `leases` |
| **Ticket** | **102** (`rent_notice`, `lease_id=1`) |
| **Why this tool** | Ticket 102 is a landlord rent notice keyed to lease 1; this tool returns `monthly_rent` (**2400**) and `next_due` (**2026-09-02**) so Facilities/Accounting can prepare the exact rent payment against shop today, instead of guessing from the email wording. |

### `get_sku_pricing(sku)`

| | |
|--|--|
| **Table** | `pricing` |
| **Ticket** | **103** (`price_override` for `CC-HOOD-NAVY` bulk discount) |
| **Why this tool** | Ticket 103 asks for a bulk hoodie discount; this tool returns `unit_cost` (**22**) and `list_price` (**58**) for that SKU so Accounting can check margin before Boss approves any override. |

---

## MCP connection + smoke test (Problem 4)

- Project MCP config: `.mcp.json` at HW 5 root (also `m.mcp.json` and Cursor `.cursor/mcp.json`).
- Server name: `campus-customs` → runs `mcp_server/server.py` with the HW 5 `.venv` Python.
- Evidence: `output/mcp_smoke.json` — each of the three tools called over MCP stdio; outputs match `data/campus_customs_new.db`.

---

## Agent team (Problem 5)

PydanticAI team in `backend/`. Model for **every** agent: **`gpt-6-luna`** via Portkey (`PORTKEY_API_KEY` in class-root `.env`). Full connectivity: each agent has `ask_*` tools for every other role. Shop facts only through the MCP toolset (`backend/mcp_access.py` → `mcp_server/server.py` → `data/campus_customs_new.db`). No second SQLite tools layer.

| Agent | Prompt file | Role |
|-------|-------------|------|
| Boss | `backend/prompts/boss.md` | Triage tickets, route work, final calls (discounts, payment priority, resolve/block) |
| Inventory | `backend/prompts/inventory.md` | Stock by SKU/size, shortfalls, vendor restock eligibility |
| Accounting | `backend/prompts/accounting.md` | Cash, invoices, margins, payment prep; never pay without human `approved_by` |
| Facilities | `backend/prompts/facilities.md` | Leases, rent timing vs `desk.date_today` |
| Customer Service | `backend/prompts/customer_service.md` | Drafts onto ticket notes only — no real email/calls |

Entry point: `backend/run_ticket.py --ticket 101` (Boss-led turn).  
Audit: append-only `output/audit_trail.json` (MCP calls + delegations + run start/end). Never wiped on startup.

Types: `backend/models.py`. Limits: `backend/llm.py` (`REQUEST_LIMIT=8`, `TOOL_CALLS_LIMIT=12`, `MAX_DELEGATION_DEPTH=3`).

---

## MCP tools — full list (Problems 3 + 5)

| Tool | Table(s) |
|------|----------|
| `get_shop_today` | `desk` |
| `list_open_tickets` | `tickets` |
| `get_ticket` | `tickets` |
| `get_stock_by_sku_size` | `inventory` |
| `get_sku_pricing` | `pricing` |
| `get_vendor` | `vendors` |
| `list_vendors` | `vendors` |
| `get_lease_details` | `leases` |
| `get_cash_balance` | `cash_accounts` |
| `get_invoice` | `invoices` |
| `list_open_invoices_for_vendor` | `invoices` |
| `vendor_can_accept_order` | `vendors`, `invoices` |
| `append_ticket_notes` | `tickets` |
| `update_ticket_status` | `tickets` |
| `prepare_payment_request` | `cash_accounts`, `invoices` / `leases`, `desk` |
| `execute_approved_payment` | `cash_accounts`, `payments`, `invoices`, `desk` |
| `record_restock_plan` | `tickets`, `vendors`, `invoices`, `inventory`, `desk` |

---

## Safety & token guardrails (Problem 5)

### Business / money / customer guardrails

- **Human approval for payments** — `execute_approved_payment` requires non-empty `approved_by`; empty or invented approvers are refused. Agents must stop at `prepare_payment_request` until a human approves.
- **No negative cash** — pay tool refuses when balance &lt; amount.
- **Cash out only** — no fabricated revenue/deposits in this homework.
- **Vendor credit hold** — no new ship / `record_restock_plan` while the vendor has an open unpaid invoice.
- **Shop clock** — overdue logic uses `desk.date_today`, not the wall clock.
- **No real outreach** — drafts stay on the ticket board (`append_ticket_notes`). Never email customers or call vendors/landlords.
- **Facts only from MCP** — agents must not invent stock, prices, rent, or balances; no parallel DB access layer in `backend/`.
- **Audit trail** — every delegation and MCP tool call appends to `output/audit_trail.json` for later review.

### Token / loop limits

- Model fixed to **`gpt-6-luna`** only (no other model strings in agent code).
- Per-run usage limits: max **8** model requests and **12** tool calls (`UsageLimits`).
- Delegation depth capped at **3** to stop agent↔agent ping-pong.
- Prompts tell agents to ask short, concrete peer questions.
- Prefer one Boss-led ticket turn at a time; reset DB before a full board run.

---

## Backend routes (Problem 7)

FastAPI app: `backend/main.py`. Start from `backend/`:

`uvicorn main:app --reload --port 8000` → `http://localhost:8000`

| Route | What it does |
|-------|----------------|
| `GET /api/health` | Liveness + model name (`gpt-6-luna`) |
| `GET /api/tickets` | Three desk tickets with status (open / resolved / waiting_approval / …) via MCP `get_ticket` |
| `POST /api/tickets/{id}/run` | Run the agent team on that ticket; returns decision + updated ticket |
| `GET /api/events?limit=` | Recent `audit_trail.json` rows shaped for the board (agent, said, tool) |
| `POST /api/payments/approve` | **Human-only** cash move via MCP `execute_approved_payment` (requires `approved_by`) |
| `GET /api/cash` | Checking balance from `cash_accounts` via MCP |
| `POST /api/reset` | Copy `campus_customs.db` → `campus_customs_new.db` for a fresh run |

---

## Frontend desk (Problem 8)

- App: `frontend/` (React + Vite + TypeScript). API base `http://localhost:8000`.
- CORS on backend allows `http://localhost:5173`.
- Start: `cd frontend && npm run dev`
- Design write-up: `output/design.md`
- Board shows ticket rail, five agent lanes, checking balance, human approve form.

---

## Full resolve run (Problem 9)

Reset `data/campus_customs_new.db` from seed, then resolved tickets **101 → 102 → 103** order used for cash: **102 (rent), 101 (invoice), 103 (discount)**.

| Step | Cash |
|------|------|
| After reset | **$3,400.00** |
| After ticket 102 human rent pay ($2,400) | **$1,000.00** |
| After ticket 101 human invoice 501 pay ($840) | **$160.00** |
| After ticket 103 (no pay) | **$160.00** |
| DB `cash_accounts.checking` | **$160.00** ✓ (`3400 − 2400 − 840`) |

Evidence files:

- `output/desk_tickets.html` — Expected kept; Actual filled; Cash tab itemized
- `output/resolved_tickets.json` (and `resolve_tickets.json`) — per-ticket status, agents, approvals
- `output/resolved_board.html` + `output/screenshots/ticket-10x-resolved.png`
- `output/audit_trail.json` — append-only real agent/MCP steps from the run

All three tickets `status=resolved` in the working DB. Invoice 501 `paid`. Two `payments` rows (rent + invoice) with `approved_by=Jake (human desk)`.

---

## Harness checklist (complete)

| Area | Where documented |
|------|------------------|
| Tables + ticket links | Top of this file (Problem 2) |
| MCP tools + tables | Problem 3 / 5 tool tables |
| Five agents + prompts | Problem 5 agent table |
| API routes | Problem 7 route table |
| Dashboard | Problem 8 + `output/design.md` |
| Safety + token limits | Problem 5 safety section |
| Resolve cash math | Problem 9 section above |
| Reflection | `output/desk_tickets.html` → Reflection tab (Problem 10) |
