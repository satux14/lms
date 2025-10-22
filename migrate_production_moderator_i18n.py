#!/usr/bin/env python3
"""
Production Migration Script: Add Moderator Role and i18n Support
=================================================================
This script safely migrates the production database to support:
1. Moderator role functionality
2. Tamil language (i18n) support

IMPORTANT: This script does NOT delete any existing data.
It only adds new columns and tables.

Run this script BEFORE deploying the new code.

Usage:
    python3 migrate_production_moderator_i18n.py
"""

import sqlite3
import os
import sys
from datetime import datetime

def get_db_paths():
    """Returns a list of potential database paths."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    db_paths = []

    # Common instance paths
    for instance_name in ['prod', 'dev', 'testing']:
        path1 = os.path.join(base_dir, 'instances', instance_name, 'database', f'lending_app_{instance_name}.db')
        path2 = os.path.join(base_dir, 'instance', instance_name, 'database', f'lending_app_{instance_name}.db')
        if os.path.exists(path1):
            db_paths.append(path1)
        if os.path.exists(path2):
            db_paths.append(path2)

    # Default single instance path
    default_path = os.path.join(base_dir, 'instance', 'lending_app.db')
    if os.path.exists(default_path):
        db_paths.append(default_path)

    return list(set(db_paths))  # Return unique paths


def backup_database(db_path):
    """Create a backup of the database before migration."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✓ Backup created: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"✗ Failed to create backup: {e}")
        return None


