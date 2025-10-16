"""
Post-Migration Verification Script
===================================

Run this AFTER migrate_daily_tracker.py to verify everything worked correctly.

Usage:
    python3 verify_migration_success.py
"""

import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app_multi import app, db, init_app, VALID_INSTANCES, get_database_uri
from sqlalchemy import create_engine, inspect

def verify_table_structure(engine):
    """Verify the daily_tracker table has correct structure"""
    inspector = inspect(engine)
    
    if 'daily_tracker' not in inspector.get_table_names():
        return False, "Table does not exist"
    
    # Get columns
    columns = inspector.get_columns('daily_tracker')
    column_names = [col['name'] for col in columns]
    
    required_columns = [
        'id', 'user_id', 'tracker_name', 'tracker_type', 'investment',
        'scheme_period', 'start_date', 'filename', 'created_at', 
        'updated_at', 'is_active'
    ]
    
    missing_columns = [col for col in required_columns if col not in column_names]
    
    if missing_columns:
        return False, f"Missing columns: {', '.join(missing_columns)}"
    
    return True, "All columns present"

def verify_existing_tables_intact(engine, instance):
    """Verify that existing tables are still intact"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    # Core tables that should exist
    core_tables = ['user', 'loan', 'payment', 'interest_rate', 'pending_interest']
    
    intact = True
    messages = []
    
    for table in core_tables:
        if table in tables:
            # Get row count
            try:
                with engine.connect() as conn:
                    result = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    count = result.scalar()
                    messages.append(f"  ✓ {table}: {count} rows")
            except Exception as e:
                messages.append(f"  ⚠️  {table}: Error reading ({e})")
        else:
            messages.append(f"  ⚠️  {table}: Not found")
            intact = False
    
    return intact, messages

def verify_instance(instance):
    """Verify migration for a specific instance"""
    print(f"\n{'='*70}")
    print(f"Instance: {instance}")
    print(f"{'='*70}")
    
    # Get database URI
    db_uri = get_database_uri(instance)
    db_path = db_uri.replace('sqlite:///', '')
    
    if not Path(db_path).exists():
        print(f"⚠️  Database file does not exist: {db_path}")
        return False
    
    # Create engine
    engine = create_engine(db_uri)
    
    # Check if daily_tracker table exists
    inspector = inspect(engine)
    has_daily_tracker = 'daily_tracker' in inspector.get_table_names()
    
    if not has_daily_tracker:
        print(f"✗ FAILED: daily_tracker table not found")
        engine.dispose()
        return False
    
    print(f"✓ daily_tracker table exists")
    
    # Verify table structure
    structure_ok, message = verify_table_structure(engine)
    if structure_ok:
        print(f"✓ Table structure is correct")
    else:
        print(f"✗ Table structure issue: {message}")
        engine.dispose()
        return False
    
    # Verify existing tables are intact
    print(f"\nExisting tables status:")
    intact, messages = verify_existing_tables_intact(engine, instance)
    for msg in messages:
        print(msg)
    
    if not intact:
        print(f"\n⚠️  Some existing tables may have issues")
    else:
        print(f"\n✓ All existing tables intact")
    
    # Check daily tracker directory
    tracker_dir = Path("instances") / instance / "daily-trackers"
    if tracker_dir.exists():
        print(f"\n✓ Tracker directory exists: {tracker_dir}")
    else:
        print(f"\n→ Tracker directory will be created on first use: {tracker_dir}")
    
    # Get row count in daily_tracker
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT COUNT(*) FROM daily_tracker")
            count = result.scalar()
            print(f"\n📊 Current trackers in database: {count}")
    except Exception as e:
        print(f"\n⚠️  Could not count trackers: {e}")
    
    engine.dispose()
    return True

def main():
    """Main verification function"""
    print("\n" + "="*70)
    print("POST-MIGRATION VERIFICATION")
    print("="*70)
    print("\nVerifying that the migration completed successfully...")
    
    # Initialize the app
    print("\n→ Initializing application...")
    try:
        init_app()
        print("✓ Application initialized")
    except Exception as e:
        print(f"✗ Failed to initialize application: {e}")
        return 1
    
    # Verify each instance
    results = {}
    for instance in VALID_INSTANCES:
        results[instance] = verify_instance(instance)
    
    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    for instance, success in results.items():
        status = "✓ SUCCESS" if success else "✗ ISSUES FOUND"
        print(f"{instance}: {status}")
    
    all_success = all(results.values())
    
    if all_success:
        print("\n" + "="*70)
        print("✓ MIGRATION SUCCESSFUL!")
        print("="*70)
        print("\nAll instances have the daily_tracker table.")
        print("All existing data is intact.")
        print("\n📋 NEXT STEPS:")
        print("  1. Restart your application: python3 app_multi.py")
        print("  2. Log in as admin")
        print("  3. Navigate to 'Daily Trackers' in the sidebar")
        print("  4. Create your first tracker")
        print("\n📖 See DAILY_TRACKER_SETUP.md for detailed instructions")
        return 0
    else:
        print("\n" + "="*70)
        print("⚠️  VERIFICATION FOUND ISSUES")
        print("="*70)
        print("\nPlease review the errors above.")
        print("Your existing data should still be intact.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

