# Quick Start: Database Migrations

## TL;DR

```bash
# 1. Set your database URL in .env
echo "DATABASE_URL=postgresql://user:pass@host:5432/dbname" >> .env

# 2. Run migrations
python run_migrations.py

# 3. Verify
python run_migrations.py --check
```

## What Gets Created

After running migrations, your database will have:

- ✅ **3 customers** (Amara Chen, Jordan Reyes, Priya Nair)
- ✅ **6 return policies** (Footwear, Apparel, Electronics, Home, Beauty, Accessories)
- ✅ **24 orders** (8 per customer, from prototype data)
- ✅ **All tables** (customers, orders, returns, return_policy, return_evidence, notifications_log)
- ✅ **All indexes** (for customer_id, purchase_date, status)

## Common Commands

```bash
# Apply all migrations
python run_migrations.py

# Check current version
python run_migrations.py --check

# View migration history
python run_migrations.py --history

# Rollback one migration
python run_migrations.py --rollback

# Reset everything (WARNING: deletes all data)
python run_migrations.py --reset
```

## Verify Setup

```sql
-- Connect to your database
psql $DATABASE_URL

-- Check customers
SELECT name, email FROM customers;

-- Check return policies
SELECT category, window_days FROM return_policy ORDER BY category;

-- Check orders count
SELECT COUNT(*) FROM orders;

-- Check orders per customer
SELECT c.name, COUNT(o.id) as order_count
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
GROUP BY c.name;
```

Expected results:
- 3 customers
- 6 return policies
- 24 orders (8 per customer)

## Troubleshooting

### "DATABASE_URL environment variable is not set"

Create a `.env` file with your database URL:

```bash
DATABASE_URL=postgresql://user:password@host:5432/database
```

### "relation already exists"

Tables already exist. Reset and reapply:

```bash
python run_migrations.py --reset
```

### Connection errors

Verify your DATABASE_URL and that PostgreSQL is running:

```bash
psql $DATABASE_URL -c "SELECT 1"
```

## More Information

- **Detailed Guide**: See [MIGRATIONS_GUIDE.md](MIGRATIONS_GUIDE.md)
- **Migration Docs**: See [migrations/README.md](migrations/README.md)
- **Task Summary**: See [TASK_2.3_SUMMARY.md](TASK_2.3_SUMMARY.md)
