"""
Cashback Routes Module
======================

This module handles all cashback-related functionality including:
- Cashback transactions and balance management
- Cashback configuration for loans and trackers
- Cashback redemption system
- User payment methods management
"""

from flask import request, redirect, url_for, flash, render_template, jsonify, abort, g
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from sqlalchemy import or_

# Import from app_multi - these will be set when register_cashback_routes is called
app = None
db = None

# These will be imported from app_multi
VALID_INSTANCES = None
DEFAULT_INSTANCE = None
User = None
Loan = None
DailyTracker = None
Payment = None
CashbackTransaction = None
LoanCashbackConfig = None
TrackerCashbackConfig = None
UserPaymentMethod = None
CashbackRedemption = None
get_user_query = None
get_loan_query = None
get_daily_tracker_query = None
get_payment_query = None
get_cashback_transaction_query = None
get_loan_cashback_config_query = None
get_tracker_cashback_config_query = None
get_user_payment_method_query = None
get_cashback_redemption_query = None
add_to_current_instance = None
commit_current_instance = None
get_current_instance_from_g = None
db_manager = None




def register_routes():
    """Register all cashback routes"""
    
    # Admin Cashback Management Routes
    @app.route('/<instance_name>/admin/cashback')
    @login_required
    def admin_cashback(instance_name):
        """Admin cashback management page"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        # Get search filter
        search_username = request.args.get('search', '').strip()
        
        # Get all users
        query = get_user_query()
        if search_username:
            query = query.filter(User.username.contains(search_username))
        
        users = query.order_by(User.username).all()
        
        # Calculate balance for each user
        user_balances = []
        total_balance = Decimal('0')
        for user in users:
            balance = get_user_cashback_balance(user.id, instance_name)
            total_balance += balance
            user_balances.append({
                'user': user,
                'balance': balance
            })
        
        # Get cashback history tab parameter
        show_history = request.args.get('tab') == 'history'
        
        # Get all cashback transactions if history tab is selected
        cashback_transactions = []
        if show_history:
            # Get filter parameters
            filter_user = request.args.get('filter_user', '').strip()
            filter_type = request.args.get('filter_type', '').strip()
            
            # Build query
            query = get_cashback_transaction_query()
            
            if filter_user:
                # Filter by username (from_user or to_user)
                user_ids = [u.id for u in get_user_query().filter(
                    User.username.contains(filter_user)
                ).all()]
                if user_ids:
                    query = query.filter(
                        or_(
                            CashbackTransaction.from_user_id.in_(user_ids),
                            CashbackTransaction.to_user_id.in_(user_ids)
                        )
                    )
            
            if filter_type:
                query = query.filter(CashbackTransaction.transaction_type == filter_type)
            
            # Order by most recent first
            cashback_transactions = query.order_by(
                CashbackTransaction.created_at.desc()
            ).limit(500).all()  # Limit to 500 most recent
        
        return render_template('admin/cashback.html',
                             user_balances=user_balances,
                             total_balance=total_balance,
                             search_username=search_username,
                             cashback_transactions=cashback_transactions,
                             show_history=show_history,
                             filter_user=request.args.get('filter_user', ''),
                             filter_type=request.args.get('filter_type', ''),
                             instance_name=instance_name)

    @app.route('/<instance_name>/admin/cashback/add', methods=['GET', 'POST'])
    @login_required
    def admin_add_cashback(instance_name):
        """Admin add unconditional cashback to users"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        if request.method == 'POST':
            # Get all user entries from form
            usernames = request.form.getlist('username[]')
            points_list = request.form.getlist('points[]')
            notes = request.form.get('notes', '').strip()
            
            if not usernames or not any(usernames):
                flash('At least one user is required', 'error')
                return redirect(url_for('admin_add_cashback', instance_name=instance_name))
            
            session = db_manager.get_session_for_instance(instance_name)
            success_count = 0
            errors = []
            
            try:
                for username, points_str in zip(usernames, points_list):
                    username = username.strip()
                    if not username:
                        continue
                    
                    try:
                        points = Decimal(str(points_str))
                        if points <= 0:
                            errors.append(f"Invalid points for {username}")
                            continue
                    except (ValueError, InvalidOperation):
                        errors.append(f"Invalid points format for {username}")
                        continue
                    
                    # Validate username
                    recipient = validate_username_exists(username, instance_name)
                    if not recipient:
                        errors.append(f"Username '{username}' not found")
                        continue
                    
                    # Create transaction
                    transaction = CashbackTransaction(
                        from_user_id=None,  # System/admin grant
                        to_user_id=recipient.id,
                        points=points,
                        transaction_type='unconditional',
                        notes=notes or f"Unconditional cashback granted by admin",
                        created_by_user_id=current_user.id
                    )
                    session.add(transaction)
                    success_count += 1
                
                session.commit()
                
                # Log admin action
                try:
                    from lms_logging import get_logging_manager
                    from lms_metrics import get_metrics_manager
                    logging_mgr = get_logging_manager(instance_name)
                    metrics_mgr = get_metrics_manager(instance_name)
                    
                    # Get list of usernames and amounts for logging
                    user_details = []
                    for username, points_str in zip(usernames, points_list):
                        username = username.strip()
                        if username:
                            try:
                                points = Decimal(str(points_str))
                                if points > 0:
                                    user_details.append({'username': username, 'points': float(points)})
                            except (ValueError, InvalidOperation):
                                pass
                    
                    logging_mgr.log_admin_action('cashback_add', 'cashback', None,
                                                username=current_user.username,
                                                details={
                                                    'users_count': success_count,
                                                    'users': user_details,
                                                    'notes': notes
                                                })
                    metrics_mgr.record_admin_action('cashback_add', current_user.username)
                except Exception as log_error:
                    print(f"[ERROR] Failed to log admin action: {log_error}")
                
                if success_count > 0:
                    flash(f'Successfully added cashback to {success_count} user(s)', 'success')
                if errors:
                    flash('Some errors occurred: ' + ', '.join(errors), 'error')
                
                return redirect(url_for('admin_cashback', instance_name=instance_name))
            except Exception as e:
                session.rollback()
                flash(f'Error adding cashback: {str(e)}', 'error')
                return redirect(url_for('admin_add_cashback', instance_name=instance_name))
        
        # GET request - show form
        # Only show user list to admins, not moderators
        all_users = None
        if current_user.is_admin:
            all_users = get_user_query().order_by(User.username).all()
        
        return render_template('admin/add_cashback.html',
                             all_users=all_users,
                             is_admin=current_user.is_admin,
                             instance_name=instance_name)

    @app.route('/<instance_name>/admin/cashback/remove', methods=['GET', 'POST'])
    @login_required
    def admin_remove_cashback(instance_name):
        """Admin remove cashback points from users"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        if request.method == 'POST':
            # Get all user entries from form
            usernames = request.form.getlist('username[]')
            points_list = request.form.getlist('points[]')
            notes = request.form.get('notes', '').strip()
            
            if not usernames or not any(usernames):
                flash('At least one user is required', 'error')
                return redirect(url_for('admin_remove_cashback', instance_name=instance_name))
            
            session = db_manager.get_session_for_instance(instance_name)
            success_count = 0
            errors = []
            
            # Get system user for deduction transactions
            system_user = get_user_query().filter_by(is_admin=True).first()
            if not system_user:
                flash('System user not found. Cannot remove cashback.', 'error')
                return redirect(url_for('admin_remove_cashback', instance_name=instance_name))
            
            try:
                for username, points_str in zip(usernames, points_list):
                    username = username.strip()
                    if not username:
                        continue
                    
                    try:
                        points = Decimal(str(points_str))
                        if points <= 0:
                            errors.append(f"Invalid points for {username} (must be positive)")
                            continue
                    except (ValueError, InvalidOperation):
                        errors.append(f"Invalid points format for {username}")
                        continue
                    
                    # Validate username
                    recipient = validate_username_exists(username, instance_name)
                    if not recipient:
                        errors.append(f"Username '{username}' not found")
                        continue
                    
                    # Check if user has sufficient balance
                    current_balance = get_user_cashback_balance(recipient.id, instance_name)
                    if current_balance < points:
                        errors.append(f"User '{username}' has insufficient balance (₹{current_balance:.2f} available, ₹{points:.2f} requested)")
                        continue
                    
                    # Create deduction transaction
                    # Use from_user_id=user_id, to_user_id=system_user_id with POSITIVE points to properly deduct from balance
                    transaction = CashbackTransaction(
                        from_user_id=recipient.id,  # User losing points
                        to_user_id=system_user.id,  # System user receiving points
                        points=points,  # Positive amount (deduction happens because balance = received - sent)
                        transaction_type='deduction',  # Admin deduction
                        notes=notes or f"Cashback points removed by admin",
                        created_by_user_id=current_user.id
                    )
                    session.add(transaction)
                    success_count += 1
                
                session.commit()
                
                # Log admin action
                try:
                    from lms_logging import get_logging_manager
                    from lms_metrics import get_metrics_manager
                    logging_mgr = get_logging_manager(instance_name)
                    metrics_mgr = get_metrics_manager(instance_name)
                    
                    # Get list of usernames and amounts for logging
                    user_details = []
                    for username, points_str in zip(usernames, points_list):
                        username = username.strip()
                        if username:
                            try:
                                points = Decimal(str(points_str))
                                if points > 0:
                                    user_details.append({'username': username, 'points': float(points)})
                            except (ValueError, InvalidOperation):
                                pass
                    
                    logging_mgr.log_admin_action('cashback_remove', 'cashback', None,
                                                username=current_user.username,
                                                details={
                                                    'users_count': success_count,
                                                    'users': user_details,
                                                    'notes': notes
                                                })
                    metrics_mgr.record_admin_action('cashback_remove', current_user.username)
                except Exception as log_error:
                    print(f"[ERROR] Failed to log admin action: {log_error}")
                
                if success_count > 0:
                    flash(f'Successfully removed cashback from {success_count} user(s)', 'success')
                if errors:
                    flash('Some errors occurred: ' + ', '.join(errors), 'error')
                
                return redirect(url_for('admin_cashback', instance_name=instance_name))
            except Exception as e:
                session.rollback()
                flash(f'Error removing cashback: {str(e)}', 'error')
                return redirect(url_for('admin_remove_cashback', instance_name=instance_name))
        
        # GET request - show form
        # Only show user list to admins, not moderators
        all_users = None
        user_balances_map = {}
        if current_user.is_admin:
            all_users = get_user_query().order_by(User.username).all()
            # Pre-calculate balances for display in dropdown
            for user in all_users:
                user_balances_map[user.id] = get_user_cashback_balance(user.id, instance_name)
        
        return render_template('admin/remove_cashback.html',
                             all_users=all_users,
                             user_balances_map=user_balances_map,
                             is_admin=current_user.is_admin,
                             instance_name=instance_name)

    @app.route('/<instance_name>/admin/loan/<int:loan_id>/cashback-config', methods=['GET', 'POST'])
    @login_required
    def admin_loan_cashback_config(instance_name, loan_id):
        """Admin configure cashback for a loan"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin and not current_user.is_moderator:
            flash('Access denied')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        loan = get_loan_query().filter_by(id=loan_id).first() or abort(404)
        
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'add':
                # Add new cashback config
                # For admins: user_id from dropdown, for moderators: username from text input
                user_id = request.form.get('user_id')
                username = request.form.get('username', '').strip()
                cashback_type = request.form.get('cashback_type')
                cashback_value = request.form.get('cashback_value')
                
                # Resolve user_id from username if moderator
                if not user_id and username:
                    user = validate_username_exists(username, instance_name)
                    if not user:
                        flash(f'User "{username}" not found', 'error')
                        return redirect(url_for('admin_loan_cashback_config', instance_name=instance_name, loan_id=loan_id))
                    user_id = user.id
                
                if not user_id or not cashback_type or not cashback_value:
                    flash('All fields are required', 'error')
                    return redirect(url_for('admin_loan_cashback_config', instance_name=instance_name, loan_id=loan_id))
                
                try:
                    cashback_value = Decimal(str(cashback_value))
                    if cashback_value <= 0:
                        flash('Cashback value must be greater than 0', 'error')
                        return redirect(url_for('admin_loan_cashback_config', instance_name=instance_name, loan_id=loan_id))
                    
                    # If percentage, ensure it's between 0 and 1
                    if cashback_type == 'percentage' and cashback_value > 1:
                        flash('Percentage must be between 0 and 1 (e.g., 0.05 for 5%)', 'error')
                        return redirect(url_for('admin_loan_cashback_config', instance_name=instance_name, loan_id=loan_id))
                    
                    session = db_manager.get_session_for_instance(instance_name)
                    config = LoanCashbackConfig(
                        loan_id=loan.id,
                        user_id=int(user_id),
                        cashback_type=cashback_type,
                        cashback_value=cashback_value,
                        is_active=True
                    )
                    session.add(config)
                    session.commit()
                    
                    flash('Cashback configuration added successfully', 'success')
                except (ValueError, InvalidOperation) as e:
                    flash(f'Invalid cashback value: {str(e)}', 'error')
                except Exception as e:
                    flash(f'Error adding configuration: {str(e)}', 'error')
            
            elif action == 'toggle':
                # Toggle active status
                config_id = request.form.get('config_id')
                try:
                    session = db_manager.get_session_for_instance(instance_name)
                    config = session.query(LoanCashbackConfig).filter_by(id=int(config_id)).first()
                    if config and config.loan_id == loan.id:
                        config.is_active = not config.is_active
                        session.commit()
                        flash('Configuration updated successfully', 'success')
                except Exception as e:
                    flash(f'Error updating configuration: {str(e)}', 'error')
            
            elif action == 'delete':
                # Delete config
                config_id = request.form.get('config_id')
                try:
                    session = db_manager.get_session_for_instance(instance_name)
                    config = session.query(LoanCashbackConfig).filter_by(id=int(config_id)).first()
                    if config and config.loan_id == loan.id:
                        session.delete(config)
                        session.commit()
                        flash('Configuration deleted successfully', 'success')
                except Exception as e:
                    flash(f'Error deleting configuration: {str(e)}', 'error')
            
            return redirect(url_for('admin_loan_cashback_config', instance_name=instance_name, loan_id=loan_id))
        
        # GET request - show configs
        configs = get_loan_cashback_config_query().filter_by(loan_id=loan.id).all()
        # Only show user list to admins, not moderators
        all_users = None
        if current_user.is_admin:
            all_users = get_user_query().order_by(User.username).all()
        
        return render_template('admin/loan_cashback_config.html',
                             loan=loan,
                             configs=configs,
                             all_users=all_users,
                             is_admin=current_user.is_admin,
                             instance_name=instance_name)

    @app.route('/<instance_name>/admin/cashback/redeem')
    @login_required
    def admin_cashback_redeem(instance_name):
        """Admin cashback redemption management page"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        # Get pending redemption requests
        pending_redemptions = get_cashback_redemption_query().filter_by(
            status='pending'
        ).order_by(CashbackRedemption.created_at.asc()).all()
        
        # Get all redemption requests for summary
        all_redemptions = get_cashback_redemption_query().order_by(CashbackRedemption.created_at.desc()).limit(50).all()
        
        # Calculate redemption statistics
        redemption_stats = {
            'pending': len(pending_redemptions),
            'completed': len([r for r in all_redemptions if r.status == 'completed']),
            'cancelled': len([r for r in all_redemptions if r.status == 'cancelled']),
            'total_pending_amount': sum(r.amount for r in pending_redemptions),
            'total_completed_amount': sum(r.amount for r in all_redemptions if r.status == 'completed'),
            'total_cancelled_amount': sum(r.amount for r in all_redemptions if r.status == 'cancelled')
        }
        
        # Get timezone for datetime formatting
        from lms_logging import get_logging_manager
        logging_mgr = get_logging_manager(instance_name)
        timezone_str = logging_mgr.get_config('system_timezone', 'Asia/Kolkata')
        
        return render_template('admin/cashback_redeem.html',
                             pending_redemptions=pending_redemptions,
                             all_redemptions=all_redemptions,
                             redemption_stats=redemption_stats,
                             logging_mgr=logging_mgr,
                             timezone_str=timezone_str,
                             instance_name=instance_name)

    @app.route('/<instance_name>/admin/cashback/redemption/<int:redemption_id>/process', methods=['GET', 'POST'])
    @login_required
    def admin_process_redemption(instance_name, redemption_id):
        """Admin process redemption request"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        redemption = get_cashback_redemption_query().filter_by(id=redemption_id).first()
        if not redemption:
            flash('Redemption request not found', 'error')
            return redirect(url_for('admin_cashback_redeem', instance_name=instance_name))
        
        if request.method == 'POST':
            action = request.form.get('action')  # 'complete' or 'cancel'
            admin_notes = request.form.get('admin_notes', '')
            
            if action == 'complete':
                # Check if redemption was already processed
                if redemption.status != 'pending':
                    flash('Redemption request has already been processed', 'error')
                    return redirect(url_for('admin_cashback_redeem', instance_name=instance_name))
                
                # Verify the original redemption transaction exists
                if not redemption.redemption_transaction_id:
                    flash('Original redemption transaction not found. Cannot complete.', 'error')
                    return redirect(url_for('admin_cashback_redeem', instance_name=instance_name))
                
                original_transaction = get_cashback_transaction_query().filter_by(
                    id=redemption.redemption_transaction_id
                ).first()
                
                if not original_transaction:
                    flash('Original redemption transaction not found. Cannot complete.', 'error')
                    return redirect(url_for('admin_cashback_redeem', instance_name=instance_name))
                
                redemption.status = 'completed'
                redemption.processed_by_user_id = current_user.id
                redemption.processed_at = datetime.utcnow()
                redemption.admin_notes = admin_notes
                commit_current_instance()
                
                # Log redemption completion
                try:
                    from lms_logging import get_logging_manager
                    logging_mgr = get_logging_manager(instance_name)
                    logging_mgr.log_admin_action('cashback_redemption_complete', 
                                               'cashback_redemption', 
                                               redemption.id,
                                               username=current_user.username,
                                               details={
                                                   'user': redemption.user.username,
                                                   'amount': float(redemption.amount),
                                                   'redemption_type': redemption.redemption_type,
                                                   'admin_notes': admin_notes
                                               })
                except Exception as log_error:
                    print(f"[ERROR] Failed to log redemption completion: {log_error}")
                
                flash('Redemption request completed successfully', 'success')
            elif action == 'cancel':
                # Check if redemption was already processed
                if redemption.status != 'pending':
                    flash('Redemption request has already been processed', 'error')
                    return redirect(url_for('admin_cashback_redeem', instance_name=instance_name))
                
                # Verify the original redemption transaction exists
                original_transaction = None
                if redemption.redemption_transaction_id:
                    original_transaction = get_cashback_transaction_query().filter_by(
                        id=redemption.redemption_transaction_id
                    ).first()
                
                if not original_transaction:
                    flash('Original redemption transaction not found. Cannot refund.', 'error')
                    return redirect(url_for('admin_cashback_redeem', instance_name=instance_name))
                
                redemption.status = 'cancelled'
                redemption.processed_by_user_id = current_user.id
                redemption.processed_at = datetime.utcnow()
                redemption.admin_notes = admin_notes
                
                # Refund points by creating a reverse transaction
                # Use from_user_id=None, to_user_id=user_id to properly add to balance
                # Balance = received - sent, so increasing 'received' increases balance
                session = db_manager.get_session_for_instance(instance_name)
                refund_transaction = CashbackTransaction(
                    from_user_id=None,  # System grant
                    to_user_id=redemption.user_id,
                    points=redemption.amount,  # Positive amount - increases 'received', which increases balance
                    transaction_type='redemption_refund',
                    notes=f"Refund for cancelled redemption request #{redemption.id}",
                    created_by_user_id=current_user.id
                )
                session.add(refund_transaction)
                session.commit()  # Commit both redemption status and refund transaction together
                
                # Log redemption cancellation
                try:
                    from lms_logging import get_logging_manager
                    logging_mgr = get_logging_manager(instance_name)
                    logging_mgr.log_admin_action('cashback_redemption_cancel', 
                                               'cashback_redemption', 
                                               redemption.id,
                                               username=current_user.username,
                                               details={
                                                   'user': redemption.user.username,
                                                   'amount': float(redemption.amount),
                                                   'redemption_type': redemption.redemption_type,
                                                   'admin_notes': admin_notes,
                                                   'refunded': True
                                               })
                except Exception as log_error:
                    print(f"[ERROR] Failed to log redemption cancellation: {log_error}")
                
                flash('Redemption request cancelled and points refunded', 'success')
            
            return redirect(url_for('admin_cashback_redeem', instance_name=instance_name))
        
        return render_template('admin/process_redemption.html',
                             redemption=redemption,
                             instance_name=instance_name)

    @app.route('/<instance_name>/admin/user/<int:user_id>/cashback-history')
    @login_required
    def admin_user_cashback_history(instance_name, user_id):
        """Admin view cashback history for a specific user"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        user = get_user_query().filter_by(id=user_id).first() or abort(404)
        
        # Get user's balance
        balance = get_user_cashback_balance(user.id, instance_name)
        
        # Get transaction history with filters
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        transaction_type = request.args.get('type', '')
        from_user_filter = request.args.get('from_user', '').strip()
        to_user_filter = request.args.get('to_user', '').strip()
        
        query = get_cashback_transaction_query().filter(
            (CashbackTransaction.from_user_id == user.id) |
            (CashbackTransaction.to_user_id == user.id)
        )
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(CashbackTransaction.created_at >= date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(CashbackTransaction.created_at < date_to_obj)
            except ValueError:
                pass
        
        if transaction_type:
            query = query.filter_by(transaction_type=transaction_type)
        
        # Filter by from_user
        if from_user_filter:
            from_user_obj = get_user_query().filter(User.username.contains(from_user_filter)).first()
            if from_user_obj:
                query = query.filter(CashbackTransaction.from_user_id == from_user_obj.id)
        
        # Filter by to_user
        if to_user_filter:
            to_user_obj = get_user_query().filter(User.username.contains(to_user_filter)).first()
            if to_user_obj:
                query = query.filter(CashbackTransaction.to_user_id == to_user_obj.id)
        
        transactions = query.order_by(CashbackTransaction.created_at.desc()).all()
        
        # Get all transaction types for filter
        all_types = get_cashback_transaction_query().with_entities(
            CashbackTransaction.transaction_type
        ).distinct().all()
        all_types = [t[0] for t in all_types]
        
        return render_template('admin/user_cashback_history.html',
                             user=user,
                             balance=balance,
                             transactions=transactions,
                             date_from=date_from,
                             date_to=date_to,
                             transaction_type=transaction_type,
                             from_user_filter=from_user_filter,
                             to_user_filter=to_user_filter,
                             all_types=all_types,
                             instance_name=instance_name)

    @app.route('/<instance_name>/admin/daily-trackers/<int:tracker_id>/cashback-config', methods=['GET', 'POST'])
    @login_required
    def admin_tracker_cashback_config(instance_name, tracker_id):
        """Admin configure cashback for a tracker"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin and not current_user.is_moderator:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        tracker = get_daily_tracker_query().filter_by(id=tracker_id).first()
        if not tracker:
            flash('Tracker not found', 'error')
            return redirect(url_for('admin_daily_trackers', instance_name=instance_name))
        
        if request.method == 'POST':
            # Handle deletion
            delete_ids = request.form.getlist('delete_config[]')
            if delete_ids:
                session = db_manager.get_session_for_instance(instance_name)
                for config_id in delete_ids:
                    config = get_tracker_cashback_config_query().filter_by(id=int(config_id)).first()
                    if config:
                        config.is_active = False
                session.commit()
            
            # Handle new/updated configs
            usernames = request.form.getlist('username[]')
            cashback_types = request.form.getlist('cashback_type[]')
            cashback_values = request.form.getlist('cashback_value[]')
            
            session = db_manager.get_session_for_instance(instance_name)
            
            for username, cashback_type, cashback_value_str in zip(usernames, cashback_types, cashback_values):
                username = username.strip()
                if not username:
                    continue
                
                try:
                    cashback_value = Decimal(str(cashback_value_str))
                    if cashback_value <= 0:
                        continue
                except (ValueError, InvalidOperation):
                    continue
                
                user = validate_username_exists(username, instance_name)
                if not user:
                    continue
                
                # Check if config already exists
                existing_config = get_tracker_cashback_config_query().filter_by(
                    tracker_id=tracker_id,
                    user_id=user.id,
                    is_active=True
                ).first()
                
                if existing_config:
                    existing_config.cashback_type = cashback_type
                    existing_config.cashback_value = cashback_value
                else:
                    new_config = TrackerCashbackConfig(
                        tracker_id=tracker_id,
                        user_id=user.id,
                        cashback_type=cashback_type,
                        cashback_value=cashback_value
                    )
                    session.add(new_config)
            
            session.commit()
            flash('Cashback configuration updated successfully', 'success')
            return redirect(url_for('admin_tracker_cashback_config', instance_name=instance_name, tracker_id=tracker_id))
        
        # GET request - show current configs
        cashback_configs = get_tracker_cashback_config_query().filter_by(
            tracker_id=tracker_id,
            is_active=True
        ).all()
        
        return render_template('admin/tracker_cashback_config.html',
                             tracker=tracker,
                             cashback_configs=cashback_configs,
                             instance_name=instance_name)

    # User Cashback Routes
    @app.route('/<instance_name>/cashback')
    @login_required
    def user_cashback(instance_name):
        """User cashback page with balance, history, and transfer form"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        # Get user's balance
        balance = get_user_cashback_balance(current_user.id, instance_name)
        
        # Get all transactions for summary calculations
        all_transactions = get_cashback_transaction_query().filter(
            (CashbackTransaction.from_user_id == current_user.id) |
            (CashbackTransaction.to_user_id == current_user.id)
        ).all()
        
        # Calculate summary statistics
        total_earned = Decimal('0')
        total_transferred = Decimal('0')
        total_redeemed = Decimal('0')
        
        for txn in all_transactions:
            if txn.to_user_id == current_user.id and txn.from_user_id != current_user.id:
                # Received cashback (earned)
                if txn.transaction_type != 'redemption' and txn.transaction_type != 'redemption_refund':
                    total_earned += txn.points
            elif txn.from_user_id == current_user.id and txn.to_user_id != current_user.id:
                # Sent cashback (transferred)
                if txn.transaction_type == 'transfer':
                    total_transferred += txn.points
            elif txn.transaction_type == 'redemption' and txn.from_user_id == current_user.id:
                # Redeemed
                total_redeemed += txn.points
        
        # Get transaction history with filters
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        transaction_type = request.args.get('type', '')
        
        query = get_cashback_transaction_query().filter(
            (CashbackTransaction.from_user_id == current_user.id) |
            (CashbackTransaction.to_user_id == current_user.id)
        )
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(CashbackTransaction.created_at >= date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(CashbackTransaction.created_at < date_to_obj)
            except ValueError:
                pass
        
        if transaction_type:
            query = query.filter_by(transaction_type=transaction_type)
        
        transactions = query.order_by(CashbackTransaction.created_at.desc()).limit(100).all()
        
        # Get all transaction types for filter
        all_types = get_cashback_transaction_query().with_entities(
            CashbackTransaction.transaction_type
        ).distinct().all()
        all_types = [t[0] for t in all_types]
        
        # Get timezone for datetime formatting
        from lms_logging import get_logging_manager
        logging_mgr = get_logging_manager(instance_name)
        timezone_str = logging_mgr.get_config('system_timezone', 'Asia/Kolkata')
        
        return render_template('cashback.html',
                             balance=balance,
                             total_earned=float(total_earned),
                             total_transferred=float(total_transferred),
                             total_redeemed=float(total_redeemed),
                             transactions=transactions,
                             date_from=date_from,
                             date_to=date_to,
                             transaction_type=transaction_type,
                             all_types=all_types,
                             logging_mgr=logging_mgr,
                             timezone_str=timezone_str,
                             instance_name=instance_name)

    @app.route('/<instance_name>/cashback/transfer', methods=['POST'])
    @login_required
    def user_cashback_transfer(instance_name):
        """Transfer cashback points to another user"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if request.is_json:
            data = request.get_json()
            recipient_username = data.get('username', '').strip()
            points = data.get('points', '0')
        else:
            recipient_username = request.form.get('username', '').strip()
            points = request.form.get('points', '0')
        
        if not recipient_username:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Username is required'}), 400
            flash('Username is required', 'error')
            return redirect(url_for('user_cashback', instance_name=instance_name))
        
        try:
            points = Decimal(str(points))
            if points <= 0:
                if request.is_json:
                    return jsonify({'success': False, 'error': 'Points must be greater than 0'}), 400
                flash('Points must be greater than 0', 'error')
                return redirect(url_for('user_cashback', instance_name=instance_name))
        except (ValueError, InvalidOperation):
            if request.is_json:
                return jsonify({'success': False, 'error': 'Invalid points amount'}), 400
            flash('Invalid points amount', 'error')
            return redirect(url_for('user_cashback', instance_name=instance_name))
        
        # Validate recipient username exists
        recipient = validate_username_exists(recipient_username, instance_name)
        if not recipient:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Username not found'}), 404
            flash('Username not found', 'error')
            return redirect(url_for('user_cashback', instance_name=instance_name))
        
        if recipient.id == current_user.id:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Cannot transfer to yourself'}), 400
            flash('Cannot transfer to yourself', 'error')
            return redirect(url_for('user_cashback', instance_name=instance_name))
        
        # Check balance
        balance = get_user_cashback_balance(current_user.id, instance_name)
        if balance < points:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Insufficient balance'}), 400
            flash('Insufficient balance', 'error')
            return redirect(url_for('user_cashback', instance_name=instance_name))
        
        # Create transaction
        try:
            session = db_manager.get_session_for_instance(instance_name)
            transaction = CashbackTransaction(
                from_user_id=current_user.id,
                to_user_id=recipient.id,
                points=points,
                transaction_type='transfer',
                notes=f"Transfer from {current_user.username} to {recipient.username}",
                created_by_user_id=current_user.id
            )
            session.add(transaction)
            session.commit()
            
            # Log the transfer
            try:
                from lms_logging import get_logging_manager
                logging_mgr = get_logging_manager(instance_name)
                logging_mgr.log_activity('cashback_transfer', 
                                        username=current_user.username,
                                        details={'recipient': recipient_username, 'points': float(points)})
            except Exception as log_error:
                print(f"[ERROR] Failed to log cashback transfer: {log_error}")
            
            if request.is_json:
                return jsonify({'success': True, 'message': f'Transferred {points} points to {recipient_username}'})
            flash(f'Successfully transferred {points} points to {recipient_username}', 'success')
            return redirect(url_for('user_cashback', instance_name=instance_name))
        except Exception as e:
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 500
            flash(f'Error transferring points: {str(e)}', 'error')
            return redirect(url_for('user_cashback', instance_name=instance_name))

    @app.route('/<instance_name>/cashback/redeem', methods=['GET', 'POST'])
    @login_required
    def user_cashback_redeem(instance_name):
        """User request cashback redemption"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        balance = get_user_cashback_balance(current_user.id, instance_name)
        
        if request.method == 'POST':
            amount = request.form.get('amount', '0')
            redemption_type = request.form.get('redemption_type', '')
            payment_method_id = request.form.get('payment_method_id', '')
            
            try:
                amount = Decimal(str(amount))
                if amount <= 0:
                    flash('Amount must be greater than 0', 'error')
                    return redirect(url_for('user_cashback_redeem', instance_name=instance_name))
                
                if amount > balance:
                    flash('Insufficient balance', 'error')
                    return redirect(url_for('user_cashback_redeem', instance_name=instance_name))
                
                # Validate Amazon gift card multiples of 500
                if redemption_type == 'amazon_gift_card':
                    if amount % 500 != 0:
                        flash('Amazon gift card amount must be in multiples of ₹500', 'error')
                        return redirect(url_for('user_cashback_redeem', instance_name=instance_name))
            except (ValueError, InvalidOperation):
                flash('Invalid amount', 'error')
                return redirect(url_for('user_cashback_redeem', instance_name=instance_name))
            
            if not redemption_type:
                flash('Please select a redemption type', 'error')
                return redirect(url_for('user_cashback_redeem', instance_name=instance_name))
            
            # Get payment details
            payment_method = None
            account_name = request.form.get('account_name', '')
            account_number = request.form.get('account_number', '')
            ifsc_code = request.form.get('ifsc_code', '')
            bank_name = request.form.get('bank_name', '')
            upi_id = request.form.get('upi_id', '')
            gpay_id = request.form.get('gpay_id', '')
            phone_number = request.form.get('phone_number', '')
            address = request.form.get('address', '')
            
            # If payment_method_id is provided, use saved payment method
            if payment_method_id:
                payment_method = get_user_payment_method_query().filter_by(
                    id=int(payment_method_id),
                    user_id=current_user.id
                ).first()
                
                if payment_method:
                    account_name = payment_method.account_name or account_name
                    account_number = payment_method.account_number or account_number
                    ifsc_code = payment_method.ifsc_code or ifsc_code
                    bank_name = payment_method.bank_name or bank_name
                    upi_id = payment_method.upi_id or upi_id
                    gpay_id = payment_method.gpay_id or gpay_id
                    phone_number = payment_method.phone_number or phone_number
                    address = payment_method.address or address
            
            # Create cashback transaction to deduct points FIRST (before creating redemption)
            # Use from_user_id=user_id, to_user_id=system_user_id with POSITIVE points to properly deduct from balance
            # Balance = received - sent, so increasing 'sent' decreases balance
            # We need a system user for to_user_id (NOT NULL constraint)
            session = db_manager.get_session_for_instance(instance_name)
            
            # Get or use first admin as system user for redemption transactions
            system_user = get_user_query().filter_by(is_admin=True).first()
            if not system_user:
                flash('System error: No admin user found for processing redemption', 'error')
                return redirect(url_for('user_cashback_redeem', instance_name=instance_name))
            
            redemption_transaction = CashbackTransaction(
                from_user_id=current_user.id,
                to_user_id=system_user.id,  # System user for redemption deduction
                points=amount,  # Positive amount - increases 'sent', which decreases balance
                transaction_type='redemption',
                notes=f"Redemption request: {redemption_type}",
                created_by_user_id=current_user.id
            )
            session.add(redemption_transaction)
            session.flush()  # Get the ID to link to redemption
            
            # Create redemption request and link to transaction
            redemption = CashbackRedemption(
                user_id=current_user.id,
                amount=amount,
                redemption_type=redemption_type,
                payment_method_id=payment_method.id if payment_method else None,
                account_name=account_name,
                account_number=account_number,
                ifsc_code=ifsc_code,
                bank_name=bank_name,
                upi_id=upi_id,
                gpay_id=gpay_id,
                phone_number=phone_number,
                address=address,
                status='pending',
                redemption_transaction_id=redemption_transaction.id
            )
            session.add(redemption)
            session.commit()  # Commit both transaction and redemption together
            
            # Log redemption request
            try:
                from lms_logging import get_logging_manager
                logging_mgr = get_logging_manager(instance_name)
                logging_mgr.log_activity('cashback_redemption', 
                                        username=current_user.username,
                                        user_id=current_user.id,
                                        resource_type='cashback_redemption',
                                        resource_id=redemption.id,
                                        details={
                                            'amount': float(amount),
                                            'redemption_type': redemption_type,
                                            'status': 'pending'
                                        })
            except Exception as log_error:
                print(f"[ERROR] Failed to log cashback redemption: {log_error}")
            
            flash('Redemption request submitted successfully', 'success')
            return redirect(url_for('user_cashback', instance_name=instance_name))
        
        # GET request - show redemption form
        payment_methods = get_user_payment_method_query().filter_by(
            user_id=current_user.id
        ).all()
        
        return render_template('cashback_redeem.html',
                             balance=balance,
                             payment_methods=payment_methods,
                             instance_name=instance_name)

    @app.route('/<instance_name>/cashback/payment-methods', methods=['GET', 'POST'])
    @login_required
    def user_payment_methods(instance_name):
        """User manage payment methods"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'add':
                payment_type = request.form.get('payment_type', '')
                account_name = request.form.get('account_name', '')
                account_number = request.form.get('account_number', '')
                ifsc_code = request.form.get('ifsc_code', '')
                bank_name = request.form.get('bank_name', '')
                upi_id = request.form.get('upi_id', '')
                gpay_id = request.form.get('gpay_id', '')
                phone_number = request.form.get('phone_number', '')
                address = request.form.get('address', '')
                is_default = request.form.get('is_default') == 'on'
                
                # If setting as default, unset other defaults
                if is_default:
                    existing_defaults = get_user_payment_method_query().filter_by(
                        user_id=current_user.id,
                        is_default=True
                    ).all()
                    for pm in existing_defaults:
                        pm.is_default = False
                
                payment_method = UserPaymentMethod(
                    user_id=current_user.id,
                    payment_type=payment_type,
                    account_name=account_name,
                    account_number=account_number,
                    ifsc_code=ifsc_code,
                    bank_name=bank_name,
                    upi_id=upi_id,
                    gpay_id=gpay_id,
                    phone_number=phone_number,
                    address=address,
                    is_default=is_default
                )
                add_to_current_instance(payment_method)
                commit_current_instance()
                flash('Payment method added successfully', 'success')
            
            elif action == 'delete':
                method_id = request.form.get('method_id')
                if method_id:
                    payment_method = get_user_payment_method_query().filter_by(
                        id=int(method_id),
                        user_id=current_user.id
                    ).first()
                    if payment_method:
                        db_manager.get_session_for_instance(instance_name).delete(payment_method)
                        commit_current_instance()
                        flash('Payment method deleted successfully', 'success')
            
            elif action == 'set_default':
                method_id = request.form.get('method_id')
                if method_id:
                    # Unset all defaults
                    existing_defaults = get_user_payment_method_query().filter_by(
                        user_id=current_user.id,
                        is_default=True
                    ).all()
                    for pm in existing_defaults:
                        pm.is_default = False
                    
                    # Set new default
                    payment_method = get_user_payment_method_query().filter_by(
                        id=int(method_id),
                        user_id=current_user.id
                    ).first()
                    if payment_method:
                        payment_method.is_default = True
                        commit_current_instance()
                        flash('Default payment method updated', 'success')
            
            return redirect(url_for('user_payment_methods', instance_name=instance_name))
        
        payment_methods = get_user_payment_method_query().filter_by(
            user_id=current_user.id
        ).order_by(UserPaymentMethod.is_default.desc(), UserPaymentMethod.created_at.desc()).all()
        
        return render_template('payment_methods.html',
                             payment_methods=payment_methods,
                             instance_name=instance_name)

    @app.route('/<instance_name>/cashback/redemptions')
    @login_required
    def user_cashback_redemptions(instance_name):
        """User view redemption history"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        redemptions = get_cashback_redemption_query().filter_by(
            user_id=current_user.id
        ).order_by(CashbackRedemption.created_at.desc()).all()
        
        # Get timezone for datetime formatting
        from lms_logging import get_logging_manager
        logging_mgr = get_logging_manager(instance_name)
        timezone_str = logging_mgr.get_config('system_timezone', 'Asia/Kolkata')
        
        return render_template('cashback_redemptions.html',
                             redemptions=redemptions,
                             logging_mgr=logging_mgr,
                             timezone_str=timezone_str,
                             instance_name=instance_name)


# Import helper functions from app_multi (they're used by non-cashback routes too)
# These will be set when register_cashback_routes is called
get_user_cashback_balance_func = None
get_loan_cashback_total_func = None
get_tracker_cashback_total_func = None
get_tracker_day_cashback_func = None
get_payment_cashback_total_func = None
process_loan_cashback_func = None
validate_username_exists_func = None


def register_cashback_routes(flask_app, flask_db, valid_instances, default_instance,
                            user_model, loan_model, tracker_model, payment_model,
                            cashback_transaction_model, loan_cashback_config_model,
                            tracker_cashback_config_model, user_payment_method_model,
                            cashback_redemption_model,
                            user_query_func, loan_query_func, tracker_query_func, payment_query_func,
                            cashback_transaction_query_func, loan_cashback_config_query_func,
                            tracker_cashback_config_query_func, user_payment_method_query_func,
                            cashback_redemption_query_func,
                            add_instance_func, commit_instance_func,
                            get_current_instance_func, db_manager_instance,
                            get_user_cashback_balance_helper,
                            get_loan_cashback_total_helper,
                            get_tracker_cashback_total_helper,
                            get_tracker_day_cashback_helper,
                            get_payment_cashback_total_helper,
                            process_loan_cashback_helper,
                            validate_username_exists_helper):
    """Register cashback routes with Flask app"""
    global app, db, VALID_INSTANCES, DEFAULT_INSTANCE
    global User, Loan, DailyTracker, Payment
    global CashbackTransaction, LoanCashbackConfig, TrackerCashbackConfig
    global UserPaymentMethod, CashbackRedemption
    global get_user_query, get_loan_query, get_daily_tracker_query, get_payment_query
    global get_cashback_transaction_query, get_loan_cashback_config_query
    global get_tracker_cashback_config_query, get_user_payment_method_query
    global get_cashback_redemption_query
    global add_to_current_instance, commit_current_instance
    global get_current_instance_from_g, db_manager
    global get_user_cashback_balance_func, get_loan_cashback_total_func
    global get_tracker_cashback_total_func, get_tracker_day_cashback_func
    global get_payment_cashback_total_func, process_loan_cashback_func
    global validate_username_exists_func
    
    app = flask_app
    db = flask_db
    VALID_INSTANCES = valid_instances
    DEFAULT_INSTANCE = default_instance
    User = user_model
    Loan = loan_model
    DailyTracker = tracker_model
    Payment = payment_model
    CashbackTransaction = cashback_transaction_model
    LoanCashbackConfig = loan_cashback_config_model
    TrackerCashbackConfig = tracker_cashback_config_model
    UserPaymentMethod = user_payment_method_model
    CashbackRedemption = cashback_redemption_model
    get_user_query = user_query_func
    get_loan_query = loan_query_func
    get_daily_tracker_query = tracker_query_func
    get_payment_query = payment_query_func
    get_cashback_transaction_query = cashback_transaction_query_func
    get_loan_cashback_config_query = loan_cashback_config_query_func
    get_tracker_cashback_config_query = tracker_cashback_config_query_func
    get_user_payment_method_query = user_payment_method_query_func
    get_cashback_redemption_query = cashback_redemption_query_func
    add_to_current_instance = add_instance_func
    commit_current_instance = commit_instance_func
    get_current_instance_from_g = get_current_instance_func
    db_manager = db_manager_instance
    get_user_cashback_balance_func = get_user_cashback_balance_helper
    get_loan_cashback_total_func = get_loan_cashback_total_helper
    get_tracker_cashback_total_func = get_tracker_cashback_total_helper
    get_tracker_day_cashback_func = get_tracker_day_cashback_helper
    get_payment_cashback_total_func = get_payment_cashback_total_helper
    process_loan_cashback_func = process_loan_cashback_helper
    validate_username_exists_func = validate_username_exists_helper
    
    # Register routes
    register_routes()


# Cashback helper functions (wrappers that call functions from app_multi)
def get_user_cashback_balance(user_id, instance_name):
    """Calculate user's cashback balance from transactions"""
    return get_user_cashback_balance_func(user_id, instance_name)

def validate_username_exists(username, instance_name):
    """Check if username exists and return user object or None"""
    return validate_username_exists_func(username, instance_name)

def get_tracker_cashback_total(tracker_id, instance_name):
    """Calculate total cashback points given for a tracker"""
    return get_tracker_cashback_total_func(tracker_id, instance_name)

def get_tracker_day_cashback(tracker_id, day, instance_name):
    """Calculate cashback points given for a specific tracker day"""
    return get_tracker_day_cashback_func(tracker_id, day, instance_name)

def get_loan_cashback_total(loan_id, instance_name):
    """Calculate total cashback points given for a loan"""
    return get_loan_cashback_total_func(loan_id, instance_name)

def get_payment_cashback_total(payment_id, instance_name):
    """Get total cashback given for a specific payment"""
    return get_payment_cashback_total_func(payment_id, instance_name)

def process_loan_cashback(loan, payment, instance_name, created_by_user_id):
    """Process automatic cashback for a loan payment based on LoanCashbackConfig"""
    return process_loan_cashback_func(loan, payment, instance_name, created_by_user_id)



