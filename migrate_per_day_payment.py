"""
Database Migration: Add per_day_payment column to DailyTracker
================================================================

This script adds the per_day_payment column to existing daily_tracker tables.
Run this if you already have trackers and need to add the new column.

Usage:
    python3 migrate_per_day_payment.py
"""

import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app_multi import app, init_app, VALID_INSTANCES, get_database_uri
from sqlalchemy import create_engine, inspect, text

def check_column_exists(engine, table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return any(col['name'] == column_name for col in columns)

def migrate_instance(instance):
    """Add per_day_payment column to an instance"""
    print(f"\n{'='*60}")
    print(f"Migrating instance: {instance}")
    print(f"{'='*60}")
    
    # Get database URI for this instance
    db_uri = get_database_uri(instance)
    print(f"Database URI: {db_uri}")
    
    # Create engine
    engine = create_engine(db_uri)
    
    # Check if daily_tracker table exists
    inspector = inspect(engine)
    if 'daily_tracker' not in inspector.get_table_names():
        print(f"ℹ️  daily_tracker table doesn't exist yet in {instance} - skipping")
        engine.dispose()
        return True
    
    # Check if per_day_payment column already exists
    if check_column_exists(engine, 'daily_tracker', 'per_day_payment'):
        print(f"✓ per_day_payment column already exists in {instance} database")
        engine.dispose()
        return True
    
    print(f"→ Adding per_day_payment column to {instance} database...")
    
    try:
        # Add the column with a default value
        with engine.connect() as conn:
            # Add column (SQLite syntax)
            conn.execute(text('ALTER TABLE daily_tracker ADD COLUMN per_day_payment NUMERIC(15, 2)'))
            
            # Update existing rows with default values based on tracker_type
            # 50K -> 500, 1L -> 1000, No Reinvest -> 3000
            conn.execute(text("UPDATE daily_tracker SET per_day_payment = 500 WHERE tracker_type = '50K' AND per_day_payment IS NULL"))
            conn.execute(text("UPDATE daily_tracker SET per_day_payment = 1000 WHERE tracker_type = '1L' AND per_day_payment IS NULL"))
            conn.execute(text("UPDATE daily_tracker SET per_day_payment = 3000 WHERE tracker_type = 'No Reinvest' AND per_day_payment IS NULL"))
            
            conn.commit()
        
        # Verify addition
        if check_column_exists(engine, 'daily_tracker', 'per_day_payment'):
            print(f"✓ per_day_payment column added successfully to {instance} database")
            print(f"  Default values set based on tracker_type")
            return True
        else:
            print(f"✗ Failed to add per_day_payment column to {instance} database")
            return False
            
    except Exception as e:
        print(f"✗ Error adding column to {instance} database: {e}")
        return False
    finally:
        engine.dispose()

def main():
    """Main migration function"""
    print("\n" + "="*60)
    print("ADD PER_DAY_PAYMENT COLUMN MIGRATION")
    print("="*60)
    print("\nThis script will add the per_day_payment column to daily_tracker tables.")
    print("Instances to migrate:", ", ".join(VALID_INSTANCES))
    
    # Initialize the app
    print("\n→ Initializing application...")
    init_app()
    print("✓ Application initialized")
    
    # Migrate each instance
    results = {}
    for instance in VALID_INSTANCES:
        results[instance] = migrate_instance(instance)
    
    # Summary
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    
    for instance, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{instance}: {status}")
    
    all_success = all(results.values())
    
    if all_success:
        print("\n✓ All instances migrated successfully!")
        print("\nThe per_day_payment column has been added.")
        print("Existing trackers have been updated with default values based on their type.")
        print("\nYou can now:")
        print("1. Restart your application")
        print("2. Create new trackers with custom per day payment")
        return 0
    else:
        print("\n✗ Some instances failed to migrate")
        print("Please check the errors above and try again")
        return 1

if __name__ == '__main__':
    sys.exit(main())

