# Campus Customs — multi-agent ops desk (HW 5)

Agentic shop ops for Campus Customs: FastMCP tools over SQLite, a PydanticAI team (Boss, Inventory, Accounting, Facilities, Customer Service), FastAPI routes, and a React ticket board with human-approved payments.

Model: **`gpt-6-luna`** via Portkey (`PORTKEY_API_KEY`). Do not commit a real `.env`.

## Layout

- `data/campus_customs.db` — original seed (leave intact)
- `data/campus_customs_new.db` — working copy the MCP server and backend use
- `mcp_server/` — FastMCP shop tools
- `backend/` — FastAPI + agent team
- `frontend/` — React + Vite ops desk
- `output/` — harness, desk tickets, resolve evidence, screenshots

## API key

```bash
cp .env.example .env   # or put PORTKEY_API_KEY in the class-root .env
# edit .env with your key — never push .env
```

The backend loads `.env` by walking up from `backend/` until it finds one.

## Clean database (original → working copy)

When you want a fresh run:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

Or with the API running: `POST http://localhost:8000/api/reset` (same copy).

**Reset the DB before a full three-ticket resolve** so cash and tickets match the seed ($3,400 checking, three open tickets).

## Python env

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Start MCP server

```bash
source .venv/bin/activate
cd mcp_server
python server.py
```

Cursor / Claude Code can also load `.mcp.json` at the project root (stdio → `.venv` + `mcp_server/server.py`).

## Start FastAPI backend

```bash
source .venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
```

API: `http://localhost:8000` (CORS allows `http://localhost:5173`).

## Start the React board

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Pick a ticket, run the team, approve pays in the Human approve panel when asked.

## Suggested full resolve order

1. Reset DB (`cp` or `POST /api/reset`)
2. Start backend + frontend (MCP tools are invoked by the backend agent team)
3. Resolve tickets on the board (human-approve rent / invoice when prompted)
4. Confirm checking balance matches `cash_accounts` in `data/campus_customs_new.db`

## Output for graders

See `output/desk_tickets.html` (Expected / Actual / Cash / Reflection), `output/resolved_tickets.json`, `output/resolved_board.html`, `output/harness.md`, and `output/github_url.txt`.
