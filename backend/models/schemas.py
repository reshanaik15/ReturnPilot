"""
Pydantic schemas for all API request/response validation.
These are the contracts between frontend and backend.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Agent / Chat
# ---------------------------------------------------------------------------

class AgentMessageRequest(BaseModel):
    customer_id: str
    message: str
    image_base64: Optional[str] = None
    conversation_history: List[dict] = Field(default_factory=list)


class ReasoningStep(BaseModel):
    """One step in the multi-agent reasoning trace."""
    agent: str                    # "orchestrator" | "order_agent" | "policy_agent" | etc.
    tool: Optional[str] = None    # Tool called, if any
    input: Optional[dict] = None  # Tool input
    result: Optional[Any] = None  # Tool result
    decision: Optional[str] = None  # Orchestrator routing decision
    timestamp: Optional[str] = None


class AgentMessageResponse(BaseModel):
    response: str
    reasoning_trace: List[ReasoningStep] = Field(default_factory=list)
    iterations: int
    return_id: Optional[str] = None     # Set if return was initiated
    return_initiated: bool = False       # Flag for frontend to show tracker button


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

class OrderMatch(BaseModel):
    order_id: str
    item_name: str
    category: str
    price: float
    purchase_date: str
    days_since_purchase: int
    final_sale: bool = False
    return_window_days: int
    potentially_eligible: bool


class OrderSearchResponse(BaseModel):
    matches: List[OrderMatch]
    total: int
    query_parsed: dict


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

class PolicyCheckResponse(BaseModel):
    eligible: bool
    reason: str
    order_id: Optional[str] = None
    item_name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    purchase_date: Optional[str] = None
    days_since_purchase: Optional[int] = None
    window_days: Optional[int] = None
    days_remaining: Optional[int] = None
    exclusions: Optional[str] = None
    notes: Optional[str] = None
    final_sale: Optional[bool] = None
    existing_return_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------------

class ReturnInitiateRequest(BaseModel):
    order_id: str
    reason: str
    customer_id: str


class ReturnResponse(BaseModel):
    id: str
    order_id: str
    item_name: Optional[str] = None
    price: Optional[float] = None
    status: str
    reason: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    ai_verdict: Optional[dict] = None
    flagged_for_review: bool = False
    fast_tracked: bool = False
    agent_reasoning_log: Optional[List[dict]] = None


class ReturnAdvanceRequest(BaseModel):
    action: str = "advance"  # always "advance" for status progression


class ReturnReviewRequest(BaseModel):
    action: str  # "approve" | "decline"
    notes: Optional[str] = None


class ReturnStatusUpdate(BaseModel):
    return_id: str
    old_status: str
    new_status: str
    message: str


class CustomerReturnSummary(BaseModel):
    """One return as shown on the customer-facing 'My Returns' page."""
    id: str
    order_id: str
    item_name: str
    price: float
    status: str
    reason: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    flagged_for_review: bool = False
    fast_tracked: bool = False


class CustomerReturnsResponse(BaseModel):
    returns: List[CustomerReturnSummary]
    total: int


class PhotoVerifyResponse(BaseModel):
    success: bool
    return_id: str
    routing: str  # "fast_track" | "human_review" | "standard"
    fast_tracked: bool
    flagged_for_review: bool
    ai_verdict: dict
    photo_url: str


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardReturn(BaseModel):
    """Return record as shown in the ops dashboard."""
    id: str
    order_id: str
    customer_name: str
    customer_email: str
    item_name: str
    category: str
    price: float
    reason: str
    status: str
    flagged_for_review: bool
    fast_tracked: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    ai_verdict: Optional[dict] = None
    reason_classification: Optional[str] = None  # NLP classification
    sentiment: Optional[str] = None              # NLP sentiment


class DashboardResponse(BaseModel):
    returns: List[DashboardReturn]
    total: int
    analytics: Optional[dict] = None  # Aggregate stats from analytics agent


# ---------------------------------------------------------------------------
# NLP / Analytics
# ---------------------------------------------------------------------------

class NLPAnalysis(BaseModel):
    reason_classification: str  # defective | wrong_item | size_mismatch | not_as_described | change_of_mind | damaged_in_transit
    confidence: float
    sentiment: str              # frustrated | neutral | polite
    keywords: List[str]
    suggested_response_tone: str  # empathetic | informative | apologetic


class AnalyticsSummary(BaseModel):
    total_returns: int
    total_value: float
    by_category: dict
    by_status: dict
    flagged_count: int
    insights: List[str]


# ---------------------------------------------------------------------------
# Health / Misc
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    service: str
    database: dict
