# ReturnPilot — viaSocket Backend Architecture

The production backend for ReturnPilot is not FastAPI (see `DECISIONS.md` Decision 17) — it is built natively in **viaSocket**, a no-code AI workflow platform, and none of that configuration lives in this git repository by default. This document is the source-controlled record of what that backend actually is, so it can be inspected without viaSocket UI access.

## Why viaSocket, not the FastAPI backend

Per `DECISIONS.md` Decision 17: mentor feedback plus the track's viaSocket sponsorship prompted a spike test of viaSocket's native **AI Agents** feature (distinct from viaSocket "Flows," which only support single-shot text completion with no tool-calling — that path was tried first and abandoned). The spike passed: the AI Agent genuinely decides when to call tools and exposes that reasoning, which the original FastAPI plan (Tasks 5–18, still unimplemented) would have had to build by hand. The FastAPI code remains in `backend/` as the documented fallback, not the live system.

## Components

### 1. Main chat agent
- **Trigger:** Webhook, wraps viaSocket's native AI Agents feature (not a Flow — Flows don't support tool use).
- **Endpoint:** `POST https://flow.sokt.io/func/scriJDWDZGHv`
- **Request:** `{"customer_id": "cust-001", "message": "..."}`
- **Response:** a JSON-encoded plain string: `"[REASONING_TRACE]\n1. ...\n[/REASONING_TRACE]\n\n<reply>\n\n[RETURN_CREATED]{...}[/RETURN_CREATED]"` — the last block is optional and only present on a successful eligible creation. Consumed by `frontend/src/api.js`'s `parseAgentResponse()`.
- **Model:** OpenAI gpt-4o (not Claude — an open discrepancy against the originally stated stack, never resolved).
- **Tools available to the agent:** Get Table Rows on `orders`, Get Table Rows on `Policies`, Add Records To Table on `returns`. All attached via viaSocket's "Let AI run the App" mode (agent-decided invocation), not "Configure Actions" (which would be an unconditional, non-agentic pipeline step — an earlier build mistake, corrected).

