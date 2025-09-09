"""
Multi-Instance Backup System for Lending Management Application
=============================================================

This module provides comprehensive backup functionality for the multi-instance system including:
- Instance-specific database backups
- Instance-specific Excel exports with instance names in filenames
- Automated backup scheduling per instance
- Manual backup execution per instance
- Cross-instance backup management

Author: Lending Management System
Version: 2.0.0
"""

import os
import shutil
import sqlite3
import pandas as pd
from datetime import datetime, date
from pathlib import Path
import zipfile
import json
from decimal import Decimal
import logging
from app_multi import VALID_INSTANCES, get_database_uri

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup_multi.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MultiInstanceBackupManager:
    """Manages all backup operations for the multi-instance lending application"""
    
    def __init__(self, app=None):
        """Initialize backup manager with Flask app context"""
        self.app = app
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Create instance-specific subdirectories
        for instance in VALID_INSTANCES:
            instance_backup_dir = self.backup_dir / instance
            (instance_backup_dir / "database").mkdir(parents=True, exist_ok=True)
            (instance_backup_dir / "excel").mkdir(parents=True, exist_ok=True)
            (instance_backup_dir / "full").mkdir(parents=True, exist_ok=True)
    
    def get_database_path(self, instance):
        """Get the database file path for a specific instance"""
        if instance not in VALID_INSTANCES:
            raise ValueError(f"Invalid instance: {instance}")
        
        db_uri = get_database_uri(instance)
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            return Path(db_path)
        return Path(f"instance/{instance}/lending_app.db")
    
    def create_database_backup(self, instance):
        """Create a backup of the SQLite database for a specific instance"""
        try:
            if instance not in VALID_INSTANCES:
                logger.error(f"Invalid instance: {instance}")
                return None
                
            db_path = self.get_database_path(instance)
            if not db_path.exists():
                logger.error(f"Database file not found for {instance}: {db_path}")
                return None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{instance}_lending_app_backup_{timestamp}.db"
            backup_path = self.backup_dir / instance / "database" / backup_filename
            
            # Copy database file
            shutil.copy2(db_path, backup_path)
            logger.info(f"Database backup created for {instance}: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Database backup failed for {instance}: {str(e)}")
            return None
    
    def export_to_excel(self, instance):
        """Export all data to Excel files for a specific instance"""
        try:
            if not self.app:
                logger.error("Flask app not initialized")
                return None
            
            if instance not in VALID_INSTANCES:
                logger.error(f"Invalid instance: {instance}")
                return None
            
            with self.app.app_context():
                from app_multi import db_manager, User, Loan, Payment, InterestRate
                from flask import g
                
                # Set the current instance
                g.current_instance = instance
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                excel_filename = f"{instance}_lending_data_export_{timestamp}.xlsx"
                excel_path = self.backup_dir / instance / "excel" / excel_filename
                
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    # Export Users
                    users_data = []
                    for user in db_manager.get_query_for_instance(instance, User).all():
                        users_data.append({
                            'ID': user.id,
                            'Username': user.username,
                            'Email': user.email or '',
                            'Is Admin': user.is_admin,
                            'Created At': user.created_at.strftime('%Y-%m-%d %H:%M:%S')
                        })
                    
                    if users_data:
                        pd.DataFrame(users_data).to_excel(writer, sheet_name='Users', index=False)
                    
                    # Export Loans
                    loans_data = []
                    for loan in db_manager.get_query_for_instance(instance, Loan).all():
                        # Get customer info
                        customer = db_manager.get_query_for_instance(instance, User).filter_by(id=loan.customer_id).first()
                        loans_data.append({
                            'ID': loan.id,
                            'Loan Name': loan.loan_name,
                            'Customer ID': loan.customer_id,
                            'Customer Username': customer.username if customer else '',
                            'Principal Amount': float(loan.principal_amount),
                            'Remaining Principal': float(loan.remaining_principal),
                            'Interest Rate': float(loan.interest_rate),
                            'Payment Frequency': loan.payment_frequency,
                            'Loan Type': loan.loan_type,
                            'Is Active': loan.is_active,
                            'Created At': loan.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                            'Admin Notes': loan.admin_notes or '',
                            'Customer Notes': loan.customer_notes or ''
                        })
                    
                    if loans_data:
                        pd.DataFrame(loans_data).to_excel(writer, sheet_name='Loans', index=False)
                    
                    # Export Payments
                    payments_data = []
                    for payment in db_manager.get_query_for_instance(instance, Payment).all():
                        # Get loan and customer info
                        loan = db_manager.get_query_for_instance(instance, Loan).filter_by(id=payment.loan_id).first()
                        customer = None
                        if loan:
                            customer = db_manager.get_query_for_instance(instance, User).filter_by(id=loan.customer_id).first()
                        
                        payments_data.append({
                            'ID': payment.id,
                            'Loan ID': payment.loan_id,
                            'Loan Name': loan.loan_name if loan else '',
                            'Customer Username': customer.username if customer else '',
                            'Amount': float(payment.amount),
                            'Principal Amount': float(payment.principal_amount),
                            'Interest Amount': float(payment.interest_amount),
                            'Payment Date': payment.payment_date.strftime('%Y-%m-%d %H:%M:%S'),
                            'Payment Method': payment.payment_method,
                            'Payment Type': payment.payment_type,
                            'Status': payment.status,
                            'Transaction ID': payment.transaction_id or '',
                            'Proof Filename': payment.proof_filename or ''
                        })
                    
                    if payments_data:
                        pd.DataFrame(payments_data).to_excel(writer, sheet_name='Payments', index=False)
                    
                    # Export Interest Rates (if any)
                    interest_rates_data = []
                    for rate in db_manager.get_query_for_instance(instance, InterestRate).all():
                        interest_rates_data.append({
                            'ID': rate.id,
                            'Rate': float(rate.rate),
                            'Created At': rate.created_at.strftime('%Y-%m-%d %H:%M:%S')
                        })
                    
                    if interest_rates_data:
                        pd.DataFrame(interest_rates_data).to_excel(writer, sheet_name='Interest Rates', index=False)
                    
                    # Create Summary Sheet
                    user_query = db_manager.get_query_for_instance(instance, User)
                    loan_query = db_manager.get_query_for_instance(instance, Loan)
                    payment_query = db_manager.get_query_for_instance(instance, Payment)
                    
                    summary_data = {
                        'Metric': [
                            'Instance',
                            'Total Users',
                            'Total Loans',
                            'Total Payments',
                            'Active Loans',
                            'Inactive Loans',
                            'Pending Payments',
                            'Verified Payments',
                            'Total Principal Amount',
                            'Total Remaining Principal',
                            'Total Interest Paid',
                            'Backup Date'
                        ],
                        'Value': [
                            instance,
                            user_query.count(),
                            loan_query.count(),
                            payment_query.count(),
                            loan_query.filter_by(is_active=True).count(),
                            loan_query.filter_by(is_active=False).count(),
                            payment_query.filter_by(status='pending').count(),
                            payment_query.filter_by(status='verified').count(),
                            float(sum(loan.principal_amount for loan in loan_query.all())),
                            float(sum(loan.remaining_principal for loan in loan_query.all())),
                            float(sum(payment.interest_amount for payment in payment_query.filter_by(status='verified').all())),
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ]
                    }
                    
                    pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                
                logger.info(f"Excel export created for {instance}: {excel_path}")
                return excel_path
                
        except Exception as e:
            logger.error(f"Excel export failed for {instance}: {str(e)}")
            return None
    
    def create_full_backup(self, instance):
        """Create a complete backup including database and Excel export for a specific instance"""
        try:
            if instance not in VALID_INSTANCES:
                logger.error(f"Invalid instance: {instance}")
                return None
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{instance}_full_backup_{timestamp}"
            backup_path = self.backup_dir / instance / "full" / f"{backup_name}.zip"
            
            # Create database backup
            db_backup = self.create_database_backup(instance)
            if not db_backup:
                logger.error(f"Database backup failed for {instance}, aborting full backup")
                return None
            
            # Create Excel export
            excel_backup = self.export_to_excel(instance)
            if not excel_backup:
                logger.error(f"Excel export failed for {instance}, aborting full backup")
                return None
            
            # Create ZIP file with all backups
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add database backup
                zipf.write(db_backup, f"{backup_name}/database/{db_backup.name}")
                
                # Add Excel export
                zipf.write(excel_backup, f"{backup_name}/excel/{excel_backup.name}")
                
                # Add backup metadata
                metadata = {
                    'instance': instance,
                    'backup_date': datetime.now().isoformat(),
                    'backup_type': 'full',
                    'database_file': db_backup.name,
                    'excel_file': excel_backup.name,
                    'version': '2.0.0'
                }
                
                zipf.writestr(f"{backup_name}/metadata.json", json.dumps(metadata, indent=2))
            
            # Clean up individual files (keep them in the ZIP)
            db_backup.unlink()
            excel_backup.unlink()
            
            logger.info(f"Full backup created for {instance}: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Full backup failed for {instance}: {str(e)}")
            return None
    
    def create_all_instances_backup(self):
        """Create backups for all instances"""
        results = {}
        for instance in VALID_INSTANCES:
            logger.info(f"Creating backup for instance: {instance}")
            results[instance] = self.create_full_backup(instance)
        return results
    
    def cleanup_old_backups(self, instance=None, days_to_keep=30):
        """Clean up backup files older than specified days for a specific instance or all instances"""
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            cleaned_count = 0
            
            instances_to_clean = [instance] if instance else VALID_INSTANCES
            
            for instance_name in instances_to_clean:
                if instance_name not in VALID_INSTANCES:
                    continue
                    
                instance_backup_dir = self.backup_dir / instance_name
                for backup_type in ["database", "excel", "full"]:
                    backup_type_dir = instance_backup_dir / backup_type
                    if backup_type_dir.exists():
                        for file_path in backup_type_dir.iterdir():
                            if file_path.is_file() and file_path.stat().st_mtime < cutoff_date:
                                file_path.unlink()
                                cleaned_count += 1
                                logger.info(f"Cleaned up old backup for {instance_name}: {file_path}")
            
            logger.info(f"Cleaned up {cleaned_count} old backup files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {str(e)}")
            return 0
    
    def get_backup_info(self, instance=None):
        """Get information about existing backups for a specific instance or all instances"""
        try:
            if instance and instance not in VALID_INSTANCES:
                logger.error(f"Invalid instance: {instance}")
                return None
            
            instances_to_check = [instance] if instance else VALID_INSTANCES
            backup_info = {
                'instances': {},
                'total_size': 0
            }
            
            for instance_name in instances_to_check:
                instance_info = {
                    'database_backups': [],
                    'excel_backups': [],
                    'full_backups': [],
                    'total_size': 0
                }
                
                instance_backup_dir = self.backup_dir / instance_name
                for backup_type in ["database", "excel", "full"]:
                    backup_type_dir = instance_backup_dir / backup_type
                    if backup_type_dir.exists():
                        for file_path in backup_type_dir.iterdir():
                            if file_path.is_file():
                                stat = file_path.stat()
                                backup_data = {
                                    'filename': file_path.name,
                                    'size': stat.st_size,
                                    'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                                    'path': str(file_path)
                                }
                                instance_info[f'{backup_type}_backups'].append(backup_data)
                                instance_info['total_size'] += stat.st_size
                                backup_info['total_size'] += stat.st_size
                
                backup_info['instances'][instance_name] = instance_info
            
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to get backup info: {str(e)}")
            return None
    
    def get_instance_database_size(self, instance):
        """Get the size of the database file for a specific instance"""
        try:
            if instance not in VALID_INSTANCES:
                return 0
                
            db_path = self.get_database_path(instance)
            if db_path.exists():
                return db_path.stat().st_size
            return 0
        except Exception as e:
            logger.error(f"Failed to get database size for {instance}: {str(e)}")
            return 0
    
    def download_backup(self, instance, filename):
        """Download a backup file for a specific instance"""
        try:
            if instance not in VALID_INSTANCES:
                raise ValueError(f"Invalid instance: {instance}")
            
            from flask import send_file, abort
            
            # Look for the file in all backup directories for this instance
            instance_backup_dir = self.backup_dir / instance
            for backup_type in ["database", "excel", "full"]:
                backup_type_dir = instance_backup_dir / backup_type
                file_path = backup_type_dir / filename
                if file_path.exists() and file_path.is_file():
                    return send_file(
                        str(file_path),
                        as_attachment=True,
                        download_name=filename
                    )
            
            # File not found
            abort(404)
            
        except Exception as e:
            logger.error(f"Download failed for {instance}/{filename}: {str(e)}")
            raise e
    
    def delete_backup_file(self, instance, filename):
        """Delete a backup file for a specific instance"""
        try:
            if instance not in VALID_INSTANCES:
                logger.error(f"Invalid instance: {instance}")
                return False
            
            # Look for the file in all backup directories for this instance
            instance_backup_dir = self.backup_dir / instance
            for backup_type in ["database", "excel", "full"]:
                backup_type_dir = instance_backup_dir / backup_type
                file_path = backup_type_dir / filename
                if file_path.exists() and file_path.is_file():
                    file_path.unlink()
                    logger.info(f"Deleted backup file for {instance}: {file_path}")
                    return True
            
            # File not found
            logger.warning(f"Backup file not found for deletion: {instance}/{filename}")
            return False
            
        except Exception as e:
            logger.error(f"Delete failed for {instance}/{filename}: {str(e)}")
            return False

