"""
Backend Tool Functions for ReturnPilot Agent.

These are the core database-backed functions that specialist agents call.
Each function is a pure async DB operation — no Claude calls here.
Claude (via the orchestrator) decides WHICH tool to call and WHEN.

Tools:
    search_orders       - Find orders from vague natural language + date heuristics
    check_policy        - Check return eligibility against return_policy table
    initiate_return     - Create a return record in DB, generate RET-NNNN ID
    verify_damage_photo - Update return with AI photo verdict
    get_return_analytics- Aggregate return patterns for NLP analytics agent
"""

import logging
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from models import Customer, Order, Return, ReturnEvidence, ReturnPolicy, NotificationLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Date Heuristic Parser
# ---------------------------------------------------------------------------

def parse_date_range(query: str) -> tuple[Optional[date], Optional[date]]:
    """
    Extract date range from natural language query.

    Examples:
        "shoes from yesterday"   → (yesterday, yesterday)
        "jacket last week"       → (7 days ago, today)
        "order this month"       → (1st of month, today)
        "watch today"            → (today, today)

    Deliberately does NOT treat "recent"/"recently"/"just bought" as a date
    hint: unlike "yesterday" or "last week" (explicit, unambiguous customer
    intent), "recent" is exactly the kind of vague word an LLM reaches for
    as generic paraphrase filler even when the customer asked for their
    full history — which silently narrowed "what all did I buy" to a
    14-day window and dropped real orders. Better to return everything and
    let the agent's own response text describe recency than to silently
    drop data behind an implicit filter.

    Returns:
        (start_date, end_date) or (None, None) if no date hint found.
    """
    today = date.today()
    q = query.lower()

    if "yesterday" in q:
        d = today - timedelta(days=1)
        return d, d
    if "today" in q:
        return today, today
    if "last week" in q or "past week" in q or "a week ago" in q:
        return today - timedelta(days=7), today
    if "this week" in q:
        # Monday of current week
        start = today - timedelta(days=today.weekday())
        return start, today
    if "last month" in q or "past month" in q:
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return last_prev.replace(day=1), last_prev
    if "this month" in q:
        return today.replace(day=1), today
    if "few days" in q or "couple of days" in q:
        return today - timedelta(days=5), today
    if "last year" in q:
        return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
    if "this year" in q:
        return date(today.year, 1, 1), today

    return None, None


# Generic conversational filler that should never be treated as an item/category
# search term — expanded after a real bug where words like "all", "are", "tell"
# leaked through as keywords and, combined with substring matching, produced
# false positives (e.g. "all" matching "Wallet", "are" matching "Apparel").
STOPWORDS = {
    "i", "the", "a", "an", "my", "want", "to", "return", "bought",
    "purchased", "ordered", "got", "from", "for", "and", "or", "of",
    "that", "which", "what", "when", "where", "how", "yesterday",
    "today", "week", "month", "last", "this", "past", "recent",
    "recently", "ago", "just", "few", "couple", "days", "year",
    "you", "your", "yours", "are", "is", "was", "were", "am", "be",
    "being", "been", "all", "other", "another", "than", "tell", "say",
    "saying", "said", "nothing", "anything", "something", "everything",
    "dont", "don't", "doesnt", "didnt", "remember", "placed", "now",
    "order", "orders", "purchases", "history",
    "only", "have", "has", "had", "do", "does", "did", "can", "could",
    "would", "should", "will", "shall", "may", "might", "must",
    "me", "it", "he", "she", "we", "us", "our", "ours", "him", "her",
    "them", "they", "find", "help", "please", "need", "looking", "look",
    "show", "list", "give", "tell", "know", "think", "in", "on", "at",
    "with", "about", "so", "not", "no", "yes", "okay", "ok", "hey",
    "hi", "hello", "there", "here", "one", "any", "some", "these",
    "those", "then", "still", "really", "actually", "till", "until",
}


def extract_keywords(query: str) -> list[str]:
    """
    Extract non-stopword keywords from a search query for item_name matching.
    Strips common filler words so "the blue shoes I bought" → ["blue", "shoes"]
    """
    words = query.lower().split()
    return [w.strip(".,!?") for w in words if w not in STOPWORDS and len(w) > 2]


# ---------------------------------------------------------------------------
# Tool 1: search_orders
# ---------------------------------------------------------------------------

