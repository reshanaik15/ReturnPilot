# Database Migrations

This directory contains Alembic migrations for the ReturnPilot database schema.

## Migration Files

### Schema Migrations

- **001_initial_schema.py** - Creates all database tables and indexes
  - Tables: customers, return_policy, orders, returns, return_evidence, notifications_log
  - Indexes on: customer_id, purchase_date, status
  - Enum type: return_status

### Seed Data Migrations

- **002_seed_customers.py** - Seeds 3 demo customers (Amara, Jordan, Priya)
- **003_seed_return_policies.py** - Seeds 6 return policy categories
- **004_seed_orders.py** - Seeds 24 demo orders across all customers

## Running Migrations

### Prerequisites

Ensure DATABASE_URL is set in your environment:

```bash
# Set in .env file or export directly
export DATABASE_URL="postgresql://user:password@host:port/database"
```

### Apply All Migrations

From the backend directory:

```bash
# Apply all pending migrations
alembic upgrade head

# Or use the helper script
python run_migrations.py
```

### Check Current Version

```bash
alembic current
```

### View Migration History

```bash
alembic history --verbose
```

### Rollback Migrations

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade 002_seed_customers

# Rollback all migrations
alembic downgrade base
```

## Creating New Migrations

### Auto-generate from model changes

```bash
alembic revision --autogenerate -m "description of changes"
```

### Create empty migration

```bash
alembic revision -m "description of changes"
```

## Migration Sequence

The migrations must be applied in order:

1. **001_initial_schema** - Creates all tables (required first)
2. **002_seed_customers** - Populates customers (required before orders)
3. **003_seed_return_policies** - Populates return policies (required before orders)
4. **004_seed_orders** - Populates orders (requires customers and policies)

## Demo Data

The seed migrations populate the database with demo data from the prototype:

### Customers
- Amara Chen (amara@demo.dev)
- Jordan Reyes (jordan@demo.dev)
- Priya Nair (priya@demo.dev)

### Return Policies
- Footwear: 30 days
- Apparel: 20 days
- Electronics: 10 days
- Home: 15 days
- Beauty: 7 days
- Accessories: 20 days

### Orders
- 8 orders per customer (24 total)
- Purchase dates relative to 2026-08-16 (prototype reference date)
- Mix of categories and price points

## Troubleshooting

### "relation already exists" error

If you see this error, the tables may already exist. Options:

1. Drop all tables and re-run migrations:
   ```bash
   alembic downgrade base
   alembic upgrade head
   ```

2. Or manually drop the tables and re-run:
   ```sql
   DROP SCHEMA public CASCADE;
   CREATE SCHEMA public;
   ```

### "column does not exist" error

This may indicate migrations are out of sync. Check the current version and re-run:

```bash
alembic current
alembic upgrade head
```

### Connection errors

Verify DATABASE_URL is correct and the database is accessible:

```bash
psql $DATABASE_URL -c "SELECT 1"
```

## Production Deployment

For production deployments:

1. Review all migrations before applying
2. Test migrations on a staging database first
3. Backup production database before applying
4. Apply migrations during a maintenance window
5. Monitor application logs after deployment

```bash
# Production migration workflow
pg_dump $DATABASE_URL > backup.sql
alembic upgrade head
# Verify application health
# If issues occur: alembic downgrade -1
```
