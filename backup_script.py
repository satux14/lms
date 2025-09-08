#!/usr/bin/env python3
"""
Standalone Backup Script for Lending Management System
====================================================

This script can be run independently to create backups without starting the Flask app.
It provides command-line interface for various backup operations.

Usage:
    python3 backup_script.py [command] [options]

Commands:
    full        - Create full backup (database + Excel)
    database    - Create database backup only
    excel       - Create Excel export only
    cleanup     - Clean up old backups
    info        - Show backup information
    schedule    - Set up daily backup schedule

Examples:
    python3 backup_script.py full
    python3 backup_script.py database
    python3 backup_script.py excel
    python3 backup_script.py cleanup --days 30
    python3 backup_script.py info
"""

import sys
import os
import argparse
import subprocess
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

def create_full_backup():
    """Create a full backup"""
    print("🔄 Creating full backup...")
    app = setup_flask_context()
    if not app:
        return False
    
    try:
        from backup import BackupManager
        backup_manager = BackupManager(app)
        
        with app.app_context():
            backup_path = backup_manager.create_full_backup()
            
        if backup_path:
            print(f"✅ Full backup created successfully: {backup_path}")
            print(f"📁 Backup size: {backup_path.stat().st_size / (1024*1024):.2f} MB")
            return True
        else:
            print("❌ Full backup failed")
            return False
            
    except Exception as e:
        print(f"❌ Backup error: {str(e)}")
        return False

def create_database_backup():
    """Create database backup only"""
    print("🔄 Creating database backup...")
    app = setup_flask_context()
    if not app:
        return False
    
    try:
        from backup import BackupManager
        backup_manager = BackupManager(app)
        
        backup_path = backup_manager.create_database_backup()
        
        if backup_path:
            print(f"✅ Database backup created successfully: {backup_path}")
            print(f"📁 Backup size: {backup_path.stat().st_size / (1024*1024):.2f} MB")
            return True
        else:
            print("❌ Database backup failed")
            return False
            
    except Exception as e:
        print(f"❌ Backup error: {str(e)}")
        return False

def create_excel_export():
    """Create Excel export only"""
    print("🔄 Creating Excel export...")
    app = setup_flask_context()
    if not app:
        return False
    
    try:
        from backup import BackupManager
        backup_manager = BackupManager(app)
        
        with app.app_context():
            excel_path = backup_manager.export_to_excel()
            
        if excel_path:
            print(f"✅ Excel export created successfully: {excel_path}")
            print(f"📁 Export size: {excel_path.stat().st_size / (1024*1024):.2f} MB")
            return True
        else:
            print("❌ Excel export failed")
            return False
            
    except Exception as e:
        print(f"❌ Export error: {str(e)}")
        return False

def cleanup_backups(days=30):
    """Clean up old backups"""
    print(f"🔄 Cleaning up backups older than {days} days...")
    app = setup_flask_context()
    if not app:
        return False
    
    try:
        from backup import BackupManager
        backup_manager = BackupManager(app)
        
        cleaned_count = backup_manager.cleanup_old_backups(days)
        print(f"✅ Cleaned up {cleaned_count} old backup files")
        return True
        
    except Exception as e:
        print(f"❌ Cleanup error: {str(e)}")
        return False

def show_backup_info():
    """Show backup information"""
    print("📊 Backup Information")
    print("=" * 50)
    
    app = setup_flask_context()
    if not app:
        return False
    
    try:
        from backup import BackupManager
        backup_manager = BackupManager(app)
        
        info = backup_manager.get_backup_info()
        if not info:
            print("❌ Failed to get backup information")
            return False
        
        total_size_mb = info['total_size'] / (1024 * 1024)
        print(f"📁 Total backup size: {total_size_mb:.2f} MB")
        print(f"🗄️  Database backups: {len(info['database_backups'])}")
        print(f"📊 Excel exports: {len(info['excel_backups'])}")
        print(f"📦 Full backups: {len(info['full_backups'])}")
        
        if info['full_backups']:
            print("\n📦 Recent Full Backups:")
            for backup in sorted(info['full_backups'], key=lambda x: x['created'], reverse=True)[:5]:
                size_mb = backup['size'] / (1024 * 1024)
                print(f"   {backup['created']} - {backup['filename']} ({size_mb:.2f} MB)")
        
        if info['database_backups']:
            print("\n🗄️  Recent Database Backups:")
            for backup in sorted(info['database_backups'], key=lambda x: x['created'], reverse=True)[:5]:
                size_mb = backup['size'] / (1024 * 1024)
                print(f"   {backup['created']} - {backup['filename']} ({size_mb:.2f} MB)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting backup info: {str(e)}")
        return False

def setup_daily_schedule():
    """Set up daily backup schedule using cron"""
    print("🔄 Setting up daily backup schedule...")
    
    # Get current script path
    script_path = os.path.abspath(__file__)
    app_dir = os.path.dirname(script_path)
    
    # Create cron job entry
    cron_entry = f"0 2 * * * cd {app_dir} && python3 {script_path} full >> {app_dir}/backup.log 2>&1"
    
    print("📝 To set up daily backups at 2:00 AM, add this line to your crontab:")
    print(f"   {cron_entry}")
    print("\n🔧 To add it automatically, run:")
    print(f"   (crontab -l 2>/dev/null; echo '{cron_entry}') | crontab -")
    
    # Ask if user wants to add it automatically
    try:
        response = input("\n❓ Do you want to add this cron job automatically? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            # Add to crontab
            result = subprocess.run(
                f"(crontab -l 2>/dev/null; echo '{cron_entry}') | crontab -",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Daily backup schedule added successfully!")
                print("🕐 Backups will run daily at 2:00 AM")
            else:
                print(f"❌ Failed to add cron job: {result.stderr}")
        else:
            print("ℹ️  Cron job not added. You can add it manually later.")
            
    except KeyboardInterrupt:
        print("\nℹ️  Setup cancelled.")
    
    return True

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(
        description="Backup script for Lending Management System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 backup_script.py full              # Create full backup
  python3 backup_script.py database          # Create database backup only
  python3 backup_script.py excel             # Create Excel export only
  python3 backup_script.py cleanup --days 30 # Clean up backups older than 30 days
  python3 backup_script.py info              # Show backup information
  python3 backup_script.py schedule          # Set up daily backup schedule
        """
    )
    
    parser.add_argument(
        'command',
        choices=['full', 'database', 'excel', 'cleanup', 'info', 'schedule'],
        help='Backup command to execute'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to keep backups (for cleanup command)'
    )
    
    args = parser.parse_args()
    
    print("🏦 Lending Management System - Backup Script")
    print("=" * 50)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = False
    
    if args.command == 'full':
        success = create_full_backup()
    elif args.command == 'database':
        success = create_database_backup()
    elif args.command == 'excel':
        success = create_excel_export()
    elif args.command == 'cleanup':
        success = cleanup_backups(args.days)
    elif args.command == 'info':
        success = show_backup_info()
    elif args.command == 'schedule':
        success = setup_daily_schedule()
    
    if success:
        print("\n✅ Operation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Operation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
