# Database Migrations and Seed Scripts - Implementation Guide

## Overview

This document describes the database migration and seed script implementation for Task 2.3 of the backend-architecture-migration spec.

## What Was Created

### 1. Alembic Configuration

- **alembic.ini** - Configured to read DATABASE_URL from environment variables
- **migrations/env.py** - Configured to import our SQLAlchemy models and use async-compatible connection strings

### 2. Migration Scripts

#### 001_initial_schema.py
Creates the complete database schema with all 6 tables:

- **customers** - Customer information (id, name, email, contact)
- **return_policy** - Return policy rules by category
- **orders** - Customer purchase records
- **returns** - Return request records with status tracking
- **return_evidence** - Photo evidence and AI verdicts
- **notifications_log** - Notification history

**Indexes Created** (per Requirements 17.1):
- `idx_orders_customer_id` - For filtering orders by customer
- `idx_orders_purchase_date` - For date-based queries
- `idx_returns_customer_id` - For filtering returns by customer
- `idx_returns_status` - For filtering returns by status
- `idx_returns_order_id` - For looking up returns by order

#### 002_seed_customers.py
Seeds 3 demo customers (per Requirements 17.3):
- **Amara Chen** (amara@demo.dev)
- **Jordan Reyes** (jordan@demo.dev)
- **Priya Nair** (priya@demo.dev)

Uses UUID v5 with DNS namespace for consistent UUID generation across runs.

#### 003_seed_return_policies.py
Seeds 6 return policy categories (per Requirements 17.5):
- **Footwear**: 30 days, exclusions: "worn outdoors or visible outsole wear"
- **Apparel**: 20 days, exclusions: "tags removed or item worn beyond trying on"
- **Electronics**: 10 days, exclusions: "opened software activation; final-sale clearance electronics"
- **Home**: 15 days, exclusions: "used or seasoned cookware"
- **Beauty**: 7 days, exclusions: "opened or used product; clearance items are final sale"
- **Accessories**: 20 days, exclusions: "signs of wear"

#### 004_seed_orders.py
Seeds 24 demo orders (per Requirements 17.4):
- 8 orders for Amara Chen (ORD-1001 through ORD-1008)
- 8 orders for Jordan Reyes (ORD-2001 through ORD-2008)
- 8 orders for Priya Nair (ORD-3001 through ORD-3008)

All orders use purchase dates relative to the prototype reference date (2026-08-16).

### 3. Helper Scripts

#### run_migrations.py
Python script to easily run migrations with various options:
- `python run_migrations.py` - Apply all migrations
- `python run_migrations.py --check` - Check current version
- `python run_migrations.py --rollback` - Rollback one migration
- `python run_migrations.py --reset` - Reset and reapply all
- `python run_migrations.py --history` - Show migration history

#### migrations/README.md
Comprehensive documentation for working with migrations.

## Usage

### First-Time Setup

1. **Configure Database URL**

Create a `.env` file in the backend directory:

```bash
cd backend
cp .env.example .env
```

Edit `.env` and set your DATABASE_URL:

```
DATABASE_URL=postgresql://user:password@localhost:5432/returnpilot
```

2. **Run Migrations**

Apply all migrations and seed data:

```bash
python run_migrations.py
```

This will:
- Create all tables and indexes
- Populate customers table with 3 demo users
- Populate return_policy table with 6 categories
- Populate orders table with 24 demo orders

### Verifying the Setup

1. **Check Migration Status**

```bash
python run_migrations.py --check
```

Should show:
```
001_initial_schema (head)
002_seed_customers
003_seed_return_policies
004_seed_orders
```

2. **Verify Data in Database**

Connect to your database and verify:

```sql
-- Check customers
SELECT COUNT(*) FROM customers; -- Should be 3

-- Check return policies
SELECT category, window_days FROM return_policy ORDER BY category;
-- Should show 6 categories

-- Check orders
SELECT COUNT(*) FROM orders; -- Should be 24
SELECT customer_id, COUNT(*) FROM orders GROUP BY customer_id;
-- Should show 8 orders per customer
```

### Using with Alembic Directly

You can also use Alembic commands directly:

```bash
# Apply all migrations
alembic upgrade head

# Check current version
alembic current

# View history
alembic history --verbose

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade 002_seed_customers
```

## Migration Order

The migrations MUST be applied in this order:

1. **001_initial_schema** - Creates tables (required first)
2. **002_seed_customers** - Requires customers table
3. **003_seed_return_policies** - Requires return_policy table
4. **004_seed_orders** - Requires customers and return_policy tables (foreign keys)

Alembic handles this automatically through the `down_revision` chain in each migration file.

## Data Model

### Customer UUIDs

The seed scripts generate consistent UUIDs for demo customers using UUID v5:

```python
namespace_uuid = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
amara_id = uuid.uuid5(namespace_uuid, 'amara@demo.dev')
```

This ensures the same UUIDs are generated each time migrations run.

### Purchase Dates

Order purchase dates are calculated relative to the prototype reference date (2026-08-16):

- `daysAgo(7)` = 2026-08-09
- `daysAgo(45)` = 2026-07-02
- etc.

This matches the prototype's date calculation logic.

## Troubleshooting

### "relation already exists" error

The tables may already exist. Options:

1. Reset and reapply:
   ```bash
   python run_migrations.py --reset
   ```

2. Or manually drop and recreate:
   ```sql
   DROP SCHEMA public CASCADE;
   CREATE SCHEMA public;
   ```
   Then run migrations again.

### "column does not exist" error

Models and migrations may be out of sync. Try:

```bash
python run_migrations.py --check
alembic upgrade head
```

### Connection errors

Verify DATABASE_URL:

```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Or check the URL in Python
python -c "from config import settings; print(settings.database_url)"
```

## Requirements Coverage

This implementation satisfies the following requirements:

- ✅ **17.1** - Migration script creates all required tables
- ✅ **17.2** - Seed script populates customers, orders, and return_policy tables
- ✅ **17.3** - Seed script inserts 3 customers (Amara, Jordan, Priya)
- ✅ **17.4** - Seed script inserts 24 orders from prototype
- ✅ **17.5** - Seed script inserts return policy rules for 6 categories
- ✅ **17.6** - Added indexes on customer_id, purchase_date, and status fields

Additionally:
- Indexes added per design document for query performance
- Foreign key constraints properly defined
- Enum type created for return_status
- Rollback functionality implemented for all migrations
- Comprehensive documentation provided

## Next Steps

After running migrations:

1. **Verify Data** - Connect to database and check tables are populated
2. **Test Queries** - Run some test queries to verify indexes work
3. **Run Backend Tests** - Use `python test_database.py` to test database connectivity
4. **Proceed to Task 2.4** - Implement tool functions (search_orders, check_policy, etc.)

## Related Files

- `backend/database.py` - Database connection and session management
- `backend/models/__init__.py` - SQLAlchemy model definitions
- `backend/config.py` - Configuration and environment variables
- `backend/test_database.py` - Database connection test script
