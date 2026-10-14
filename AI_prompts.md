# AI Prompts Log — Homework 5

Log of this Cursor chat. Updated as we work. This file is a rolling log of what was typed to the vibe coder.

One section per problem. Each section has the problem number and title, the prompt typed, and any follow-up prompt.

---

## Problem 1: Vibe coder prompts

**Status:** done (2026-10-14 18:07). Created `AI_prompts.md` and locked the log format.

### Prompt 1

**Student (2026-10-14 18:05):**

> Okay, we need to do homework five. So the scenario, campus customs multi-agent operations is the agentic team that runs the shop. Open tickets land on a board, customer orders, rent, unpaid bills, discount requests, whatever the shop has to handle. We'll build three pieces that talk to each other, an MCP server, a fast API backend with a multi-agent team, and a React dashboard, so a human can watch the agents at work and approve requests. Your agent team has full connectivity, any agent may delegate tasks to any other agent for help, and this assignment will build the following agents. Boss reads each ticket, decides who should work on it, and makes final calls. Inventory, check stock by SKU and size, spots shortfalls, and figure out which vendor can restock. Accounting watches cash and invoices, checks margins, and prepares payments or purchase orders for human approval. Facilities handles the shop space side, leases, rent, et cetera, and then customer service drafts messages for customers. so data.zip should be in the folder. Unzip it so we have data/campus_customs.db. That file is the original shop database. Tables include desk, tickets, inventory, pricing, vendors, leases, cash_accounts, payments, and invoices. Our tools will update the databases, tickets get resolved, make a copy of the database file called data/campus_customs_new.db, and point the MCP server in the backend at that working copy. Keep campus_customs.db untouched so we can reset when we want to restart resolving the tickets. So the rules of the shop The field desk.date_today is today for the shop. Use this date to determine what is overdue. Vendor lead times come from the vendors table. A vendor won't ship new product while they have an open unpaid invoice. Human approval is required for any payments. Points will be deducted if this is not done. If payment is made, make sure to update the relevant table. If there's not enough cash, the pay tool must refuse. No negative balances. Cash only goes out in this homework. We did not model revenue, so no money comes in. Before a full run to resolve the tickets, make sure to reset databases to the original values. Do not, under any circumstances, email customers or call real vendors. Draft stay on the board. Use portkey_API_key for AI calls for this assignment. Use only gpt-six.luna through portkey for every agent. Multi-agent chats burn tokens fast. points will be deducted if any other model shows up in your code or runs. Work one problem at a time with Vibecoder. Type each problem in your own words. final submission will be a public GitHub repo.

### Prompt 2

**Why a second prompt was needed:** The first message set the homework scenario and data rules. It did not ask to create the prompts log file for Problem 1.

**Student (2026-10-14 18:07):**

> Create AI_prompts.md at the start of the assignment and keep it updated as we work. It's the log of what we typed into the Vibecoder. put one section for each problem. Each section must include the problem number and title, at least one prompt we typed and one follow-up prompt if it's needed. So this is problem one, Vibecoder prompts.

---

## Problem 2: Study the Campus Customs database

**Status:** done (2026-10-14 18:09). Copied `data/campus_customs_new.db`. Wrote table/field notes and ticket-link walkthrough in `output/harness.md`.

### Prompt 1

**Student (2026-10-14 18:09):**

> Problem two, study the campus customs database. Open data/campus_customs.db and look through every table and fields. Copy the original file to data/campus_customs_new.db.. Later problems update that working copy. Study the three open tickets so we see how they link to other tables. Start outputs, start output/harness.md. For each table, list the fields in one short line and why the table matters for the agents. We'll keep growing this harness file in later problems.

No follow-up prompt.

---

## Problem 3: Build the MCP server

**Status:** done (2026-10-14 18:12). FastMCP server in `mcp_server/` with three ticket-tied tools; harness and README updated. Not connected/run yet.

### Prompt 1

**Student (2026-10-14 18:12):**

> Problem three, build the MCP server. Write an MCP server in mcp_server/using fastMCP. It's gonna talk to data/custom, it's going to talk to data/campus_customs_new.db. We do not need to connect or run it in this problem. So every agent in this homework will use the tools in this MCP server. We'll need to add more tools to it later. For now, just write three tools you know you will need for the tickets in the database. Keep the names clear, never invent any data, only use information in the database. In output/harness.md, list each of the three MCP tools. For every tool include which table it reads, which ticket it helps unlock 101, 102, or 103, and one sentence on why that tool is the right one for that ticket. Vague lines like "reads inventory" will score low. Tie the tool to the ticket. Also, add a short MCP_server/readme.md file that explains what the MCP server is for, which database file it uses, and the three tools it has.

