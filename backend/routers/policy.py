"""Policy Router — GET /api/policy/check"""

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query
from database import get_db
from models.schemas import PolicyCheckResponse
from services.tools import check_policy

router = APIRouter(tags=["policy"])


@router.get("/policy/check", response_model=PolicyCheckResponse)
async def check_policy_endpoint(
    order_id: str = Query(..., description="Order ID to check"),
    db: AsyncSession = Depends(get_db),
):
    result = await check_policy(order_id=order_id, db=db)
    return PolicyCheckResponse(**result)
