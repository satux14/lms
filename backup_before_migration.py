"""
Pre-Migration Backup Script
============================

This script creates a backup of all databases before running the migration.
Run this FIRST before migrate_daily_tracker.py

Usage:
    python3 backup_before_migration.py
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

VALID_INSTANCES = ['prod', 'dev', 'testing']

def backup_database(instance):
    """Backup database for an instance"""
    # Source database path
    db_path = Path("instance") / instance / "database" / f"lending_app_{instance}.db"
    
    if not db_path.exists():
        print(f"⚠️  Database not found for {instance}: {db_path}")
        return False
    
    # Create backup directory
    backup_dir = Path("instance") / instance / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"lending_app_{instance}_pre_daily_tracker_migration_{timestamp}.db"
    backup_path = backup_dir / backup_filename
    
    # Copy database
    print(f"→ Backing up {instance} database...")
    shutil.copy2(str(db_path), str(backup_path))
    
    # Verify backup
    if backup_path.exists():
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        print(f"✓ Backup created: {backup_path}")
        print(f"  Size: {size_mb:.2f} MB")
        return True
    else:
        print(f"✗ Failed to create backup for {instance}")
        return False

def main():
    """Main backup function"""
    print("\n" + "="*70)
    print("PRE-MIGRATION DATABASE BACKUP")
    print("="*70)
    print("\nThis script will backup all databases before the migration.")
    print("Instances to backup:", ", ".join(VALID_INSTANCES))
    
    results = {}
    for instance in VALID_INSTANCES:
        print(f"\n{'='*70}")
        print(f"Instance: {instance}")
        print(f"{'='*70}")
        results[instance] = backup_database(instance)
    
    # Summary
    print("\n" + "="*70)
    print("BACKUP SUMMARY")
    print("="*70)
    
    for instance, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED/NOT FOUND"
        print(f"{instance}: {status}")
    
    all_success = all(results.values())
    
    if all_success:
        print("\n✓ All databases backed up successfully!")
        print("\nBackup locations:")
        for instance in VALID_INSTANCES:
            backup_dir = Path("instance") / instance / "backups"
            print(f"  {instance}: {backup_dir.absolute()}/")
        print("\n" + "="*70)
        print("You can now safely run: python3 migrate_daily_tracker.py")
        print("="*70)
        return 0
    else:
        print("\n⚠️  Some backups failed or databases not found")
        print("This might be normal if you don't use all instances")
        print("\nYou can still proceed with migration if your production instance was backed up")
        return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())