def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def check_table_exists(cursor, table_name):
    """Check if a table exists."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None


def migrate_database(db_path):
    """
    Migrate a single database to add moderator and i18n support.
    
    Steps:
    1. Add is_moderator column to user table
    2. Add language_preference column to user table
    3. Create moderator_loans association table
    4. Create moderator_trackers association table
    """
    print(f"\n{'='*70}")
    print(f"Migrating database: {db_path}")
    print(f"{'='*70}")
    
    # Create backup
    backup_path = backup_database(db_path)
    if not backup_path:
        response = input("Warning: Backup failed. Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        changes_made = False
        
        # Step 1: Add is_moderator column to user table
        print("\n1. Checking is_moderator column in user table...")
        if not check_column_exists(cursor, 'user', 'is_moderator'):
            print("   Adding is_moderator column...")
            cursor.execute("""
                ALTER TABLE user ADD COLUMN is_moderator INTEGER DEFAULT 0
            """)
            conn.commit()
            print("   ✓ is_moderator column added")
            changes_made = True
        else:
            print("   ✓ is_moderator column already exists")
        
        # Step 2: Add language_preference column to user table
        print("\n2. Checking language_preference column in user table...")
        if not check_column_exists(cursor, 'user', 'language_preference'):
            print("   Adding language_preference column...")
            cursor.execute("""
                ALTER TABLE user ADD COLUMN language_preference VARCHAR(10)
            """)
            conn.commit()
            print("   ✓ language_preference column added")
            changes_made = True
        else:
            print("   ✓ language_preference column already exists")
        
        # Step 3: Create moderator_loans association table
        print("\n3. Checking moderator_loans association table...")
        if not check_table_exists(cursor, 'moderator_loans'):
            print("   Creating moderator_loans table...")
            cursor.execute("""
                CREATE TABLE moderator_loans (
                    moderator_id INTEGER NOT NULL,
                    loan_id INTEGER NOT NULL,
                    PRIMARY KEY (moderator_id, loan_id),
                    FOREIGN KEY (moderator_id) REFERENCES user (id) ON DELETE CASCADE,
                    FOREIGN KEY (loan_id) REFERENCES loan (id) ON DELETE CASCADE
                )
            """)
            conn.commit()
            print("   ✓ moderator_loans table created")
            changes_made = True
        else:
            print("   ✓ moderator_loans table already exists")
        
        # Step 4: Create moderator_trackers association table
        print("\n4. Checking moderator_trackers association table...")
        if not check_table_exists(cursor, 'moderator_trackers'):
            print("   Creating moderator_trackers table...")
            cursor.execute("""
                CREATE TABLE moderator_trackers (
                    moderator_id INTEGER NOT NULL,
                    tracker_id INTEGER NOT NULL,
                    PRIMARY KEY (moderator_id, tracker_id),
                    FOREIGN KEY (moderator_id) REFERENCES user (id) ON DELETE CASCADE,
                    FOREIGN KEY (tracker_id) REFERENCES daily_tracker (id) ON DELETE CASCADE
                )
            """)
            conn.commit()
            print("   ✓ moderator_trackers table created")
            changes_made = True
        else:
            print("   ✓ moderator_trackers table already exists")
        
        # Verify data integrity
        print("\n5. Verifying data integrity...")
        cursor.execute("SELECT COUNT(*) FROM user")
        user_count = cursor.fetchone()[0]
        print(f"   ✓ User count: {user_count}")
        
        cursor.execute("SELECT COUNT(*) FROM loan")
        loan_count = cursor.fetchone()[0]
        print(f"   ✓ Loan count: {loan_count}")
        
        cursor.execute("SELECT COUNT(*) FROM payment")
        payment_count = cursor.fetchone()[0]
        print(f"   ✓ Payment count: {payment_count}")
        
        cursor.execute("SELECT COUNT(*) FROM daily_tracker")
        tracker_count = cursor.fetchone()[0]
        print(f"   ✓ Tracker count: {tracker_count}")
        
        conn.close()
        
        if changes_made:
            print(f"\n{'='*70}")
            print("✓ Migration completed successfully!")
            print(f"  Backup saved at: {backup_path}")
            print(f"{'='*70}")
        else:
            print(f"\n{'='*70}")
            print("✓ Database already up to date. No changes needed.")
            print(f"{'='*70}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        print(f"  You can restore from backup: {backup_path}")
        return False


def main():
    """Main migration function."""
    print("="*70)
    print("Production Migration: Moderator Role + i18n Support")
    print("="*70)
    print("\nThis script will:")
    print("  1. Add is_moderator column to user table")
    print("  2. Add language_preference column to user table")
    print("  3. Create moderator_loans association table")
    print("  4. Create moderator_trackers association table")
    print("\nIMPORTANT: No existing data will be deleted.")
    print("           A backup will be created before any changes.")
    
    # Get database paths
    db_paths = get_db_paths()
    
    if not db_paths:
        print("\n✗ No database files found!")
        print("  Expected locations:")
        print("    - instances/prod/database/lending_app_prod.db")
        print("    - instance/prod/database/lending_app_prod.db")
        print("    - instance/lending_app.db")
        sys.exit(1)
    
    print(f"\nFound {len(db_paths)} database(s):")
    for i, path in enumerate(db_paths, 1):
        print(f"  {i}. {path}")
    
    # Confirm migration
    print("\n" + "="*70)
    response = input("Proceed with migration? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        sys.exit(0)
    
    # Migrate each database
    success_count = 0
    for db_path in db_paths:
        if migrate_database(db_path):
            success_count += 1
    
    # Final summary
    print("\n" + "="*70)
    print("MIGRATION SUMMARY")
    print("="*70)
    print(f"Total databases: {len(db_paths)}")
    print(f"Successfully migrated: {success_count}")
    print(f"Failed: {len(db_paths) - success_count}")
    
    if success_count == len(db_paths):
        print("\n✓ All databases migrated successfully!")
        print("\nNext steps:")
        print("  1. Deploy the new application code")
        print("  2. Restart the application")
        print("  3. Test the moderator and language features")
        print("  4. If everything works, you can delete the backup files")
    else:
        print("\n⚠ Some migrations failed. Please check the errors above.")
        print("   Restore from backups if needed.")
    
    print("="*70)


if __name__ == '__main__':
    main()

