"""
Complete Daily Tracker System Migration
========================================

This script ensures your production database has all required columns
for the daily tracker system including today's updates.

✓ Safe for production - only ADDS missing columns
✗ Never deletes or modifies existing data

Usage:
    python3 migrate_complete_tracker_system.py
"""

import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app_multi import app, db, init_app, VALID_INSTANCES, get_database_uri
from sqlalchemy import create_engine, inspect, text

def check_table_exists(engine, table_name):
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def check_column_exists(engine, table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return False
    columns = inspector.get_columns(table_name)
    return any(col['name'] == column_name for col in columns)

def get_existing_columns(engine, table_name):
    """Get list of existing column names"""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return []
    columns = inspector.get_columns(table_name)
    return [col['name'] for col in columns]

def migrate_instance(instance):
    """Ensure all required columns exist in an instance"""
    print(f"\n{'='*70}")
    print(f"Checking instance: {instance}")
    print(f"{'='*70}")
    
    # Get database URI for this instance
    db_uri = get_database_uri(instance)
    print(f"Database: {db_uri}")
    
    # Create engine
    engine = create_engine(db_uri)
    changes_made = []
    
    try:
        # Step 1: Check if daily_tracker table exists
        if not check_table_exists(engine, 'daily_tracker'):
            print(f"\n→ Creating daily_tracker table...")
            from app_multi import DailyTracker
            db.metadata.create_all(engine, tables=[DailyTracker.__table__])
            print(f"✓ daily_tracker table created")
            changes_made.append("Created daily_tracker table")
        else:
            print(f"✓ daily_tracker table exists")
        
        # Get existing columns
        existing_cols = get_existing_columns(engine, 'daily_tracker')
        print(f"  Existing columns: {', '.join(existing_cols)}")
        
        # Step 2: Check and add per_day_payment column
        if not check_column_exists(engine, 'daily_tracker', 'per_day_payment'):
            print(f"\n→ Adding per_day_payment column...")
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE daily_tracker ADD COLUMN per_day_payment NUMERIC(15, 2)'))
                
                # Set default values based on tracker_type
                conn.execute(text("UPDATE daily_tracker SET per_day_payment = 500 WHERE tracker_type = '50K' AND per_day_payment IS NULL"))
                conn.execute(text("UPDATE daily_tracker SET per_day_payment = 1000 WHERE tracker_type = '1L' AND per_day_payment IS NULL"))
                conn.execute(text("UPDATE daily_tracker SET per_day_payment = 3000 WHERE tracker_type = 'No Reinvest' AND per_day_payment IS NULL"))
                
                conn.commit()
            print(f"✓ per_day_payment column added with default values")
            changes_made.append("Added per_day_payment column")
        else:
            print(f"✓ per_day_payment column exists")
        
        # Step 3: Check and add is_closed_by_user column
        if not check_column_exists(engine, 'daily_tracker', 'is_closed_by_user'):
            print(f"\n→ Adding is_closed_by_user column...")
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE daily_tracker ADD COLUMN is_closed_by_user BOOLEAN DEFAULT 0'))
                conn.execute(text("UPDATE daily_tracker SET is_closed_by_user = 0 WHERE is_closed_by_user IS NULL"))
                conn.commit()
            print(f"✓ is_closed_by_user column added (all trackers set to active)")
            changes_made.append("Added is_closed_by_user column")
        else:
            print(f"✓ is_closed_by_user column exists")
        
        # Step 4: Verify all required columns exist
        required_columns = [
            'id', 'user_id', 'tracker_name', 'tracker_type', 
            'investment', 'scheme_period', 'per_day_payment', 
            'start_date', 'filename', 'created_at', 'updated_at',
            'is_active', 'is_closed_by_user'
        ]
        
        print(f"\n→ Verifying all required columns...")
        final_cols = get_existing_columns(engine, 'daily_tracker')
        missing_cols = [col for col in required_columns if col not in final_cols]
        
        if missing_cols:
            print(f"⚠️  Missing columns: {', '.join(missing_cols)}")
            print(f"   This might require manual intervention")
            return False, changes_made
        else:
            print(f"✓ All required columns present")
        
        # Get tracker count
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM daily_tracker"))
            count = result.scalar()
            print(f"\n📊 Total trackers in database: {count}")
        
        if changes_made:
            print(f"\n✅ Changes made:")
            for change in changes_made:
                print(f"   • {change}")
        else:
            print(f"\n✅ No changes needed - database is up to date")
        
        return True, changes_made
        
    except Exception as e:
        print(f"\n❌ Error migrating {instance}: {e}")
        import traceback
        traceback.print_exc()
        return False, changes_made
    finally:
        engine.dispose()

def main():
    """Main migration function"""
    print("\n" + "="*70)
    print("COMPLETE DAILY TRACKER SYSTEM MIGRATION")
    print("="*70)
    print("\n📋 This script will check and update your database schema.")
    print("   It ONLY adds missing columns - existing data is safe!")
    print("\n✓ Checks for daily_tracker table")
    print("✓ Checks for per_day_payment column")
    print("✓ Checks for is_closed_by_user column")
    print("✓ Sets appropriate default values")
    print("\nInstances to check:", ", ".join(VALID_INSTANCES))
    
    # Initialize the app
    print("\n→ Initializing application...")
    init_app()
    print("✓ Application initialized")
    
    # Migrate each instance
    results = {}
    all_changes = {}
    
    for instance in VALID_INSTANCES:
        success, changes = migrate_instance(instance)
        results[instance] = success
        all_changes[instance] = changes
    
    # Summary
    print("\n" + "="*70)
    print("MIGRATION SUMMARY")
    print("="*70)
    
    for instance in VALID_INSTANCES:
        success = results[instance]
        changes = all_changes[instance]
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"\n{instance}: {status}")
        if changes:
            for change in changes:
                print(f"  • {change}")
        else:
            print(f"  • No changes needed")
    
    all_success = all(results.values())
    
    print("\n" + "="*70)
    if all_success:
        print("✅ ALL INSTANCES READY!")
        print("="*70)
        print("\nYour database is now up to date with all tracker features:")
        print("  ✓ Daily tracker table with all columns")
        print("  ✓ Custom per day payment support")
        print("  ✓ User close/hide tracker feature")
        print("  ✓ Admin filters and summary tiles")
        print("  ✓ All existing data preserved")
        print("\n📝 Next steps:")
        print("  1. Deploy the new code to production")
        print("  2. Restart your application")
        print("  3. Test the admin tracker filters and summary tiles")
        print("  4. Verify customer tracker views work correctly")
        return 0
    else:
        print("❌ SOME INSTANCES FAILED")
        print("="*70)
        print("\nPlease check the errors above and:")
        print("  1. Ensure the database files are not locked")
        print("  2. Check file permissions")
        print("  3. Verify database connections")
        print("  4. Try running the script again")
        return 1

if __name__ == '__main__':
    sys.exit(main())

