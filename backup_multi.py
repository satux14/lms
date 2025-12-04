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
Version: 2.1.0
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
        return Path(f"instances/{instance}/database/lending_app_{instance}.db")
    
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
                from app_multi import (
                    db_manager, User, Loan, Payment, InterestRate, DailyTracker,
                    CashbackTransaction, LoanCashbackConfig, TrackerEntry,
                    TrackerCashbackConfig, UserPaymentMethod, CashbackRedemption
                )
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
                            'Is Moderator': getattr(user, 'is_moderator', False),
                            'Language Preference': getattr(user, 'language_preference', ''),
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
                    
                    # Export Daily Trackers
                    try:
                        trackers_data = []
                        for tracker in db_manager.get_query_for_instance(instance, DailyTracker).all():
                            customer = db_manager.get_query_for_instance(instance, User).filter_by(id=tracker.user_id).first()
                            trackers_data.append({
                                'ID': tracker.id,
                                'Tracker Name': tracker.tracker_name,
                                'Customer ID': tracker.user_id,
                                'Customer Username': customer.username if customer else '',
                                'Tracker Type': tracker.tracker_type,
                                'Investment': float(tracker.investment) if tracker.investment else 0,
                                'Scheme Period': tracker.scheme_period,
                                'Per Day Payment': float(tracker.per_day_payment) if hasattr(tracker, 'per_day_payment') and tracker.per_day_payment else 0,
                                'Start Date': tracker.start_date.strftime('%Y-%m-%d') if tracker.start_date else '',
                                'Filename': tracker.filename or '',
                                'Is Active': tracker.is_active,
                                'Created At': tracker.created_at.strftime('%Y-%m-%d %H:%M:%S') if tracker.created_at else '',
                                'Updated At': tracker.updated_at.strftime('%Y-%m-%d %H:%M:%S') if tracker.updated_at else ''
                            })
                        
                        if trackers_data:
                            pd.DataFrame(trackers_data).to_excel(writer, sheet_name='Daily Trackers', index=False)
                    except Exception as e:
                        logger.warning(f"Failed to export Daily Trackers: {e}")
                    
                    # Export Tracker Entries
                    try:
                        tracker_entries_data = []
                        for entry in db_manager.get_query_for_instance(instance, TrackerEntry).all():
                            submitted_by = db_manager.get_query_for_instance(instance, User).filter_by(id=entry.submitted_by_user_id).first()
                            verified_by = None
                            if entry.verified_by_user_id:
                                verified_by = db_manager.get_query_for_instance(instance, User).filter_by(id=entry.verified_by_user_id).first()
                            
                            tracker_entries_data.append({
                                'ID': entry.id,
                                'Tracker ID': entry.tracker_id,
                                'Day': entry.day,
                                'Status': entry.status,
                                'Submitted By': submitted_by.username if submitted_by else '',
                                'Verified By': verified_by.username if verified_by else '',
                                'Submitted At': entry.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if entry.submitted_at else '',
                                'Verified At': entry.verified_at.strftime('%Y-%m-%d %H:%M:%S') if entry.verified_at else '',
                                'Rejection Reason': entry.rejection_reason or ''
                            })
                        
                        if tracker_entries_data:
                            pd.DataFrame(tracker_entries_data).to_excel(writer, sheet_name='Tracker Entries', index=False)
                    except Exception as e:
                        logger.warning(f"Failed to export Tracker Entries: {e}")
                    
                    # Export Cashback Transactions
                    try:
                        cashback_transactions_data = []
                        for trans in db_manager.get_query_for_instance(instance, CashbackTransaction).all():
                            from_user = None
                            if trans.from_user_id:
                                from_user = db_manager.get_query_for_instance(instance, User).filter_by(id=trans.from_user_id).first()
                            to_user = db_manager.get_query_for_instance(instance, User).filter_by(id=trans.to_user_id).first()
                            created_by = db_manager.get_query_for_instance(instance, User).filter_by(id=trans.created_by_user_id).first()
                            
                            cashback_transactions_data.append({
                                'ID': trans.id,
                                'From User': from_user.username if from_user else 'System',
                                'To User': to_user.username if to_user else '',
                                'Points': float(trans.points),
                                'Transaction Type': trans.transaction_type,
                                'Related Loan ID': trans.related_loan_id or '',
                                'Related Payment ID': trans.related_payment_id or '',
                                'Related Tracker ID': trans.related_tracker_id or '',
                                'Related Tracker Entry Day': trans.related_tracker_entry_day or '',
                                'Notes': trans.notes or '',
                                'Created By': created_by.username if created_by else '',
                                'Created At': trans.created_at.strftime('%Y-%m-%d %H:%M:%S') if trans.created_at else ''
                            })
                        
                        if cashback_transactions_data:
                            pd.DataFrame(cashback_transactions_data).to_excel(writer, sheet_name='Cashback Transactions', index=False)
                    except Exception as e:
                        logger.warning(f"Failed to export Cashback Transactions: {e}")
                    
                    # Export Loan Cashback Config
                    try:
                        loan_cashback_config_data = []
                        for config in db_manager.get_query_for_instance(instance, LoanCashbackConfig).all():
                            loan = db_manager.get_query_for_instance(instance, Loan).filter_by(id=config.loan_id).first()
                            user = db_manager.get_query_for_instance(instance, User).filter_by(id=config.user_id).first()
                            
                            loan_cashback_config_data.append({
                                'ID': config.id,
                                'Loan ID': config.loan_id,
                                'Loan Name': loan.loan_name if loan else '',
                                'User ID': config.user_id,
                                'Username': user.username if user else '',
                                'Cashback Type': config.cashback_type,
                                'Cashback Value': float(config.cashback_value),
                                'Is Active': config.is_active,
                                'Created At': config.created_at.strftime('%Y-%m-%d %H:%M:%S') if config.created_at else ''
                            })
                        
                        if loan_cashback_config_data:
                            pd.DataFrame(loan_cashback_config_data).to_excel(writer, sheet_name='Loan Cashback Config', index=False)
                    except Exception as e:
                        logger.warning(f"Failed to export Loan Cashback Config: {e}")
                    
                    # Export Tracker Cashback Config
                    try:
                        tracker_cashback_config_data = []
                        for config in db_manager.get_query_for_instance(instance, TrackerCashbackConfig).all():
                            tracker = db_manager.get_query_for_instance(instance, DailyTracker).filter_by(id=config.tracker_id).first()
                            user = db_manager.get_query_for_instance(instance, User).filter_by(id=config.user_id).first()
                            
                            tracker_cashback_config_data.append({
                                'ID': config.id,
                                'Tracker ID': config.tracker_id,
                                'Tracker Name': tracker.tracker_name if tracker else '',
                                'User ID': config.user_id,
                                'Username': user.username if user else '',
                                'Cashback Type': config.cashback_type,
                                'Cashback Value': float(config.cashback_value),
                                'Is Active': config.is_active,
                                'Created At': config.created_at.strftime('%Y-%m-%d %H:%M:%S') if config.created_at else ''
                            })
                        
                        if tracker_cashback_config_data:
                            pd.DataFrame(tracker_cashback_config_data).to_excel(writer, sheet_name='Tracker Cashback Config', index=False)
                    except Exception as e:
                        logger.warning(f"Failed to export Tracker Cashback Config: {e}")
                    
                    # Export User Payment Methods
                    try:
                        payment_methods_data = []
                        for method in db_manager.get_query_for_instance(instance, UserPaymentMethod).all():
                            user = db_manager.get_query_for_instance(instance, User).filter_by(id=method.user_id).first()
                            
                            payment_methods_data.append({
                                'ID': method.id,
                                'User ID': method.user_id,
                                'Username': user.username if user else '',
                                'Payment Type': method.payment_type,
                                'Account Name': method.account_name or '',
                                'Account Number': method.account_number or '',
                                'IFSC Code': method.ifsc_code or '',
                                'Bank Name': method.bank_name or '',
                                'UPI ID': method.upi_id or '',
                                'GPay ID': method.gpay_id or '',
                                'Phone Number': method.phone_number or '',
                                'Address': method.address or '',
                                'Is Default': method.is_default,
                                'Created At': method.created_at.strftime('%Y-%m-%d %H:%M:%S') if method.created_at else '',
                                'Updated At': method.updated_at.strftime('%Y-%m-%d %H:%M:%S') if method.updated_at else ''
                            })
                        
                        if payment_methods_data:
                            pd.DataFrame(payment_methods_data).to_excel(writer, sheet_name='User Payment Methods', index=False)
                    except Exception as e:
                        logger.warning(f"Failed to export User Payment Methods: {e}")
                    
                    # Export Cashback Redemptions
                    try:
                        redemptions_data = []
                        for redemption in db_manager.get_query_for_instance(instance, CashbackRedemption).all():
                            user = db_manager.get_query_for_instance(instance, User).filter_by(id=redemption.user_id).first()
                            
                            redemptions_data.append({
                                'ID': redemption.id,
                                'User ID': redemption.user_id,
                                'Username': user.username if user else '',
                                'Amount': float(redemption.amount),
                                'Redemption Type': redemption.redemption_type,
                                'Payment Method ID': redemption.payment_method_id or '',
                                'Account Name': redemption.account_name or '',
                                'Account Number': redemption.account_number or '',
                                'IFSC Code': redemption.ifsc_code or '',
                                'Bank Name': redemption.bank_name or '',
                                'UPI ID': redemption.upi_id or '',
                                'GPay ID': redemption.gpay_id or '',
                                'Phone Number': redemption.phone_number or '',
                                'Address': redemption.address or '',
                                'Status': redemption.status,
                                'Admin Notes': redemption.admin_notes or '',
                                'Created At': redemption.created_at.strftime('%Y-%m-%d %H:%M:%S') if redemption.created_at else '',
                                'Completed At': redemption.completed_at.strftime('%Y-%m-%d %H:%M:%S') if redemption.completed_at else ''
                            })
                        
                        if redemptions_data:
                            pd.DataFrame(redemptions_data).to_excel(writer, sheet_name='Cashback Redemptions', index=False)
                    except Exception as e:
                        logger.warning(f"Failed to export Cashback Redemptions: {e}")
                    
                    # Create Summary Sheet
                    user_query = db_manager.get_query_for_instance(instance, User)
                    loan_query = db_manager.get_query_for_instance(instance, Loan)
                    payment_query = db_manager.get_query_for_instance(instance, Payment)
                    
                    # Get tracker and cashback stats
                    tracker_count = 0
                    active_tracker_count = 0
                    tracker_entry_count = 0
                    cashback_transaction_count = 0
                    total_cashback_balance = Decimal('0')
                    redemption_count = 0
                    pending_redemption_count = 0
                    
                    try:
                        tracker_query = db_manager.get_query_for_instance(instance, DailyTracker)
                        tracker_count = tracker_query.count()
                        active_tracker_count = tracker_query.filter_by(is_active=True).count()
                        
                        tracker_entry_query = db_manager.get_query_for_instance(instance, TrackerEntry)
                        tracker_entry_count = tracker_entry_query.count()
                        
                        cashback_query = db_manager.get_query_for_instance(instance, CashbackTransaction)
                        cashback_transaction_count = cashback_query.count()
                        
                        # Calculate total cashback balance (sum of all credits to users, excluding transfers)
                        # Only count transactions where points are given (not transfers between users)
                        for trans in cashback_query.all():
                            # Count only credits (transactions TO users, excluding transfers)
                            if trans.transaction_type != 'transfer':
                                total_cashback_balance += trans.points
                        
                        redemption_query = db_manager.get_query_for_instance(instance, CashbackRedemption)
                        redemption_count = redemption_query.count()
                        pending_redemption_count = redemption_query.filter_by(status='pending').count()
                    except Exception as e:
                        logger.warning(f"Failed to get tracker/cashback stats: {e}")
                    
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
                            'Total Trackers',
                            'Active Trackers',
                            'Tracker Entries',
                            'Cashback Transactions',
                            'Total Cashback Given',
                            'Redemption Requests',
                            'Pending Redemptions',
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
                            tracker_count,
                            active_tracker_count,
                            tracker_entry_count,
                            cashback_transaction_count,
                            float(total_cashback_balance),
                            redemption_count,
                            pending_redemption_count,
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
                
                # Add daily tracker files
                tracker_dir = Path("instances") / instance / "daily-trackers"
                tracker_files_added = 0
                if tracker_dir.exists():
                    for tracker_file in tracker_dir.glob("*.xlsx"):
                        zipf.write(tracker_file, f"{backup_name}/daily-trackers/{tracker_file.name}")
                        tracker_files_added += 1
                    logger.info(f"Added {tracker_files_added} daily tracker files to backup")
                
                # Add backup metadata
                metadata = {
                    'instance': instance,
                    'backup_date': datetime.now().isoformat(),
                    'backup_type': 'full',
                    'database_file': db_backup.name,
                    'excel_file': excel_backup.name,
                    'tracker_files_count': tracker_files_added,
                    'version': '2.1.0'
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
