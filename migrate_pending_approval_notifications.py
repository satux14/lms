#!/usr/bin/env python3
"""
Migration script to add pending_approval_notification table

This script adds the pending_approval_notification table to queue approval notifications
for collation and delayed sending.

Usage:
    python migrate_pending_approval_notifications.py [--dry-run]
    
Options:
    --dry-run    Show what would be done without making changes
"""

import sqlite3
import sys
from pathlib import Path

# Define valid instances
VALID_INSTANCES = ['prod', 'dev', 'testing']

def get_database_path(instance):
    """Get the database path for an instance"""
    base_path = Path(__file__).parent / 'instances' / instance / 'database'
    return base_path / f'lending_app_{instance}.db'

def check_table_exists(cursor, table_name):
    """Check if a table exists in the database"""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

def migrate_instance(instance, dry_run=False):
    """Run migration for a single instance"""
    db_path = get_database_path(instance)
    
    if not db_path.exists():
        print(f"⚠️  Database not found: {db_path}")
        return False
    
    print(f"\n{'='*60}")
    if dry_run:
        print(f"Migrating instance: {instance} [DRY RUN MODE - No changes will be made]")
    else:
        print(f"Migrating instance: {instance}")
    print(f"{'='*60}")
    print(f"Database URI: sqlite:///{db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if table already exists
        if check_table_exists(cursor, 'pending_approval_notification'):
            print("✓ pending_approval_notification table already exists")
            conn.close()
            return True
        
        print("→ Creating pending_approval_notification table...")
        
        if not dry_run:
            # Create pending_approval_notification table
            cursor.execute("""
                CREATE TABLE pending_approval_notification (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_name VARCHAR(20) NOT NULL,
                    recipient_id INTEGER NOT NULL,
                    approval_type VARCHAR(20) NOT NULL,
                    item_id INTEGER NOT NULL,
                    item_details TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    sent_at TIMESTAMP,
                    is_sent BOOLEAN NOT NULL DEFAULT 0,
                    FOREIGN KEY (recipient_id) REFERENCES user(id)
                )
            """)
            
            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX idx_pending_approval_instance_sent 
                ON pending_approval_notification(instance_name, is_sent, created_at)
            """)
            
            cursor.execute("""
                CREATE INDEX idx_pending_approval_recipient 
                ON pending_approval_notification(recipient_id)
            """)
            
            conn.commit()
            print("✓ Successfully created pending_approval_notification table")
            print("✓ Created indexes")
        else:
            print("  [DRY RUN] Would create pending_approval_notification table")
            print("  [DRY RUN] Would create indexes")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error migrating {instance}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main migration function"""
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN MODE - No changes will be made")
        print("="*60 + "\n")
    
    success_count = 0
    total_count = len(VALID_INSTANCES)
    
    for instance in VALID_INSTANCES:
        if migrate_instance(instance, dry_run):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"Migration Summary: {success_count}/{total_count} instances processed")
    print(f"{'='*60}\n")
    
    if not dry_run and success_count == total_count:
        print("✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Restart your Flask application to activate the new notification system")
        print("2. Configure approval_email_delay_minutes in NotificationPreference preferences")
        print("   (Default is 5 minutes if not configured)")
    elif dry_run:
        print("✅ Dry run completed. Run without --dry-run to apply changes.")

if __name__ == '__main__':
    main()

