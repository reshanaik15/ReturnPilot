"""
Returns Router — all return lifecycle endpoints.
"""

import base64
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from database import get_db
from models import Return, Order, Customer, ReturnEvidence
from models.schemas import (
    ReturnInitiateRequest, ReturnResponse,
    ReturnAdvanceRequest, ReturnReviewRequest, ReturnStatusUpdate,
    PhotoVerifyResponse, CustomerReturnSummary, CustomerReturnsResponse,
)
from services.tools import initiate_return, verify_damage_photo
from services.notifications import send_notification
from services.storage import upload_photo
from services.photo_analyzer import analyze_damage_photo

logger = logging.getLogger(__name__)

router = APIRouter(tags=["returns"])

# Status state machine: initiated → shipped → refunded
STATUS_TRANSITIONS = {
    "initiated": "shipped",
    "shipped": "refunded",
}


@router.post("/returns/initiate", response_model=dict)
async def api_initiate_return(
    request: ReturnInitiateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Initiate a return for an order."""
    result = await initiate_return(
        order_id=request.order_id,
        reason=request.reason,
        customer_id=request.customer_id,
        db=db,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Return initiation failed"))

    await send_notification(
        return_id=result["return_id"],
        trigger_reason="return_initiated",
        db=db,
    )
    return result


@router.get("/returns/customer/{customer_id}", response_model=CustomerReturnsResponse)
async def get_customer_returns(customer_id: str, db: AsyncSession = Depends(get_db)):
    """List all returns belonging to one customer, for the 'My Returns' page."""
    try:
        customer_uuid = UUID(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid customer_id format")

    result = await db.execute(
        select(Return, Order)
        .join(Order, Return.order_id == Order.id)
        .where(Return.customer_id == customer_uuid)
        .order_by(Return.created_at.desc())
    )
    rows = result.fetchall()

    returns = [
        CustomerReturnSummary(
            id=ret.id,
            order_id=order.id,
            item_name=order.item_name,
            price=float(order.price),
            status=ret.status,
            reason=ret.reason,
            created_at=ret.created_at,
            updated_at=ret.updated_at,
            flagged_for_review=ret.flagged_for_review,
            fast_tracked=ret.fast_tracked,
        )
        for ret, order in rows
    ]

    return CustomerReturnsResponse(returns=returns, total=len(returns))


@router.get("/returns/{return_id}", response_model=ReturnResponse)
async def get_return(return_id: str, db: AsyncSession = Depends(get_db)):
    """Get current status and details of a return."""
    result = await db.execute(
        select(Return, Order)
        .join(Order, Return.order_id == Order.id)
        .where(Return.id == return_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Return {return_id} not found")
    ret, order = row

    evidence_result = await db.execute(
        select(ReturnEvidence)
        .where(ReturnEvidence.return_id == return_id)
        .order_by(ReturnEvidence.created_at.desc())
        .limit(1)
    )
    latest_evidence = evidence_result.scalar_one_or_none()

    return ReturnResponse(
        id=ret.id,
        order_id=ret.order_id,
        item_name=order.item_name,
        price=float(order.price),
        status=ret.status,
        reason=ret.reason,
        created_at=ret.created_at,
        updated_at=ret.updated_at,
        ai_verdict=latest_evidence.ai_verdict if latest_evidence else None,
        flagged_for_review=ret.flagged_for_review,
        fast_tracked=ret.fast_tracked,
        agent_reasoning_log=ret.agent_reasoning_log,
    )


@router.post("/returns/{return_id}/advance", response_model=ReturnStatusUpdate)
async def advance_return_status(
    return_id: str,
    request: ReturnAdvanceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Advance return status through lifecycle:
    initiated → shipped → refunded

    Called by the ops dashboard when warehouse/payment events occur.
    Triggers customer notification at each stage.
    """
    result = await db.execute(select(Return).where(Return.id == return_id))
    ret = result.scalar_one_or_none()
    if not ret:
        raise HTTPException(status_code=404, detail=f"Return {return_id} not found")

    if ret.status == "declined":
        raise HTTPException(status_code=400, detail="Cannot advance a declined return")
    if ret.status == "refunded":
        raise HTTPException(status_code=400, detail="Return already completed (refunded)")

    next_status = STATUS_TRANSITIONS.get(ret.status)
    if not next_status:
        raise HTTPException(status_code=400, detail=f"No transition defined from status '{ret.status}'")

    old_status = ret.status
    ret.status = next_status

    # Map status to notification trigger
    trigger_map = {
        "shipped": "return_shipped",
        "refunded": "return_refunded",
    }
    trigger = trigger_map.get(next_status)
    if trigger:
        await send_notification(return_id=return_id, trigger_reason=trigger, db=db)

    return ReturnStatusUpdate(
        return_id=return_id,
        old_status=old_status,
        new_status=next_status,
        message=f"Return {return_id} advanced from '{old_status}' to '{next_status}'.",
    )


@router.post("/returns/{return_id}/review", response_model=ReturnStatusUpdate)
async def review_return(
    return_id: str,
    request: ReturnReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve a flagged return (approve → refunded, decline → declined).
    Called by ops dashboard for human-review cases.
    """
    if request.action not in ("approve", "decline"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'decline'")

    result = await db.execute(select(Return).where(Return.id == return_id))
    ret = result.scalar_one_or_none()
    if not ret:
        raise HTTPException(status_code=404, detail=f"Return {return_id} not found")

    if not ret.flagged_for_review:
        raise HTTPException(status_code=400, detail="This return is not flagged for review")

    old_status = ret.status
    ret.flagged_for_review = False

    if request.action == "approve":
        ret.status = "refunded"
        await send_notification(return_id=return_id, trigger_reason="return_refunded", db=db)
        new_status = "refunded"
    else:
        ret.status = "declined"
        new_status = "declined"

    return ReturnStatusUpdate(
        return_id=return_id,
        old_status=old_status,
        new_status=new_status,
        message=f"Return {return_id} review {'approved (refunded)' if request.action == 'approve' else 'declined'}.",
    )


@router.post("/returns/verify-photo", response_model=PhotoVerifyResponse)
async def verify_photo(
    return_id: str = Form(...),
    claimed_issue: str = Form(...),
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload return-evidence photo, run AI consistency verification against
    the claimed issue, and route the return to fast-track or human review
    based on the verdict.
    """
    result = await db.execute(select(Return).where(Return.id == return_id))
    ret = result.scalar_one_or_none()
    if not ret:
        raise HTTPException(status_code=404, detail=f"Return {return_id} not found")

    photo_bytes = await photo.read()
    content_type = photo.content_type or "image/jpeg"

    photo_url = await upload_photo(photo_bytes, return_id, content_type)
    image_base64 = base64.b64encode(photo_bytes).decode()

    verdict = await analyze_damage_photo(image_base64, claimed_issue, content_type)

    outcome = await verify_damage_photo(
        return_id=return_id,
        consistent=verdict["consistent"],
        confidence=verdict["confidence"],
        notes=verdict["notes"],
        db=db,
        photo_url=photo_url,
        claimed_issue=claimed_issue,
    )
    if outcome.get("error"):
        raise HTTPException(status_code=404, detail=outcome["error"])

    if outcome.get("routing") == "human_review":
        await send_notification(return_id=return_id, trigger_reason="flagged_for_review", db=db)

    return PhotoVerifyResponse(**outcome, photo_url=photo_url)
