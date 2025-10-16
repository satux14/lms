"""
Production Database Status Checker
===================================

Run this FIRST to see what migrations are needed WITHOUT making any changes.
This is a read-only script - it won't modify your database.

Usage:
    python3 verify_production_status.py
"""

import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app_multi import app, init_app, VALID_INSTANCES, get_database_uri
from sqlalchemy import create_engine, inspect, text

def check_table_exists(engine, table_name):
    """Check if a table exists"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def get_table_columns(engine, table_name):
    """Get all columns in a table"""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return []
    return inspector.get_columns(table_name)

def check_instance_status(instance):
    """Check the status of an instance database"""
    print(f"\n{'='*70}")
    print(f"Instance: {instance}")
    print(f"{'='*70}")
    
    db_uri = get_database_uri(instance)
    print(f"Database: {db_uri}")
    
    engine = create_engine(db_uri)
    needs_migration = False
    
    try:
        # Check if daily_tracker table exists
        if not check_table_exists(engine, 'daily_tracker'):
            print(f"\n❌ daily_tracker table: NOT FOUND")
            print(f"   → Migration needed: Will create table with all columns")
            needs_migration = True
            return needs_migration
        
        print(f"\n✅ daily_tracker table: EXISTS")
        
        # Get all columns
        columns = get_table_columns(engine, 'daily_tracker')
        column_names = [col['name'] for col in columns]
        
        print(f"\n📋 Current columns ({len(column_names)}):")
        for col in columns:
            col_type = str(col['type'])
            nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
            default = f" DEFAULT {col.get('default', '')}" if col.get('default') else ""
            print(f"   • {col['name']}: {col_type} {nullable}{default}")
        
        # Check required columns
        required_columns = {
            'id': 'Primary key',
            'user_id': 'Foreign key to user',
            'tracker_name': 'Name of tracker',
            'tracker_type': 'Tracker type (50K/1L/No Reinvest)',
            'investment': 'Investment amount',
            'scheme_period': 'Scheme period in days',
            'per_day_payment': '⭐ Daily payment amount',
            'start_date': 'Start date',
            'filename': 'Excel filename',
            'created_at': 'Creation timestamp',
            'updated_at': 'Update timestamp',
            'is_active': 'Soft delete flag',
            'is_closed_by_user': '⭐ User close/hide flag'
        }
        
        print(f"\n🔍 Column Status Check:")
        missing = []
        for col, description in required_columns.items():
            if col in column_names:
                print(f"   ✅ {col}: {description}")
            else:
                print(f"   ❌ {col}: {description} - MISSING!")
                missing.append(col)
                needs_migration = True
        
        # Get tracker count and sample data
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM daily_tracker"))
            count = result.scalar()
            print(f"\n📊 Current tracker count: {count}")
            
            if count > 0:
                # Get sample tracker info
                result = conn.execute(text("""
                    SELECT tracker_name, tracker_type, user_id 
                    FROM daily_tracker 
                    LIMIT 3
                """))
                print(f"\n📝 Sample trackers:")
                for row in result:
                    print(f"   • {row[0]} ({row[1]}) - User ID: {row[2]}")
        
        if missing:
            print(f"\n⚠️  MIGRATION NEEDED for {instance}")
            print(f"   Missing columns: {', '.join(missing)}")
            print(f"\n   What will happen during migration:")
            for col in missing:
                if col == 'per_day_payment':
                    print(f"   • Add {col} column")
                    print(f"     - 50K trackers will get default: 500")
                    print(f"     - 1L trackers will get default: 1000")
                    print(f"     - No Reinvest trackers will get default: 3000")
                elif col == 'is_closed_by_user':
                    print(f"   • Add {col} column")
                    print(f"     - All existing trackers will be set to: False (active)")
                else:
                    print(f"   • Add {col} column with appropriate defaults")
        else:
            print(f"\n✅ NO MIGRATION NEEDED for {instance}")
            print(f"   All required columns are present!")
        
        return needs_migration
        
    except Exception as e:
        print(f"\n❌ Error checking {instance}: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        engine.dispose()

def main():
    """Main verification function"""
    print("\n" + "="*70)
    print("PRODUCTION DATABASE STATUS CHECK")
    print("="*70)
    print("\n📋 This script checks your database WITHOUT making changes.")
    print("   Use this to see what migrations are needed.")
    print("\nInstances to check:", ", ".join(VALID_INSTANCES))
    
    # Initialize the app
    print("\n→ Initializing application...")
    init_app()
    print("✓ Application initialized")
    
    # Check each instance
    results = {}
    for instance in VALID_INSTANCES:
        results[instance] = check_instance_status(instance)
    
    # Final Summary
    print("\n" + "="*70)
    print("OVERALL SUMMARY")
    print("="*70)
    
    needs_migration = []
    up_to_date = []
    errors = []
    
    for instance, status in results.items():
        if status is None:
            errors.append(instance)
        elif status:
            needs_migration.append(instance)
        else:
            up_to_date.append(instance)
    
    if up_to_date:
        print(f"\n✅ Up to date ({len(up_to_date)}):")
        for inst in up_to_date:
            print(f"   • {inst}")
    
    if needs_migration:
        print(f"\n⚠️  Needs migration ({len(needs_migration)}):")
        for inst in needs_migration:
            print(f"   • {inst}")
    
    if errors:
        print(f"\n❌ Errors ({len(errors)}):")
        for inst in errors:
            print(f"   • {inst}")
    
    print("\n" + "="*70)
    if needs_migration:
        print("📝 NEXT STEPS:")
        print("="*70)
        print("\n1. Review the changes above carefully")
        print("2. Backup your database (RECOMMENDED!):")
        print("   python3 backup_before_migration.py")
        print("\n3. Run the migration:")
        print("   python3 migrate_complete_tracker_system.py")
        print("\n4. Deploy new code and restart application")
    elif errors:
        print("❌ ERRORS DETECTED")
        print("="*70)
        print("\nPlease fix the errors above before proceeding.")
    else:
        print("✅ ALL INSTANCES UP TO DATE!")
        print("="*70)
        print("\nYour database already has all required columns.")
        print("You can deploy the new code directly!")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

