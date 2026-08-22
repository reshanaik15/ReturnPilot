"""
Agent Router — POST /api/agent/message

Entry point for all customer chat interactions.
Routes through the multi-agent orchestrator.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException

from database import get_db
from models import Customer, Return
from models.schemas import AgentMessageRequest, AgentMessageResponse, ReasoningStep
from services.agents.orchestrator import agent_turn
from services.notifications import send_notification

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent"])


@router.post("/agent/message", response_model=AgentMessageResponse)
async def handle_agent_message(
    request: AgentMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Process a customer message through the multi-agent orchestration loop.

    Flow:
        1. Validate customer exists
        2. Run NLP analysis + agent tool-use loop
        3. If a return was initiated, send notification
        4. Return response + reasoning trace to frontend
    """
    # Verify customer exists
    customer_result = await db.execute(
        select(Customer).where(Customer.id == request.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {request.customer_id} not found")

    # Run multi-agent turn
    try:
        result = await agent_turn(
            customer_id=str(customer.id),
            message=request.message,
            conversation_history=request.conversation_history,
            db=db,
            image_base64=request.image_base64,
            customer_name=customer.name,
        )
    except Exception as e:
        logger.error(f"Agent turn failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Agent processing failed")

    # If a return was initiated, persist the reasoning trace (dashboard reads
    # NLP classification/sentiment from this column) and send the notification
    if result.get("return_initiated") and result.get("return_id"):
        return_result = await db.execute(
            select(Return).where(Return.id == result["return_id"])
        )
        return_record = return_result.scalar_one_or_none()
        if return_record:
            return_record.agent_reasoning_log = result.get("reasoning_trace", [])

        await send_notification(
            return_id=result["return_id"],
            trigger_reason="return_initiated",
            db=db,
        )

    # Build response
    trace_steps = [
        ReasoningStep(**step) if isinstance(step, dict) else step
        for step in result.get("reasoning_trace", [])
    ]

    return AgentMessageResponse(
        response=result["response"],
        reasoning_trace=trace_steps,
        iterations=result.get("iterations", 1),
        return_id=result.get("return_id"),
        return_initiated=result.get("return_initiated", False),
    )
