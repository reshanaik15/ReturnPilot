"""Orders Router — GET /api/orders/search"""

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query
from database import get_db
from models.schemas import OrderSearchResponse
from services.tools import search_orders

router = APIRouter(tags=["orders"])


@router.get("/orders/search", response_model=OrderSearchResponse)
async def search_orders_endpoint(
    customer_id: str = Query(..., description="Customer UUID"),
    q: str = Query("", description="Natural language search query"),
    db: AsyncSession = Depends(get_db),
):
    result = await search_orders(customer_id=customer_id, query=q, db=db)
    return OrderSearchResponse(**result)
