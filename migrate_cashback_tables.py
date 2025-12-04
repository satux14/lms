#!/usr/bin/env python3
"""
Database Migration: Add Cashback Tables
========================================

This script adds all cashback-related tables to existing databases.
This migration is SAFE because it only ADDS new tables - it does NOT modify existing tables.

New tables that will be created:
- cashback_transaction
- loan_cashback_config
- tracker_entry
- tracker_cashback_config
- user_payment_method
- cashback_redemption

Usage:
    python3 migrate_cashback_tables.py [prod|dev|testing|all]

Examples:
    python3 migrate_cashback_tables.py prod          # Migrate only prod
    python3 migrate_cashback_tables.py all           # Migrate all instances
    python3 migrate_cashback_tables.py prod --dry-run  # Dry run (no changes)
"""

import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app_multi import app, db, init_app, VALID_INSTANCES, get_database_uri
from sqlalchemy import create_engine, inspect

def check_table_exists(engine, table_name):
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def migrate_instance(instance, dry_run=False):
    """Migrate a specific instance"""
    print(f"\n{'='*60}")
    print(f"Migrating instance: {instance}")
    if dry_run:
        print("  [DRY RUN MODE - No changes will be made]")
    print(f"{'='*60}")
    
    # Get database URI for this instance
    db_uri = get_database_uri(instance)
    print(f"Database URI: {db_uri}")
    
    # Create engine
    engine = create_engine(db_uri)
    
    # List of tables to create
    cashback_tables = [
        ('cashback_transaction', 'CashbackTransaction'),
        ('loan_cashback_config', 'LoanCashbackConfig'),
        ('tracker_entry', 'TrackerEntry'),
        ('tracker_cashback_config', 'TrackerCashbackConfig'),
        ('user_payment_method', 'UserPaymentMethod'),
        ('cashback_redemption', 'CashbackRedemption')
    ]
    
    tables_created = []
    tables_existing = []
    
    try:
        for table_name, model_name in cashback_tables:
            if check_table_exists(engine, table_name):
                print(f"✓ {table_name} table already exists")
                tables_existing.append(table_name)
            else:
                if dry_run:
                    print(f"→ [DRY RUN] Would create {table_name} table")
                    tables_created.append(table_name)
                else:
                    print(f"→ Creating {table_name} table...")
                    
                    # Import the model
                    from app_multi import (
                        CashbackTransaction, LoanCashbackConfig, TrackerEntry,
                        TrackerCashbackConfig, UserPaymentMethod, CashbackRedemption
                    )
                    
                    # Get the model class
                    model_map = {
                        'CashbackTransaction': CashbackTransaction,
                        'LoanCashbackConfig': LoanCashbackConfig,
                        'TrackerEntry': TrackerEntry,
                        'TrackerCashbackConfig': TrackerCashbackConfig,
                        'UserPaymentMethod': UserPaymentMethod,
                        'CashbackRedemption': CashbackRedemption
                    }
                    
                    model_class = model_map[model_name]
                    
                    # Create the table
                    with engine.connect() as conn:
                        db.metadata.create_all(engine, tables=[model_class.__table__])
                        conn.commit()
                    
                    # Verify creation
                    if check_table_exists(engine, table_name):
                        print(f"✓ {table_name} table created successfully")
                        tables_created.append(table_name)
                    else:
                        print(f"✗ Failed to create {table_name} table")
                        return False
        
        if dry_run:
            print(f"\n[DRY RUN SUMMARY]")
            print(f"  Tables that would be created: {len(tables_created)}")
            if tables_created:
                for t in tables_created:
                    print(f"    - {t}")
            print(f"  Tables that already exist: {len(tables_existing)}")
            return True
        else:
            print(f"\n✓ Migration completed for {instance}")
            print(f"  Tables created: {len(tables_created)}")
            print(f"  Tables already existed: {len(tables_existing)}")
            return True
            
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        engine.dispose()

def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate cashback tables to database')
    parser.add_argument('instance', nargs='?', default='all',
                       choices=['prod', 'dev', 'testing', 'all'],
                       help='Instance to migrate (default: all)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode - show what would be done without making changes')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("CASHBACK TABLES MIGRATION")
    print("="*60)
    print("\nThis migration will add the following NEW tables:")
    print("  - cashback_transaction")
    print("  - loan_cashback_config")
    print("  - tracker_entry")
    print("  - tracker_cashback_config")
    print("  - user_payment_method")
    print("  - cashback_redemption")
    print("\n⚠️  SAFETY GUARANTEE:")
    print("  ✅ Only ADDS new tables")
    print("  ✅ Does NOT modify existing tables")
    print("  ✅ Does NOT delete any data")
    print("  ✅ Safe to run multiple times")
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
    
    # Determine which instances to migrate
    if args.instance == 'all':
        instances = VALID_INSTANCES
    else:
        instances = [args.instance]
    
    print(f"\nInstances to migrate: {', '.join(instances)}")
    
    if not args.dry_run:
        response = input("\nProceed with migration? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Migration cancelled.")
            return
    
    # Initialize app
    init_app()
    
    # Migrate each instance
    success_count = 0
    for instance in instances:
        if migrate_instance(instance, dry_run=args.dry_run):
            success_count += 1
    
    # Summary
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    if args.dry_run:
        print(f"✅ Dry run completed: {success_count}/{len(instances)} instances would be migrated")
    else:
        print(f"✅ Migration completed: {success_count}/{len(instances)} instances migrated successfully")
    
    if success_count == len(instances):
        print("\n🎉 All instances migrated successfully!")
        print("\nNext steps:")
        print("  1. Restart your application")
        print("  2. Verify cashback features are working")
    else:
        print(f"\n⚠️  {len(instances) - success_count} instance(s) failed to migrate")
        print("  Please check the errors above and try again")

if __name__ == '__main__':
    main()

