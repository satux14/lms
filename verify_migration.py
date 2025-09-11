#!/usr/bin/env python3
"""
Verify Migration Success
=======================
Quick verification that the migration was successful
"""

import os
import sqlite3

def verify_migration():
    """Verify that the migration was successful"""
    
    print("🔍 VERIFYING MIGRATION SUCCESS")
    print("=" * 50)
    
    # Find all database files
    db_files = []
    
    # Instance databases
    for instance in ['prod', 'dev', 'testing']:
        for base_path in ['instances', 'instance']:
            db_path = f"{base_path}/{instance}/database/lending_app_{instance}.db"
            if os.path.exists(db_path):
                db_files.append(db_path)
    
    if not db_files:
        print("❌ No database files found")
        return False
    
    all_good = True
    
    for db_file in db_files:
        print(f"\n📊 Checking {db_file}...")
        
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Check if status column exists
            cursor.execute("PRAGMA table_info(loan)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'status' not in columns:
                print(f"❌ Status column missing")
                all_good = False
                continue
            
            # Check loan counts
            cursor.execute("SELECT COUNT(*) FROM loan")
            total_loans = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM loan WHERE status = 'active'")
            active_loans = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM loan WHERE status IS NULL")
            null_status = cursor.fetchone()[0]
            
            print(f"   • Total loans: {total_loans}")
            print(f"   • Active loans: {active_loans}")
            print(f"   • Null status: {null_status}")
            
            if null_status > 0:
                print(f"⚠️  Warning: {null_status} loans have NULL status")
                all_good = False
            else:
                print(f"✅ All loans have proper status")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error checking {db_file}: {str(e)}")
            all_good = False
    
    print(f"\n📋 SUMMARY:")
    if all_good:
        print("🎉 Migration verification PASSED!")
        print("   • All databases have status column")
        print("   • All loans have proper status")
        print("   • Ready for production use")
    else:
        print("❌ Migration verification FAILED!")
        print("   • Check the errors above")
        print("   • Consider running migration again")
    
    return all_good

if __name__ == '__main__':
    verify_migration()
