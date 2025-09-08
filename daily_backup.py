#!/usr/bin/env python3
"""
Daily Backup Scheduler for Lending Management System
==================================================

This script is designed to be run as a cron job for automated daily backups.
It creates a full backup and cleans up old files automatically.

Usage:
    python3 daily_backup.py

Cron Setup:
    # Run daily at 2:00 AM
    0 2 * * * cd /path/to/lending_app && python3 daily_backup.py >> backup.log 2>&1

    # Run daily at 2:00 AM with cleanup of files older than 30 days
    0 2 * * * cd /path/to/lending_app && python3 daily_backup.py --cleanup-days 30 >> backup.log 2>&1
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_flask_context():
    """Setup Flask application context for backup operations"""
    try:
        from app import app
        return app
    except ImportError as e:
        print(f"❌ Error importing Flask app: {e}")
        print("Make sure you're running this script from the lending_app directory")
        return None

def run_daily_backup(cleanup_days=30):
    """Run daily backup with optional cleanup"""
    print("🔄 Starting daily backup process...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    app = setup_flask_context()
    if not app:
        return False
    
    try:
        from backup import BackupManager
        backup_manager = BackupManager(app)
        
        # Create full backup
        print("📦 Creating full backup...")
        with app.app_context():
            backup_path = backup_manager.create_full_backup()
        
        if backup_path:
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            print(f"✅ Full backup created successfully: {backup_path}")
            print(f"📁 Backup size: {size_mb:.2f} MB")
        else:
            print("❌ Full backup failed")
            return False
        
        # Cleanup old backups if requested
        if cleanup_days > 0:
            print(f"🧹 Cleaning up backups older than {cleanup_days} days...")
            cleaned_count = backup_manager.cleanup_old_backups(cleanup_days)
            print(f"✅ Cleaned up {cleaned_count} old backup files")
        
        print("✅ Daily backup process completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Daily backup failed: {str(e)}")
        return False

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(
        description="Daily backup scheduler for Lending Management System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 daily_backup.py                    # Create backup, no cleanup
  python3 daily_backup.py --cleanup-days 30  # Create backup, cleanup files older than 30 days
  python3 daily_backup.py --cleanup-days 0   # Create backup, no cleanup

Cron Setup:
  # Add to crontab for daily backup at 2:00 AM
  0 2 * * * cd /path/to/lending_app && python3 daily_backup.py --cleanup-days 30 >> backup.log 2>&1
        """
    )
    
    parser.add_argument(
        '--cleanup-days',
        type=int,
        default=30,
        help='Number of days to keep backups (0 = no cleanup)'
    )
    
    args = parser.parse_args()
    
    print("🏦 Lending Management System - Daily Backup")
    print("=" * 50)
    
    success = run_daily_backup(args.cleanup_days)
    
    if success:
        print("\n✅ Daily backup completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Daily backup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
