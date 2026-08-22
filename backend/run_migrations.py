#!/usr/bin/env python
"""
Helper script to run Alembic migrations for ReturnPilot database.

This script applies all pending migrations to bring the database schema
up to date and populate it with demo data.

Usage:
    python run_migrations.py                    # Apply all migrations
    python run_migrations.py --check            # Check current version
    python run_migrations.py --rollback         # Rollback one migration
    python run_migrations.py --reset            # Reset to base and reapply all
"""

import sys

# Windows consoles default to cp1252, which can't encode the checkmark/emoji
# characters this script prints — force UTF-8 so it doesn't crash mid-run.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import argparse
from alembic.config import Config
from alembic import command
from config import settings


def run_migrations(action='upgrade'):
    """Run Alembic migrations."""
    
    # Verify DATABASE_URL is set
    if not settings.database_url:
        print("❌ ERROR: DATABASE_URL environment variable is not set.")
        print("Please set DATABASE_URL in your .env file or environment.")
        print("\nExample:")
        print("  DATABASE_URL=postgresql://user:password@host:port/database")
        sys.exit(1)
    
    # Create Alembic config
    alembic_cfg = Config("alembic.ini")
    
    try:
        if action == 'upgrade':
            print("🚀 Applying database migrations...")
            command.upgrade(alembic_cfg, "head")
            print("✅ All migrations applied successfully!")
            print("\n📊 Current database state:")
            command.current(alembic_cfg, verbose=True)
            
        elif action == 'check':
            print("📊 Current migration version:")
            command.current(alembic_cfg, verbose=True)
            
        elif action == 'rollback':
            print("⏪ Rolling back one migration...")
            command.downgrade(alembic_cfg, "-1")
            print("✅ Rollback complete!")
            print("\n📊 Current database state:")
            command.current(alembic_cfg, verbose=True)
            
        elif action == 'reset':
            print("🔄 Resetting database to base...")
            command.downgrade(alembic_cfg, "base")
            print("🚀 Reapplying all migrations...")
            command.upgrade(alembic_cfg, "head")
            print("✅ Database reset complete!")
            print("\n📊 Current database state:")
            command.current(alembic_cfg, verbose=True)
            
        elif action == 'history':
            print("📜 Migration history:")
            command.history(alembic_cfg, verbose=True)
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Verify DATABASE_URL is correct")
        print("2. Ensure database is accessible")
        print("3. Check that PostgreSQL is running")
        print("4. Review the error message above for specific issues")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run ReturnPilot database migrations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_migrations.py              Apply all pending migrations
  python run_migrations.py --check      Check current migration version
  python run_migrations.py --rollback   Rollback one migration
  python run_migrations.py --reset      Reset and reapply all migrations
  python run_migrations.py --history    Show migration history
        """
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check current migration version'
    )
    
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Rollback one migration'
    )
    
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset database to base and reapply all migrations'
    )
    
    parser.add_argument(
        '--history',
        action='store_true',
        help='Show migration history'
    )
    
    args = parser.parse_args()
    
    # Determine action
    if args.check:
        action = 'check'
    elif args.rollback:
        action = 'rollback'
    elif args.reset:
        # Confirm reset action
        print("⚠️  WARNING: This will reset the database and delete all data!")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Reset cancelled.")
            sys.exit(0)
        action = 'reset'
    elif args.history:
        action = 'history'
    else:
        action = 'upgrade'
    
    run_migrations(action)


if __name__ == '__main__':
    main()
