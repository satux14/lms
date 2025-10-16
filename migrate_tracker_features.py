"""
Database Migration: Add tracker close/delete features
======================================================

This script adds the is_closed_by_user column to existing daily_tracker tables.
Run this to add the new close/delete/download features.

Usage:
    python3 migrate_tracker_features.py
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
    if table_name not in inspector.get_table_names():
        return False
    columns = inspector.get_columns(table_name)
    return any(col['name'] == column_name for col in columns)

def migrate_instance(instance):
    """Add is_closed_by_user column to an instance"""
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
    
    # Check if is_closed_by_user column already exists
    if check_column_exists(engine, 'daily_tracker', 'is_closed_by_user'):
        print(f"✓ is_closed_by_user column already exists in {instance} database")
        engine.dispose()
        return True
    
    print(f"→ Adding is_closed_by_user column to {instance} database...")
    
    try:
        # Add the column with default value False
        with engine.connect() as conn:
            # Add column (SQLite syntax)
            conn.execute(text('ALTER TABLE daily_tracker ADD COLUMN is_closed_by_user BOOLEAN DEFAULT 0'))
            
            # Set default to False for existing rows
            conn.execute(text("UPDATE daily_tracker SET is_closed_by_user = 0 WHERE is_closed_by_user IS NULL"))
            
            conn.commit()
        
        # Verify addition
        if check_column_exists(engine, 'daily_tracker', 'is_closed_by_user'):
            print(f"✓ is_closed_by_user column added successfully to {instance} database")
            print(f"  All existing trackers set to is_closed_by_user=False (active for users)")
            return True
        else:
            print(f"✗ Failed to add is_closed_by_user column to {instance} database")
            return False
            
    except Exception as e:
        print(f"✗ Error adding column to {instance} database: {e}")
        return False
    finally:
        engine.dispose()

def main():
    """Main migration function"""
    print("\n" + "="*60)
    print("ADD TRACKER FEATURES MIGRATION")
    print("="*60)
    print("\nThis script adds features for:")
    print("  • Users can close/hide their trackers")
    print("  • Admin can delete trackers")
    print("  • Admin can download Excel files")
    print("  • Admin can reopen trackers closed by users")
    print("\nInstances to migrate:", ", ".join(VALID_INSTANCES))
    
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
        print("\nNew features enabled:")
        print("  ✓ Users can close their trackers (hidden from their view)")
        print("  ✓ Admin can see all trackers including closed ones")
        print("  ✓ Admin can delete trackers (soft delete)")
        print("  ✓ Admin can download Excel files")
        print("  ✓ Admin can reopen trackers for users")
        print("\nYou can now:")
        print("1. Restart your application")
        print("2. Users will see 'Close Tracker' button on their tracker page")
        print("3. Admin will see Download, Delete, and Reopen buttons")
        return 0
    else:
        print("\n✗ Some instances failed to migrate")
        print("Please check the errors above and try again")
        return 1

if __name__ == '__main__':
    sys.exit(main())

