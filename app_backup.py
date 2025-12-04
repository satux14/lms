"""
Backup Management Module
========================

This module handles all backup-related functionality including:
- Creating backups (full, database, Excel)
- Downloading backups
- Deleting backups
- Cleanup of old backups
"""

from flask import request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user

# Import from app_multi - these will be set when register_backup_routes is called
app = None

# These will be imported from app_multi
VALID_INSTANCES = None


def register_backup_routes(flask_app, valid_instances):
    """Register backup routes with Flask app"""
    global app, VALID_INSTANCES
    
    app = flask_app
    VALID_INSTANCES = valid_instances
    
    # Register routes
    register_routes()


def register_routes():
    """Register all backup routes"""
    
    @app.route('/<instance_name>/admin/backup')
    @login_required
    def admin_backup(instance_name):
        """Admin backup page for specific instance"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        from backup_multi import MultiInstanceBackupManager
        backup_manager = MultiInstanceBackupManager(app)
        backup_info = backup_manager.get_backup_info(instance_name)
        
        # Calculate total size in MB
        total_size_mb = 0
        if backup_info and 'instances' in backup_info and instance_name in backup_info['instances']:
            total_size_mb = backup_info['instances'][instance_name].get('total_size', 0) / (1024 * 1024)
        
        # Get database size for current instance
        db_size_mb = backup_manager.get_instance_database_size(instance_name) / (1024 * 1024)
        
        return render_template('admin/backup.html', 
                             backup_info=backup_info,
                             total_size_mb=total_size_mb,
                             db_size_mb=db_size_mb,
                             instance_name=instance_name)

    @app.route('/<instance_name>/admin/backup/create', methods=['GET', 'POST'])
    @login_required
    def admin_create_backup(instance_name):
        """Admin create backup for specific instance"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        from backup_multi import MultiInstanceBackupManager
        backup_manager = MultiInstanceBackupManager(app)
        
        try:
            if request.method == 'POST':
                backup_type = request.form.get('backup_type', 'full')
                
                if backup_type == 'full':
                    backup_path = backup_manager.create_full_backup(instance_name)
                    if backup_path:
                        flash(f'Full backup created successfully for {instance_name}: {backup_path.name}')
                    else:
                        flash(f'Full backup failed for {instance_name}')
                elif backup_type == 'database':
                    backup_path = backup_manager.create_database_backup(instance_name)
                    if backup_path:
                        flash(f'Database backup created successfully for {instance_name}: {backup_path.name}')
                    else:
                        flash(f'Database backup failed for {instance_name}')
                elif backup_type == 'excel':
                    backup_path = backup_manager.export_to_excel(instance_name)
                    if backup_path:
                        flash(f'Excel export created successfully for {instance_name}: {backup_path.name}')
                    else:
                        flash(f'Excel export failed for {instance_name}')
                else:
                    flash(f'Invalid backup type: {backup_type}')
            else:
                # GET request - redirect to backup page
                return redirect(url_for('admin_backup', instance_name=instance_name))
                
        except Exception as e:
            flash(f'Backup failed for {instance_name}: {str(e)}')
        
        return redirect(url_for('admin_backup', instance_name=instance_name))

    @app.route('/<instance_name>/admin/backup/cleanup', methods=['POST'])
    @login_required
    def admin_cleanup_backups(instance_name):
        """Admin cleanup old backups for specific instance"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        from backup_multi import MultiInstanceBackupManager
        backup_manager = MultiInstanceBackupManager(app)
        
        try:
            days = int(request.form.get('days', 30))
            cleaned_count = backup_manager.cleanup_old_backups(instance_name, days)
            flash(f'Cleaned up {cleaned_count} backup files older than {days} days for {instance_name}')
        except Exception as e:
            flash(f'Cleanup failed for {instance_name}: {str(e)}')
        
        return redirect(url_for('admin_backup', instance_name=instance_name))

    @app.route('/<instance_name>/admin/backup/download/<filename>')
    @login_required
    def admin_download_backup(instance_name, filename):
        """Admin download backup file for specific instance"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        from backup_multi import MultiInstanceBackupManager
        backup_manager = MultiInstanceBackupManager(app)
        
        try:
            return backup_manager.download_backup(instance_name, filename)
        except Exception as e:
            flash(f'Download failed for {instance_name}: {str(e)}')
            return redirect(url_for('admin_backup', instance_name=instance_name))

    @app.route('/<instance_name>/admin/backup/delete/<filename>', methods=['POST'])
    @login_required
    def admin_delete_backup(instance_name, filename):
        """Admin delete backup file for specific instance"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        from backup_multi import MultiInstanceBackupManager
        backup_manager = MultiInstanceBackupManager(app)
        
        try:
            success = backup_manager.delete_backup_file(instance_name, filename)
            if success:
                flash(f'Backup file deleted successfully: {filename}')
            else:
                flash(f'Failed to delete backup file: {filename}')
        except Exception as e:
            flash(f'Delete failed for {instance_name}: {str(e)}')
        
        return redirect(url_for('admin_backup', instance_name=instance_name))

