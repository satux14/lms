"""
Database Migration: Add DailyTracker Table
===========================================

This script adds the DailyTracker table to existing databases.
Run this once after deploying the daily tracker feature.

Usage:
    python migrate_daily_tracker.py
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

def migrate_instance(instance):
    """Migrate a specific instance"""
    print(f"\n{'='*60}")
    print(f"Migrating instance: {instance}")
    print(f"{'='*60}")
    
    # Get database URI for this instance
    db_uri = get_database_uri(instance)
    print(f"Database URI: {db_uri}")
    
    # Create engine
    engine = create_engine(db_uri)
    
    # Check if DailyTracker table exists
    if check_table_exists(engine, 'daily_tracker'):
        print(f"✓ DailyTracker table already exists in {instance} database")
        return True
    
    print(f"→ Creating DailyTracker table in {instance} database...")
    
    try:
        # Create the table
        with engine.connect() as conn:
            # Import models to ensure they're registered
            from app_multi import DailyTracker
            
            # Create the table
            db.metadata.create_all(engine, tables=[DailyTracker.__table__])
            conn.commit()
        
        # Verify creation
        if check_table_exists(engine, 'daily_tracker'):
            print(f"✓ DailyTracker table created successfully in {instance} database")
            return True
        else:
            print(f"✗ Failed to create DailyTracker table in {instance} database")
            return False
            
    except Exception as e:
        print(f"✗ Error creating table in {instance} database: {e}")
        return False
    finally:
        engine.dispose()

def main():
    """Main migration function"""
    print("\n" + "="*60)
    print("DAILY TRACKER DATABASE MIGRATION")
    print("="*60)
    print("\nThis script will add the DailyTracker table to all instances.")
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
        print("\nNext steps:")
        print("1. Restart your application")
        print("2. Log in as admin")
        print("3. Navigate to Daily Trackers section")
        print("4. Create your first tracker")
        return 0
    else:
        print("\n✗ Some instances failed to migrate")
        print("Please check the errors above and try again")
        return 1

if __name__ == '__main__':
    sys.exit(main())

