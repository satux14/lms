#!/usr/bin/env python3
"""
Migration Script: Add language_preference column to User table
===============================================================

This script adds support for storing user language preferences in the database.

Usage:
    python3 migrate_add_language_preference.py

The script will:
1. Create a backup of the database
2. Add 'language_preference' column to the user table
3. Set default value to 'en' (English) for existing users
"""

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

def backup_database(db_path):
    """Create a backup of the database"""
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"✓ Database backed up to: {backup_path}")
    return backup_path

def add_language_preference_column(db_path):
    """Add language_preference column to user table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'language_preference' in columns:
            print("✓ Column 'language_preference' already exists")
            return True
        
        # Add the column
        print("Adding 'language_preference' column...")
        cursor.execute("""
            ALTER TABLE user 
            ADD COLUMN language_preference VARCHAR(5) DEFAULT 'en'
        """)
        
        # Set default value for existing users
        cursor.execute("""
            UPDATE user 
            SET language_preference = 'en' 
            WHERE language_preference IS NULL
        """)
        
        conn.commit()
        print("✓ Column 'language_preference' added successfully")
        print("✓ All existing users set to English (en) by default")
        return True
        
    except sqlite3.Error as e:
        print(f"✗ Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verify_migration(db_path):
    """Verify the migration was successful"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(user)")
        columns = {column[1]: column[2] for column in cursor.fetchall()}
        
        if 'language_preference' in columns:
            cursor.execute("SELECT COUNT(*) FROM user WHERE language_preference IS NOT NULL")
            count = cursor.fetchone()[0]
            print(f"\n✓ Verification successful:")
            print(f"  - Column exists: language_preference ({columns['language_preference']})")
            print(f"  - Users with language preference: {count}")
            return True
        else:
            print("\n✗ Verification failed: Column not found")
            return False
            
    finally:
        conn.close()

def main():
    """Main migration function"""
    print("=" * 60)
    print("Language Preference Migration")
    print("=" * 60)
    print()
    
    # Find all database files
    db_files = []
    
    # Check standard locations
    locations = [
        Path("instances/prod/database/lending_app_prod.db"),
        Path("instances/dev/database/lending_app_dev.db"),
        Path("instances/testing/database/lending_app_testing.db"),
        Path("instance/prod/database/lending_app_prod.db"),
        Path("instance/dev/database/lending_app_dev.db"),
        Path("instance/testing/database/lending_app_testing.db"),
        Path("instance/lending_app.db"),
        Path("lending_app.db")
    ]
    
    for db_path in locations:
        if db_path.exists():
            db_files.append(db_path)
    
    if not db_files:
        print("✗ No database files found!")
        print("\nSearched in:")
        for loc in locations:
            print(f"  - {loc}")
        return
    
    print(f"Found {len(db_files)} database file(s):\n")
    for db_file in db_files:
        print(f"  - {db_file}")
    print()
    
    # Confirm migration
    response = input("Proceed with migration? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("\nMigration cancelled")
        return
    
    print()
    
    # Process each database
    success_count = 0
    for db_path in db_files:
        print(f"\nProcessing: {db_path}")
        print("-" * 60)
        
        # Backup
        backup_path = backup_database(str(db_path))
        
        # Migrate
        if add_language_preference_column(str(db_path)):
            # Verify
            if verify_migration(str(db_path)):
                success_count += 1
    
    print("\n" + "=" * 60)
    print(f"Migration completed: {success_count}/{len(db_files)} successful")
    print("=" * 60)

if __name__ == '__main__':
    main()

