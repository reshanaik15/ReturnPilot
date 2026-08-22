# Notification Flow Playbook

Reference for finishing the ReturnPilot × viaSocket notification flow. Payload shape sourced from `backend/services/notifications.py`.

**Status:** webhook trigger is live and confirmed receiving real payloads. Three things still to build: the send step, AI personalization, and (optionally) conditional branching.

**Verified moments ago:** `POST https://flow.sokt.io/func/scrimQ4U85cJ` → `200 OK`, triggered by a real return (`RET-0002`) initiated through the backend. Open your flow's run history — that event is sitting there right now, with the full payload below, ready to build against.

> **Before you start:** I can't see your viaSocket screen, so exact button/node names below may not match what you see — the underlying pattern (add a step after the trigger, pick an action, map fields from the payload) holds regardless. If something on screen doesn't match, describe what you're looking at and I'll adjust.

---

## Build order

Three things are missing from the flow. Build them in this order — each is usable on its own, so the flow works after step 1 even before you add 2 and 3.

### 1. The send step — build first, makes something actually happen

Right now the trigger fires but nothing is delivered anywhere. This is the only piece actually required for a working demo: an email, SMS, or Slack message that goes out when a return event happens.

### 2. AI personalization — build second, polish

Once something is sending, layer an AI step in front of it to turn the raw `message` field into a warmer, more natural note. Good demo moment, not required for the flow to work.

### 3. Branch by event type — optional, skip for tomorrow unless you need it

The backend already writes a different `message` per event (initiated / shipped / refunded / flagged) — you don't need branching just to vary the text. Only add this if you want different *channels* per event, e.g. SMS only when a return is flagged for review.

---

## 1 · The send step (email, SMS, or Slack)

1. **Open your flow and find the "+" after the webhook trigger node.** This adds the next step in the pipeline, run every time the trigger fires.
2. **Search the action library for your channel.** For a demo, email is the fastest to prove works — search "Email" (viaSocket's built-in sender) or "Gmail" if you want it from your own address. SMS (Twilio) and Slack are both in the same library if you'd rather show one of those.
3. **Map the recipient field.** Click the "To" field, open the variable picker, and select the trigger's `customer.email` field (for email) or `customer.contact` (for SMS). This is dynamic — it changes per customer automatically, you're not hardcoding an address.
4. **Map the body to the trigger's `message` field.** This is already a complete, readable sentence built server-side per event type — safe to send as-is with zero further work.
5. **Save, then trigger a real test.** Tell me and I'll fire a fresh return from the backend — you'll see the run land in your history within seconds, and the email/SMS should arrive right after.

---

## 2 · AI personalization (optional polish)

1. **Insert a step between the trigger and the send step.** Search the action library for an "AI" or "AI Text" block — viaSocket's AI step takes a prompt plus input variables and returns generated text.
2. **Feed it the raw context, not just the fallback message.** Give the prompt access to `trigger_reason`, `customer.name`, `order.item_name`, and `message` — the more fields it sees, the less generic the output.
3. **Write a short, constrained prompt.** For example:

   > Rewrite this return-update notification for {{customer.name}} in one warm, concise paragraph. Event: {{trigger_reason}}. Item: {{order.item_name}}. Base message: {{message}}. Keep it under 40 words, no greeting line, no sign-off.

   Constraining length and format matters more than the prompt being clever.
4. **Point the send step's body at the AI step's output** instead of the raw `message` field. The variable picker in the send step should now list the AI block as a source alongside the trigger fields.

---

## 3 · Branch by event type (skip unless you need per-channel routing)

1. **Add a Router / Filter / Condition step** right after the trigger. Named differently across tools — look for anything that splits the flow into multiple paths based on a field value.
2. **Branch on `trigger_reason`.** Four possible values: `return_initiated`, `return_shipped`, `return_refunded`, `flagged_for_review`. A common demo-worthy split: email for the first three, SMS added for `flagged_for_review` since that one's time-sensitive.
3. **Reconnect each branch to its own send step** (or the same one, if you're only changing channel choice, not content).

---

## Payload reference

Every field the webhook trigger receives, straight from the backend.

| Field | Type | Example |
|---|---|---|
| `return_id` | string | `"RET-0002"` |
| `trigger_reason` | enum | `"return_initiated"` |
| `message` | string | `"Your return has been initiated for…"` |
| `customer.name` | string | `"Jordan Reyes"` |
| `customer.email` | string | `"jordan@demo.dev"` |
| `customer.contact` | string | `""` (often empty in seed data) |
| `order.order_id` | string | `"ORD-2002"` |
| `order.item_name` | string | `"Everyday Sneakers"` |
| `order.price` | number | `89.0` |
| `order.category` | string | `"Footwear"` |
| `return_status` | string | `"initiated"` |
| `timestamp` | string (ISO 8601) | `"2026-08-22T03:30:32Z"` |

Full example payload, exactly as sent:

```json
{
  "return_id": "RET-0002",
  "trigger_reason": "return_initiated",
  "message": "Your return has been initiated for Everyday Sneakers (Order ORD-2002). Return ID: RET-0002. Use label reference RTN-ORD-2002-20260822 for shipping. We'll notify you when we receive your item.",
  "customer": {
    "name": "Jordan Reyes",
    "email": "jordan@demo.dev",
    "contact": ""
  },
  "order": {
    "order_id": "ORD-2002",
    "item_name": "Everyday Sneakers",
    "price": 89.0,
    "category": "Footwear"
  },
  "return_status": "initiated",
  "timestamp": "2026-08-22T03:30:32.938000"
}
```

---

## Testing as you go

Three ways to fire a real trigger, cheapest first:

- **Ask me** — I'll initiate a fresh return against the live backend; a new event lands in your flow's run history within a couple seconds, with a real customer/order pair from the seed data.
- **Re-run from history** — most flow builders let you re-run a past trigger event without a new request, useful for testing the send step or AI block in isolation.
- **Paste in a sample** — if your builder supports a manual test payload, paste the JSON example above directly, no live backend call needed.

*Webhook trigger confirmed live and receiving real payloads as of this session.*
