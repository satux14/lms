#!/usr/bin/env python3
"""
Database Migration: Add loan.status column
=========================================
Safely adds the status column to existing loan tables without data loss
"""

import os
import sqlite3
import shutil
from datetime import datetime

def backup_database(db_path):
    """Create a backup of the database before migration"""
    if not os.path.exists(db_path):
        return None
    
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"✅ Database backed up to: {backup_path}")
    return backup_path

def migrate_database(db_path):
    """Add status column to loan table"""
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    try:
        # Create backup
        backup_path = backup_database(db_path)
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if status column already exists
        cursor.execute("PRAGMA table_info(loan)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'status' in columns:
            print(f"✅ Status column already exists in {db_path}")
            conn.close()
            return True
        
        # Add status column with default value 'active'
        print(f"🔄 Adding status column to {db_path}...")
        cursor.execute("ALTER TABLE loan ADD COLUMN status VARCHAR(20) DEFAULT 'active'")
        
        # Update existing loans to have 'active' status
        cursor.execute("UPDATE loan SET status = 'active' WHERE status IS NULL")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print(f"✅ Successfully added status column to {db_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error migrating {db_path}: {str(e)}")
        if 'backup_path' in locals() and os.path.exists(backup_path):
            print(f"🔄 Restoring from backup: {backup_path}")
            shutil.copy2(backup_path, db_path)
        return False

def main():
    """Run migration on all database files"""
    print("🔄 Starting Database Migration: Add loan.status column")
    print("=" * 60)
    
    # Find all database files
    db_files = []
    
    # Main database
    if os.path.exists('lending_app.db'):
        db_files.append('lending_app.db')
    
    # Instance databases
    for instance in ['prod', 'dev', 'testing']:
        # Check both possible locations with actual file names
        for base_path in ['instances', 'instance']:
            db_path = f"{base_path}/{instance}/database/lending_app_{instance}.db"
            if os.path.exists(db_path):
                db_files.append(db_path)
    
    if not db_files:
        print("❌ No database files found to migrate")
        return
    
    print(f"📋 Found {len(db_files)} database files to migrate:")
    for db_file in db_files:
        print(f"   • {db_file}")
    print()
    
    # Migrate each database
    success_count = 0
    for db_file in db_files:
        print(f"🔄 Migrating {db_file}...")
        if migrate_database(db_file):
            success_count += 1
        print()
    
    print("📊 Migration Summary:")
    print(f"   • Total databases: {len(db_files)}")
    print(f"   • Successful: {success_count}")
    print(f"   • Failed: {len(db_files) - success_count}")
    
    if success_count == len(db_files):
        print("🎉 All databases migrated successfully!")
    else:
        print("⚠️  Some migrations failed. Check the logs above.")

if __name__ == '__main__':
    main()
