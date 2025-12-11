#!/usr/bin/env python3
"""
Migration script to add report preference and history tables

This script adds two new tables:
- report_preference: Stores user preferences for daily reports
- report_history: Tracks sent reports and their status

Usage:
    python3 migrate_report_preferences.py [--dry-run]
    
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
        
        # Check if report_preference table exists
        if check_table_exists(cursor, 'report_preference'):
            print("✓ report_preference table already exists")
        else:
            print("→ Creating report_preference table...")
            
            if not dry_run:
                # Create report_preference table
                cursor.execute("""
                    CREATE TABLE report_preference (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL UNIQUE,
                        enabled BOOLEAN NOT NULL DEFAULT 1,
                        morning_time VARCHAR(5) DEFAULT '08:00',
                        evening_time VARCHAR(5) DEFAULT '20:00',
                        timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
                        include_trends BOOLEAN DEFAULT 1,
                        include_user_activity BOOLEAN DEFAULT 1,
                        include_alerts BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user(id)
                    )
                """)
                
                # Create index on user_id
                cursor.execute("""
                    CREATE INDEX idx_report_preference_user_id 
                    ON report_preference(user_id)
                """)
                
                conn.commit()
                print("✓ Successfully created report_preference table")
                print("✓ Created indexes")
                
                # Initialize default preferences for admin users
                print("→ Creating default report preferences for admins...")
                cursor.execute("""
                    INSERT INTO report_preference (user_id, enabled, morning_time, evening_time)
                    SELECT id, 1, '08:00', '20:00'
                    FROM user 
                    WHERE is_admin = 1
                """)
                admin_count = cursor.rowcount
                conn.commit()
                print(f"✓ Created report preferences for {admin_count} admin user(s)")
            else:
                print("  [DRY RUN] Would create report_preference table")
                print("  [DRY RUN] Would create indexes")
                print("  [DRY RUN] Would initialize preferences for admin users")
        
        # Check if report_history table exists
        if check_table_exists(cursor, 'report_history'):
            print("✓ report_history table already exists")
        else:
            print("→ Creating report_history table...")
            
            if not dry_run:
                # Create report_history table
                cursor.execute("""
                    CREATE TABLE report_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        report_type VARCHAR(20) NOT NULL,
                        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        sent_successfully BOOLEAN DEFAULT 0,
                        error_message TEXT,
                        report_data TEXT,
                        FOREIGN KEY (user_id) REFERENCES user(id)
                    )
                """)
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX idx_report_history_user_id 
                    ON report_history(user_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX idx_report_history_generated_at 
                    ON report_history(generated_at)
                """)
                
                conn.commit()
                print("✓ Successfully created report_history table")
                print("✓ Created indexes")
            else:
                print("  [DRY RUN] Would create report_history table")
                print("  [DRY RUN] Would create indexes")
        
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
    print("Report Preference Migration Script")
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
        print("  python3 migrate_report_preferences.py")
    else:
        print("\n✓ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Restart your Flask application")
        print("2. Admins can configure daily reports in Settings → Reports tab")
        print("3. Set up cron jobs for scheduled report delivery (see documentation)")

if __name__ == '__main__':
    main()

