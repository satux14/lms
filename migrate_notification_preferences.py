#!/usr/bin/env python3
"""
Migration script to add notification_preference table

This script adds the notification_preference table to store user notification preferences
for email, SMS, Slack, and other notification channels.

Usage:
    python migrate_notification_preferences.py [--dry-run]
    
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
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None

def migrate_instance(instance, dry_run=False):
    """Run migration for a single instance"""
    print(f"\n{'='*60}")
    print(f"Migrating instance: {instance}")
    if dry_run:
        print("[DRY RUN MODE - No changes will be made]")
    print(f"{'='*60}")
    
    db_path = get_database_path(instance)
    
    if not db_path.exists():
        print(f"⚠ Database not found: {db_path}")
        print(f"  Skipping {instance} instance")
        return False
    
    print(f"Database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if notification_preference table exists
        if check_table_exists(cursor, 'notification_preference'):
            print("✓ notification_preference table already exists")
            conn.close()
            return True
        
        print("→ Creating notification_preference table...")
        
        if not dry_run:
            # Create notification_preference table
            cursor.execute("""
                CREATE TABLE notification_preference (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    channel VARCHAR(20) NOT NULL DEFAULT 'email',
                    enabled BOOLEAN NOT NULL DEFAULT 1,
                    preferences TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user(id)
                )
            """)
            
            # Create index on user_id for faster lookups
            cursor.execute("""
                CREATE INDEX idx_notification_preference_user_id 
                ON notification_preference(user_id)
            """)
            
            # Create index on channel for faster filtering
            cursor.execute("""
                CREATE INDEX idx_notification_preference_channel 
                ON notification_preference(channel)
            """)
            
            conn.commit()
            print("✓ Successfully created notification_preference table")
            print("✓ Created indexes")
            
            # Initialize default preferences for existing admins
            print("→ Creating default notification preferences for admins...")
            cursor.execute("""
                INSERT INTO notification_preference (user_id, channel, enabled, preferences)
                SELECT 
                    id, 
                    'email', 
                    1,
                    '{"payment_approvals": true, "tracker_approvals": true, "payment_status": false, "tracker_status": false}'
                FROM user 
                WHERE is_admin = 1
            """)
            admin_count = cursor.rowcount
            conn.commit()
            print(f"✓ Created notification preferences for {admin_count} admin user(s)")
        else:
            print("  [DRY RUN] Would create notification_preference table")
            print("  [DRY RUN] Would create indexes")
            print("  [DRY RUN] Would initialize preferences for admin users")
        
        conn.close()
        print(f"✓ Migration completed for {instance}")
        return True
        
    except sqlite3.Error as e:
        print(f"✗ Error migrating {instance}: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def main():
    """Main migration function"""
    dry_run = '--dry-run' in sys.argv
    
    print("\n" + "="*60)
    print("Notification Preference Migration Script")
    print("="*60)
    
    if dry_run:
        print("\n⚠ DRY RUN MODE - No changes will be made")
    
    success_count = 0
    for instance in VALID_INSTANCES:
        if migrate_instance(instance, dry_run):
            success_count += 1
    
    print("\n" + "="*60)
    print(f"Migration Summary: {success_count}/{len(VALID_INSTANCES)} instances completed")
    print("="*60)
    
    if dry_run:
        print("\nTo apply changes, run without --dry-run flag:")
        print("  python migrate_notification_preferences.py")
    else:
        print("\n✓ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Restart your Flask application")
        print("2. Users can configure notification preferences in Settings")
        print("3. Configure SMTP settings in .env file or environment variables")

if __name__ == '__main__':
    main()

