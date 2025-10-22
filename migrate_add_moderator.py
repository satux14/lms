#!/usr/bin/env python3
"""
Database Migration Script: Add is_moderator column to User table
============================================================

This script adds the 'is_moderator' column to the User table in existing databases.

Usage:
    python migrate_add_moderator.py

The script will:
1. Backup the database before migration
2. Add is_moderator column to User table (default False)
3. Verify the migration was successful

Author: Lending Management System
Date: 2025
"""

import sqlite3
import shutil
import os
from datetime import datetime
from pathlib import Path

# Instance configuration
VALID_INSTANCES = ['prod', 'dev', 'testing']

def backup_database(db_path):
    """Create a backup of the database before migration"""
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = db_path.replace('.db', f'_backup_before_moderator_{timestamp}.db')
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✓ Backup created: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"✗ Error creating backup: {e}")
        return None

def migrate_database(db_path):
    """Add is_moderator column to User table"""
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_moderator' in columns:
            print(f"✓ Column 'is_moderator' already exists in {db_path}")
            conn.close()
            return True
        
        # Add the new column
        cursor.execute("ALTER TABLE user ADD COLUMN is_moderator BOOLEAN DEFAULT 0")
        conn.commit()
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_moderator' in columns:
            print(f"✓ Successfully added 'is_moderator' column to {db_path}")
            
            # Count users
            cursor.execute("SELECT COUNT(*) FROM user")
            user_count = cursor.fetchone()[0]
            print(f"  Total users: {user_count}")
            print(f"  All users set to is_moderator=False by default")
            
            conn.close()
            return True
        else:
            print(f"✗ Failed to add column to {db_path}")
            conn.close()
            return False
            
    except Exception as e:
        print(f"✗ Error migrating {db_path}: {e}")
        return False

def main():
    """Main migration function"""
    print("=" * 70)
    print("Database Migration: Add is_moderator Column to User Table")
    print("=" * 70)
    print()
    
    # Find all database files
    db_files = []
    
    # Check instances directory (new structure)
    instances_dir = Path('instances')
    if instances_dir.exists():
        for instance in VALID_INSTANCES:
            instance_dir = instances_dir / instance / 'database'
            db_path = instance_dir / f'lending_app_{instance}.db'
            if db_path.exists():
                db_files.append(str(db_path))
    
    # Check instance directory (old structure)
    instance_dir = Path('instance')
    if instance_dir.exists():
        for instance in VALID_INSTANCES:
            inst_dir = instance_dir / instance / 'database'
            db_path = inst_dir / f'lending_app_{instance}.db'
            if db_path.exists() and str(db_path) not in db_files:
                db_files.append(str(db_path))
        
        # Check root instance directory
        root_db = instance_dir / 'lending_app.db'
        if root_db.exists() and str(root_db) not in db_files:
            db_files.append(str(root_db))
    
    if not db_files:
        print("No database files found.")
        print("Please ensure you run this script from the lending_app directory.")
        return
    
    print(f"Found {len(db_files)} database(s) to migrate:")
    for db_file in db_files:
        print(f"  - {db_file}")
    print()
    
    # Confirm migration
    response = input("Do you want to proceed with the migration? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled.")
        return
    
    print()
    print("Starting migration...")
    print("-" * 70)
    
    # Migrate each database
    success_count = 0
    for db_file in db_files:
        print(f"\nMigrating: {db_file}")
        print("-" * 70)
        
        # Create backup
        backup = backup_database(db_file)
        if not backup:
            print(f"Skipping {db_file} due to backup failure")
            continue
        
        # Perform migration
        if migrate_database(db_file):
            success_count += 1
        else:
            print(f"✗ Migration failed for {db_file}")
            print(f"  Backup available at: {backup}")
    
    print()
    print("=" * 70)
    print(f"Migration Summary: {success_count}/{len(db_files)} successful")
    print("=" * 70)
    
    if success_count == len(db_files):
        print("✓ All databases migrated successfully!")
        print()
        print("Next steps:")
        print("1. Restart your application")
        print("2. Login as admin")
        print("3. Go to User Management")
        print("4. Use the toggle button to make users moderators")
    else:
        print("⚠ Some migrations failed. Please check the errors above.")
        print("Backups have been created for your databases.")

if __name__ == '__main__':
    main()

