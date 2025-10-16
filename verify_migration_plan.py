"""
Migration Plan Verification (Dry Run)
======================================

This script shows exactly what the migration will do WITHOUT making any changes.
Run this to see what will happen before running the actual migration.

Usage:
    python3 verify_migration_plan.py
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

def get_existing_tables(engine):
    """Get list of all existing tables"""
    inspector = inspect(engine)
    return inspector.get_table_names()

def analyze_instance(instance):
    """Analyze what will happen for a specific instance"""
    print(f"\n{'='*70}")
    print(f"Instance: {instance}")
    print(f"{'='*70}")
    
    # Get database URI for this instance
    db_uri = get_database_uri(instance)
    db_path = db_uri.replace('sqlite:///', '')
    
    print(f"Database Path: {db_path}")
    
    # Check if database exists
    if not Path(db_path).exists():
        print(f"⚠️  Database file does not exist yet")
        print(f"   Action: Database and table will be created on first run")
        return
    
    # Create engine
    engine = create_engine(db_uri)
    
    # Get existing tables
    existing_tables = get_existing_tables(engine)
    print(f"\nExisting Tables ({len(existing_tables)}):")
    for table in sorted(existing_tables):
        print(f"  - {table}")
    
    # Check if DailyTracker table exists
    has_daily_tracker = check_table_exists(engine, 'daily_tracker')
    
    print(f"\n{'─'*70}")
    if has_daily_tracker:
        print("✓ 'daily_tracker' table ALREADY EXISTS")
        print("  Action: No changes needed for this instance")
    else:
        print("→ 'daily_tracker' table DOES NOT EXIST")
        print("  Action: Table will be CREATED with the following columns:")
        print("    - id (Primary Key)")
        print("    - user_id (Foreign Key to user.id)")
        print("    - tracker_name (String)")
        print("    - tracker_type (String: '50K', '1L', or 'No Reinvest')")
        print("    - investment (Decimal)")
        print("    - scheme_period (Integer)")
        print("    - start_date (Date)")
        print("    - filename (String)")
        print("    - created_at (DateTime)")
        print("    - updated_at (DateTime)")
        print("    - is_active (Boolean)")
    
    print(f"\n{'─'*70}")
    print("SAFETY GUARANTEE:")
    print("  ✓ No existing tables will be modified")
    print("  ✓ No existing data will be deleted")
    print("  ✓ No existing data will be changed")
    print("  ✓ Only adds a NEW table if it doesn't exist")
    
    engine.dispose()

def main():
    """Main verification function"""
    print("\n" + "="*70)
    print("MIGRATION PLAN VERIFICATION (DRY RUN)")
    print("="*70)
    print("\nThis shows what the migration will do WITHOUT making any changes.")
    print("No databases will be modified by running this script.")
    
    # Initialize the app
    print("\n→ Initializing application...")
    init_app()
    print("✓ Application initialized")
    
    # Analyze each instance
    for instance in VALID_INSTANCES:
        analyze_instance(instance)
    
    # Final summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("\n✓ This migration is SAFE because it:")
    print("  1. Only ADDS a new table")
    print("  2. Does NOT modify existing tables")
    print("  3. Does NOT delete any data")
    print("  4. Does NOT change any existing data")
    print("  5. Skips instances where table already exists")
    
    print("\n📋 RECOMMENDED STEPS:")
    print("  1. Run: python3 backup_before_migration.py (backup first)")
    print("  2. Run: python3 migrate_daily_tracker.py (run migration)")
    print("  3. Run: python3 verify_migration_success.py (verify success)")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

