"""
Backup System for Lending Management Application
===============================================

This module provides comprehensive backup functionality including:
- Database backup (SQLite file copy)
- Excel export of all data
- Automated backup scheduling
- Manual backup execution

Author: Lending Management System
Version: 1.0.1
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BackupManager:
    """Manages all backup operations for the lending application"""
    
    def __init__(self, app=None):
        """Initialize backup manager with Flask app context"""
        self.app = app
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.db_backup_dir = self.backup_dir / "database"
        self.excel_backup_dir = self.backup_dir / "excel"
        self.full_backup_dir = self.backup_dir / "full"
        
        for dir_path in [self.db_backup_dir, self.excel_backup_dir, self.full_backup_dir]:
            dir_path.mkdir(exist_ok=True)
    
    def get_database_path(self):
        """Get the current database file path"""
        if self.app:
            with self.app.app_context():
                from app import app
                db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///lending_app.db')
                if db_uri.startswith('sqlite:///'):
                    db_path = db_uri.replace('sqlite:///', '')
                    return Path(db_path)
        return Path("lending_app.db")
    
    def create_database_backup(self):
        """Create a backup of the SQLite database"""
        try:
            db_path = self.get_database_path()
            if not db_path.exists():
                logger.error(f"Database file not found: {db_path}")
                return None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"lending_app_backup_{timestamp}.db"
            backup_path = self.db_backup_dir / backup_filename
            
            # Copy database file
            shutil.copy2(db_path, backup_path)
            logger.info(f"Database backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Database backup failed: {str(e)}")
            return None
    
    def export_to_excel(self):
        """Export all data to Excel files"""
        try:
            if not self.app:
                logger.error("Flask app not initialized")
                return None
            
            with self.app.app_context():
                from app import db, User, Loan, Payment, InterestRate
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                excel_filename = f"lending_data_export_{timestamp}.xlsx"
                excel_path = self.excel_backup_dir / excel_filename
                
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    # Export Users
                    users_data = []
                    for user in User.query.all():
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
                    for loan in Loan.query.all():
                        loans_data.append({
                            'ID': loan.id,
                            'Loan Name': loan.loan_name,
                            'Customer ID': loan.customer_id,
                            'Customer Username': loan.customer.username if loan.customer else '',
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
                    for payment in Payment.query.all():
                        payments_data.append({
                            'ID': payment.id,
                            'Loan ID': payment.loan_id,
                            'Loan Name': payment.loan.loan_name if payment.loan else '',
                            'Customer Username': payment.loan.customer.username if payment.loan and payment.loan.customer else '',
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
                    for rate in InterestRate.query.all():
                        interest_rates_data.append({
                            'ID': rate.id,
                            'Rate': float(rate.rate),
                            'Created At': rate.created_at.strftime('%Y-%m-%d %H:%M:%S')
                        })
                    
                    if interest_rates_data:
                        pd.DataFrame(interest_rates_data).to_excel(writer, sheet_name='Interest Rates', index=False)
                    
                    # Create Summary Sheet
                    summary_data = {
                        'Metric': [
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
                            User.query.count(),
                            Loan.query.count(),
                            Payment.query.count(),
                            Loan.query.filter_by(is_active=True).count(),
                            Loan.query.filter_by(is_active=False).count(),
                            Payment.query.filter_by(status='pending').count(),
                            Payment.query.filter_by(status='verified').count(),
                            float(sum(loan.principal_amount for loan in Loan.query.all())),
                            float(sum(loan.remaining_principal for loan in Loan.query.all())),
                            float(sum(payment.interest_amount for payment in Payment.query.filter_by(status='verified').all())),
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ]
                    }
                    
                    pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                
                logger.info(f"Excel export created: {excel_path}")
                return excel_path
                
        except Exception as e:
            logger.error(f"Excel export failed: {str(e)}")
            return None
    
    def create_full_backup(self):
        """Create a complete backup including database and Excel export"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"full_backup_{timestamp}"
            backup_path = self.full_backup_dir / f"{backup_name}.zip"
            
            # Create database backup
            db_backup = self.create_database_backup()
            if not db_backup:
                logger.error("Database backup failed, aborting full backup")
                return None
            
            # Create Excel export
            excel_backup = self.export_to_excel()
            if not excel_backup:
                logger.error("Excel export failed, aborting full backup")
                return None
            
            # Create ZIP file with all backups
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add database backup
                zipf.write(db_backup, f"{backup_name}/database/{db_backup.name}")
                
                # Add Excel export
                zipf.write(excel_backup, f"{backup_name}/excel/{excel_backup.name}")
                
                # Add backup metadata
                metadata = {
                    'backup_date': datetime.now().isoformat(),
                    'backup_type': 'full',
                    'database_file': db_backup.name,
                    'excel_file': excel_backup.name,
                    'version': '1.0.1'
                }
                
                zipf.writestr(f"{backup_name}/metadata.json", json.dumps(metadata, indent=2))
            
            # Clean up individual files (keep them in the ZIP)
            db_backup.unlink()
            excel_backup.unlink()
            
            logger.info(f"Full backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Full backup failed: {str(e)}")
            return None
    
    def cleanup_old_backups(self, days_to_keep=30):
        """Clean up backup files older than specified days"""
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            cleaned_count = 0
            
            for backup_dir in [self.db_backup_dir, self.excel_backup_dir, self.full_backup_dir]:
                for file_path in backup_dir.iterdir():
                    if file_path.is_file() and file_path.stat().st_mtime < cutoff_date:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.info(f"Cleaned up old backup: {file_path}")
            
            logger.info(f"Cleaned up {cleaned_count} old backup files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {str(e)}")
            return 0
    
    def get_backup_info(self):
        """Get information about existing backups"""
        try:
            backup_info = {
                'database_backups': [],
                'excel_backups': [],
                'full_backups': [],
                'total_size': 0
            }
            
            for backup_dir, key in [
                (self.db_backup_dir, 'database_backups'),
                (self.excel_backup_dir, 'excel_backups'),
                (self.full_backup_dir, 'full_backups')
            ]:
                for file_path in backup_dir.iterdir():
                    if file_path.is_file():
                        stat = file_path.stat()
                        backup_info[key].append({
                            'filename': file_path.name,
                            'size': stat.st_size,
                            'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                            'path': str(file_path)
                        })
                        backup_info['total_size'] += stat.st_size
            
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to get backup info: {str(e)}")
            return None

def create_backup(app=None):
    """Convenience function to create a full backup"""
    backup_manager = BackupManager(app)
    return backup_manager.create_full_backup()

def export_excel(app=None):
    """Convenience function to export data to Excel"""
    backup_manager = BackupManager(app)
    return backup_manager.export_to_excel()

if __name__ == "__main__":
    # This allows the module to be run directly for testing
    print("Backup Manager - Testing mode")
    backup_manager = BackupManager()
    
    # Test database backup
    print("Testing database backup...")
    db_backup = backup_manager.create_database_backup()
    if db_backup:
        print(f"✅ Database backup successful: {db_backup}")
    else:
        print("❌ Database backup failed")
    
    # Test Excel export (requires Flask app context)
    print("\nTesting Excel export...")
    print("Note: Excel export requires Flask app context")
    
    # Test backup info
    print("\nBackup information:")
    info = backup_manager.get_backup_info()
    if info:
        print(f"Total backup size: {info['total_size'] / (1024*1024):.2f} MB")
        print(f"Database backups: {len(info['database_backups'])}")
        print(f"Excel backups: {len(info['excel_backups'])}")
        print(f"Full backups: {len(info['full_backups'])}")