No follow-up prompt.

---

## Problem 4: Add the MCP server to vibe coder and test each tool

**Status:** done (2026-10-14 18:14). Wrote `.mcp.json` / `m.mcp.json` / `.cursor/mcp.json`. Ran each tool over MCP stdio; saved `output/mcp_smoke.json` (outputs match the working DB).

### Prompt 1

**Student (2026-10-14 18:14):**

> Problem four, add the MCP server to the Vibecoder and test each tool. In the Vibecoder, add your MCP server to this project so the Vibecoder can call the tools. Save the connection json text in m.mcp.json at the project root, or however the Vibecoder is saving local MCP server lists. With the Vibecoder connected, test each of the three MCP tools. Save the evidence in output/mcp_smoke.json. For every tool, include the prompt you asked the Vibecoder, the tool name, and the tool output, which must match the values in data/campus_customs_new.dv.

No follow-up prompt.

---

## Problem 5: Build the agent team and grow the MCP tools

**Status:** done (2026-10-14 18:19). Five PydanticAI agents (Boss, Inventory, Accounting, Facilities, Customer Service) with full connectivity, `gpt-6-luna` only via Portkey, expanded MCP tools, append-only `output/audit_trail.json`, harness safety section, MCP README updated.

### Prompt 1

**Student (2026-10-14 18:19):**

> Problem five. Build the agent team and grow the MCP tools. Build the agentic team for campus customers using Pydantic AI, boss, inventory, accounting, facilities, and customer service. Include prompts, models, and agent loops so they can delegate work with full connectivity. Put the agent prompts in backend/prompts/one file per agent. Put data types in backend/models.pi and the agent files under backend slash the layout can vary as long as the five roles are clear. use the port key_API_key and only GPT/six/Luna for every agent. Write each prompt in your own words with the shop rules that agent needs. More detailed prompts can cover all aspects of an agent's work and scope score higher than a short generic prompt. Add any tools the agents need to the MCP server so they can work on the open tickets. Shop facts come from the MCP server over data/campus_customs_new.db. Don't invent a 2nd shop tools layer that bypasses MCP. Wire the agents so they append to output/audit_trail.json as they run. For each agent loop step, record enough so we can audit, audit it later. Append to this file, do not wipe it each run. In output/harness.md, list each agent in each MCP tool, including ones we add in this problem, along with which table the tool uses. Also, add a short safety section. The guardrails a real business would want when agents touch real customers and real money, plus limits that keep token use in check. Update mcp_server/readme.md so the tool list matches what we have now.

No follow-up prompt.

---

## Problem 6: Plan the three tickets

**Status:** done (2026-10-14 18:34). Wrote `output/desk_tickets.html` with Expected plans for 101/102/103; Actual empty; Cash and Reflection stubs for later.

### Prompt 1

**Student (2026-10-14 18:34):**

> Problem six, plan the three tickets. Before we wire the backend, write down what you expect the team to do on each open ticket. Build output/desk_tickets.html, a page we can double-click with one tab per ticket, 101, 102, and 103. Also add empty cache and reflection tabs for later problems, leave them blank or with a short coming later note for now. On each ticket tab, fill an expected section only. Leave room for an actual section we'll fill after we run the agents. For each ticket's expected section, write in your own words. Who the boss should call 1st and why, all the agent delegations you expect, not boss calls everyone, and then which MCP tools we expect that run to use. Plans that every, plans that send every specialist on every ticket score low, we'll compare this plan to what actually happens when our agents resolve the three tickets.

No follow-up prompt.

---

## Problem 7: Backend routes

**Status:** done (2026-10-14 18:38). FastAPI routes in `backend/main.py` (tickets, run, events, human approve-pay, cash, reset). Harness route list updated.

### Prompt 1

**Student (2026-10-14 18:38):**

> Backend seven, problem routes. Your React front-end dashboard, the next problem needs a backend it can call. In backend/main.pi, use FastAPI and add routes that do the following. Return the three tickets and whether each is open or resolved, take a ticket ID and run the agent team on that ticket. Return recent agent events, what agent, what each agent said and what tools they used, so the board can refresh. Approve a payment or purchase after a human clicks approve, agents only prepare the pay, this route is what actually changes cash. Return checking account balance from cash account, cash_accounts. Reset the database to the original values when we want to try a fresh run. From the backend/folder, start the server with unicorn main colon app dash-reload space-dash port space 8000. This turns on the backend at HTTP Colon slash/localhost colon 8000, so the front-end dashboard can call those routes. In output/harness.md, list each route in one line, what URL/what it does.

No follow-up prompt.

---

## Problem 8: Agent dashboard

**Status:** done (2026-10-14 18:40). React + Vite + TypeScript desk in `frontend/`; talks to `http://localhost:8000`; design notes in `output/design.md`.

