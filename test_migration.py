#!/usr/bin/env python3
"""
Test Migration Success
=====================
Verify that the status column was added successfully
"""

import sqlite3
import os

def test_migration():
    """Test that the migration was successful"""
    
    print("🧪 TESTING MIGRATION SUCCESS")
    print("=" * 40)
    
    # Test one of the database files
    db_path = "instances/prod/database/lending_app_prod.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if status column exists
        cursor.execute("PRAGMA table_info(loan)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'status' in columns:
            print(f"✅ Status column found in {db_path}")
            
            # Check if existing loans have status set
            cursor.execute("SELECT COUNT(*) FROM loan WHERE status = 'active'")
            active_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM loan")
            total_count = cursor.fetchone()[0]
            
            print(f"   • Total loans: {total_count}")
            print(f"   • Active loans: {active_count}")
            print(f"   • Migration successful!")
            
        else:
            print(f"❌ Status column not found in {db_path}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error testing database: {str(e)}")

if __name__ == '__main__':
    test_migration()
