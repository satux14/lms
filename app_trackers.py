"""
Tracker Routes Module
=====================

This module handles all tracker-related functionality including:
- Daily tracker management (admin and customer)
- Tracker entry approval
- Tracker cashback configuration
"""

from flask import request, redirect, url_for, flash, render_template, send_from_directory, g
from flask_login import login_required, current_user
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from pathlib import Path
import sys
import json
import os

# Import from app_multi - these will be set when register_tracker_routes is called
app = None
db = None

# These will be imported from app_multi
VALID_INSTANCES = None
DEFAULT_INSTANCE = None
DailyTracker = None
TrackerEntry = None
TrackerCashbackConfig = None
User = None
CashbackTransaction = None
get_daily_tracker_query = None
get_tracker_entry_query = None
get_tracker_cashback_config_query = None
get_user_query = None
get_cashback_transaction_query = None
add_to_current_instance = None
commit_current_instance = None
get_current_instance_from_g = None
db_manager = None
validate_username_exists = None
get_user_cashback_balance = None

# Tracker manager functions
create_tracker_file = None
get_tracker_data = None
update_tracker_entry = None
get_tracker_summary = None
TRACKER_TYPES = None
get_tracker_directory = None


def register_tracker_routes(flask_app, flask_db, valid_instances, default_instance,
                           tracker_model, tracker_entry_model, tracker_cashback_config_model,
                           user_model, cashback_transaction_model,
                           tracker_query_func, tracker_entry_query_func, tracker_cashback_config_query_func,
                           user_query_func, cashback_transaction_query_func,
                           add_instance_func, commit_instance_func, get_current_instance_func,
                           db_manager_instance, validate_username_exists_helper, get_user_cashback_balance_helper,
                           create_tracker_file_func, get_tracker_data_func, update_tracker_entry_func,
                           get_tracker_summary_func, tracker_types, get_tracker_directory_func):
    """Register tracker routes with Flask app"""
    global app, db, VALID_INSTANCES, DEFAULT_INSTANCE
    global DailyTracker, TrackerEntry, TrackerCashbackConfig, User, CashbackTransaction
    global get_daily_tracker_query, get_tracker_entry_query, get_tracker_cashback_config_query
    global get_user_query, get_cashback_transaction_query
    global add_to_current_instance, commit_current_instance, get_current_instance_from_g
    global db_manager, validate_username_exists, get_user_cashback_balance
    global create_tracker_file, get_tracker_data, update_tracker_entry, get_tracker_summary
    global TRACKER_TYPES, get_tracker_directory
    
    app = flask_app
    db = flask_db
    VALID_INSTANCES = valid_instances
    DEFAULT_INSTANCE = default_instance
    DailyTracker = tracker_model
    TrackerEntry = tracker_entry_model
    TrackerCashbackConfig = tracker_cashback_config_model
    User = user_model
    CashbackTransaction = cashback_transaction_model
    get_daily_tracker_query = tracker_query_func
    get_tracker_entry_query = tracker_entry_query_func
    get_tracker_cashback_config_query = tracker_cashback_config_query_func
    get_user_query = user_query_func
    get_cashback_transaction_query = cashback_transaction_query_func
    add_to_current_instance = add_instance_func
    commit_current_instance = commit_instance_func
    get_current_instance_from_g = get_current_instance_func
    db_manager = db_manager_instance
    validate_username_exists = validate_username_exists_helper
    get_user_cashback_balance = get_user_cashback_balance_helper
    create_tracker_file = create_tracker_file_func
    get_tracker_data = get_tracker_data_func
    update_tracker_entry = update_tracker_entry_func
    get_tracker_summary = get_tracker_summary_func
    TRACKER_TYPES = tracker_types
    get_tracker_directory = get_tracker_directory_func
    
    # Register routes
    register_routes()


def get_tracker_cashback_total(tracker_id, instance_name):
    """Calculate total cashback points given for a tracker"""
    try:
        session = db_manager.get_session_for_instance(instance_name)
        total = session.query(
            db.func.sum(CashbackTransaction.points)
        ).filter_by(
            related_tracker_id=tracker_id,
            transaction_type='tracker_entry'
        ).scalar() or Decimal('0')
        return total
    except Exception as e:
        print(f"Error calculating tracker cashback total: {e}")
        return Decimal('0')


def get_tracker_day_cashback(tracker_id, day, instance_name):
    """Calculate cashback points given for a specific tracker day"""
    try:
        session = db_manager.get_session_for_instance(instance_name)
        total = session.query(
            db.func.sum(CashbackTransaction.points)
        ).filter_by(
            related_tracker_id=tracker_id,
            related_tracker_entry_day=day,
            transaction_type='tracker_entry'
        ).scalar() or Decimal('0')
        return total
    except Exception as e:
        print(f"Error calculating tracker day cashback: {e}")
        return Decimal('0')


