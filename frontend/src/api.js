/**
 * API Client for ReturnPilot — viaSocket-backed agent
 */

const VIASOCKET_WEBHOOK_URL = 'https://flow.sokt.io/func/scriJDWDZGHv';
const GET_MY_RETURNS_URL = 'https://flow.sokt.io/func/scrinfNHTNQP';

export const CUSTOMERS = [
  { id: 'cust-001', name: 'Amara Chen', email: 'amara.chen@example.com' },
  { id: 'cust-002', name: 'Jordan Reyes', email: 'jordan.reyes@example.com' },
  { id: 'cust-003', name: 'Priya', email: 'priya@example.com' }, // surname unconfirmed — fix once known
];

function parseAgentResponse(content) {
  const traceMatch = content.match(/\[REASONING_TRACE\]([\s\S]*?)\[\/REASONING_TRACE\]/);

  let reasoningSteps = [];
  let customerMessage = content;

  if (traceMatch) {
    reasoningSteps = traceMatch[1]
      .trim()
      .split(/\n(?=\d+\.)/)
      .map((step) => step.replace(/^\d+\.\s*/, '').trim())
      .filter(Boolean);

    customerMessage = customerMessage.replace(traceMatch[0], '').trim();
  }

  // Optional structured tag the agent's prompt can emit when it actually creates a return
  // (mirrors the REASONING_TRACE pattern) — not present yet unless the backend prompt is
  // updated to output it. See chat for the exact prompt addition needed.
  let createdReturn = null;
  const returnMatch = customerMessage.match(/\[RETURN_CREATED\]([\s\S]*?)\[\/RETURN_CREATED\]/);
  if (returnMatch) {
    try {
      createdReturn = JSON.parse(returnMatch[1].trim());
    } catch (e) {
      console.warn('[RETURN_CREATED] tag found but not valid JSON:', returnMatch[1], e);
      createdReturn = null;
    }
    customerMessage = customerMessage.replace(returnMatch[0], '').trim();
  }

  return { customerMessage, reasoningSteps, createdReturn };
}

export async function sendMessage(customerId, message) {
  const response = await fetch(VIASOCKET_WEBHOOK_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ customer_id: customerId, message }),
  });

  if (!response.ok) {
    throw new Error(`Agent request failed: ${response.status}`);
  }

  const raw = await response.json();
  const content = typeof raw === 'string' ? raw : raw.output ?? raw.content ?? '';

  if (!content) {
    throw new Error('Agent returned an empty response');
  }

  return parseAgentResponse(content);
}

export async function getMyReturns(customerName) {
  const response = await fetch(GET_MY_RETURNS_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ customer_name: customerName }),
  });

  if (!response.ok) {
    throw new Error(`Get My Returns request failed: ${response.status}`);
  }

  const raw = await response.json();
  // The flow returns {"message": "No data found..."} instead of [] when there are zero
  // matches — not an array, so guard against that instead of assuming rows is always a list.
  const rows = Array.isArray(raw) ? raw : [];

  // order_id is guaranteed numeric going forward, but earlier test rows can still have a
  // stray rowid string ("row9qrzaarhs") left in that field from before the fix — drop those
  // rather than show a broken-looking "Order #row9qrzaarhs" card.
  const validRows = rows.filter((row) => /^\d+$/.test(String(row.order_id)));

  // No duplicate-check on writes server-side — same order_id can appear more than once.
  // Keep only the most recent row per order_id.
  const latestByOrderId = new Map();
  for (const row of validRows) {
    const existing = latestByOrderId.get(row.order_id);
    if (!existing || new Date(row.createdat) > new Date(existing.createdat)) {
      latestByOrderId.set(row.order_id, row);
    }
  }

  return Array.from(latestByOrderId.values())
    // Declined returns never happened from the customer's point of view — don't show a
    // card implying progress. They're still visible on the ops dashboard separately.
    .filter((row) => row.status !== 'declined')
    .sort((a, b) => new Date(b.createdat) - new Date(a.createdat))
    .map((row) => ({
      id: `RET-${row.autonumber}`,
      rowid: row.rowid,
      orderId: row.order_id,
      itemName: row.item_name ?? 'Return item',
      status: row.status,
      reason: row.reason_,
      date: row.createdat?.slice(0, 10),
    }));
}

// --- Not yet available: these need the CRUD flows from Task 23a (dashboard/advance/review) ---
// Wiring these to viaSocket is not done yet. Calling them throws on purpose rather than
// returning fabricated data, so a missing integration fails loudly instead of silently.

export async function getReturn(_returnId) {
  throw new Error('getReturn() not wired yet — pending Task 23a CRUD flows');
}

export async function advanceReturn(_returnId) {
  throw new Error('advanceReturn() not wired yet — pending Task 23a CRUD flows');
}