async def search_orders(
    customer_id: str,
    query: str,
    db: AsyncSession
) -> dict:
    """
    Search orders for a customer using natural language query.

    Implements:
    - Customer scoping (WHERE customer_id = ?)
    - Whole-word keyword matching on item_name and category (case-insensitive)
    - Date heuristics ("yesterday", "last week", "this month", etc.)
    - Returns ranked results (date match + keyword match)

    Uses word-boundary regex matching rather than raw substring LIKE, since
    substring matching produces false positives on short keywords (e.g. a
    stray "all" keyword matching "Wallet", or "are" matching "Apparel").
    If no usable keywords are found (a vague query like "what did I buy"),
    no keyword filter is applied and the customer's full order list (subject
    only to any date filter) is returned — safer than an accidental narrow
    match that would misrepresent the customer's order history.

    Args:
        customer_id: Customer UUID string
        query: Natural language search string e.g. "shoes from yesterday"
        db: AsyncSession injected by FastAPI

    Returns:
        {"matches": [...], "total": int, "query_parsed": {...}}
    """
    try:
        customer_uuid = UUID(customer_id)
    except ValueError:
        return {"matches": [], "total": 0, "error": "Invalid customer_id format"}

    today = date.today()
    start_date, end_date = parse_date_range(query)
    keywords = extract_keywords(query)

    # Build base query scoped to customer
    stmt = (
        select(Order, ReturnPolicy)
        .join(ReturnPolicy, Order.category == ReturnPolicy.category)
        .where(Order.customer_id == customer_uuid)
        .order_by(Order.purchase_date.desc())
    )

    # Apply date filter if date hint was found
    if start_date and end_date:
        stmt = stmt.where(
            and_(
                Order.purchase_date >= start_date,
                Order.purchase_date <= end_date,
            )
        )

    # Apply keyword filter if keywords were found (whole-word match, not substring)
    if keywords:
        keyword_conditions = []
        for kw in keywords:
            pattern = rf"\y{re.escape(kw)}\y"
            keyword_conditions.append(Order.item_name.op("~*")(pattern))
            keyword_conditions.append(Order.category.op("~*")(pattern))
        stmt = stmt.where(or_(*keyword_conditions))

    result = await db.execute(stmt)
    rows = result.fetchall()

    matches = []
    for order, policy in rows:
        days_since = (today - order.purchase_date).days
        matches.append({
            "order_id": order.id,
            "item_name": order.item_name,
            "category": order.category,
            "price": float(order.price),
            "purchase_date": order.purchase_date.isoformat(),
            "days_since_purchase": days_since,
            "final_sale": order.final_sale,
            "return_window_days": policy.window_days,
            "potentially_eligible": not order.final_sale and days_since <= policy.window_days,
        })

    return {
        "matches": matches,
        "total": len(matches),
        "query_parsed": {
            "keywords": keywords,
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            }
        }
    }


# ---------------------------------------------------------------------------
# Tool 2: check_policy
# ---------------------------------------------------------------------------

