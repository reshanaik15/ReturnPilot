"""Seed demo orders

Revision ID: 004_seed_orders
Revises: 003_seed_return_policies
Create Date: 2024-01-20 10:03:00.000000

Seeds the orders table with 24 demo orders from the prototype:
- 8 orders for Amara Chen
- 8 orders for Jordan Reyes
- 8 orders for Priya Nair

These orders match the SEED_ORDERS data in ReturnPilot.jsx.
The reference date for the prototype is 2026-08-16, and purchase dates
are calculated as days before that date.
"""
from typing import Sequence, Union
from datetime import date, timedelta
import uuid

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_seed_orders'
down_revision: Union[str, None] = '003_seed_return_policies'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert 24 demo orders."""
    
    # Reference date from prototype: 2026-08-16
    TODAY = date(2026, 8, 16)
    
    def days_ago(n):
        """Calculate date n days before TODAY."""
        return TODAY - timedelta(days=n)
    
    # Generate consistent UUIDs for customers (same as in 002_seed_customers.py)
    namespace_uuid = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    amara_id = str(uuid.uuid5(namespace_uuid, 'amara@demo.dev'))
    jordan_id = str(uuid.uuid5(namespace_uuid, 'jordan@demo.dev'))
    priya_id = str(uuid.uuid5(namespace_uuid, 'priya@demo.dev'))
    
    orders_table = sa.table(
        'orders',
        sa.column('id', sa.String),
        sa.column('customer_id', sa.String),
        sa.column('item_name', sa.String),
        sa.column('category', sa.String),
        sa.column('price', sa.Numeric),
        sa.column('purchase_date', sa.Date),
        sa.column('final_sale', sa.Boolean),
    )
    
    op.bulk_insert(
        orders_table,
        [
            # Amara Chen's orders (8)
            {'id': 'ORD-1001', 'customer_id': amara_id, 'item_name': 'Aria Trail Running Shoes', 'category': 'Footwear', 'price': 118, 'purchase_date': days_ago(7), 'final_sale': False},
            {'id': 'ORD-1002', 'customer_id': amara_id, 'item_name': 'Wool Blend Overcoat', 'category': 'Apparel', 'price': 210, 'purchase_date': days_ago(45), 'final_sale': False},
            {'id': 'ORD-1003', 'customer_id': amara_id, 'item_name': 'NoiseCancel Buds Pro', 'category': 'Electronics', 'price': 159, 'purchase_date': days_ago(2), 'final_sale': False},
            {'id': 'ORD-1004', 'customer_id': amara_id, 'item_name': 'Ceramic Pour-Over Set', 'category': 'Home', 'price': 64, 'purchase_date': days_ago(19), 'final_sale': False},
            {'id': 'ORD-1005', 'customer_id': amara_id, 'item_name': 'Matte Lipstick Duo', 'category': 'Beauty', 'price': 28, 'purchase_date': days_ago(1), 'final_sale': True},
            {'id': 'ORD-1006', 'customer_id': amara_id, 'item_name': 'Canvas Weekender Bag', 'category': 'Accessories', 'price': 95, 'purchase_date': days_ago(27), 'final_sale': False},
            {'id': 'ORD-1007', 'customer_id': amara_id, 'item_name': 'Linen Button-Down Shirt', 'category': 'Apparel', 'price': 58, 'purchase_date': days_ago(6), 'final_sale': False},
            {'id': 'ORD-1008', 'customer_id': amara_id, 'item_name': 'Trail Runner Shoes (Kids)', 'category': 'Footwear', 'price': 64, 'purchase_date': days_ago(15), 'final_sale': False},
            
            # Jordan Reyes' orders (8)
            {'id': 'ORD-2001', 'customer_id': jordan_id, 'item_name': 'Studio Desk Lamp', 'category': 'Home', 'price': 46, 'purchase_date': days_ago(4), 'final_sale': False},
            {'id': 'ORD-2002', 'customer_id': jordan_id, 'item_name': 'Everyday Sneakers', 'category': 'Footwear', 'price': 89, 'purchase_date': days_ago(49), 'final_sale': False},
            {'id': 'ORD-2003', 'customer_id': jordan_id, 'item_name': '4K Streaming Stick', 'category': 'Electronics', 'price': 54, 'purchase_date': days_ago(1), 'final_sale': False},
            {'id': 'ORD-2004', 'customer_id': jordan_id, 'item_name': 'Merino Crew Socks (3-pack)', 'category': 'Apparel', 'price': 24, 'purchase_date': days_ago(5), 'final_sale': False},
            {'id': 'ORD-2005', 'customer_id': jordan_id, 'item_name': 'Cast Iron Skillet', 'category': 'Home', 'price': 52, 'purchase_date': days_ago(13), 'final_sale': False},
            {'id': 'ORD-2006', 'customer_id': jordan_id, 'item_name': 'Leather Card Wallet', 'category': 'Accessories', 'price': 42, 'purchase_date': days_ago(22), 'final_sale': False},
            {'id': 'ORD-2007', 'customer_id': jordan_id, 'item_name': 'Bluetooth Keyboard', 'category': 'Electronics', 'price': 71, 'purchase_date': days_ago(10), 'final_sale': False},
            {'id': 'ORD-2008', 'customer_id': jordan_id, 'item_name': 'Rain Shell Jacket', 'category': 'Apparel', 'price': 132, 'purchase_date': days_ago(3), 'final_sale': False},
            
            # Priya Nair's orders (8)
            {'id': 'ORD-3001', 'customer_id': priya_id, 'item_name': 'Espresso Machine Compact', 'category': 'Electronics', 'price': 189, 'purchase_date': days_ago(17), 'final_sale': False},
            {'id': 'ORD-3002', 'customer_id': priya_id, 'item_name': 'Yoga Mat Pro', 'category': 'Home', 'price': 38, 'purchase_date': days_ago(7), 'final_sale': False},
            {'id': 'ORD-3003', 'customer_id': priya_id, 'item_name': 'Suede Ankle Boots', 'category': 'Footwear', 'price': 145, 'purchase_date': days_ago(11), 'final_sale': False},
            {'id': 'ORD-3004', 'customer_id': priya_id, 'item_name': 'Silk Scarf', 'category': 'Accessories', 'price': 48, 'purchase_date': days_ago(2), 'final_sale': False},
            {'id': 'ORD-3005', 'customer_id': priya_id, 'item_name': 'Vitamin C Serum', 'category': 'Beauty', 'price': 34, 'purchase_date': days_ago(6), 'final_sale': False},
            {'id': 'ORD-3006', 'customer_id': priya_id, 'item_name': 'Wireless Charging Pad', 'category': 'Electronics', 'price': 29, 'purchase_date': days_ago(1), 'final_sale': False},
            {'id': 'ORD-3007', 'customer_id': priya_id, 'item_name': 'Cropped Denim Jacket', 'category': 'Apparel', 'price': 86, 'purchase_date': days_ago(37), 'final_sale': False},
            {'id': 'ORD-3008', 'customer_id': priya_id, 'item_name': 'Ceramic Dinner Set', 'category': 'Home', 'price': 72, 'purchase_date': days_ago(14), 'final_sale': False},
        ]
    )


def downgrade() -> None:
    """Remove demo orders."""
    op.execute("DELETE FROM orders WHERE id LIKE 'ORD-%'")
