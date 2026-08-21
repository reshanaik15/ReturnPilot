"""Initial schema migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-01-20 10:00:00.000000

Creates all tables for ReturnPilot application:
- customers: Customer information
- return_policy: Return policy rules by category
- orders: Customer purchase records
- returns: Return request records
- return_evidence: Photo evidence and AI verdicts
- notifications_log: Notification history

Also creates indexes for performance optimization.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables and indexes."""
    
    # Create customers table
    op.create_table(
        'customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('contact', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Create return_policy table
    op.create_table(
        'return_policy',
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('window_days', sa.Integer(), nullable=False),
        sa.Column('exclusions', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('category')
    )
    
    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('purchase_date', sa.Date(), nullable=False),
        sa.Column('final_sale', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['category'], ['return_policy.category'], ),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # # Create return_status enum type
    # op.execute("CREATE TYPE return_status AS ENUM ('initiated', 'shipped', 'refunded', 'declined')")
    
    # Create returns table
    op.create_table(
        'returns',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('order_id', sa.String(length=50), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM('initiated', 'shipped', 'refunded', 'declined', name='return_status'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('agent_reasoning_log', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('flagged_for_review', sa.Boolean(), nullable=True),
        sa.Column('fast_tracked', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create return_evidence table
    op.create_table(
        'return_evidence',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('return_id', sa.String(length=50), nullable=False),
        sa.Column('photo_url', sa.String(length=500), nullable=False),
        sa.Column('claimed_issue', sa.Text(), nullable=False),
        sa.Column('ai_verdict', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['return_id'], ['returns.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create notifications_log table
    op.create_table(
        'notifications_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('return_id', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('trigger_reason', sa.String(length=100), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['return_id'], ['returns.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    # Requirements 17.1 specifies indexes on customer_id, purchase_date, and status
    op.create_index('idx_orders_customer_id', 'orders', ['customer_id'], unique=False)
    op.create_index('idx_orders_purchase_date', 'orders', ['purchase_date'], unique=False)
    op.create_index('idx_returns_customer_id', 'returns', ['customer_id'], unique=False)
    op.create_index('idx_returns_status', 'returns', ['status'], unique=False)
    op.create_index('idx_returns_order_id', 'returns', ['order_id'], unique=False)


def downgrade() -> None:
    """Drop all tables and indexes."""
    
    # Drop indexes
    op.drop_index('idx_returns_order_id', table_name='returns')
    op.drop_index('idx_returns_status', table_name='returns')
    op.drop_index('idx_returns_customer_id', table_name='returns')
    op.drop_index('idx_orders_purchase_date', table_name='orders')
    op.drop_index('idx_orders_customer_id', table_name='orders')
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('notifications_log')
    op.drop_table('return_evidence')
    op.drop_table('returns')
    op.drop_table('orders')
    op.drop_table('return_policy')
    op.drop_table('customers')
    
    # Drop enum type
    op.execute("DROP TYPE return_status")