async def check_policy(order_id: str, db: AsyncSession) -> dict:
    """
    Check return eligibility for an order against the return_policy table.

    Implements:
    - JOIN orders + return_policy on category
    - Calculate days_since_purchase
    - Check final_sale flag (always ineligible)
    - Check return window (days_since <= window_days)
    - Return detailed eligibility with human-readable reason

    Args:
        order_id: Order ID string e.g. "ORD-1001"
        db: AsyncSession

    Returns:
        PolicyCheckResult dict with eligible, reason, window info, etc.
    """
    stmt = (
        select(Order, ReturnPolicy, Customer)
        .join(ReturnPolicy, Order.category == ReturnPolicy.category)
        .join(Customer, Order.customer_id == Customer.id)
        .where(Order.id == order_id)
    )
    result = await db.execute(stmt)
    row = result.first()

    if not row:
        return {
            "eligible": False,
            "reason": f"Order {order_id} not found.",
            "error": "order_not_found",
        }

    order, policy, customer = row
    today = date.today()
    days_since = (today - order.purchase_date).days

    # Check existing return (don't allow duplicate)
    existing_stmt = select(Return).where(Return.order_id == order_id)
    existing_result = await db.execute(existing_stmt)
    existing_return = existing_result.scalar_one_or_none()

    if existing_return:
        return {
            "eligible": False,
            "reason": f"A return already exists for this order (Return ID: {existing_return.id}, Status: {existing_return.status}).",
            "existing_return_id": existing_return.id,
            "existing_status": existing_return.status,
        }

    # Final sale check
    if order.final_sale:
        return {
            "eligible": False,
            "reason": "This item was marked as Final Sale and is not eligible for return.",
            "order_id": order_id,
            "item_name": order.item_name,
            "category": order.category,
            "final_sale": True,
            "days_since_purchase": days_since,
            "window_days": policy.window_days,
            "exclusions": policy.exclusions or "",
        }

    # Return window check
    if days_since > policy.window_days:
        return {
            "eligible": False,
            "reason": (
                f"Return window has expired. {order.item_name} ({order.category}) "
                f"has a {policy.window_days}-day return window, "
                f"but it has been {days_since} days since purchase."
            ),
            "order_id": order_id,
            "item_name": order.item_name,
            "category": order.category,
            "price": float(order.price),
            "purchase_date": order.purchase_date.isoformat(),
            "days_since_purchase": days_since,
            "window_days": policy.window_days,
            "days_over": days_since - policy.window_days,
            "exclusions": policy.exclusions or "",
            "notes": policy.notes or "",
        }

    # Eligible
    days_remaining = policy.window_days - days_since
    return {
        "eligible": True,
        "reason": (
            f"{order.item_name} is eligible for return. "
            f"You have {days_remaining} days remaining in the {policy.window_days}-day return window."
        ),
        "order_id": order_id,
        "item_name": order.item_name,
        "category": order.category,
        "price": float(order.price),
        "purchase_date": order.purchase_date.isoformat(),
        "days_since_purchase": days_since,
        "window_days": policy.window_days,
        "days_remaining": days_remaining,
        "exclusions": policy.exclusions or "",
        "notes": policy.notes or "",
        "customer_name": customer.name,
        "customer_email": customer.email,
    }


# ---------------------------------------------------------------------------
# Tool 3: initiate_return
# ---------------------------------------------------------------------------

async def initiate_return(
    order_id: str,
    reason: str,
    customer_id: str,
    db: AsyncSession,
) -> dict:
    """
    Create a new return record in the database.

    Implements:
    - Duplicate check (one return per order)
    - Auto-generate RET-NNNN ID
    - Insert into returns table with status = "initiated"
    - Returns return_id and label_reference for shipping

    Args:
        order_id: Order ID e.g. "ORD-1001"
        reason: Customer's stated return reason (plain text)
        customer_id: Customer UUID string
        db: AsyncSession

    Returns:
        {"return_id": "RET-0047", "status": "initiated", "label_reference": "..."}
    """
    try:
        customer_uuid = UUID(customer_id)
    except ValueError:
        return {"error": "Invalid customer_id format", "success": False}

    # Check for existing return on this order
    existing = await db.execute(
        select(Return).where(Return.order_id == order_id)
    )
    existing_return = existing.scalar_one_or_none()
    if existing_return:
        return {
            "success": False,
            "error": "duplicate_return",
            "message": f"A return already exists for order {order_id}.",
            "existing_return_id": existing_return.id,
            "existing_status": existing_return.status,
        }

    # Verify order exists and belongs to customer
    order_result = await db.execute(
        select(Order).where(
            and_(Order.id == order_id, Order.customer_id == customer_uuid)
        )
    )
    order = order_result.scalar_one_or_none()
    if not order:
        return {
            "success": False,
            "error": "order_not_found",
            "message": f"Order {order_id} not found for this customer.",
        }

    # Generate next RET-NNNN ID
    max_id_result = await db.execute(
        select(Return.id).order_by(Return.created_at.desc()).limit(1)
    )
    last_id = max_id_result.scalar_one_or_none()
    if last_id and last_id.startswith("RET-"):
        try:
            last_num = int(last_id.split("-")[1])
            new_num = last_num + 1
        except (ValueError, IndexError):
            new_num = 1
    else:
        new_num = 1
    return_id = f"RET-{new_num:04d}"

    # Generate shipping label reference
    label_reference = f"RTN-{order_id}-{date.today().strftime('%Y%m%d')}"

    # Create return record
    new_return = Return(
        id=return_id,
        order_id=order_id,
        customer_id=customer_uuid,
        status="initiated",
        reason=reason,
        agent_reasoning_log=[],  # Will be populated by orchestrator
        flagged_for_review=False,
        fast_tracked=False,
    )
    db.add(new_return)
    await db.flush()  # Get DB-generated fields without full commit

    logger.info(f"Return initiated: {return_id} for order {order_id}")

    return {
        "success": True,
        "return_id": return_id,
        "order_id": order_id,
        "status": "initiated",
        "label_reference": label_reference,
        "item_name": order.item_name,
        "price": float(order.price),
        "message": f"Return {return_id} successfully initiated for {order.item_name}.",
    }


