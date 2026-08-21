"""Seed return policies

Revision ID: 003_seed_return_policies
Revises: 002_seed_customers
Create Date: 2024-01-20 10:02:00.000000

Seeds the return_policy table with 6 product category policies from the prototype:
- Footwear: 30 days
- Apparel: 20 days
- Electronics: 10 days
- Home: 15 days
- Beauty: 7 days
- Accessories: 20 days

These policies match the RETURN_POLICY data in ReturnPilot.jsx.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_seed_return_policies'
down_revision: Union[str, None] = '002_seed_customers'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert return policy rules for all 6 categories."""
    
    return_policy_table = sa.table(
        'return_policy',
        sa.column('category', sa.String),
        sa.column('window_days', sa.Integer),
        sa.column('exclusions', sa.Text),
        sa.column('notes', sa.Text),
    )
    
    op.bulk_insert(
        return_policy_table,
        [
            {
                'category': 'Footwear',
                'window_days': 30,
                'exclusions': 'worn outdoors or visible outsole wear',
                'notes': 'Shoes must be unworn outdoors and in original condition'
            },
            {
                'category': 'Apparel',
                'window_days': 20,
                'exclusions': 'tags removed or item worn beyond trying on',
                'notes': 'All tags must be attached and item unworn'
            },
            {
                'category': 'Electronics',
                'window_days': 10,
                'exclusions': 'opened software activation; final-sale clearance electronics',
                'notes': 'Software products cannot be opened; clearance items are final sale'
            },
            {
                'category': 'Home',
                'window_days': 15,
                'exclusions': 'used or seasoned cookware',
                'notes': 'Home goods must be unused and in original packaging'
            },
            {
                'category': 'Beauty',
                'window_days': 7,
                'exclusions': 'opened or used product; clearance items are final sale',
                'notes': 'Beauty products must be sealed and unopened'
            },
            {
                'category': 'Accessories',
                'window_days': 20,
                'exclusions': 'signs of wear',
                'notes': 'Accessories must show no signs of use'
            }
        ]
    )


def downgrade() -> None:
    """Remove return policy rules."""
    op.execute("DELETE FROM return_policy WHERE category IN ('Footwear', 'Apparel', 'Electronics', 'Home', 'Beauty', 'Accessories')")
