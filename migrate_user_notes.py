#!/usr/bin/env python3
"""
Migration Script: Add user_notes field to cashback_transaction table

This script adds a new 'user_notes' column to the cashback_transaction table
to store user-visible notes/reasons for cashback transactions.

Usage:
    python3 migrate_user_notes.py [--dry-run] [instance1] [instance2] ...

If no instances are specified, all valid instances will be migrated.
"""

import sqlite3
import os
import sys
from pathlib import Path

# Valid instances
VALID_INSTANCES = ['prod', 'dev', 'testing']

def get_database_path(instance_name):
    """Get the database path for an instance"""
    script_dir = Path(__file__).parent
    db_path = script_dir / 'instances' / instance_name / 'database' / f'lending_app_{instance_name}.db'
    return db_path

def migrate_instance(instance_name, dry_run=False):
    """Migrate a single instance"""
    db_path = get_database_path(instance_name)
    
    if not db_path.exists():
        print(f"⚠️  Database not found: {db_path}")
        return False
    
    print(f"\n{'='*60}")
    if dry_run:
        print(f"Migrating instance: {instance_name} [DRY RUN MODE - No changes will be made]")
    else:
        print(f"Migrating instance: {instance_name}")
    print(f"{'='*60}")
    print(f"Database URI: sqlite:///{db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(cashback_transaction)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'user_notes' in columns:
            print("✓ user_notes column already exists")
            conn.close()
            return True
        
        if dry_run:
            print("✓ Would add user_notes column to cashback_transaction table")
            conn.close()
            return True
        
        # Add the column
        cursor.execute("""
            ALTER TABLE cashback_transaction 
            ADD COLUMN user_notes TEXT
        """)
        
        conn.commit()
        conn.close()
        
        print("✓ Successfully added user_notes column to cashback_transaction table")
        return True
        
    except Exception as e:
        print(f"✗ Error migrating {instance_name}: {str(e)}")
        return False

def main():
    """Main migration function"""
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        sys.argv.remove('--dry-run')
    
    # Get instances to migrate
    if len(sys.argv) > 1:
        instances = [inst for inst in sys.argv[1:] if inst in VALID_INSTANCES]
    else:
        instances = VALID_INSTANCES
    
    if not instances:
        print("No valid instances specified")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    if dry_run:
        print("CASHBACK USER NOTES MIGRATION - DRY RUN MODE")
    else:
        print("CASHBACK USER NOTES MIGRATION")
    print(f"{'='*60}")
    
    success_count = 0
    for instance in instances:
        if migrate_instance(instance, dry_run=dry_run):
            success_count += 1
    
    print(f"\n{'='*60}")
    if dry_run:
        print(f"[DRY RUN SUMMARY]")
        print(f"Instances that would be migrated: {success_count}/{len(instances)}")
    else:
        print(f"Migration Summary:")
        print(f"Successfully migrated: {success_count}/{len(instances)}")
    print(f"{'='*60}\n")
    
    if success_count == len(instances):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()

