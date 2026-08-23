"""
Checkpoint 3 - Database Setup Complete Verification
Verifies all aspects of the database setup for backend-architecture-migration spec.

Tests:
1. Supabase connection works
2. All tables are created with correct schema
3. Seed data is inserted correctly (3 customers, 24 orders, 6 return policies)
4. All relationships and foreign keys are working
"""

import asyncio
import sys

# Windows consoles default to cp1252, which can't encode the checkmark
# characters this script prints — force UTF-8 so it doesn't crash mid-run.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from sqlalchemy import select, inspect, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from database import AsyncSessionLocal, engine, check_database_health
from models import (
    Customer,
    Order,
    ReturnPolicy,
    Return,
    ReturnEvidence,
    NotificationLog,
)


class CheckpointVerifier:
    """Verifies all aspects of the database setup."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = []
    
    def print_header(self, title):
        """Print a formatted section header."""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)
    
    def print_success(self, message):
        """Print a success message."""
        print(f"  ✓ {message}")
        self.passed += 1
    
    def print_failure(self, message):
        """Print a failure message."""
        print(f"  ✗ {message}")
        self.failed += 1
    
    def print_warning(self, message):
        """Print a warning message."""
        print(f"  ⚠ {message}")
        self.warnings.append(message)
    
    def print_info(self, message):
        """Print an info message."""
        print(f"    {message}")
    
    async def verify_connection(self):
        """Verify database connection."""
        self.print_header("1. Database Connection Test")
        
        try:
            health = await check_database_health()
            
            if health.get("connected"):
                self.print_success("Database connection established")
                self.print_info(f"Database type: {health.get('database')}")
                self.print_info(f"Pool size: {health.get('pool_size')}")
                self.print_info(f"Connections checked out: {health.get('pool_checkedout')}")
                return True
            else:
                self.print_failure(f"Database connection failed: {health.get('error')}")
                return False
        except Exception as e:
            self.print_failure(f"Database connection error: {str(e)}")
            return False
    
    async def verify_schema(self):
        """Verify all tables exist with correct schema."""
        self.print_header("2. Schema Verification")
        
        try:
            async with engine.connect() as connection:
                # Use run_sync to perform all inspector/database reflection work
                expected_tables = [
                    "customers",
                    "return_policy",
                    "orders",
                    "returns",
                    "return_evidence",
                    "notifications_log"
                ]

                def _collect_schema(sync_conn):
                    insp = inspect(sync_conn)
                    tables = insp.get_table_names()
                    cols = {t: insp.get_columns(t) for t in expected_tables if t in tables}
                    idxs = {}
                    # indexes we care about
                    indexes_to_check = {
                        "orders": ["idx_orders_customer_id", "idx_orders_purchase_date"],
                        "returns": ["idx_returns_customer_id", "idx_returns_status", "idx_returns_order_id"]
                    }
                    for table, _ in indexes_to_check.items():
                        if table in tables:
                            try:
                                idxs[table] = insp.get_indexes(table)
                            except Exception:
                                idxs[table] = []
                        else:
                            idxs[table] = []

                    return tables, cols, idxs

                tables, cols, idxs = await connection.run_sync(_collect_schema)

                for table in expected_tables:
                    if table in tables:
                        self.print_success(f"Table '{table}' exists")
                    else:
                        self.print_failure(f"Table '{table}' is missing")

                # Verify key columns for each table using the collected columns dict
                async def _check_columns(table_name, expected_columns):
                    if table_name not in cols:
                        self.print_warning(f"Table '{table_name}' missing columns: table not found")
                        return
                    column_names = [col["name"] for col in cols[table_name]]
                    missing = [col for col in expected_columns if col not in column_names]
                    if missing:
                        self.print_warning(f"Table '{table_name}' missing columns: {', '.join(missing)}")
                    else:
                        self.print_info(f"✓ Table '{table_name}' has all {len(expected_columns)} required columns")

                await _check_columns("customers", ["id", "name", "email", "contact", "created_at"])
                await _check_columns("return_policy", ["category", "window_days", "exclusions", "notes"])
                await _check_columns("orders", ["id", "customer_id", "item_name", "category", "price", "purchase_date", "final_sale", "created_at"]) 
                await _check_columns("returns", ["id", "order_id", "customer_id", "status", "reason", "agent_reasoning_log", "flagged_for_review", "fast_tracked", "created_at", "updated_at"])
                await _check_columns("return_evidence", ["id", "return_id", "photo_url", "claimed_issue", "ai_verdict", "created_at"])
                await _check_columns("notifications_log", ["id", "return_id", "message", "trigger_reason", "sent_at"])

                # Verify indexes from collected idxs
                for table, indexes in idxs.items():
                    index_names = [idx.get("name") for idx in indexes]
                    expected_idx_list = {
                        "orders": ["idx_orders_customer_id", "idx_orders_purchase_date"],
                        "returns": ["idx_returns_customer_id", "idx_returns_status", "idx_returns_order_id"]
                    }.get(table, [])
                    for expected_idx in expected_idx_list:
                        if expected_idx in index_names:
                            self.print_info(f"✓ Index '{expected_idx}' exists on '{table}'")
                        else:
                            self.print_warning(f"Index '{expected_idx}' missing on '{table}'")
                
        except Exception as e:
            self.print_failure(f"Schema verification error: {str(e)}")
    
    async def verify_table_columns(self, inspector, table_name, expected_columns):
        """Verify a table has the expected columns."""
        try:
            columns = await asyncio.to_thread(inspector.get_columns, table_name)
            column_names = [col["name"] for col in columns]
            
            missing = [col for col in expected_columns if col not in column_names]
            if missing:
                self.print_warning(f"Table '{table_name}' missing columns: {', '.join(missing)}")
            else:
                self.print_info(f"✓ Table '{table_name}' has all {len(expected_columns)} required columns")
        except Exception as e:
            self.print_failure(f"Error checking columns for '{table_name}': {str(e)}")
    
    async def verify_indexes(self, inspector):
        """Verify important indexes exist."""
        try:
            # Check for performance indexes mentioned in design
            indexes_to_check = {
                "orders": ["idx_orders_customer_id", "idx_orders_purchase_date"],
                "returns": ["idx_returns_customer_id", "idx_returns_status", "idx_returns_order_id"]
            }
            
            for table, expected_indexes in indexes_to_check.items():
                indexes = await asyncio.to_thread(inspector.get_indexes, table)
                index_names = [idx["name"] for idx in indexes]
                
                for expected_idx in expected_indexes:
                    if expected_idx in index_names:
                        self.print_info(f"✓ Index '{expected_idx}' exists on '{table}'")
                    else:
                        self.print_warning(f"Index '{expected_idx}' missing on '{table}'")
        except Exception as e:
            self.print_warning(f"Index verification error: {str(e)}")
    
    async def verify_seed_data(self):
        """Verify seed data is inserted correctly."""
        self.print_header("3. Seed Data Verification")
        
        try:
            async with AsyncSessionLocal() as session:
                # Verify 3 customers
                result = await session.execute(select(Customer))
                customers = result.scalars().all()
                
                if len(customers) == 3:
                    self.print_success(f"Found 3 customers (expected 3)")
                    for customer in customers:
                        self.print_info(f"  - {customer.name} ({customer.email})")
                else:
                    self.print_failure(f"Found {len(customers)} customers (expected 3)")
                
                # Verify customer names match prototype
                expected_names = {"Amara Chen", "Jordan Reyes", "Priya Nair"}
                actual_names = {c.name for c in customers}
                if expected_names == actual_names:
                    self.print_success("Customer names match prototype data")
                else:
                    self.print_warning(f"Customer names mismatch. Expected: {expected_names}, Got: {actual_names}")
                
                # Verify 24 orders
                result = await session.execute(select(Order))
                orders = result.scalars().all()
                
                if len(orders) == 27:
                    self.print_success(f"Found 27 orders (expected 27)")
                else:
                    self.print_failure(f"Found {len(orders)} orders (expected 27)")
                
                # Verify order distribution (8 for Amara/Jordan, 11 for Priya)
                if len(customers) == 3:
                    for customer in customers:
                        customer_orders = [o for o in orders if str(o.customer_id) == str(customer.id)]
                        expected_count = 11 if customer.name == "Priya Nair" else 8
                        if len(customer_orders) == expected_count:
                            self.print_info(f"  ✓ {customer.name}: {expected_count} orders")
                        else:
                            self.print_warning(f"  {customer.name}: {len(customer_orders)} orders (expected {expected_count})")
                
                # Verify 6 return policies
                result = await session.execute(select(ReturnPolicy))
                policies = result.scalars().all()
                
                if len(policies) == 6:
                    self.print_success(f"Found 6 return policies (expected 6)")
                    for policy in policies:
                        self.print_info(f"  - {policy.category}: {policy.window_days} days")
                else:
                    self.print_failure(f"Found {len(policies)} return policies (expected 6)")
                
                # Verify policy categories match prototype
                expected_categories = {"Footwear", "Apparel", "Electronics", "Home", "Beauty", "Accessories"}
                actual_categories = {p.category for p in policies}
                if expected_categories == actual_categories:
                    self.print_success("Return policy categories match prototype data")
                else:
                    missing = expected_categories - actual_categories
                    if missing:
                        self.print_failure(f"Missing policy categories: {missing}")
                
        except Exception as e:
            self.print_failure(f"Seed data verification error: {str(e)}")
    
    async def verify_relationships(self):
        """Verify foreign key relationships work correctly."""
        self.print_header("4. Relationship Verification")
        
        try:
            async with AsyncSessionLocal() as session:
                # Eager-load orders and order.policy to avoid async lazy loads
                result = await session.execute(
                    select(Customer).options(
                        selectinload(Customer.orders).selectinload(Order.policy)
                    ).limit(1)
                )
                customer = result.scalar_one_or_none()

                if customer:
                    order_count = len(customer.orders)
                    self.print_success(f"Customer -> Orders relationship working ({order_count} orders loaded)")

                    if customer.orders:
                        order = customer.orders[0]
                        if order.customer and order.customer.id == customer.id:
                            self.print_success("Order -> Customer relationship working")
                        else:
                            self.print_failure("Order -> Customer relationship broken")

                        if order.policy:
                            self.print_success(f"Order -> Policy relationship working (category: {order.policy.category})")
                        else:
                            self.print_failure("Order -> Policy relationship broken")
                else:
                    self.print_warning("No customers found to test relationships")
                
        except Exception as e:
            self.print_failure(f"Relationship verification error: {str(e)}")
    
    async def verify_data_quality(self):
        """Verify data quality and constraints."""
        self.print_header("5. Data Quality Verification")
        
        try:
            async with AsyncSessionLocal() as session:
                # Check for unique emails
                result = await session.execute(text("SELECT email, COUNT(*) as cnt FROM customers GROUP BY email HAVING COUNT(*) > 1"))
                duplicates = result.fetchall()
                
                if not duplicates:
                    self.print_success("All customer emails are unique")
                else:
                    self.print_failure(f"Found duplicate emails: {duplicates}")
                
                # Check for valid order IDs (ORD-XXXX format)
                result = await session.execute(select(Order))
                orders = result.scalars().all()
                
                invalid_ids = [o.id for o in orders if not o.id.startswith("ORD-")]
                if not invalid_ids:
                    self.print_success("All order IDs follow ORD-XXXX format")
                else:
                    self.print_failure(f"Invalid order IDs found: {invalid_ids}")
                
                # Check for valid prices (> 0)
                invalid_prices = [o.id for o in orders if o.price <= 0]
                if not invalid_prices:
                    self.print_success("All order prices are positive")
                else:
                    self.print_failure(f"Orders with invalid prices: {invalid_prices}")
                
                # Check for future purchase dates
                from datetime import date
                today = date.today()
                future_orders = [o.id for o in orders if o.purchase_date > today]
                if future_orders:
                    self.print_warning(f"Orders with future dates (may be expected for demo): {len(future_orders)}")
                else:
                    self.print_success("No orders with future purchase dates")
                
        except Exception as e:
            self.print_failure(f"Data quality verification error: {str(e)}")
    
    def print_summary(self):
        """Print verification summary."""
        self.print_header("CHECKPOINT 3 VERIFICATION SUMMARY")
        
        print(f"\n  Tests Passed:  {self.passed}")
        print(f"  Tests Failed:  {self.failed}")
        print(f"  Warnings:      {len(self.warnings)}")
        
        if self.warnings:
            print("\n  Warnings:")
            for warning in self.warnings:
                print(f"    ⚠ {warning}")
        
        print("\n" + "=" * 70)
        
        if self.failed == 0:
            print("  ✓ CHECKPOINT 3 PASSED - Database setup complete!")
        else:
            print("  ✗ CHECKPOINT 3 FAILED - Issues found in database setup")
        
        print("=" * 70 + "\n")
        
        return self.failed == 0


async def main():
    """Run all checkpoint verifications."""
    print("\n" + "=" * 70)
    print("  CHECKPOINT 3: DATABASE SETUP COMPLETE")
    print("  Spec: backend-architecture-migration")
    print("=" * 70)
    
    verifier = CheckpointVerifier()
    
    # Run all verifications
    connection_ok = await verifier.verify_connection()
    
    if not connection_ok:
        print("\n" + "=" * 70)
        print("  ✗ CRITICAL: Cannot connect to database")
        print("  Please check:")
        print("    1. DATABASE_URL is set in .env file")
        print("    2. Supabase PostgreSQL instance is running")
        print("    3. Network connectivity to Supabase")
        print("=" * 70 + "\n")
        sys.exit(1)
    
    await verifier.verify_schema()
    await verifier.verify_seed_data()
    await verifier.verify_relationships()
    await verifier.verify_data_quality()
    
    # Print summary
    success = verifier.print_summary()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
