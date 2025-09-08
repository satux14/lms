#!/usr/bin/env python3
"""
Instance Management Script for Lending Management System
======================================================

This script helps manage multiple instances (prod, dev, testing) of the lending application.
It provides commands to create, reset, and manage instance databases.

Usage:
    python3 manage_instances.py [command] [options]

Commands:
    create <instance>    - Create a new instance
    reset <instance>     - Reset an instance (delete all data)
    list                - List all instances and their status
    info <instance>     - Show detailed information about an instance
    backup <instance>   - Create backup of an instance
    restore <instance> <backup_file> - Restore instance from backup

Examples:
    python3 manage_instances.py create dev
    python3 manage_instances.py reset testing
    python3 manage_instances.py list
    python3 manage_instances.py info prod
"""

import sys
import os
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VALID_INSTANCES = ['prod', 'dev', 'testing']

def get_instance_path(instance):
    """Get the path for an instance"""
    return Path("instances") / instance

def get_database_path(instance):
    """Get the database path for an instance"""
    return get_instance_path(instance) / "database" / f"lending_app_{instance}.db"

def get_uploads_path(instance):
    """Get the uploads path for an instance"""
    return get_instance_path(instance) / "uploads"

def get_backups_path(instance):
    """Get the backups path for an instance"""
    return get_instance_path(instance) / "backups"

def create_instance(instance):
    """Create a new instance"""
    if instance not in VALID_INSTANCES:
        print(f"❌ Invalid instance: {instance}")
        print(f"Valid instances: {', '.join(VALID_INSTANCES)}")
        return False
    
    print(f"🔄 Creating {instance} instance...")
    
    try:
        # Create instance directory structure
        instance_path = get_instance_path(instance)
        instance_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (instance_path / "database").mkdir(exist_ok=True)
        (instance_path / "uploads").mkdir(exist_ok=True)
        (instance_path / "backups").mkdir(exist_ok=True)
        
        # Create database using the app
        from app_multi import app, db, User, InterestRate
        from decimal import Decimal
        from werkzeug.security import generate_password_hash
        
        # Configure app for this instance
        db_path = get_database_path(instance)
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
        
        with app.app_context():
            db.create_all()
            
            # Create default admin user
            if not User.query.filter_by(username='admin').first():
                admin = User(
                    username='admin',
                    email=f'admin@{instance}.lendingapp.com',
                    password_hash=generate_password_hash('admin123'),
                    is_admin=True
                )
                db.session.add(admin)
                
                # Create default interest rate
                default_rate = InterestRate(rate=Decimal('0.21'))  # 21%
                db.session.add(default_rate)
                
                db.session.commit()
                print(f"✅ Created default admin user: username='admin', password='admin123'")
        
        print(f"✅ {instance} instance created successfully!")
        print(f"📁 Instance path: {instance_path}")
        print(f"🗄️  Database: {get_database_path(instance)}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create {instance} instance: {str(e)}")
        return False

