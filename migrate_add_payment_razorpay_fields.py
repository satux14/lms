#!/usr/bin/env python3
"""
Migration: Add Razorpay/Google Pay fields to Payment table
==========================================================

Adds the following columns to the payment table:
- razorpay_order_id (String, nullable)
- razorpay_payment_id (String, nullable)
- razorpay_signature (String, nullable)
- payment_initiated_at (DateTime, nullable)

This migration is safe to run multiple times (idempotent).
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Instance configuration
VALID_INSTANCES = ['prod', 'dev', 'testing']
INSTANCES_DIR = Path('instances')

def get_database_path(instance):
    """Get database path for instance"""
    return INSTANCES_DIR / instance / 'database' / f'lending_app_{instance}.db'

def check_column_exists(conn, table_name, column_name):
    """Check if a column exists in a table"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate_instance(instance, dry_run=False):
    """Migrate a single instance"""
    db_path = get_database_path(instance)
    
    if not db_path.exists():
        print(f"⚠️  Database not found for {instance}: {db_path}")
        return False
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating {instance} instance...")
    print(f"  Database: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check current columns
        cursor.execute("PRAGMA table_info(payment)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"  Current columns: {', '.join(existing_columns)}")
        
        # Columns to add
        columns_to_add = [
            ('razorpay_order_id', 'VARCHAR(100)'),
            ('razorpay_payment_id', 'VARCHAR(100)'),
            ('razorpay_signature', 'VARCHAR(255)'),
            ('payment_initiated_at', 'DATETIME')
        ]
        
        changes_needed = []
        for col_name, col_type in columns_to_add:
            if not check_column_exists(conn, 'payment', col_name):
                changes_needed.append((col_name, col_type))
                print(f"  ➕ Will add column: {col_name} ({col_type})")
            else:
                print(f"  ✓ Column already exists: {col_name}")
        
        if not changes_needed:
            print(f"  ✅ {instance} instance is already up to date!")
            conn.close()
            return True
        
        if dry_run:
            print(f"  [DRY RUN] Would add {len(changes_needed)} columns")
            conn.close()
            return True
        
        # Add columns
        print(f"  Adding {len(changes_needed)} columns...")
        for col_name, col_type in changes_needed:
            try:
                sql = f"ALTER TABLE payment ADD COLUMN {col_name} {col_type}"
                cursor.execute(sql)
                print(f"    ✅ Added {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"    ⚠️  Column {col_name} already exists (skipping)")
                else:
                    raise
        
        conn.commit()
        print(f"  ✅ {instance} instance migrated successfully!")
        
        # Verify columns were added
        cursor.execute("PRAGMA table_info(payment)")
        final_columns = [row[1] for row in cursor.fetchall()]
        print(f"  Final columns: {', '.join(final_columns)}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Error migrating {instance}: {e}")
        if not dry_run:
            conn.rollback()
            conn.close()
        return False

def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Add Razorpay/Google Pay fields to Payment table')
    parser.add_argument('instance', nargs='?', choices=VALID_INSTANCES + ['all'],
                       help='Instance to migrate (prod, dev, testing, or all)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be changed without making changes')
    
    args = parser.parse_args()
    
    if not args.instance:
        print("Usage: python migrate_add_payment_razorpay_fields.py [prod|dev|testing|all] [--dry-run]")
        print("\nExamples:")
        print("  python migrate_add_payment_razorpay_fields.py prod")
        print("  python migrate_add_payment_razorpay_fields.py all")
        print("  python migrate_add_payment_razorpay_fields.py prod --dry-run")
        sys.exit(1)
    
    if args.instance == 'all':
        instances = VALID_INSTANCES
    else:
        instances = [args.instance]
    
    print("=" * 60)
    print("Payment Table Migration: Add Razorpay/Google Pay Fields")
    print("=" * 60)
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made")
    
    success_count = 0
    for instance in instances:
        if migrate_instance(instance, dry_run=args.dry_run):
            success_count += 1
    
    print("\n" + "=" * 60)
    if args.dry_run:
        print(f"✅ Dry run completed: {success_count}/{len(instances)} instances would be migrated")
    else:
        print(f"✅ Migration completed: {success_count}/{len(instances)} instances migrated successfully")
    print("=" * 60)
    
    if success_count == len(instances):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()