def register_routes():
    """Register all tracker routes"""
    
    # Admin Tracker Routes
    @app.route('/<instance_name>/admin/daily-trackers')
    @login_required
    def admin_daily_trackers(instance_name):
        """Admin view all daily trackers"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        # Get filter parameters
        filter_user_id = request.args.get('user_id', type=int)
        filter_status = request.args.get('status', '')
        filter_tracker_name = request.args.get('tracker_name', '')
        filter_per_day_payment = request.args.get('per_day_payment', type=float)
        filter_pending_min = request.args.get('pending_min', type=float)
        filter_pending_max = request.args.get('pending_max', type=float)
        
        # Base query
        query = get_daily_tracker_query().filter_by(is_active=True)
        
        # Apply filters
        if filter_user_id:
            query = query.filter_by(user_id=filter_user_id)
        
        if filter_tracker_name:
            query = query.filter(DailyTracker.tracker_name.ilike(f'%{filter_tracker_name}%'))
        
        if filter_per_day_payment:
            query = query.filter(DailyTracker.per_day_payment == filter_per_day_payment)
        
        trackers = query.all()
        
        # Get summary data for each tracker
        tracker_summaries = []
        total_trackers = 0
        total_payments_sum = 0
        total_pending_sum = 0
        total_cashback = Decimal('0')
        
        for tracker in trackers:
            try:
                summary = get_tracker_summary(instance_name, tracker.filename)
                
                # Apply status filter
                if filter_status:
                    if filter_status == 'active' and tracker.is_closed_by_user:
                        continue
                    elif filter_status == 'closed' and not tracker.is_closed_by_user:
                        continue
                
                # Apply pending filter
                pending = summary.get('pending', 0)
                if filter_pending_min is not None and pending < filter_pending_min:
                    continue
                if filter_pending_max is not None and pending > filter_pending_max:
                    continue
                
                # Calculate cashback total for this tracker
                tracker_cashback = get_tracker_cashback_total(tracker.id, instance_name)
                
                tracker_summaries.append({
                    'tracker': tracker,
                    'summary': summary,
                    'pending': pending,
                    'total_payments': summary.get('total_payments', 0),
                    'days_with_payments': summary.get('total_days', 0),
                    'total_days_count': summary.get('total_days_count', 0),
                    'cashback_total': tracker_cashback
                })
                
                total_trackers += 1
                total_payments_sum += summary.get('total_payments', 0)
                total_pending_sum += pending
                total_cashback += tracker_cashback
                
            except Exception as e:
                # If we can't read the tracker, still include it with error
                tracker_cashback = get_tracker_cashback_total(tracker.id, instance_name)
                total_cashback += tracker_cashback
                tracker_summaries.append({
                    'tracker': tracker,
                    'summary': {},
                    'pending': 0,
                    'total_payments': 0,
                    'days_with_payments': 0,
                    'total_days_count': 0,
                    'cashback_total': tracker_cashback,
                    'error': str(e)
                })
        
        # Get users for dropdown
        users = get_user_query().filter_by(is_admin=False).all()
        
        return render_template('admin/daily_trackers.html', 
                             tracker_summaries=tracker_summaries,
                             total_trackers=total_trackers,
                             total_payments_sum=total_payments_sum,
                             total_pending_sum=total_pending_sum,
                             total_cashback=total_cashback,
                             users=users,
                             instance_name=instance_name,
                             tracker_types=TRACKER_TYPES,
                             filters={
                                 'user_id': filter_user_id,
                                 'status': filter_status,
                                 'tracker_name': filter_tracker_name,
                                 'per_day_payment': filter_per_day_payment,
                                 'pending_min': filter_pending_min,
                                 'pending_max': filter_pending_max
                             })


    @app.route('/<instance_name>/admin/daily-trackers/create', methods=['GET', 'POST'])
    @login_required
    def admin_create_daily_tracker(instance_name):
        """Admin create new daily tracker"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        if request.method == 'POST':
            try:
                user_id = int(request.form['user_id'])
                tracker_name = request.form['tracker_name']
                tracker_type = request.form['tracker_type']
                investment = Decimal(request.form['investment'])
                scheme_period = int(request.form['scheme_period'])
                per_day_payment = Decimal(request.form['per_day_payment'])
                start_date_str = request.form['start_date']
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                
                # Validate tracker type
                if tracker_type not in TRACKER_TYPES:
                    flash('Invalid tracker type', 'error')
                    users = get_user_query().filter_by(is_admin=False).all()
                    return render_template('admin/create_daily_tracker.html',
                                         users=users,
                                         instance_name=instance_name,
                                         tracker_types=TRACKER_TYPES)
                
                # Get user
                user = get_user_query().filter_by(id=user_id).first()
                if not user:
                    flash('User not found', 'error')
                    users = get_user_query().filter_by(is_admin=False).all()
                    return render_template('admin/create_daily_tracker.html',
                                         users=users,
                                         instance_name=instance_name,
                                         tracker_types=TRACKER_TYPES)
                
                # Create Excel file
                filename = create_tracker_file(
                    instance_name,
                    user.username,
                    tracker_name,
                    tracker_type,
                    investment,
                    scheme_period,
                    start_date,
                    per_day_payment
                )
                
                # Create database entry
                tracker = DailyTracker(
                    user_id=user_id,
                    tracker_name=tracker_name,
                    tracker_type=tracker_type,
                    investment=investment,
                    scheme_period=scheme_period,
                    per_day_payment=per_day_payment,
                    start_date=start_date,
                    filename=filename
                )
                
                add_to_current_instance(tracker)
                commit_current_instance()
                
                flash(f'Daily tracker created successfully for {user.username}', 'success')
                return redirect(url_for('admin_daily_trackers', instance_name=instance_name))
                
            except Exception as e:
                flash(f'Error creating daily tracker: {str(e)}', 'error')
                print(f"Error creating daily tracker: {e}")
        
        # GET request
        users = get_user_query().filter_by(is_admin=False).all()
        return render_template('admin/create_daily_tracker.html',
                             users=users,
                             instance_name=instance_name,
                             tracker_types=TRACKER_TYPES)


    @app.route('/<instance_name>/admin/daily-trackers/<int:tracker_id>')
    @login_required
    def admin_view_daily_tracker(instance_name, tracker_id):
        """Admin view a specific daily tracker"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        tracker = get_daily_tracker_query().filter_by(id=tracker_id, is_active=True).first()
        if not tracker:
            flash('Tracker not found', 'error')
            return redirect(url_for('admin_daily_trackers', instance_name=instance_name))
        
        try:
            # Get tracker data from Excel
            tracker_data = get_tracker_data(instance_name, tracker.filename)
            summary = get_tracker_summary(instance_name, tracker.filename)
            
            # Get pending entries for this tracker
            pending_entries = get_tracker_entry_query().filter_by(
                tracker_id=tracker_id,
                status='pending'
            ).order_by(TrackerEntry.day).all()
            
            # Calculate total cashback given for this tracker
            tracker_cashback_total = get_tracker_cashback_total(tracker_id, instance_name)
            
            # Calculate cashback for each day/row
            day_cashback_map = {}
            for row in tracker_data['data']:
                day = row.get('day')
                if day is not None:
                    # Convert day to int if it's a string
                    if isinstance(day, str):
                        try:
                            day = int(float(day.replace(',', '').strip()))
                        except (ValueError, AttributeError):
                            continue
                    elif isinstance(day, float):
                        day = int(day)
                    
                    day_cashback = get_tracker_day_cashback(tracker_id, day, instance_name)
                    day_cashback_map[day] = day_cashback
            
            # Get cashback configs for this tracker
            cashback_configs = get_tracker_cashback_config_query().filter_by(
                tracker_id=tracker_id,
                is_active=True
            ).all()
            
            # Get all users for assignment - any user (customer or admin) can be assigned as moderator
            # Exclude the current admin user to avoid self-assignment
            all_moderators = get_user_query().filter(User.id != current_user.id).order_by(User.username).all()
            
            return render_template('admin/view_daily_tracker.html',
                                 tracker=tracker,
                                 tracker_data=tracker_data,
                                 summary=summary,
                                 pending_entries=pending_entries,
                                 tracker_cashback_total=tracker_cashback_total,
                                 day_cashback_map=day_cashback_map,
                                 cashback_configs=cashback_configs,
                                 all_moderators=all_moderators,
                                 instance_name=instance_name)
        except Exception as e:
            flash(f'Error reading tracker data: {str(e)}', 'error')
            return redirect(url_for('admin_daily_trackers', instance_name=instance_name))


    @app.route('/<instance_name>/admin/daily-trackers/<int:tracker_id>/add-entry', methods=['GET', 'POST'])
    @login_required
    def admin_add_tracker_entry(instance_name, tracker_id):
        """Admin add entry to daily tracker"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        tracker = get_daily_tracker_query().filter_by(id=tracker_id, is_active=True).first()
        if not tracker:
            flash('Tracker not found', 'error')
            return redirect(url_for('admin_daily_trackers', instance_name=instance_name))
        
        if request.method == 'POST':
            try:
                day = int(request.form['day'])
                entry_data = {}
                
                # Collect all form fields dynamically
                for key, value in request.form.items():
                    if key != 'day' and value.strip():
                        # Convert numeric fields
                        if key in ['daily_payments', 'cumulative', 'balance', 
                                  'reinvest', 'pocket_money', 'total_invested']:
                            try:
                                entry_data[key] = Decimal(value)
                            except:
                                entry_data[key] = value
                        else:
                            entry_data[key] = value
                
                # Update the tracker
                update_tracker_entry(instance_name, tracker.filename, day, entry_data)
                
                # Update the tracker's updated_at timestamp
                tracker.updated_at = datetime.utcnow()
                commit_current_instance()
                
                # Process cashback if provided
                session = db_manager.get_session_for_instance(instance_name)
                usernames = request.form.getlist('cashback_username[]')
                points_list = request.form.getlist('cashback_points[]')
                
                for username, points_str in zip(usernames, points_list):
                    username = username.strip()
                    if not username:
                        continue
                    
                    try:
                        points = Decimal(str(points_str))
                        if points <= 0:
                            continue
                    except (ValueError, InvalidOperation):
                        continue
                    
                    # Validate username
                    recipient = validate_username_exists(username, instance_name)
                    if recipient:
                        transaction = CashbackTransaction(
                            from_user_id=None,  # System/admin grant
                            to_user_id=recipient.id,
                            points=points,
                            transaction_type='tracker_entry',
                            related_tracker_id=tracker.id,
                            related_tracker_entry_day=day,
                            notes=f"Cashback from tracker '{tracker.tracker_name}' entry (Day {day})",
                            created_by_user_id=current_user.id
                        )
                        session.add(transaction)
                
                session.commit()
                
                # Log tracker entry update
                from lms_logging import get_logging_manager
                from lms_metrics import get_metrics_manager
                logging_mgr = get_logging_manager(instance_name)
                metrics_mgr = get_metrics_manager(instance_name)
                
                daily_payment = entry_data.get('daily_payments', 0)
                
                # Get cashback info for this entry
                cashback_info = None
                try:
                    day_cashback = get_tracker_day_cashback(tracker_id, day, instance_name)
                    if day_cashback > 0:
                        # Get cashback transactions for this day
                        session = db_manager.get_session_for_instance(instance_name)
                        cashback_txns = session.query(CashbackTransaction).filter_by(
                            related_tracker_id=tracker_id,
                            related_tracker_entry_day=day,
                            transaction_type='tracker_entry'
                        ).all()
                        cashback_info = {
                            'total': float(day_cashback),
                            'transactions': [
                                {
                                    'user': txn.to_user.username if txn.to_user else 'unknown',
                                    'points': float(txn.points)
                                }
                                for txn in cashback_txns
                            ]
                        }
                except Exception as e:
                    print(f"[ERROR] Failed to get cashback info for logging: {e}")
                
                log_details = {
                    'tracker_name': tracker.tracker_name,
                    'day': day,
                    'daily_payment': str(daily_payment),
                    'customer': tracker.user.username if tracker.user else None,
                    'row_index': day  # Using day as row_index approximation
                }
                if cashback_info:
                    log_details['cashback'] = cashback_info
                
                logging_mgr.log_admin_action(
                    action='admin_tracker_entry_update',
                    resource_type='tracker',
                    resource_id=tracker_id,
                    username=current_user.username,
                    details=log_details
                )
                metrics_mgr.record_tracker_entry(
                    tracker_id=tracker_id,
                    username=current_user.username,
                    amount=float(daily_payment) if daily_payment else 0
                )
                
                flash(f'Entry for Day {day} updated successfully', 'success')
                return redirect(url_for('admin_view_daily_tracker', 
                                      instance_name=instance_name, 
                                      tracker_id=tracker_id))
                
            except Exception as e:
                flash(f'Error updating entry: {str(e)}', 'error')
                print(f"Error updating entry: {e}")
        
        # GET request - show form
        try:
            tracker_data = get_tracker_data(instance_name, tracker.filename)
            return render_template('admin/add_tracker_entry.html',
                                 tracker=tracker,
                                 tracker_data=tracker_data,
                                 instance_name=instance_name)
        except Exception as e:
            flash(f'Error reading tracker data: {str(e)}', 'error')
            return redirect(url_for('admin_daily_trackers', instance_name=instance_name))


    @app.route('/<instance_name>/admin/daily-trackers/<int:tracker_id>/edit-entry/<int:row_index>', methods=['GET', 'POST'])
    @login_required
    def admin_edit_tracker_entry(instance_name, tracker_id, row_index):
        """Admin edit a specific entry by row index"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        tracker = get_daily_tracker_query().filter_by(id=tracker_id, is_active=True).first()
        if not tracker:
            flash('Tracker not found', 'error')
            return redirect(url_for('admin_daily_trackers', instance_name=instance_name))
        
        # Get tracker data
        try:
            tracker_data = get_tracker_data(instance_name, tracker.filename)
        except Exception as e:
            flash(f'Error reading tracker data: {str(e)}', 'error')
            return redirect(url_for('admin_view_daily_tracker', 
                                  instance_name=instance_name, 
                                  tracker_id=tracker_id))
        
        # Validate row_index
        if row_index < 0 or row_index >= len(tracker_data['data']):
            flash('Invalid row index', 'error')
            return redirect(url_for('admin_view_daily_tracker', 
                                  instance_name=instance_name, 
                                  tracker_id=tracker_id))
        
        row_data = tracker_data['data'][row_index]
        
        if request.method == 'POST':
            try:
                entry_data = {}
                
                # Collect all form fields dynamically
                for key, value in request.form.items():
                    if value.strip():
                        # Convert numeric fields
                        if key in ['day', 'daily_payments', 'cumulative', 'balance', 
                                  'reinvest', 'pocket_money', 'total_invested']:
                            try:
                                entry_data[key] = Decimal(value) if key != 'day' else int(value)
                            except:
                                entry_data[key] = value
                        else:
                            entry_data[key] = value
                
                # Update the tracker by row index
                sys.path.insert(0, str(Path(__file__).parent / 'daily-trackers'))
                from tracker_manager import update_tracker_entry_by_index
                update_tracker_entry_by_index(instance_name, tracker.filename, row_index, entry_data)
                
                # Update the tracker's updated_at timestamp
                tracker.updated_at = datetime.utcnow()
                commit_current_instance()
                
                # Process cashback if provided
                session = db_manager.get_session_for_instance(instance_name)
                day = entry_data.get('day', row_index + 1)
                
                # Delete existing cashback transactions for this entry (to handle edits/deletions)
                existing_transactions = session.query(CashbackTransaction).filter_by(
                    related_tracker_id=tracker.id,
                    related_tracker_entry_day=day,
                    transaction_type='tracker_entry'
                ).all()
                for txn in existing_transactions:
                    session.delete(txn)
                
                # Add new cashback transactions from form
                usernames = request.form.getlist('cashback_username[]')
                points_list = request.form.getlist('cashback_points[]')
                
                for username, points_str in zip(usernames, points_list):
                    username = username.strip()
                    if not username:
                        continue
                    
                    try:
                        points = Decimal(str(points_str))
                        if points <= 0:
                            continue
                    except (ValueError, InvalidOperation):
                        continue
                    
                    # Validate username
                    recipient = validate_username_exists(username, instance_name)
                    if recipient:
                        transaction = CashbackTransaction(
                            from_user_id=None,  # System/admin grant
                            to_user_id=recipient.id,
                            points=points,
                            transaction_type='tracker_entry',
                            related_tracker_id=tracker.id,
                            related_tracker_entry_day=day,
                            notes=f"Cashback from tracker '{tracker.tracker_name}' entry (Day {day})",
                            created_by_user_id=current_user.id
                        )
                        session.add(transaction)
                
                session.commit()
                
                # Log tracker entry update
                from lms_logging import get_logging_manager
                from lms_metrics import get_metrics_manager
                logging_mgr = get_logging_manager(instance_name)
                metrics_mgr = get_metrics_manager(instance_name)
                
                daily_payment = entry_data.get('daily_payments', 0)
                day = row_data.get('day', row_index)
                
                # Get cashback info for this entry
                cashback_info = None
                try:
                    day_cashback = get_tracker_day_cashback(tracker_id, day, instance_name)
                    if day_cashback > 0:
                        # Get cashback transactions for this day
                        cashback_txns = session.query(CashbackTransaction).filter_by(
                            related_tracker_id=tracker_id,
                            related_tracker_entry_day=day,
                            transaction_type='tracker_entry'
                        ).all()
                        cashback_info = {
                            'total': float(day_cashback),
                            'transactions': [
                                {
                                    'user': txn.to_user.username if txn.to_user else 'unknown',
                                    'points': float(txn.points)
                                }
                                for txn in cashback_txns
                            ]
                        }
                except Exception as e:
                    print(f"[ERROR] Failed to get cashback info for logging: {e}")
                
                log_details = {
                    'tracker_name': tracker.tracker_name,
                    'day': day,
                    'daily_payment': str(daily_payment),
                    'customer': tracker.user.username if tracker.user else None,
                    'row_index': row_index
                }
                if cashback_info:
                    log_details['cashback'] = cashback_info
                
                logging_mgr.log_admin_action(
                    action='admin_tracker_entry_update',
                    resource_type='tracker',
                    resource_id=tracker_id,
                    username=current_user.username,
                    details=log_details
                )
                metrics_mgr.record_tracker_entry(
                    tracker_id=tracker_id,
                    username=current_user.username,
                    amount=float(daily_payment) if daily_payment else 0
                )
                
                flash(f'Entry for Day {row_data.get("day", row_index)} updated successfully', 'success')
                return redirect(url_for('admin_view_daily_tracker', 
                                      instance_name=instance_name, 
                                      tracker_id=tracker_id))
                
            except Exception as e:
                flash(f'Error updating entry: {str(e)}', 'error')
                print(f"Error updating entry: {e}")
        
        # Get existing cashback transactions for this tracker entry
        existing_cashback = []
        day = row_data.get('day', row_index + 1)
        # Convert day to int if it's a string
        if isinstance(day, str):
            try:
                day = int(float(day.replace(',', '').strip()))
            except (ValueError, AttributeError):
                day = row_index + 1
        elif isinstance(day, float):
            day = int(day)
        
        try:
            session = db_manager.get_session_for_instance(instance_name)
            existing_transactions = session.query(CashbackTransaction).filter_by(
                related_tracker_id=tracker.id,
                related_tracker_entry_day=day,
                transaction_type='tracker_entry'
            ).all()
            
            for txn in existing_transactions:
                existing_cashback.append({
                    'user': txn.to_user,
                    'points': txn.points,
                    'transaction_id': txn.id
                })
        except Exception as e:
            print(f"Error fetching existing cashback: {e}")
        
        # Get tracker cashback configs and calculate configured cashback
        configured_cashback = []
        try:
            cashback_configs = get_tracker_cashback_config_query().filter_by(
                tracker_id=tracker.id,
                is_active=True
            ).all()
            
            # Get daily_payments from row_data - handle various formats
            daily_payment = row_data.get('daily_payments', 0)
            
            # Convert to Decimal, handling strings, None, and numeric types
            if daily_payment is None:
                daily_payment = Decimal('0')
            elif isinstance(daily_payment, str):
                try:
                    # Remove any currency symbols, commas, and whitespace
                    cleaned = daily_payment.replace('₹', '').replace(',', '').replace(' ', '').strip()
                    daily_payment = Decimal(cleaned) if cleaned else Decimal('0')
                except (ValueError, InvalidOperation):
                    daily_payment = Decimal('0')
            elif isinstance(daily_payment, (int, float)):
                daily_payment = Decimal(str(daily_payment))
            else:
                try:
                    daily_payment = Decimal(str(daily_payment))
                except (ValueError, InvalidOperation):
                    daily_payment = Decimal('0')
            
            # Calculate cashback for each config
            for config in cashback_configs:
                if config.cashback_type == 'percentage':
                    # config.cashback_value is already a Decimal (0.01 = 1%)
                    points = daily_payment * config.cashback_value
                else:  # fixed
                    points = config.cashback_value
                
                # Round to 2 decimal places
                points = points.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                configured_cashback.append({
                    'username': config.user.username,
                    'points': points,
                    'config_type': config.cashback_type,
                    'config_value': config.cashback_value,
                    'daily_payment_used': daily_payment  # For debugging
                })
        except Exception as e:
            print(f"Error fetching configured cashback: {e}")
            import traceback
            traceback.print_exc()
        
        # GET request - show form with current values
        # Import cashback templates
        from app_cashback import CASHBACK_TEMPLATES
        
        # Get all users for admin dropdown
        all_users = None
        if current_user.is_admin:
            all_users = get_user_query().order_by(User.username).all()
        
        return render_template('admin/edit_tracker_entry.html',
                             tracker=tracker,
                             tracker_data=tracker_data,
                             row_data=row_data,
                             row_index=row_index,
                             existing_cashback=existing_cashback,
                             configured_cashback=configured_cashback,
                             templates=CASHBACK_TEMPLATES,
                             all_users=all_users,
                             is_admin=current_user.is_admin,
                             instance_name=instance_name)


    @app.route('/<instance_name>/admin/daily-trackers/pending-entries')
    @login_required
    def admin_pending_tracker_entries(instance_name):
        """Admin view all pending tracker entries"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        # Get all pending tracker entries
        pending_entries = get_tracker_entry_query().filter_by(status='pending').order_by(
            TrackerEntry.submitted_at.desc()
        ).all()
        
        # Group by tracker for better organization
        entries_by_tracker = {}
        for entry in pending_entries:
            if entry.tracker_id not in entries_by_tracker:
                entries_by_tracker[entry.tracker_id] = []
            entries_by_tracker[entry.tracker_id].append(entry)
        
        return render_template('admin/pending_tracker_entries.html',
                             pending_entries=pending_entries,
                             entries_by_tracker=entries_by_tracker,
                             instance_name=instance_name)

    @app.route('/<instance_name>/admin/daily-trackers/approve-entry/<int:entry_id>', methods=['GET', 'POST'])
    @login_required
    def admin_approve_tracker_entry(instance_name, entry_id):
        """Admin approve/reject tracker entry"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        entry = get_tracker_entry_query().filter_by(id=entry_id).first()
        if not entry:
            flash('Entry not found', 'error')
            return redirect(url_for('admin_pending_tracker_entries', instance_name=instance_name))
        
        tracker = entry.tracker
        entry_data = json.loads(entry.entry_data)
        
        if request.method == 'POST':
            action = request.form.get('action')  # 'approve' or 'reject'
            
            if action == 'approve':
                try:
                    # Update Excel file with the entry data
                    update_tracker_entry(instance_name, tracker.filename, entry.day, entry_data)
                    
                    # Update tracker timestamp
                    tracker.updated_at = datetime.utcnow()
                    
                    # Mark entry as verified
                    entry.status = 'verified'
                    entry.verified_by_user_id = current_user.id
                    entry.verified_at = datetime.utcnow()
                    
                    commit_current_instance()
                    
                    # Check if cashback is enabled
                    enable_cashback = request.form.get('enable_cashback') == 'on'
                    
                    # Process cashback only if enabled
                    if enable_cashback:
                        session = db_manager.get_session_for_instance(instance_name)
                        
                        # Get tracker cashback configs
                        cashback_configs = get_tracker_cashback_config_query().filter_by(
                            tracker_id=tracker.id,
                            is_active=True
                        ).all()
                        
                        daily_payment = entry_data.get('daily_payments', Decimal('0'))
                        # Convert string to Decimal, handling various formats
                        if isinstance(daily_payment, str):
                            try:
                                cleaned = daily_payment.replace('₹', '').replace(',', '').replace(' ', '').strip()
                                daily_payment = Decimal(cleaned) if cleaned else Decimal('0')
                            except (ValueError, InvalidOperation):
                                daily_payment = Decimal('0')
                        elif daily_payment is None:
                            daily_payment = Decimal('0')
                        elif isinstance(daily_payment, (int, float)):
                            daily_payment = Decimal(str(daily_payment))
                        else:
                            try:
                                daily_payment = Decimal(str(daily_payment))
                            except (ValueError, InvalidOperation):
                                daily_payment = Decimal('0')
                        
                        # Process manual cashback from form
                        usernames = request.form.getlist('cashback_username[]')
                        points_list = request.form.getlist('cashback_points[]')
                        
                        # Check if manual cashback is provided
                        has_manual_cashback = False
                        manual_cashback_users = set()
                        for username, points_str in zip(usernames, points_list):
                            username = username.strip()
                            if username and points_str:
                                try:
                                    points = Decimal(str(points_str))
                                    if points > 0:
                                        has_manual_cashback = True
                                        manual_cashback_users.add(username.lower())
                                except (ValueError, InvalidOperation):
                                    pass
                        
                        cashback_details = []
                        total_cashback = Decimal('0')
                        
                        # Only process automatic cashback if no manual cashback is provided
                        # This prevents double-adding when admin uses pre-filled values
                        if not has_manual_cashback:
                            # Process automatic cashback from configs
                            for config in cashback_configs:
                                if config.cashback_type == 'percentage':
                                    points = daily_payment * config.cashback_value
                                else:  # fixed
                                    points = config.cashback_value
                                
                                if points > 0:
                                    transaction = CashbackTransaction(
                                        from_user_id=None,
                                        to_user_id=config.user_id,
                                        points=points,
                                        transaction_type='tracker_entry',
                                        related_tracker_id=tracker.id,
                                        related_tracker_entry_day=entry.day,
                                        notes=f"Auto cashback from tracker '{tracker.tracker_name}' entry (Day {entry.day})",
                                        created_by_user_id=current_user.id
                                    )
                                    session.add(transaction)
                                    total_cashback += points
                                    cashback_details.append({
                                        'user': config.user.username,
                                        'points': float(points),
                                        'type': 'auto'
                                    })
                        # Process manual cashback from form (if provided, this overrides automatic)
                        if has_manual_cashback:
                            for username, points_str in zip(usernames, points_list):
                                username = username.strip()
                                if not username:
                                    continue
                                
                                try:
                                    points = Decimal(str(points_str))
                                    if points <= 0:
                                        continue
                                except (ValueError, InvalidOperation):
                                    continue
                                
                                recipient = validate_username_exists(username, instance_name)
                                if recipient:
                                    transaction = CashbackTransaction(
                                        from_user_id=None,
                                        to_user_id=recipient.id,
                                        points=points,
                                        transaction_type='tracker_entry',
                                        related_tracker_id=tracker.id,
                                        related_tracker_entry_day=entry.day,
                                        notes=f"Cashback from tracker '{tracker.tracker_name}' entry (Day {entry.day})",
                                        created_by_user_id=current_user.id
                                    )
                                    session.add(transaction)
                                    total_cashback += points
                                    cashback_details.append({
                                        'user': username,
                                        'points': float(points),
                                        'type': 'manual'
                                    })
                        
                        session.commit()
                        
                        # Log cashback activity if any cashback was given
                        if total_cashback > 0:
                            try:
                                from lms_logging import get_logging_manager
                                logging_mgr = get_logging_manager(instance_name)
                                logging_mgr.log_activity(
                                    action='cashback_tracker_entry',
                                    username=current_user.username,
                                    user_id=current_user.id,
                                    resource_type='tracker',
                                    resource_id=tracker.id,
                                    details={
                                        'tracker_name': tracker.tracker_name,
                                        'day': entry.day,
                                        'daily_payment': float(daily_payment),
                                        'total_cashback': float(total_cashback),
                                        'cashback_details': cashback_details
                                    }
                                )
                            except Exception as log_error:
                                print(f"[ERROR] Failed to log tracker cashback: {log_error}")
                    
                    flash(f'Entry for Day {entry.day} approved successfully', 'success')
                    return redirect(url_for('admin_pending_tracker_entries', instance_name=instance_name))
                    
                except Exception as e:
                    flash(f'Error approving entry: {str(e)}', 'error')
                    print(f"Error approving entry: {e}")
            
            elif action == 'reject':
                rejection_reason = request.form.get('rejection_reason', '')
                
                # Get original daily_payments value for the note
                original_daily_payment = entry_data.get('daily_payments', Decimal('0'))
                # Convert to Decimal, handling various formats
                if isinstance(original_daily_payment, str):
                    try:
                        cleaned = original_daily_payment.replace('₹', '').replace(',', '').replace(' ', '').strip()
                        original_daily_payment = Decimal(cleaned) if cleaned else Decimal('0')
                    except (ValueError, InvalidOperation):
                        original_daily_payment = Decimal('0')
                elif original_daily_payment is None:
                    original_daily_payment = Decimal('0')
                elif isinstance(original_daily_payment, (int, float)):
                    original_daily_payment = Decimal(str(original_daily_payment))
                else:
                    try:
                        original_daily_payment = Decimal(str(original_daily_payment))
                    except (ValueError, InvalidOperation):
                        original_daily_payment = Decimal('0')
                
                # Create entry data with 0 values (as if they filled 0)
                rejected_entry_data = entry_data.copy()
                rejected_entry_data['daily_payments'] = Decimal('0')
                # Don't set cumulative - let it be recalculated automatically by update_tracker_entry
                
                # Build notes: combine rejection reason with original value info
                notes_parts = []
                if original_daily_payment > 0:
                    notes_parts.append(f"Rejected by admin for value: ₹{original_daily_payment:.2f}")
                else:
                    notes_parts.append("Rejected by admin")
                
                if rejection_reason:
                    notes_parts.append(f"Reason: {rejection_reason}")
                
                # Update notes field (append to existing notes if any)
                existing_notes = rejected_entry_data.get('notes', '')
                if existing_notes:
                    rejected_entry_data['notes'] = f"{existing_notes}. {'. '.join(notes_parts)}"
                else:
                    rejected_entry_data['notes'] = '. '.join(notes_parts)
                
                # Remove cumulative from entry_data so it gets recalculated
                if 'cumulative' in rejected_entry_data:
                    del rejected_entry_data['cumulative']
                
                # Update Excel file with 0 values and rejection note
                try:
                    update_tracker_entry(instance_name, tracker.filename, entry.day, rejected_entry_data)
                    
                    # Update tracker timestamp
                    tracker.updated_at = datetime.utcnow()
                except Exception as e:
                    print(f"Error updating Excel file on rejection: {e}")
                    flash(f'Entry rejected but error updating Excel file: {str(e)}', 'warning')
                
                # Mark entry as rejected in database
                entry.status = 'rejected'
                entry.verified_by_user_id = current_user.id
                entry.verified_at = datetime.utcnow()
                entry.rejection_reason = rejection_reason
                commit_current_instance()
                
                flash(f'Entry for Day {entry.day} rejected and set to 0', 'success')
                return redirect(url_for('admin_pending_tracker_entries', instance_name=instance_name))
        
        # GET request - show approval form
        # Get existing cashback configs for this tracker
        cashback_configs = get_tracker_cashback_config_query().filter_by(
            tracker_id=tracker.id,
            is_active=True
        ).all()
        
        # Calculate configured cashback
        configured_cashback = []
        daily_payment = entry_data.get('daily_payments', Decimal('0'))
        
        # Convert to Decimal, handling strings, None, and numeric types
        if daily_payment is None:
            daily_payment = Decimal('0')
        elif isinstance(daily_payment, str):
            try:
                # Remove any currency symbols, commas, and whitespace
                cleaned = daily_payment.replace('₹', '').replace(',', '').replace(' ', '').strip()
                daily_payment = Decimal(cleaned) if cleaned else Decimal('0')
            except (ValueError, InvalidOperation):
                daily_payment = Decimal('0')
        elif isinstance(daily_payment, (int, float)):
            daily_payment = Decimal(str(daily_payment))
        else:
            try:
                daily_payment = Decimal(str(daily_payment))
            except (ValueError, InvalidOperation):
                daily_payment = Decimal('0')
        
        for config in cashback_configs:
            if config.cashback_type == 'percentage':
                points = daily_payment * config.cashback_value
            else:  # fixed
                points = config.cashback_value
            
            # Round to 2 decimal places
            points = points.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            configured_cashback.append({
                'username': config.user.username,
                'points': points,
                'config_type': config.cashback_type,
                'config_value': config.cashback_value  # Percentage as decimal (e.g., 0.001 for 0.1%)
            })
        
        # Only show user list to admins, not moderators
        all_users = None
        if current_user.is_admin:
            all_users = get_user_query().order_by(User.username).all()
        
        return render_template('admin/approve_tracker_entry.html',
                             entry=entry,
                             tracker=tracker,
                             entry_data=entry_data,
                             configured_cashback=configured_cashback,
                             all_users=all_users,
                             is_admin=current_user.is_admin,
                             instance_name=instance_name)


    @app.route('/<instance_name>/admin/daily-trackers/<int:tracker_id>/delete', methods=['POST'])
    @login_required
    def admin_delete_tracker(instance_name, tracker_id):
        """Admin deletes a tracker permanently"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        tracker = get_daily_tracker_query().filter_by(id=tracker_id).first()
        if not tracker:
            flash('Tracker not found', 'error')
            return redirect(url_for('admin_daily_trackers', instance_name=instance_name))
        
        # Mark as deleted (soft delete)
        tracker.is_active = False
        tracker.updated_at = datetime.utcnow()
        commit_current_instance()
        
        flash(f'Tracker "{tracker.tracker_name}" deleted successfully', 'success')
        return redirect(url_for('admin_daily_trackers', instance_name=instance_name))


    @app.route('/<instance_name>/admin/daily-trackers/<int:tracker_id>/reopen', methods=['POST'])
    @login_required
    def admin_reopen_tracker(instance_name, tracker_id):
        """Admin reopens a tracker closed by user"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        tracker = get_daily_tracker_query().filter_by(id=tracker_id, is_active=True).first()
        if not tracker:
            flash('Tracker not found', 'error')
            return redirect(url_for('admin_daily_trackers', instance_name=instance_name))
        
        # Reopen the tracker for user
        tracker.is_closed_by_user = False
        tracker.updated_at = datetime.utcnow()
        commit_current_instance()
        
        flash(f'Tracker "{tracker.tracker_name}" reopened successfully', 'success')
        return redirect(url_for('admin_daily_trackers', instance_name=instance_name))


    @app.route('/<instance_name>/admin/daily-trackers/<int:tracker_id>/close', methods=['POST'])
    @login_required
    def admin_close_tracker(instance_name, tracker_id):
        """Admin closes a tracker for user (hides it from user view)"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        tracker = get_daily_tracker_query().filter_by(id=tracker_id, is_active=True).first()
        if not tracker:
            flash('Tracker not found', 'error')
            return redirect(url_for('admin_daily_trackers', instance_name=instance_name))
        
        # Close the tracker (user won't see it)
        tracker.is_closed_by_user = True
        tracker.updated_at = datetime.utcnow()
        commit_current_instance()
        
        flash(f'Tracker "{tracker.tracker_name}" closed successfully', 'success')
        return redirect(url_for('admin_daily_trackers', instance_name=instance_name))


    @app.route('/<instance_name>/admin/daily-trackers/<int:tracker_id>/download')
    @login_required
    def admin_download_tracker(instance_name, tracker_id):
        """Admin downloads the Excel file for a tracker"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        tracker = get_daily_tracker_query().filter_by(id=tracker_id, is_active=True).first()
        if not tracker:
            flash('Tracker not found', 'error')
            return redirect(url_for('admin_daily_trackers', instance_name=instance_name))
        
        try:
            # Get the directory where the tracker file is stored
            tracker_dir = get_tracker_directory(instance_name)
            
            # Send the file for download
            return send_from_directory(
                tracker_dir,
                tracker.filename,
                as_attachment=True,
                download_name=f"{tracker.user.username}_{tracker.tracker_name}_{tracker.filename}"
            )
        except Exception as e:
            flash(f'Error downloading tracker: {str(e)}', 'error')
            return redirect(url_for('admin_view_daily_tracker', 
                                  instance_name=instance_name, 
                                  tracker_id=tracker_id))


    @app.route('/<instance_name>/admin/tracker/<int:tracker_id>/assign-moderator/<int:moderator_id>', methods=['POST'])
    @login_required
    def admin_assign_moderator_to_tracker(instance_name, tracker_id, moderator_id):
        """Assign a moderator to a tracker"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        tracker = get_daily_tracker_query().filter_by(id=tracker_id).first()
        # Allow any user (customer or admin) to be assigned as moderator - no need for is_moderator flag
        moderator = get_user_query().filter_by(id=moderator_id).first()
        
        if not tracker or not moderator:
            flash('Tracker or user not found', 'error')
            return redirect(url_for('admin_daily_trackers', instance_name=instance_name))
        
        if moderator not in tracker.assigned_moderators:
            tracker.assigned_moderators.append(moderator)
            commit_current_instance()
            flash(f'{moderator.username} assigned to tracker: {tracker.tracker_name}', 'success')
        else:
            flash(f'{moderator.username} is already assigned to this tracker', 'info')
        
        return redirect(url_for('admin_view_daily_tracker', instance_name=instance_name, tracker_id=tracker_id))


    @app.route('/<instance_name>/admin/tracker/<int:tracker_id>/unassign-moderator/<int:moderator_id>', methods=['POST'])
    @login_required
    def admin_unassign_moderator_from_tracker(instance_name, tracker_id, moderator_id):
        """Unassign a moderator from a tracker"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if not current_user.is_admin:
            flash('Access denied', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        tracker = get_daily_tracker_query().filter_by(id=tracker_id).first()
        moderator = get_user_query().filter_by(id=moderator_id).first()
        
        if not tracker or not moderator:
            flash('Tracker or moderator not found', 'error')
            return redirect(url_for('admin_daily_trackers', instance_name=instance_name))
        
        if moderator in tracker.assigned_moderators:
            tracker.assigned_moderators.remove(moderator)
            commit_current_instance()
            flash(f'{moderator.username} unassigned from tracker: {tracker.tracker_name}', 'success')
        else:
            flash(f'{moderator.username} is not assigned to this tracker', 'info')
        
        return redirect(url_for('admin_view_daily_tracker', instance_name=instance_name, tracker_id=tracker_id))

    # Customer Tracker Routes
    @app.route('/<instance_name>/customer/trackers-dashboard')
    @login_required
    def customer_trackers_dashboard(instance_name):
        """Customer trackers dashboard - list all trackers with summary"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        # Get all user's trackers (active and not closed)
        trackers = get_daily_tracker_query().filter_by(
            user_id=current_user.id, 
            is_active=True,
            is_closed_by_user=False
        ).all()
        
        if not trackers:
            flash('No daily trackers found for your account', 'info')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        # Build tracker summary data
        tracker_summaries = []
        total_pending = 0.0  # Use float instead of Decimal
        
        for tracker in trackers:
            try:
                # Get tracker data and summary
                tracker_data = get_tracker_data(instance_name, tracker.filename)
                summary = get_tracker_summary(instance_name, tracker.filename)
                
                # Find last paid date from data rows with date
                last_paid_date = None
                for row in reversed(tracker_data['data']):
                    if row.get('daily_payments') and row.get('date'):
                        last_paid_date = row.get('date')
                        break
                
                # Use pending from summary (already calculated correctly)
                pending = float(summary['pending'])  # Ensure it's float
                total_pending += pending
                
                tracker_summaries.append({
                    'tracker': tracker,
                    'last_paid_date': last_paid_date if last_paid_date else "No payments yet",
                    'total_payments': summary['total_payments'],
                    'pending': pending,
                    'balance': summary.get('balance', 0),
                    'cumulative': summary.get('cumulative', 0),
                    'days_with_payments': summary['total_days'],
                    'total_days_count': summary['total_days_count']
                })
            except Exception as e:
                print(f"Error processing tracker {tracker.id}: {e}")
                # Add tracker with error indication
                tracker_summaries.append({
                    'tracker': tracker,
                    'last_paid_date': None,
                    'total_payments': 0,
                    'pending': 0,
                    'balance': 0,
                    'cumulative': 0,
                    'days_with_payments': 0,
                    'total_days_count': 0,
                    'error': str(e)
                })
        
        return render_template('customer/trackers_dashboard.html',
                             tracker_summaries=tracker_summaries,
                             total_pending=total_pending,
                             instance_name=instance_name)


    @app.route('/<instance_name>/customer/daily-tracker')
    @app.route('/<instance_name>/customer/daily-tracker/<int:tracker_id>')
    @login_required
    def customer_daily_tracker(instance_name, tracker_id=None):
        """Customer view their daily tracker"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        # Get user's tracker (active and not closed)
        if tracker_id:
            # Specific tracker requested - verify it belongs to user
            tracker = get_daily_tracker_query().filter_by(
                id=tracker_id,
                user_id=current_user.id, 
                is_active=True,
                is_closed_by_user=False
            ).first()
        else:
            # No specific tracker - get first one
            tracker = get_daily_tracker_query().filter_by(
                user_id=current_user.id, 
                is_active=True,
                is_closed_by_user=False
            ).first()
        
        if not tracker:
            flash('No daily tracker found for your account', 'info')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        try:
            # Get tracker data from Excel
            tracker_data = get_tracker_data(instance_name, tracker.filename)
            summary = get_tracker_summary(instance_name, tracker.filename)
            
            # Get pending entries for this tracker
            pending_entries = get_tracker_entry_query().filter_by(
                tracker_id=tracker.id,
                status='pending'
            ).order_by(TrackerEntry.day).all()
            
            # Merge pending entries with tracker data
            # Create a map of day -> pending entry data
            pending_entries_map = {}
            for entry in pending_entries:
                entry_data = json.loads(entry.entry_data)
                day = entry.day
                pending_entries_map[day] = {
                    'entry': entry,
                    'data': entry_data,
                    'is_pending': True
                }
            
            # Update tracker_data to include pending entries
            # For each row, if there's a pending entry for that day, use pending data
            merged_data = []
            seen_days = set()  # Track days to prevent duplicates
            
            # Helper function to convert numeric values
            def convert_numeric_value(value, field_name=''):
                """Convert value to float, handling strings with currency symbols"""
                if value is None:
                    return None
                if isinstance(value, (int, float, Decimal)):
                    return float(value)
                if isinstance(value, str):
                    try:
                        # Remove currency symbols, commas, and whitespace
                        cleaned = value.replace('₹', '').replace('$', '').replace(',', '').strip()
                        if not cleaned:
                            return None
                        return float(cleaned)
                    except (ValueError, AttributeError, TypeError):
                        return None
                # Try to convert unknown types
                try:
                    return float(value)
                except (ValueError, TypeError, AttributeError):
                    return None
            
            for row in tracker_data['data']:
                day = row.get('day')
                # Convert day to int if needed
                if isinstance(day, str):
                    try:
                        day = int(float(day.replace(',', '').strip()))
                    except (ValueError, AttributeError):
                        day = None
                elif isinstance(day, float):
                    day = int(day)
                
                # Skip if day is None or duplicate
                if day is None:
                    continue
                
                # Handle duplicate days - prefer pending entry, skip duplicate Excel rows
                if day in seen_days:
                    if day in pending_entries_map:
                        # Already added as pending entry, skip this Excel row
                        continue
                    else:
                        # Duplicate Excel row, skip it
                        continue
                
                seen_days.add(day)
                
                if day is not None and day in pending_entries_map:
                    # Use pending entry data, but keep some fields from Excel (like cumulative formulas)
                    pending_data = pending_entries_map[day]['data'].copy()
                    # Merge with Excel row, pending data takes precedence
                    merged_row = row.copy()
                    merged_row.update(pending_data)
                    merged_row['is_pending'] = True
                    merged_row['pending_entry_id'] = pending_entries_map[day]['entry'].id
                    
                    # Convert all numeric fields to float
                    for numeric_field in ['daily_payments', 'cumulative', 'balance', 
                                         'reinvest', 'pocket_money', 'total_invested']:
                        if numeric_field in merged_row:
                            merged_row[numeric_field] = convert_numeric_value(
                                merged_row[numeric_field], 
                                field_name=numeric_field
                            )
                    
                    merged_data.append(merged_row)
                else:
                    # Use Excel data
                    merged_row = row.copy()
                    merged_row['is_pending'] = False
                    
                    # Convert all numeric fields to float
                    for numeric_field in ['daily_payments', 'cumulative', 'balance', 
                                         'reinvest', 'pocket_money', 'total_invested']:
                        if numeric_field in merged_row:
                            merged_row[numeric_field] = convert_numeric_value(
                                merged_row[numeric_field], 
                                field_name=numeric_field
                            )
                    
                    merged_data.append(merged_row)
            
            # Recalculate summary including pending entries
            # Calculate totals as if pending entries are approved
            total_payments_from_excel = summary.get('total_payments', 0)
            pending_payments_sum = Decimal('0')
            for entry in pending_entries:
                entry_data = json.loads(entry.entry_data)
                daily_payment = entry_data.get('daily_payments', 0)
                if isinstance(daily_payment, str):
                    try:
                        daily_payment = Decimal(str(daily_payment).replace(',', '').strip())
                    except (ValueError, InvalidOperation):
                        daily_payment = Decimal('0')
                elif daily_payment is None:
                    daily_payment = Decimal('0')
                else:
                    daily_payment = Decimal(str(daily_payment))
                pending_payments_sum += daily_payment
            
            # Calculate total cashback for tracker for logged-in user only
            session = db_manager.get_session_for_instance(instance_name)
            tracker_cashback_total = session.query(
                db.func.sum(CashbackTransaction.points)
            ).filter_by(
                related_tracker_id=tracker.id,
                transaction_type='tracker_entry',
                to_user_id=current_user.id
            ).scalar() or Decimal('0')
            
            # Updated summary with pending included
            updated_summary = summary.copy()
            updated_summary['total_payments'] = float(total_payments_from_excel) + float(pending_payments_sum)
            updated_summary['pending_entries_count'] = len(pending_entries)
            updated_summary['pending_payments_sum'] = float(pending_payments_sum)
            updated_summary['cashback_total'] = float(tracker_cashback_total)
            
            # Calculate cashback for each day for logged-in user only
            day_cashback_map = {}
            has_any_cashback = False
            for row in merged_data:
                day = row.get('day')
                if day is not None:
                    if isinstance(day, str):
                        try:
                            day = int(float(day.replace(',', '').strip()))
                        except (ValueError, AttributeError):
                            continue
                    elif isinstance(day, float):
                        day = int(day)
                    
                    day_cashback = session.query(
                        db.func.sum(CashbackTransaction.points)
                    ).filter_by(
                        related_tracker_id=tracker.id,
                        related_tracker_entry_day=day,
                        transaction_type='tracker_entry',
                        to_user_id=current_user.id
                    ).scalar() or Decimal('0')
                    
                    day_cashback = float(day_cashback)
                    day_cashback_map[day] = day_cashback
                    if day_cashback > 0:
                        has_any_cashback = True
            
            return render_template('customer/daily_tracker.html',
                                 tracker=tracker,
                                 tracker_data={'data': merged_data, 'parameters': tracker_data['parameters'], 'tracker_type': tracker_data['tracker_type']},
                                 summary=updated_summary,
                                 pending_entries=pending_entries,
                                 day_cashback_map=day_cashback_map,
                                 has_any_cashback=has_any_cashback,
                                 instance_name=instance_name)
        except Exception as e:
            flash(f'Error reading tracker data: {str(e)}', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))


    @app.route('/<instance_name>/customer/daily-tracker/close', methods=['POST'])
    @login_required
    def customer_close_tracker(instance_name):
        """Customer closes/hides their daily tracker"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        # Get user's tracker
        tracker = get_daily_tracker_query().filter_by(
            user_id=current_user.id, 
            is_active=True,
            is_closed_by_user=False
        ).first()
        
        if not tracker:
            flash('No active tracker found', 'error')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        # Close the tracker (user won't see it anymore, but admin can still access)
        tracker.is_closed_by_user = True
        tracker.updated_at = datetime.utcnow()
        commit_current_instance()
        
        flash('Tracker closed successfully. Contact admin if you need to reopen it.', 'success')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))