def create_backup(instance, app=None):
    """Convenience function to create a full backup for a specific instance"""
    backup_manager = MultiInstanceBackupManager(app)
    return backup_manager.create_full_backup(instance)

def export_excel(instance, app=None):
    """Convenience function to export data to Excel for a specific instance"""
    backup_manager = MultiInstanceBackupManager(app)
    return backup_manager.export_to_excel(instance)

def create_all_backups(app=None):
    """Convenience function to create backups for all instances"""
    backup_manager = MultiInstanceBackupManager(app)
    return backup_manager.create_all_instances_backup()

if __name__ == "__main__":
    # This allows the module to be run directly for testing
    print("Multi-Instance Backup Manager - Testing mode")
    backup_manager = MultiInstanceBackupManager()
    
    # Test database backup for each instance
    for instance in VALID_INSTANCES:
        print(f"\nTesting database backup for {instance}...")
        db_backup = backup_manager.create_database_backup(instance)
        if db_backup:
            print(f"✅ Database backup successful for {instance}: {db_backup}")
        else:
            print(f"❌ Database backup failed for {instance}")
    
    # Test backup info
    print("\nBackup information:")
    info = backup_manager.get_backup_info()
    if info:
        print(f"Total backup size: {info['total_size'] / (1024*1024):.2f} MB")
        for instance, instance_info in info['instances'].items():
            print(f"\n{instance} instance:")
            print(f"  Database backups: {len(instance_info['database_backups'])}")
            print(f"  Excel backups: {len(instance_info['excel_backups'])}")
            print(f"  Full backups: {len(instance_info['full_backups'])}")
            print(f"  Total size: {instance_info['total_size'] / (1024*1024):.2f} MB")
