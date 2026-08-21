"""
Database models for ReturnPilot application.
Defines SQLAlchemy ORM models for all database tables.
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, String, Integer, Numeric, Date, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Customer(Base):
    """Customer table storing user information."""
    __tablename__ = "customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    contact = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    orders = relationship("Order", back_populates="customer")
    returns = relationship("Return", back_populates="customer")


class ReturnPolicy(Base):
    """Return policy table storing rules for different product categories."""
    __tablename__ = "return_policy"
    
    category = Column(String(50), primary_key=True)
    window_days = Column(Integer, nullable=False)
    exclusions = Column(Text)
    notes = Column(Text)
    
    # Relationships
    orders = relationship("Order", back_populates="policy")


class Order(Base):
    """Order table storing customer purchase records."""
    __tablename__ = "orders"
    
    id = Column(String(50), primary_key=True)  # ORD-1001 format
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    item_name = Column(String(255), nullable=False)
    category = Column(String(50), ForeignKey("return_policy.category"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    purchase_date = Column(Date, nullable=False)
    final_sale = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="orders")
    policy = relationship("ReturnPolicy", back_populates="orders")
    returns = relationship("Return", back_populates="order")


class Return(Base):
    """Return table storing return request records and status."""
    __tablename__ = "returns"
    
    id = Column(String(50), primary_key=True)  # RET-1001 format
    order_id = Column(String(50), ForeignKey("orders.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    status = Column(
        SQLEnum("initiated", "shipped", "refunded", "declined", name="return_status"),
        nullable=False
    )
    reason = Column(Text, nullable=False)
    agent_reasoning_log = Column(JSONB)  # List of tool calls and results
    flagged_for_review = Column(Boolean, default=False)
    fast_tracked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="returns")
    customer = relationship("Customer", back_populates="returns")
    evidence = relationship("ReturnEvidence", back_populates="return_record")
    notifications = relationship("NotificationLog", back_populates="return_record")


class ReturnEvidence(Base):
    """Return evidence table storing photo evidence and AI verdicts."""
    __tablename__ = "return_evidence"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    return_id = Column(String(50), ForeignKey("returns.id"), nullable=False)
    photo_url = Column(String(500), nullable=False)  # Supabase Storage URL
    claimed_issue = Column(Text, nullable=False)
    ai_verdict = Column(JSONB)  # {consistent: bool, confidence: str, notes: str, reviewed_by_human: bool}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    return_record = relationship("Return", back_populates="evidence")


class NotificationLog(Base):
    """Notification log table storing all sent notifications."""
    __tablename__ = "notifications_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    return_id = Column(String(50), ForeignKey("returns.id"), nullable=False)
    message = Column(Text, nullable=False)
    trigger_reason = Column(String(100))  # "return_initiated", "refund_issued", "flagged_for_review"
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    return_record = relationship("Return", back_populates="notifications")


# Export all models for easy importing
__all__ = [
    "Base",
    "Customer",
    "Order",
    "ReturnPolicy",
    "Return",
    "ReturnEvidence",
    "NotificationLog",
]