def reset_instance(instance):
    """Reset an instance (delete all data)"""
    if instance not in VALID_INSTANCES:
        print(f"❌ Invalid instance: {instance}")
        print(f"Valid instances: {', '.join(VALID_INSTANCES)}")
        return False
    
    print(f"⚠️  Resetting {instance} instance...")
    print("This will delete ALL data in this instance!")
    
    try:
        response = input(f"Are you sure you want to reset {instance}? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("❌ Reset cancelled")
            return False
        
        instance_path = get_instance_path(instance)
        
        if instance_path.exists():
            shutil.rmtree(instance_path)
            print(f"🗑️  Deleted {instance} instance directory")
        
        # Recreate the instance
        return create_instance(instance)
        
    except Exception as e:
        print(f"❌ Failed to reset {instance} instance: {str(e)}")
        return False

def list_instances():
    """List all instances and their status"""
    print("📋 Instance Status")
    print("=" * 50)
    
    for instance in VALID_INSTANCES:
        instance_path = get_instance_path(instance)
        db_path = get_database_path(instance)
        
        print(f"\n🔹 {instance.upper()} Instance:")
        print(f"   Path: {instance_path}")
        print(f"   Database: {'✅ Exists' if db_path.exists() else '❌ Not found'}")
        
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            print(f"   Size: {size_mb:.2f} MB")
            print(f"   Modified: {datetime.fromtimestamp(db_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check uploads directory
        uploads_path = get_uploads_path(instance)
        uploads_count = len(list(uploads_path.glob('*'))) if uploads_path.exists() else 0
        print(f"   Uploads: {uploads_count} files")
        
        # Check backups directory
        backups_path = get_backups_path(instance)
        backups_count = len(list(backups_path.glob('*'))) if backups_path.exists() else 0
        print(f"   Backups: {backups_count} files")

def show_instance_info(instance):
    """Show detailed information about an instance"""
    if instance not in VALID_INSTANCES:
        print(f"❌ Invalid instance: {instance}")
        print(f"Valid instances: {', '.join(VALID_INSTANCES)}")
        return False
    
    print(f"📊 {instance.upper()} Instance Information")
    print("=" * 50)
    
    instance_path = get_instance_path(instance)
    db_path = get_database_path(instance)
    
    print(f"Instance Name: {instance}")
    print(f"Instance Path: {instance_path}")
    print(f"Database Path: {db_path}")
    print(f"Database Exists: {'✅ Yes' if db_path.exists() else '❌ No'}")
    
    if db_path.exists():
        stat = db_path.stat()
        print(f"Database Size: {stat.st_size / (1024 * 1024):.2f} MB")
        print(f"Created: {datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Try to get database info
        try:
            from app_multi import app, db, User, Loan, Payment
            app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
            
            with app.app_context():
                users_count = User.query.count()
                loans_count = Loan.query.count()
                payments_count = Payment.query.count()
                
                print(f"\n📈 Database Statistics:")
                print(f"   Users: {users_count}")
                print(f"   Loans: {loans_count}")
                print(f"   Payments: {payments_count}")
                
        except Exception as e:
            print(f"⚠️  Could not read database statistics: {e}")
    
    # Check other directories
    uploads_path = get_uploads_path(instance)
    if uploads_path.exists():
        uploads_files = list(uploads_path.glob('*'))
        print(f"\n📁 Uploads Directory: {len(uploads_files)} files")
        for file in uploads_files[:5]:  # Show first 5 files
            print(f"   - {file.name}")
        if len(uploads_files) > 5:
            print(f"   ... and {len(uploads_files) - 5} more files")
    
    backups_path = get_backups_path(instance)
    if backups_path.exists():
        backups_files = list(backups_path.glob('*'))
        print(f"\n💾 Backups Directory: {len(backups_files)} files")
        for file in backups_files[:5]:  # Show first 5 files
            print(f"   - {file.name}")
        if len(backups_files) > 5:
            print(f"   ... and {len(backups_files) - 5} more files")

def backup_instance(instance):
    """Create backup of an instance"""
    if instance not in VALID_INSTANCES:
        print(f"❌ Invalid instance: {instance}")
        print(f"Valid instances: {', '.join(VALID_INSTANCES)}")
        return False
    
    print(f"🔄 Creating backup of {instance} instance...")
    
    try:
        from backup import BackupManager
        from app_multi import app
        
        # Configure app for this instance
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{get_database_path(instance)}"
        app.config['UPLOAD_FOLDER'] = str(get_uploads_path(instance))
        
        backup_manager = BackupManager(app)
        backup_manager.backup_dir = get_backups_path(instance)
        
        with app.app_context():
            backup_path = backup_manager.create_full_backup()
        
        if backup_path:
            print(f"✅ Backup created successfully: {backup_path}")
            return True
        else:
            print("❌ Backup failed")
            return False
            
    except Exception as e:
        print(f"❌ Backup failed: {str(e)}")
        return False

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(
        description="Instance management script for Lending Management System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 manage_instances.py create dev          # Create development instance
  python3 manage_instances.py reset testing       # Reset testing instance
  python3 manage_instances.py list                # List all instances
  python3 manage_instances.py info prod           # Show production instance info
  python3 manage_instances.py backup dev          # Backup development instance
        """
    )
    
    parser.add_argument(
        'command',
        choices=['create', 'reset', 'list', 'info', 'backup'],
        help='Command to execute'
    )
    
    parser.add_argument(
        'instance',
        nargs='?',
        choices=VALID_INSTANCES,
        help='Instance name (required for create, reset, info, backup)'
    )
    
    args = parser.parse_args()
    
    print("🏦 Lending Management System - Instance Manager")
    print("=" * 50)
    
    success = False
    
    if args.command == 'create':
        if not args.instance:
            print("❌ Instance name required for create command")
            sys.exit(1)
        success = create_instance(args.instance)
    elif args.command == 'reset':
        if not args.instance:
            print("❌ Instance name required for reset command")
            sys.exit(1)
        success = reset_instance(args.instance)
    elif args.command == 'list':
        list_instances()
        success = True
    elif args.command == 'info':
        if not args.instance:
            print("❌ Instance name required for info command")
            sys.exit(1)
        success = show_instance_info(args.instance)
    elif args.command == 'backup':
        if not args.instance:
            print("❌ Instance name required for backup command")
            sys.exit(1)
        success = backup_instance(args.instance)
    
    if success:
        print("\n✅ Operation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Operation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
