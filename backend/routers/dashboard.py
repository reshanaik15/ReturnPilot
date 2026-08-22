"""Dashboard Router — ops view of all returns with analytics."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import APIRouter, Depends

from database import get_db
from models import Return, Order, Customer, ReturnEvidence
from models.schemas import DashboardReturn, DashboardResponse
from services.tools import get_return_analytics

logger = logging.getLogger(__name__)
router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/returns", response_model=DashboardResponse)
async def get_dashboard_returns(db: AsyncSession = Depends(get_db)):
    """
    Get all returns across all customers for the ops dashboard.
    Includes NLP classification from agent_reasoning_log JSONB.
    """
    result = await db.execute(
        select(Return, Order, Customer)
        .join(Order, Return.order_id == Order.id)
        .join(Customer, Return.customer_id == Customer.id)
        .order_by(Return.created_at.desc())
    )
    rows = result.fetchall()

    # Bulk-fetch the latest AI verdict per return (avoids one query per row)
    return_ids = [ret.id for ret, order, customer in rows]
    latest_verdict_by_return: dict = {}
    if return_ids:
        evidence_result = await db.execute(
            select(ReturnEvidence)
            .where(ReturnEvidence.return_id.in_(return_ids))
            .order_by(ReturnEvidence.created_at.desc())
        )
        for evidence in evidence_result.scalars().all():
            latest_verdict_by_return.setdefault(evidence.return_id, evidence.ai_verdict)

    returns = []
    for ret, order, customer in rows:
        # Extract NLP data from reasoning log if available
        nlp_analysis = None
        if ret.agent_reasoning_log:
            for step in ret.agent_reasoning_log:
                if step.get("agent") == "nlp_analyzer":
                    nlp_analysis = step.get("result", {})
                    break

        returns.append(DashboardReturn(
            id=ret.id,
            order_id=ret.order_id,
            customer_name=customer.name,
            customer_email=customer.email,
            item_name=order.item_name,
            category=order.category,
            price=float(order.price),
            reason=ret.reason,
            status=ret.status,
            flagged_for_review=ret.flagged_for_review,
            fast_tracked=ret.fast_tracked,
            created_at=ret.created_at,
            updated_at=ret.updated_at,
            ai_verdict=latest_verdict_by_return.get(ret.id),
            reason_classification=nlp_analysis.get("reason_classification") if nlp_analysis else None,
            sentiment=nlp_analysis.get("sentiment") if nlp_analysis else None,
        ))

    # Business-wide analytics
    analytics = await get_return_analytics(customer_id=None, db=db)

    return DashboardResponse(
        returns=returns,
        total=len(returns),
        analytics=analytics,
    )
