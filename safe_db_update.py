#!/usr/bin/env python3
"""
Safe Database Update System
==========================

This module provides safe database update functions that:
1. Always create backups before changes
2. Use migrations instead of recreating databases
3. Preserve all existing data
4. Ask for user confirmation before destructive operations

Usage:
    from safe_db_update import safe_add_columns, safe_backup_database
"""

import sqlite3
import os
import shutil
from datetime import datetime
from pathlib import Path

def safe_backup_database(instance_name, backup_type="manual"):
    """Create a safe backup of the database"""
    db_path = f"instances/{instance_name}/database/lending_app_{instance_name}.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return None
    
    # Create backup directory
    backup_dir = Path(f"backups/{instance_name}/database")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{instance_name}_lending_app_backup_{backup_type}_{timestamp}.db"
    
    # Copy database
    shutil.copy2(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    return str(backup_path)

def safe_add_columns(instance_name, table_name, columns, ask_confirmation=True):
    """
    Safely add columns to a table
    
    Args:
        instance_name: The instance to update
        table_name: The table to modify
        columns: List of tuples (column_name, column_type, default_value)
        ask_confirmation: Whether to ask user before proceeding
    """
    db_path = f"instances/{instance_name}/database/lending_app_{instance_name}.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    print(f"🔄 Planning to add columns to {table_name} in {instance_name}:")
    for col_name, col_type, default_val in columns:
        print(f"   - {col_name} ({col_type})")
    
    if ask_confirmation:
        response = input("Do you want to proceed? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Operation cancelled by user")
            return False
    
    # Create backup
    backup_path = safe_backup_database(instance_name, "column_addition")
    if not backup_path:
        return False
    
    # Apply changes
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        for col_name, col_type, default_val in columns:
            # Check if column already exists
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            if col_name in existing_columns:
                print(f"⚠️  Column {col_name} already exists, skipping")
                continue
            
            # Add column
            if default_val is not None:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} DEFAULT {default_val}"
            else:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
            
            cursor.execute(sql)
            print(f"✅ Added column: {col_name}")
        
        conn.commit()
        print(f"✅ Successfully added columns to {table_name} in {instance_name}")
        return True
        
    except Exception as e:
        print(f"❌ Error adding columns: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def safe_modify_column(instance_name, table_name, column_name, new_type, ask_confirmation=True):
    """
    Safely modify a column type (SQLite limitation: can only add columns)
    For complex changes, this will create a new table and migrate data
    """
    print(f"⚠️  SQLite doesn't support modifying column types directly.")
    print(f"   To modify {column_name} in {table_name}, we would need to:")
    print(f"   1. Create a new table with the desired schema")
    print(f"   2. Copy data from old table to new table")
    print(f"   3. Drop old table and rename new table")
    print(f"   This is a complex operation that requires careful planning.")
    
    if ask_confirmation:
        response = input("Do you want to proceed with this complex migration? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Operation cancelled by user")
            return False
    
    # This would be implemented for specific use cases
    print("❌ Complex column modification not implemented yet")
    return False

def check_database_integrity(instance_name):
    """Check database integrity and report issues"""
    db_path = f"instances/{instance_name}/database/lending_app_{instance_name}.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check integrity
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        
        if result[0] == "ok":
            print(f"✅ Database integrity check passed for {instance_name}")
            return True
        else:
            print(f"❌ Database integrity issues found in {instance_name}: {result[0]}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking database integrity: {e}")
        return False
    finally:
        conn.close()

def get_database_info(instance_name):
    """Get information about the database"""
    db_path = f"instances/{instance_name}/database/lending_app_{instance_name}.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return None
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get table information
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 Database info for {instance_name}:")
        print(f"   Path: {db_path}")
        print(f"   Tables: {', '.join(tables)}")
        
        # Get row counts
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   {table}: {count} rows")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting database info: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python safe_db_update.py backup <instance>")
        print("  python safe_db_update.py info <instance>")
        print("  python safe_db_update.py check <instance>")
        return
    
    command = sys.argv[1]
    instance = sys.argv[2] if len(sys.argv) > 2 else None
    
    if command == "backup" and instance:
        safe_backup_database(instance)
    elif command == "info" and instance:
        get_database_info(instance)
    elif command == "check" and instance:
        check_database_integrity(instance)
    else:
        print("❌ Invalid command or missing instance name")
