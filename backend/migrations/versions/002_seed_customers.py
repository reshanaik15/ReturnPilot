"""Seed demo customers

Revision ID: 002_seed_customers
Revises: 001_initial_schema
Create Date: 2024-01-20 10:01:00.000000

Seeds the customers table with 3 demo customers from the prototype:
- Amara Chen
- Jordan Reyes
- Priya Nair

These customers match the prototype data in ReturnPilot.jsx.
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_seed_customers'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert 3 demo customers."""
    
    # Generate consistent UUIDs for the demo customers
    # Using UUID v5 with a namespace to ensure consistency across runs
    namespace_uuid = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # DNS namespace
    
    amara_id = uuid.uuid5(namespace_uuid, 'amara@demo.dev')
    jordan_id = uuid.uuid5(namespace_uuid, 'jordan@demo.dev')
    priya_id = uuid.uuid5(namespace_uuid, 'priya@demo.dev')
    
    customers_table = sa.table(
        'customers',
        sa.column('id', sa.String),
        sa.column('name', sa.String),
        sa.column('email', sa.String),
        sa.column('contact', sa.String),
    )
    
    op.bulk_insert(
        customers_table,
        [
            {
                'id': str(amara_id),
                'name': 'Amara Chen',
                'email': 'amara@demo.dev',
                'contact': '+1-555-0101'
            },
            {
                'id': str(jordan_id),
                'name': 'Jordan Reyes',
                'email': 'jordan@demo.dev',
                'contact': '+1-555-0102'
            },
            {
                'id': str(priya_id),
                'name': 'Priya Nair',
                'email': 'priya@demo.dev',
                'contact': '+1-555-0103'
            }
        ]
    )


def downgrade() -> None:
    """Remove demo customers."""
    op.execute("DELETE FROM customers WHERE email LIKE '%@demo.dev'")
