# Campus Customs ops desk — design notes

## Feel

The board is meant to feel like a **Chapel Street shop counter after opening**, not a generic SaaS dashboard. Soft paper light, a navy ink brand mark, and a brass “approve & pay” control. The page should be something a manager would leave pinned on a second monitor.

## Type & color

- **Fraunces** for the shop name and ticket titles (a little editorial, not Inter).
- **Figtree** for UI chrome.
- **IBM Plex Mono** for live agent feeds (reads like a dispatch log).
- Palette: deep navy (`#0F2A3D`), warm paper, blotter blue-gray, brass for money actions. Teal / forest / bronze / slate mark the five agent lanes without neon or purple-gradient clichés.

## Layout

Three columns on a wide desk:

1. **Ticket rail (left)** — the three tickets as selectable slips. Status badges (`open`, `running`, `waiting_approval`, `resolved`) sit on each slip so you always know where money or stock is stuck.
2. **Agent stage (center)** — five lanes (Boss, Inventory, Accounting, Facilities, Customer Service). Customer Service spans the full width as the “voice to the board.” While a run is live, lanes pulse when that agent’s events arrive.
3. **Cash + human approve (right)** — checking balance on a dark navy tile so money is always in peripheral vision; approve form underneath with an explicit human name field.

Top bar carries the **Campus Customs** brand at hero scale for the desk, plus Refresh / Reset DB.

## How agents read differently

Each agent lane has its own accent and blurb. The mono feed shows:

- tool calls as `→ tool name`
- returns as `← tool returned`
- delegation text in plain language

After a run, a **summary strip** collapses each agent into one short line (tools used + last useful speech) so you can skim without re-reading the whole log.

## Tickets & cash

- Selecting a ticket prefills the approve form (invoice 501 / $840 for order tickets, rent lease 1 / $2400 for the rent notice).
- **Run** calls `POST /api/tickets/{id}/run` and polls `GET /api/events` so the stage updates while agents work.
- When the run finishes, the ticket flips to **resolved**, unless the team left it **waiting_approval** (or blocked) — then the human pay panel is highlighted instead of faking a resolve.
- **Approve & pay** hits `POST /api/payments/approve`. The cash figure animates a short brass pulse when the balance drops, so the human feels the ledger move.

## Motion (presence, not noise)

1. Ticket slips ease in on load.
2. Active agent lanes get a soft border glow.
3. Cash amount scales/pulses on a successful approved payment.

## Why it should be enjoyable

Operators see **who is talking**, **what tool they touched**, and **whether cash still needs a human** without digging through JSON. The desk metaphor (rail / stage / till) matches how the homework’s multi-agent board is taught in class, and the approve control makes the “agents only prepare pay” rule impossible to miss.
