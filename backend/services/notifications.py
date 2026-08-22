"""
Notification Service — viaSocket Integration.

Sends personalized notifications at 3 key lifecycle events:
    - Return initiated
    - Return shipped (in transit)
    - Return refunded

viaSocket workflow receives our structured event data and uses
its AI block to personalize the message before dispatching.
Failures are logged but never block the main return flow.
"""

import logging
from datetime import datetime
from typing import Optional
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from models import NotificationLog, Return, Order, Customer

logger = logging.getLogger(__name__)


# Notification message templates
NOTIFICATION_TEMPLATES = {
    "return_initiated": (
        "Your return has been initiated for {item_name} (Order {order_id}). "
        "Return ID: {return_id}. Use label reference {label_reference} for shipping. "
        "We'll notify you when we receive your item."
    ),
    "return_shipped": (
        "We've received your returned {item_name} and it's now in transit for inspection. "
        "Return ID: {return_id}. Your refund of ₹{price:.0f} will be processed within 2-3 business days."
    ),
    "return_refunded": (
        "Your refund of ₹{price:.0f} for {item_name} has been processed! "
        "Return ID: {return_id}. The amount will reflect in your account within 3-5 business days."
    ),
    "flagged_for_review": (
        "Your return (Return ID: {return_id}) for {item_name} is under manual review. "
        "Our team will assess it and get back to you within 24 hours."
    ),
}


async def send_notification(
    return_id: str,
    trigger_reason: str,
    db: AsyncSession,
    extra_data: Optional[dict] = None,
) -> bool:
    """
    Send a notification via viaSocket for a return lifecycle event.

    Args:
        return_id: Return ID e.g. "RET-0047"
        trigger_reason: One of "return_initiated", "return_shipped", "return_refunded", "flagged_for_review"
        db: AsyncSession for logging to notifications_log
        extra_data: Optional dict with label_reference or other dynamic fields

    Returns:
        True if sent successfully, False otherwise (never raises)
    """
    try:
        # Fetch return + order + customer details for personalization
        result = await db.execute(
            select(Return, Order, Customer)
            .join(Order, Return.order_id == Order.id)
            .join(Customer, Return.customer_id == Customer.id)
            .where(Return.id == return_id)
        )
        row = result.first()

        if not row:
            logger.warning(f"Notification skipped — return {return_id} not found")
            return False

        return_rec, order, customer = row

        # Build notification message from template
        template = NOTIFICATION_TEMPLATES.get(trigger_reason, "Your return status has been updated.")
        message = template.format(
            item_name=order.item_name,
            order_id=order.id,
            return_id=return_id,
            price=float(order.price),
            label_reference=extra_data.get("label_reference", f"RTN-{order.id}") if extra_data else f"RTN-{order.id}",
        )

        # Payload for viaSocket webhook
        payload = {
            "return_id": return_id,
            "trigger_reason": trigger_reason,
            "message": message,
            "customer": {
                "name": customer.name,
                "email": customer.email,
                "contact": customer.contact or "",
            },
            "order": {
                "order_id": order.id,
                "item_name": order.item_name,
                "price": float(order.price),
                "category": order.category,
            },
            "return_status": return_rec.status,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Send to viaSocket webhook (if configured)
        notification_url = settings.notification_service_url
        success = False

        if notification_url and notification_url.startswith("http") and "..." not in notification_url:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(notification_url, json=payload)
                    response.raise_for_status()
                    success = True
                    logger.info(f"Notification sent: {trigger_reason} for {return_id}")
            except httpx.TimeoutException:
                logger.warning(f"Notification timeout for {return_id} — logged anyway")
            except Exception as e:
                logger.warning(f"Notification delivery failed: {e} — logged anyway")
        else:
            logger.info(f"Notification (no-op — viaSocket not configured): {trigger_reason} for {return_id}")
            logger.info(f"Message would have been: {message}")
            success = True  # Count as success in dev mode

        # Always log to notifications_log table
        log_entry = NotificationLog(
            return_id=return_id,
            message=message,
            trigger_reason=trigger_reason,
        )
        db.add(log_entry)
        await db.flush()

        return success

    except Exception as e:
        # NEVER let notification failure break the main flow
        logger.error(f"Notification service error: {e}", exc_info=True)
        return False