### Prompt 1

**Student (2026-10-14 18:40):**

> Problem eight, agent dashboard. Build the front-end dashboard in front-end slash with react plus vite plus typescript. The page should call the routes we built in problem seven. At minimum, the board should list all three tickets. Let us pick one ticket and start the agent team on it. Show each agent and what they are saying/doing while the ticket runs. Mark a ticket resolves when the run finishes. Show a short summary of what each agent did on the ticket. Let a human approve or pay, let a human approve a pay or purchase when asked. Show the checking balance. It should drop after an approved pay. Make the dashboard look good. Be creative with layout and feel. This is a real desk people would want to sit at, so put thought into how it looks. Tell the front end to talk to back end at http colon slash/localhost colon 8000 on the back end, allow the Vite page origin, usually http colon slash/localhost colon 5173, so the browser is allowed to call these routes. Start the board with npm space run space dev. This opens the React desk in the browser, so we can pick tickets and watch agents write output/design.md with what we chose for the dashboard look, layout, how agents read differently, how result tickets and cash show up, and why, including the creative choices that make it feel special and something humans would actually enjoy using.

No follow-up prompt.

---

## Problem 9: Resolve the tickets

**Status:** done (2026-10-14 18:53). Reset DB; resolved 101/102/103 with human pays; cash $3400→$160; filled Actual + Cash on `desk_tickets.html`; wrote `resolved_tickets.json`, `resolved_board.html` screenshots; audit appended; harness finished.

### Prompt 1

**Student (2026-10-14 18:46):**

> Problem nine, resolve the tickets. Before testing the agents on a full run over the three tickets, reset the working database data/campus_customs_new.db, again, so we start clean. Note the starting checking balance, then run all three tickets on the board, 101, 102, 103, until each is resolved. Open output/desk_tickets.html from problem six. On each ticket tab, fill the actual section from this run. Which agents worked, what they delegated, and which tools they used. Keep your expected section so we can now compare the two. On the cash tab of the same output/desk_tickets.html, itemize the money. Starting checking balance after the reset for each ticket, how cash changed when that ticket resolved and why. Which pay/purchase dollar amount ending checking balance it must match, cash_accounts in the working database. Wrong cash math loses points even if the board shows every ticket resolved. Also save output/resolve_tickets.json for each ticket ID. Final status, short outcome, what each agent contributed, and any human approvals. output/resolved_board.html, a page we can double click with a screenshot of your react board for each resolved ticket, 101, 102, and 103. Append real runs to output/audit_trail.json. Finish output/harness.md so it covers tables, MCP tools, the five agents, API routes. The dashboard and safety rules.

No follow-up prompt.

### Follow-up (tooling)

**Why needed:** First agent call failed — Portkey/`gpt-6-luna` rejects function tools unless `reasoning_effort` is `none`. Set `thinking: False` and `openai_reasoning_effort: "none"` on every agent, then re-ran the full resolve.

---

## Problem 10: Reflection

**Status:** done (2026-10-14 18:57). Filled the Reflection tab on `output/desk_tickets.html` with ticket-tied evaluation, Expected vs Actual, one-agent comparison, and solvable / unsolvable problem sets.

### Prompt 1

**Student (2026-10-14 18:57):**

> Problem 10, reflection. Open output/desk_tickets.html and fill the reflection tab. Answer in your own vibe and be detailed and thorough. How would you evaluate the performance of the agent on each ticket and why? For each ticket, how did actual compare to expected plan we wrote earlier? What would have been simpler as one agent with tools and why? Describe three new problems campus customs might face that this agent team could solve with the tools you built. Describe three new problems campus customs might face that this agent team could not solve with the tools we built and explain the tools and agents we would need to solve them. Tie every answer to this app and the three tickets we ran. Use the ticket tabs and cash tab on the same page as the evidence. generic AI essays without campus customs details will score low.

No follow-up prompt.

---

## Problem 11: Submit to GitHub

**Status:** done (2026-10-14 19:00). Public repo https://github.com/jakeelsarhan/campus-customs-hw5 — no real `.env`; both DBs under `data/`; URL in `output/github_url.txt`.

### Prompt 1

**Student (2026-10-14 18:59):**

> Problem eleven, submit to GitHub, push code to a public GitHub repository so graders can clone it. do not push the real.env to GitHub repo. Do include both database files under data slash, the, both the original and the working copy, so graders can run the app easily. Submit the repo URL to canvas and also put it in output/GitHub_URL.text. Readme should explain, copy original DB to the working copy when we need a clean run, start MCP server, start fast API backend, start the React board, reset the DB before a full three ticket run.

No follow-up prompt.