# ---------------------------------------------------------------------------
# Tool 4: verify_damage_photo
# ---------------------------------------------------------------------------

async def verify_damage_photo(
    return_id: str,
    consistent: bool,
    confidence: str,  # "high", "medium", "low"
    notes: str,
    db: AsyncSession,
    photo_url: str = "",
    claimed_issue: str = "",
) -> dict:
    """
    Update return record with AI photo verdict.

    Routing logic:
    - consistent=True + confidence="high" → fast_tracked=True
    - consistent=False OR confidence="low" → flagged_for_review=True
    - Otherwise → standard processing

    Args:
        return_id: Return ID e.g. "RET-0047"
        consistent: Whether photo matches claimed issue
        confidence: "high", "medium", or "low"
        notes: AI analysis notes
        db: AsyncSession
        photo_url: Supabase Storage URL of uploaded photo
        claimed_issue: Customer's stated damage description

    Returns:
        {"routing": "fast_track" | "human_review" | "standard", ...}
    """
    result = await db.execute(select(Return).where(Return.id == return_id))
    return_record = result.scalar_one_or_none()

    if not return_record:
        return {"error": "return_not_found", "return_id": return_id}

    ai_verdict = {
        "consistent": consistent,
        "confidence": confidence,
        "notes": notes,
        "analyzed_at": datetime.utcnow().isoformat(),
    }

    # Routing logic
    if consistent and confidence == "high":
        return_record.fast_tracked = True
        routing = "fast_track"
    elif not consistent or confidence == "low":
        return_record.flagged_for_review = True
        routing = "human_review"
    else:
        routing = "standard"

    await db.flush()

    # Record evidence if photo was uploaded
    if photo_url:
        evidence = ReturnEvidence(
            return_id=return_id,
            photo_url=photo_url,
            claimed_issue=claimed_issue,
            ai_verdict=ai_verdict,
        )
        db.add(evidence)
        await db.flush()

    return {
        "success": True,
        "return_id": return_id,
        "routing": routing,
        "fast_tracked": return_record.fast_tracked,
        "flagged_for_review": return_record.flagged_for_review,
        "ai_verdict": ai_verdict,
    }


# ---------------------------------------------------------------------------
# Tool 5: get_return_analytics (for analytics agent)
# ---------------------------------------------------------------------------

async def get_return_analytics(customer_id: Optional[str], db: AsyncSession) -> dict:
    """
    Aggregate return statistics for the analytics agent.

    If customer_id provided: customer-scoped analytics
    If None: business-wide analytics (for ops dashboard)

    Returns:
        Aggregated stats: by category, by reason_classification, avg days to return, etc.
    """
    # Base query
    returns_stmt = select(Return, Order).join(Order, Return.order_id == Order.id)

    if customer_id:
        try:
            cust_uuid = UUID(customer_id)
            returns_stmt = returns_stmt.where(Return.customer_id == cust_uuid)
        except ValueError:
            pass

    result = await db.execute(returns_stmt)
    rows = result.fetchall()

    if not rows:
        return {"total_returns": 0, "by_category": {}, "by_status": {}, "insights": []}

    by_category: dict = {}
    by_status: dict = {}
    total_price = 0.0

    for ret, order in rows:
        cat = order.category
        by_category[cat] = by_category.get(cat, 0) + 1
        by_status[ret.status] = by_status.get(ret.status, 0) + 1
        total_price += float(order.price)

    total = len(rows)
    insights = []

    # Most returned category
    if by_category:
        top_cat = max(by_category, key=by_category.get)
        insights.append(f"Most returned category: {top_cat} ({by_category[top_cat]} returns)")

    # Refund rate
    refunded = by_status.get("refunded", 0)
    if total > 0:
        refund_rate = round(refunded / total * 100, 1)
        insights.append(f"Refund completion rate: {refund_rate}%")

    # Flagged rate
    flagged_count = sum(1 for ret, _ in rows if ret.flagged_for_review)
    if flagged_count > 0:
        insights.append(f"{flagged_count} return(s) flagged for human review")

    return {
        "total_returns": total,
        "total_value": round(total_price, 2),
        "by_category": by_category,
        "by_status": by_status,
        "flagged_count": flagged_count,
        "insights": insights,
    }