### 2. Get My Returns
- **Endpoint:** `POST https://flow.sokt.io/func/scrinfNHTNQP`
- **Request:** `{"customer_name": "Jordan Reyes"}` — filters by the customer's display name, not `customer_id`.
- **Response:** JSON array of raw return rows, or `{"message": "No data found for the given search."}` when empty (not `[]` — `frontend/src/api.js`'s `getMyReturns()` explicitly guards for this).
- No unfiltered "get all returns" flow exists. The ops dashboard (`frontend/public/ops-dashboard.html`) works around this by calling this endpoint once per hardcoded known customer name and merging client-side.

### 3. Advance Return Status
- **Endpoint:** `POST https://flow.sokt.io/func/scriWZw9Q5vC`
- **Request:** `{"customer_name": "...", "order_id": "...", "item_name": "...", "new_status": "shipped" | "refunded"}`
- Status changes are implemented as **new row inserts** (Add Records), not in-place updates — an Update Row action hit persistent permission errors during setup, so every status transition for a given `order_id` is a separate row, and the latest by `createdat` is treated as current (see `getMyReturns()`'s dedup logic and its mirror in `ops-dashboard.html`).
- Sends a confirmation email via Gmail on every transition, **hardcoded to one test inbox** (`reshanaik15@gmail.com`) for all customers — there is no real per-customer email lookup anywhere in the system, including the "initiated" notification sent from the main agent.

## Data model (viaSocket Databases, workspace `DBdash`)

**`orders`** — `order_id` (numeric), `customer_id`, `item_name`, `category`, `price`, `purchase_date`, `final_sale`

**`returns`** — no native `return_id` column. Real fields: `order_id`, `status`, `reason_`, `customer_name`, `item_name`, plus system fields `rowid`, `autonumber`, `createdat`. `status` must be exactly one of `initiated` / `shipped` / `refunded` / `declined` (a prompt bug once caused a full sentence to be written into this field instead — fixed, but the fix's reliability under repeated live use is not independently re-verified).

**`Policies`** — `category`, `window_days`, `final_sale_excluded`, `exclusions`. **Known reliability issue:** a live test returned "policy details unavailable" for a real category and the agent incorrectly approved a return it should have declined, before a safety-net prompt instruction was added ("if the Policies lookup fails, never default to eligible"). Separately, the Electronics category's `window_days` has returned inconsistent values (10 vs. 15) across different live calls — root cause not diagnosed; the live table's stored value has not been directly inspected to confirm which is correct.

## Current agent system prompt (verbatim, as last confirmed correct in testing)

```
Data (via viaSocket_Table): Orders, Returns, Policies (category, window_days, final_sale_excluded, exclusions).
Customer names: cust-001=Amara Chen, cust-002=Jordan Reyes, cust-003=Priya [surname].
CRITICAL: order_id must be the numeric order_id field from Orders, never the table's internal rowid. If you cannot find a numeric order_id, do not proceed.

1. Look up the order. If ambiguous, ask — don't guess. State the order_id you matched.
2. Check eligibility against Policies (window, final_sale, exclusions). Always state the result.
3. If eligible and confirmed: check Returns for a duplicate on this order_id, then create the record (customer_name, order_id, item_name, reason, status "initiated"), then email confirmation. If a return request is NOT eligible (outside the policy window, excluded item, etc.), still create a record via the Add Records tool — do not skip creation. Set status to "declined" and put the specific ineligibility reason in reason_ (e.g., "outside 30-day return window"). Only skip creating a record if the order itself can't be found at all. The status field must be EXACTLY one of these four literal words: initiated, shipped, refunded, declined — nothing else, never a sentence or explanation. All explanation always goes in reason_ only, never in status.
4. Trust only fresh tool results, never prior claims in this conversation. If a tool call fails or asks a question, stop and say so honestly — never claim success unless confirmed. If the Policies lookup does not return a matching category, do NOT treat the item as eligible and do NOT create a return — tell the customer you're unable to verify eligibility right now, and never guess or default to approving.

Always start every response with:
[REASONING_TRACE]
1. Understood request
2. Order lookup result (state the numeric order_id explicitly, not the row ID)
3. Policy check (category, window, days, final_sale, verdict)
4. Return write result — state the exact return_id returned by the tool, or "failed" if not confirmed
5. Email result — sent or not
[/REASONING_TRACE]

Then write your customer-facing response.

If the return was eligible and successfully created with status "initiated", end with:
[RETURN_CREATED]{"return_id": "<the exact ID the Add Records tool returned>", "order_id": "<the numeric order_id you matched>", "item_name": "<the item name>", "status": "initiated"}[/RETURN_CREATED]
Never include this block for a declined record — only for a real, successful "initiated" creation.
```

## Verified end-to-end (via direct `curl` testing against the live endpoints, this session)

- Vague-language order resolution, including cold/first-touch with no prior conversation context.
- Eligibility approval and eligibility decline, each independently confirmed against real order data with correct policy math.
- Declined requests now create a `status: "declined"` row (not silently skipped) and correctly omit `[RETURN_CREATED]`.
- Status advancement (`initiated` → `shipped`) confirmed via a real write, re-fetched and verified in the raw table data.
- CORS confirmed open for all three endpoints from a browser origin.

## Known unresolved issues

- Electronics policy window inconsistency (10 vs. 15 days) — not diagnosed.
- Response latency 25–46 seconds per message, consistent across dozens of live tests — not addressed.
- Notification email hardcoded to one test inbox for every customer.
- Model is gpt-4o, not Claude, contradicting the originally stated tech stack.
- No unfiltered "all returns" endpoint — the ops dashboard's per-customer-name merge is a workaround, not a scalable solution.
