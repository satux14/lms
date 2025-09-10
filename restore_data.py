#!/usr/bin/env python3
"""
Data Restoration Script
======================

This script restores data from backup databases and adds the new password reset fields.
"""

import sqlite3
import shutil
import os
from pathlib import Path

def restore_data():
    """Restore data from backup and add new schema fields"""
    
    # Source backup database
    backup_db = "backups/dev/database/dev_lending_app_backup_20250909_143843.db"
    
    # Target databases for each instance
    instances = ['prod', 'dev', 'testing']
    
    for instance in instances:
        print(f"Restoring data for {instance} instance...")
        
        # Create instance directory if it doesn't exist
        instance_dir = Path(f"instances/{instance}/database")
        instance_dir.mkdir(parents=True, exist_ok=True)
        
        # Target database path
        target_db = f"instances/{instance}/database/lending_app_{instance}.db"
        
        # Copy backup to target
        shutil.copy2(backup_db, target_db)
        
        # Add new columns for password reset functionality
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        
        try:
            # Add reset_token column if it doesn't exist
            cursor.execute("ALTER TABLE user ADD COLUMN reset_token VARCHAR(100)")
            print(f"  ✓ Added reset_token column to {instance}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"  ✓ reset_token column already exists in {instance}")
            else:
                print(f"  ⚠ Error adding reset_token to {instance}: {e}")
        
        try:
            # Add reset_token_expires column if it doesn't exist
            cursor.execute("ALTER TABLE user ADD COLUMN reset_token_expires DATETIME")
            print(f"  ✓ Added reset_token_expires column to {instance}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"  ✓ reset_token_expires column already exists in {instance}")
            else:
                print(f"  ⚠ Error adding reset_token_expires to {instance}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"  ✅ {instance} instance restored successfully")
    
    print("\n🎉 Data restoration completed!")
    print("Your users, loans, and payments have been restored.")
    print("The new password management features are now available.")

if __name__ == "__main__":
    restore_data()