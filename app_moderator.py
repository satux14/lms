"""
Moderator Routes Module
=======================

This module handles all moderator-related functionality including:
- Moderator dashboard
- Assigned loans and trackers management
- Adding payments and tracker entries
- Personal loans and trackers view
"""

from flask import request, redirect, url_for, flash, render_template, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from functools import wraps
import sys
import json
from pathlib import Path

# Import from app_multi - these will be set when register_moderator_routes is called
app = None
db = None

# These will be imported from app_multi
VALID_INSTANCES = None
DEFAULT_INSTANCE = None
Payment = None
Loan = None
DailyTracker = None
get_payment_query = None
get_loan_query = None
get_user_query = None
get_daily_tracker_query = None
add_to_current_instance = None
commit_current_instance = None
calculate_accumulated_interest = None
calculate_daily_interest = None
calculate_monthly_interest = None
process_payment = None
get_tracker_data = None
get_tracker_summary = None
update_tracker_entry = None


def moderator_required(f):
    """Decorator to require moderator access - checks if user is admin OR has assigned loans/trackers"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', instance_name=kwargs.get('instance_name', DEFAULT_INSTANCE)))
        
        # Allow admin users
        if current_user.is_admin:
            return f(*args, **kwargs)
        
        # Check if user has any assigned loans or trackers (assignment-based moderation)
        has_assigned_loans = len(current_user.assigned_loans.filter_by(is_active=True).all()) > 0
        has_assigned_trackers = len(current_user.assigned_trackers.filter_by(is_active=True).all()) > 0
        
        # Also allow if user has is_moderator flag (for backward compatibility)
        if current_user.is_moderator or has_assigned_loans or has_assigned_trackers:
            return f(*args, **kwargs)
        
        flash('Access denied. You need to be assigned to loans or trackers to access moderator features.', 'error')
        return redirect(url_for('customer_dashboard', instance_name=kwargs.get('instance_name', DEFAULT_INSTANCE)))
    return decorated_function


def is_loan_assigned_to_moderator(loan_id, moderator_id):
    """Check if a loan is assigned to a specific moderator"""
    loan = get_loan_query().filter_by(id=loan_id).first()
    if not loan:
        return False
    moderator = get_user_query().filter_by(id=moderator_id).first()
    if not moderator:
        return False
    return moderator in loan.assigned_moderators


def is_tracker_assigned_to_moderator(tracker_id, moderator_id):
    """Check if a tracker is assigned to a specific moderator"""
    tracker = get_daily_tracker_query().filter_by(id=tracker_id).first()
    if not tracker:
        return False
    moderator = get_user_query().filter_by(id=moderator_id).first()
    if not moderator:
        return False
    return moderator in tracker.assigned_moderators


def register_moderator_routes(flask_app, flask_db, valid_instances, default_instance,
                            payment_model, loan_model, tracker_model,
                            payment_query_func, loan_query_func, user_query_func, tracker_query_func,
                            add_instance_func, commit_instance_func,
                            calc_accumulated_func, calc_daily_interest_func, calc_monthly_interest_func,
                            process_payment_func,
                            get_tracker_data_func, get_tracker_summary_func, update_tracker_entry_func):
    """Register moderator routes with Flask app"""
    global app, db, VALID_INSTANCES, DEFAULT_INSTANCE
    global Payment, Loan, DailyTracker
    global get_payment_query, get_loan_query, get_user_query, get_daily_tracker_query
    global add_to_current_instance, commit_current_instance
    global calculate_accumulated_interest, calculate_daily_interest, calculate_monthly_interest
    global process_payment, get_tracker_data, get_tracker_summary, update_tracker_entry
    
    app = flask_app
    db = flask_db
    VALID_INSTANCES = valid_instances
    DEFAULT_INSTANCE = default_instance
    Payment = payment_model
    Loan = loan_model
    DailyTracker = tracker_model
    get_payment_query = payment_query_func
    get_loan_query = loan_query_func
    get_user_query = user_query_func
    get_daily_tracker_query = tracker_query_func
    add_to_current_instance = add_instance_func
    commit_current_instance = commit_instance_func
    calculate_accumulated_interest = calc_accumulated_func
    calculate_daily_interest = calc_daily_interest_func
    calculate_monthly_interest = calc_monthly_interest_func
    process_payment = process_payment_func
    get_tracker_data = get_tracker_data_func
    get_tracker_summary = get_tracker_summary_func
    update_tracker_entry = update_tracker_entry_func
    
    # Register routes
    register_routes()


def register_routes():
    """Register all moderator routes"""
    
    @app.route('/<instance_name>/moderator/dashboard')
    @login_required
    @moderator_required
    def moderator_dashboard(instance_name):
        """Moderator dashboard - overview of assigned loans and trackers"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        # Get assigned loans summary
        assigned_loans = current_user.assigned_loans.filter_by(is_active=True).all()
        assigned_total_principal = sum(loan.principal_amount for loan in assigned_loans)
        assigned_total_loans = len(assigned_loans)
        
        # Get assigned trackers
        assigned_trackers = current_user.assigned_trackers.filter_by(is_active=True).all()
        assigned_total_trackers = len(assigned_trackers)
        
        return render_template('moderator/dashboard.html',
                             # Assigned items only
                             assigned_total_loans=assigned_total_loans,
                             assigned_total_trackers=assigned_total_trackers,
                             instance_name=instance_name)

    @app.route('/<instance_name>/moderator/loans')
    @login_required
    @moderator_required
    def moderator_loans(instance_name):
        """View assigned loans (moderator view)"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        status_filter = request.args.get('status', 'active')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Get only loans assigned to this moderator
        query = current_user.assigned_loans
        
        if status_filter == 'active':
            query = query.filter_by(is_active=True, status='active')
        elif status_filter == 'closed':
            query = query.filter_by(status='closed')
        elif status_filter == 'paid_off':
            query = query.filter(Loan.remaining_principal <= 0, Loan.is_active == True)
        
        # Apply sorting
        if sort_by == 'created_at':
            query = query.order_by(Loan.created_at.desc() if sort_order == 'desc' else Loan.created_at.asc())
        elif sort_by == 'principal_amount':
            query = query.order_by(Loan.principal_amount.desc() if sort_order == 'desc' else Loan.principal_amount.asc())
        elif sort_by == 'remaining_principal':
            query = query.order_by(Loan.remaining_principal.desc() if sort_order == 'desc' else Loan.remaining_principal.asc())
        
        loans = query.all()
        
        # Calculate interest paid and accumulated interest for each loan
        loans_with_interest = []
        for loan in loans:
            interest_paid = get_payment_query().with_entities(db.func.sum(Payment.interest_amount)).filter_by(
                loan_id=loan.id,
                status='verified'
            ).scalar() or 0
            
            # Calculate accumulated interest
            interest_data = calculate_accumulated_interest(loan)
            accumulated_interest_daily = interest_data['daily']
            accumulated_interest_monthly = interest_data['monthly']
            
            loans_with_interest.append({
                'loan': loan,
                'interest_paid': Decimal(str(interest_paid)),
                'accumulated_interest_daily': accumulated_interest_daily,
                'accumulated_interest_monthly': accumulated_interest_monthly
            })
        
        return render_template('moderator/loans.html',
                             loans=loans_with_interest,
                             status_filter=status_filter,
                             sort_by=sort_by,
                             sort_order=sort_order,
                             instance_name=instance_name)

    @app.route('/<instance_name>/moderator/loan/<int:loan_id>')
    @login_required
    @moderator_required
    def moderator_view_loan(instance_name, loan_id):
        """View detailed loan information (moderator view)"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        loan = get_loan_query().filter_by(id=loan_id).first()
        if not loan:
            flash('Loan not found', 'error')
            return redirect(url_for('moderator_loans', instance_name=instance_name))
        
        # Check if moderator has access to this loan
        if current_user not in loan.assigned_moderators:
            flash('Access denied. You are not assigned to this loan.', 'error')
            return redirect(url_for('moderator_loans', instance_name=instance_name))
        
        # Get all payments for this loan
        payments = get_payment_query().filter_by(loan_id=loan_id).order_by(Payment.payment_date.desc()).all()
        
        # Calculate interest information
        daily_interest = calculate_daily_interest(loan.remaining_principal, loan.interest_rate)
        monthly_interest = calculate_monthly_interest(loan.remaining_principal, loan.interest_rate)
        interest_data = calculate_accumulated_interest(loan)
        accumulated_interest_daily = interest_data['daily']
        accumulated_interest_monthly = interest_data['monthly']
        
        # Calculate total interest paid for this loan
        total_interest_paid = sum(payment.interest_amount for payment in payments if payment.status == 'verified')
        
        # Calculate verified principal and interest paid for this loan
        verified_principal = sum(payment.principal_amount for payment in payments if payment.status == 'verified')
        verified_interest = sum(payment.interest_amount for payment in payments if payment.status == 'verified')
        
        # Calculate pending amounts for this loan
        pending_principal = sum(payment.principal_amount for payment in payments if payment.status == 'pending')
        pending_interest = sum(payment.interest_amount for payment in payments if payment.status == 'pending')
        pending_total = pending_principal + pending_interest
        
        # Calculate days active
        days_active = (date.today() - loan.created_at.date()).days
        
        return render_template('moderator/view_loan.html',
                             loan=loan,
                             payments=payments,
                             daily_interest=daily_interest,
                             monthly_interest=monthly_interest,
                             accumulated_interest_daily=accumulated_interest_daily,
                             accumulated_interest_monthly=accumulated_interest_monthly,
                             interest_data=interest_data,
                             total_interest_paid=total_interest_paid,
                             verified_principal=verified_principal,
                             verified_interest=verified_interest,
                             pending_principal=pending_principal,
                             pending_interest=pending_interest,
                             pending_total=pending_total,
                             days_active=days_active,
                             instance_name=instance_name)

    @app.route('/<instance_name>/moderator/loan/<int:loan_id>/add-payment', methods=['GET', 'POST'])
    @login_required
    @moderator_required
    def moderator_add_payment(instance_name, loan_id):
        """Moderator add payment for assigned loan"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        loan = get_loan_query().filter_by(id=loan_id).first()
        if not loan:
            flash('Loan not found', 'error')
            return redirect(url_for('moderator_loans', instance_name=instance_name))
        
        # Check if loan is assigned to this moderator
        if not is_loan_assigned_to_moderator(loan_id, current_user.id):
            flash('Access denied. You are not assigned to this loan.', 'error')
            return redirect(url_for('moderator_loans', instance_name=instance_name))
        
        if request.method == 'POST':
            amount = Decimal(request.form['amount'])
            payment_method = request.form['payment_method']
            transaction_id = request.form.get('transaction_id', '')
            payment_date_str = request.form.get('payment_date')
            
            # Parse payment date
            if payment_date_str:
                try:
                    payment_date = datetime.strptime(payment_date_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    flash('Invalid date format', 'error')
                    return render_template('moderator/add_payment.html',
                                         loan=loan,
                                         instance_name=instance_name)
            else:
                payment_date = datetime.utcnow()
            
            # Process payment (creates pending payment)
            try:
                payment = process_payment(
                    loan=loan,
                    payment_amount=amount,
                    payment_date=payment_date,
                    transaction_id=transaction_id,
                    payment_method=payment_method,
                    proof_filename=None,
                    razorpay_order_id=None,
                    razorpay_payment_id=None,
                    razorpay_signature=None,
                    payment_initiated_at=None
                )
                commit_current_instance()
                flash('Payment added successfully. It will be verified by admin.', 'success')
                return redirect(url_for('moderator_view_loan', instance_name=instance_name, loan_id=loan_id))
            except ValueError as e:
                flash(str(e), 'error')
                return render_template('moderator/add_payment.html',
                                     loan=loan,
                                     instance_name=instance_name)
            except Exception as e:
                flash(f'Error adding payment: {str(e)}', 'error')
                return render_template('moderator/add_payment.html',
                                     loan=loan,
                                     instance_name=instance_name)
        
        return render_template('moderator/add_payment.html',
                             loan=loan,
                             instance_name=instance_name)

    @app.route('/<instance_name>/moderator/trackers')
    @login_required
    @moderator_required
    def moderator_daily_trackers(instance_name):
        """View assigned daily trackers (moderator view)"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        # Get filter parameters (for display purposes - moderators see only assigned trackers)
        filters = {
            'user_id': request.args.get('user_id', type=int),
            'status': request.args.get('status', ''),
            'tracker_name': request.args.get('tracker_name', ''),
            'per_day_payment': request.args.get('per_day_payment', type=float),
            'pending_min': request.args.get('pending_min', type=float),
            'pending_max': request.args.get('pending_max', type=float)
        }
        
        # Get only trackers assigned to this moderator
        trackers = current_user.assigned_trackers.filter_by(is_active=True).order_by(DailyTracker.created_at.desc()).all()
        
        # Get summary for each tracker
        tracker_summaries = []
        total_pending_sum = 0
        total_payments_sum = 0
        total_trackers = len(trackers)
        
        for tracker in trackers:
            try:
                summary = get_tracker_summary(instance_name, tracker.filename)
                pending = summary.get('pending', 0)
                total_payments = summary.get('total_payments', 0)
                
                total_pending_sum += pending
                total_payments_sum += total_payments
                
                tracker_summaries.append({
                    'tracker': tracker,
                    'last_paid_date': summary.get('last_paid_date'),
                    'total_payments': total_payments,
                    'pending': pending,
                    'balance': summary.get('balance', 0),
                    'cumulative': summary.get('cumulative', 0),
                    'days_with_payments': summary.get('total_days', 0),
                    'total_days_count': summary.get('total_days_count', 0)
                })
            except Exception as e:
                print(f"Error processing tracker {tracker.id}: {e}")
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
        
        # Get all users for filter dropdown
        users = get_user_query().filter_by(is_admin=False).all()
        
        return render_template('moderator/trackers.html',
                             tracker_summaries=tracker_summaries,
                             total_trackers=total_trackers,
                             total_pending_sum=total_pending_sum,
                             total_payments_sum=total_payments_sum,
                             filters=filters,
                             users=users,
                             instance_name=instance_name)

    @app.route('/<instance_name>/moderator/tracker/<int:tracker_id>')
    @login_required
    @moderator_required
    def moderator_view_tracker(instance_name, tracker_id):
        """View specific tracker details (moderator view)"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        tracker = get_daily_tracker_query().filter_by(id=tracker_id, is_active=True).first()
        if not tracker:
            flash('Tracker not found', 'error')
            return redirect(url_for('moderator_daily_trackers', instance_name=instance_name))
        
        # Check if moderator has access to this tracker
        if current_user not in tracker.assigned_moderators:
            flash('Access denied. You are not assigned to this tracker.', 'error')
            return redirect(url_for('moderator_daily_trackers', instance_name=instance_name))
        
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[MODERATOR_VIEW_TRACKER] Starting view for tracker {tracker_id}, filename: {tracker.filename}")
            
            tracker_data = get_tracker_data(instance_name, tracker.filename)
            logger.info(f"[MODERATOR_VIEW_TRACKER] Tracker data loaded, rows: {len(tracker_data.get('data', []))}")
            
            summary = get_tracker_summary(instance_name, tracker.filename)
            logger.info(f"[MODERATOR_VIEW_TRACKER] Summary loaded: {summary}")
            
            # Get pending entries for this tracker
            from app_multi import TrackerEntry, get_tracker_entry_query
            from app_trackers import get_tracker_day_cashback, get_tracker_cashback_total
            pending_entries = get_tracker_entry_query().filter_by(
                tracker_id=tracker_id,
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
                        logger.warning(f"[MODERATOR_VIEW_TRACKER] Failed to convert {field_name} '{value}' to float")
                        return None
                # Try to convert unknown types
                try:
                    return float(value)
                except (ValueError, TypeError, AttributeError):
                    logger.warning(f"[MODERATOR_VIEW_TRACKER] Failed to convert {field_name} '{value}' to float")
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
                        logger.warning(f"[MODERATOR_VIEW_TRACKER] Skipping duplicate day {day} in Excel data")
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
                    # Only mark as not pending if daily_payments is actually filled
                    daily_payments = merged_row.get('daily_payments')
                    if daily_payments is not None:
                        # Check if it's a valid non-zero value
                        try:
                            if isinstance(daily_payments, str):
                                daily_payments_float = float(daily_payments.replace(',', '').strip())
                            else:
                                daily_payments_float = float(daily_payments)
                            merged_row['is_pending'] = False if daily_payments_float > 0 else None
                        except (ValueError, TypeError):
                            merged_row['is_pending'] = None
                    else:
                        merged_row['is_pending'] = None
                    
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
            
            # Calculate total cashback for tracker
            tracker_cashback_total = get_tracker_cashback_total(tracker_id, instance_name)
            
            # Updated summary with pending included
            logger.info(f"[MODERATOR_VIEW_TRACKER] total_payments_from_excel: {total_payments_from_excel} (type: {type(total_payments_from_excel).__name__})")
            logger.info(f"[MODERATOR_VIEW_TRACKER] pending_payments_sum: {pending_payments_sum} (type: {type(pending_payments_sum).__name__})")
            
            updated_summary = summary.copy()
            try:
                total_payments_from_excel_float = float(total_payments_from_excel) if not isinstance(total_payments_from_excel, (int, float)) else float(total_payments_from_excel)
                pending_payments_sum_float = float(pending_payments_sum) if not isinstance(pending_payments_sum, (int, float)) else float(pending_payments_sum)
                logger.info(f"[MODERATOR_VIEW_TRACKER] Converting to float: {total_payments_from_excel_float} + {pending_payments_sum_float}")
                updated_summary['total_payments'] = total_payments_from_excel_float + pending_payments_sum_float
            except (ValueError, TypeError) as e:
                logger.error(f"[MODERATOR_VIEW_TRACKER] Error converting payments to float: {e}")
                logger.error(f"[MODERATOR_VIEW_TRACKER] total_payments_from_excel: {total_payments_from_excel} (type: {type(total_payments_from_excel).__name__})")
                logger.error(f"[MODERATOR_VIEW_TRACKER] pending_payments_sum: {pending_payments_sum} (type: {type(pending_payments_sum).__name__})")
                raise
            
            updated_summary['pending_entries_count'] = len(pending_entries)
            updated_summary['pending_payments_sum'] = float(pending_payments_sum)
            updated_summary['cashback_total'] = float(tracker_cashback_total)
            
            # Calculate cashback for each day
            day_cashback_map = {}
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
                    
                    day_cashback = get_tracker_day_cashback(tracker_id, day, instance_name)
                    day_cashback_map[day] = day_cashback
            
            return render_template('moderator/view_tracker.html',
                                 tracker=tracker,
                                 tracker_data={'data': merged_data, 'parameters': tracker_data['parameters'], 'tracker_type': tracker_data['tracker_type']},
                                 summary=updated_summary,
                                 pending_entries=pending_entries,
                                 day_cashback_map=day_cashback_map,
                                 instance_name=instance_name)
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"[MODERATOR_VIEW_TRACKER] Error reading tracker data for tracker {tracker_id}: {str(e)}")
            logger.error(f"[MODERATOR_VIEW_TRACKER] Traceback: {traceback.format_exc()}")
            flash(f'Error reading tracker data: {str(e)}', 'error')
            return redirect(url_for('moderator_daily_trackers', instance_name=instance_name))

    @app.route('/<instance_name>/moderator/tracker/<int:tracker_id>/add-entry', methods=['GET', 'POST'])
    @login_required
    @moderator_required
    def moderator_add_tracker_entry(instance_name, tracker_id):
        """Moderator add entry to assigned tracker"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        tracker = get_daily_tracker_query().filter_by(id=tracker_id, is_active=True).first()
        if not tracker:
            flash('Tracker not found', 'error')
            return redirect(url_for('moderator_daily_trackers', instance_name=instance_name))
        
        # Check if tracker is assigned to this moderator
        if not is_tracker_assigned_to_moderator(tracker_id, current_user.id):
            flash('Access denied. You are not assigned to this tracker.', 'error')
            return redirect(url_for('moderator_daily_trackers', instance_name=instance_name))
        
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
                
                # Create TrackerEntry record with pending status (don't update Excel yet)
                import json
                from app_multi import TrackerEntry, get_tracker_entry_query, add_to_current_instance
                
                # Convert Decimal values to strings for JSON serialization
                def convert_decimals(obj):
                    """Recursively convert Decimal values to strings for JSON serialization"""
                    if isinstance(obj, Decimal):
                        return str(obj)
                    elif isinstance(obj, dict):
                        return {key: convert_decimals(value) for key, value in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_decimals(item) for item in obj]
                    else:
                        return obj
                
                entry_data_json = json.dumps(convert_decimals(entry_data))
                
                # Check if there's already a pending entry for this day
                existing_entry = get_tracker_entry_query().filter_by(
                    tracker_id=tracker_id,
                    day=day,
                    status='pending'
                ).first()
                
                if existing_entry:
                    # Update existing pending entry
                    existing_entry.entry_data = entry_data_json
                    existing_entry.submitted_at = datetime.utcnow()
                else:
                    # Create new pending entry
                    tracker_entry = TrackerEntry(
                        tracker_id=tracker_id,
                        day=day,
                        entry_data=entry_data_json,
                        status='pending',
                        submitted_by_user_id=current_user.id
                    )
                    add_to_current_instance(tracker_entry)
                
                # Update the tracker's updated_at timestamp
                tracker.updated_at = datetime.utcnow()
                commit_current_instance()
                
                # Log tracker entry update
                from lms_logging import get_logging_manager
                from lms_metrics import get_metrics_manager
                logging_mgr = get_logging_manager(instance_name)
                metrics_mgr = get_metrics_manager(instance_name)
                
                daily_payment = entry_data.get('daily_payments', 0)
                logging_mgr.log_moderator_action(
                    action='moderator_tracker_entry_update',
                    resource_type='tracker',
                    resource_id=tracker_id,
                    username=current_user.username,
                    details={
                        'tracker_name': tracker.tracker_name,
                        'day': day,
                        'daily_payment': str(daily_payment),
                        'customer': tracker.user.username if tracker.user else None
                    }
                )
                metrics_mgr.record_tracker_entry(
                    tracker_id=tracker_id,
                    username=current_user.username,
                    amount=float(daily_payment) if daily_payment else 0
                )
                
                flash(f'Entry for Day {day} submitted for approval', 'success')
                return redirect(url_for('moderator_view_tracker', 
                                      instance_name=instance_name, 
                                      tracker_id=tracker_id))
                
            except Exception as e:
                flash(f'Error adding entry: {str(e)}', 'error')
                print(f"Error adding entry: {e}")
        
        # GET request - show form
        try:
            tracker_data = get_tracker_data(instance_name, tracker.filename)
            return render_template('moderator/add_tracker_entry.html',
                                 tracker=tracker,
                                 tracker_data=tracker_data,
                                 instance_name=instance_name)
        except Exception as e:
            flash(f'Error reading tracker data: {str(e)}', 'error')
            return redirect(url_for('moderator_daily_trackers', instance_name=instance_name))

    @app.route('/<instance_name>/moderator/tracker/<int:tracker_id>/edit-entry/<int:row_index>', methods=['GET', 'POST'])
    @login_required
    @moderator_required
    def moderator_edit_tracker_entry(instance_name, tracker_id, row_index):
        """Moderator edit entry in assigned tracker"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        tracker = get_daily_tracker_query().filter_by(id=tracker_id, is_active=True).first()
        if not tracker:
            flash('Tracker not found', 'error')
            return redirect(url_for('moderator_daily_trackers', instance_name=instance_name))
        
        # Check if tracker is assigned to this moderator
        if not is_tracker_assigned_to_moderator(tracker_id, current_user.id):
            flash('Access denied. You are not assigned to this tracker.', 'error')
            return redirect(url_for('moderator_daily_trackers', instance_name=instance_name))
        
        # Get tracker data
        try:
            tracker_data = get_tracker_data(instance_name, tracker.filename)
        except Exception as e:
            flash(f'Error reading tracker data: {str(e)}', 'error')
            return redirect(url_for('moderator_view_tracker', instance_name=instance_name, tracker_id=tracker_id))
        
        # Validate row_index
        if row_index < 0 or row_index >= len(tracker_data['data']):
            flash('Invalid row index', 'error')
            return redirect(url_for('moderator_view_tracker', instance_name=instance_name, tracker_id=tracker_id))
        
        row_data = tracker_data['data'][row_index]
        
        if request.method == 'POST':
            try:
                entry_data = {}
                
                # Collect all form fields dynamically
                for key, value in request.form.items():
                    # Include all non-empty values (including "0" for numeric fields)
                    if value is not None and value.strip() != '':
                        # Convert numeric fields
                        if key in ['day', 'daily_payments', 'cumulative', 'balance', 
                                  'reinvest', 'pocket_money', 'total_invested']:
                            try:
                                entry_data[key] = Decimal(value) if key != 'day' else int(value)
                            except:
                                entry_data[key] = value
                        else:
                            entry_data[key] = value
                    # Handle explicit "0" for daily_payments
                    elif key == 'daily_payments' and value == '0':
                        entry_data[key] = Decimal('0')
                
                # Create TrackerEntry record with pending status (don't update Excel yet)
                import json
                from app_multi import TrackerEntry, get_tracker_entry_query, add_to_current_instance
                
                day = entry_data.get('day', row_data.get('day', row_index + 1))
                
                # Convert Decimal values to strings for JSON serialization
                def convert_decimals(obj):
                    """Recursively convert Decimal values to strings for JSON serialization"""
                    if isinstance(obj, Decimal):
                        return str(obj)
                    elif isinstance(obj, dict):
                        return {key: convert_decimals(value) for key, value in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_decimals(item) for item in obj]
                    else:
                        return obj
                
                entry_data_json = json.dumps(convert_decimals(entry_data))
                
                # Check if there's already a pending entry for this day
                existing_entry = get_tracker_entry_query().filter_by(
                    tracker_id=tracker_id,
                    day=day,
                    status='pending'
                ).first()
                
                if existing_entry:
                    # Update existing pending entry
                    existing_entry.entry_data = entry_data_json
                    existing_entry.submitted_at = datetime.utcnow()
                else:
                    # Create new pending entry
                    tracker_entry = TrackerEntry(
                        tracker_id=tracker_id,
                        day=day,
                        entry_data=entry_data_json,
                        status='pending',
                        submitted_by_user_id=current_user.id
                    )
                    add_to_current_instance(tracker_entry)
                
                # Update the tracker's updated_at timestamp
                tracker.updated_at = datetime.utcnow()
                commit_current_instance()
                
                # Log tracker entry update
                from lms_logging import get_logging_manager
                from lms_metrics import get_metrics_manager
                logging_mgr = get_logging_manager(instance_name)
                metrics_mgr = get_metrics_manager(instance_name)
                
                daily_payment = entry_data.get('daily_payments', 0)
                logging_mgr.log_moderator_action(
                    action='moderator_tracker_entry_update',
                    resource_type='tracker',
                    resource_id=tracker_id,
                    username=current_user.username,
                    details={
                        'tracker_name': tracker.tracker_name,
                        'day': row_data.get('day', row_index),
                        'daily_payment': str(daily_payment),
                        'customer': tracker.user.username if tracker.user else None,
                        'row_index': row_index
                    }
                )
                metrics_mgr.record_tracker_entry(
                    tracker_id=tracker_id,
                    username=current_user.username,
                    amount=float(daily_payment) if daily_payment else 0
                )
                
                flash(f'Entry for Day {row_data.get("day", row_index)} submitted for approval', 'success')
                return redirect(url_for('moderator_view_tracker', 
                                      instance_name=instance_name, 
                                      tracker_id=tracker_id))
                
            except Exception as e:
                flash(f'Error updating entry: {str(e)}', 'error')
                print(f"Error updating entry: {e}")
        
        # GET request - render edit template
        return render_template('moderator/edit_tracker_entry.html',
                             tracker=tracker,
                             tracker_data=tracker_data,
                             row_data=row_data,
                             row_index=row_index,
                             instance_name=instance_name)

    @app.route('/<instance_name>/moderator/tracker/<int:tracker_id>/no-payment/<int:row_index>', methods=['POST'])
    @login_required
    @moderator_required
    def moderator_no_payment_today(instance_name, tracker_id, row_index):
        """Quick action: Set no payment for today (daily_payments=0, payment_mode=Other)"""
        if instance_name not in VALID_INSTANCES:
            return jsonify({'success': False, 'error': 'Invalid instance'}), 400
        
        tracker = get_daily_tracker_query().filter_by(id=tracker_id, is_active=True).first()
        if not tracker:
            return jsonify({'success': False, 'error': 'Tracker not found'}), 404
        
        # Check if tracker is assigned to this moderator
        if not is_tracker_assigned_to_moderator(tracker_id, current_user.id):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        try:
            tracker_data = get_tracker_data(instance_name, tracker.filename)
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error reading tracker data: {str(e)}'}), 500
        
        # Validate row_index
        if row_index < 0 or row_index >= len(tracker_data['data']):
            return jsonify({'success': False, 'error': 'Invalid row index'}), 400
        
        row_data = tracker_data['data'][row_index]
        
        try:
            # Set no payment: daily_payments=0, payment_mode=Other
            entry_data = {
                'daily_payments': Decimal('0'),
                'payment_mode': 'Other'
            }
            
            # Update the tracker by row index
            sys.path.insert(0, str(Path(__file__).parent / 'daily-trackers'))
            from tracker_manager import update_tracker_entry_by_index
            update_tracker_entry_by_index(instance_name, tracker.filename, row_index, entry_data)
            
            # Update the tracker's updated_at timestamp
            tracker.updated_at = datetime.utcnow()
            commit_current_instance()
            
            # Log tracker entry update
            from lms_logging import get_logging_manager
            from lms_metrics import get_metrics_manager
            logging_mgr = get_logging_manager(instance_name)
            metrics_mgr = get_metrics_manager(instance_name)
            
            logging_mgr.log_moderator_action(
                action='moderator_tracker_entry_update',
                resource_type='tracker',
                resource_id=tracker_id,
                username=current_user.username,
                    details={
                        'tracker_name': tracker.tracker_name,
                        'day': row_data.get('day', row_index),
                        'daily_payment': '0',
                        'payment_mode': 'Other',
                        'action': 'no_payment_today',
                        'customer': tracker.user.username if tracker.user else None,
                        'row_index': row_index
                    }
            )
            metrics_mgr.record_tracker_entry(
                tracker_id=tracker_id,
                username=current_user.username,
                amount=0.0
            )
            
            return jsonify({
                'success': True,
                'message': f'Entry for Day {row_data.get("day", row_index)} updated successfully'
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error updating entry: {str(e)}'}), 500

    @app.route('/<instance_name>/moderator/users')
    @login_required
    @moderator_required
    def moderator_users(instance_name):
        """View all users - Access denied for moderators (sensitive data)"""
        flash('Access denied. User information is restricted to administrators only.', 'error')
        return redirect(url_for('moderator_dashboard', instance_name=instance_name))

    @app.route('/<instance_name>/moderator/my-loans')
    @login_required
    @moderator_required
    def moderator_my_loans(instance_name):
        """Moderator's own loans"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        loans = get_loan_query().filter_by(customer_id=current_user.id, is_active=True).all()
        
        loans_data = []
        for loan in loans:
            interest_data = calculate_accumulated_interest(loan)
            loans_data.append({
                'loan': loan,
                'accumulated_interest_daily': interest_data['daily'],
                'accumulated_interest_monthly': interest_data['monthly']
            })
        
        return render_template('moderator/my_loans.html',
                             loans_data=loans_data,
                             instance_name=instance_name)

    @app.route('/<instance_name>/moderator/my-trackers')
    @login_required
    @moderator_required
    def moderator_my_trackers(instance_name):
        """Moderator's own trackers"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        trackers = get_daily_tracker_query().filter_by(
            user_id=current_user.id, 
            is_active=True,
            is_closed_by_user=False
        ).all()
        
        tracker_summaries = []
        total_pending = 0
        
        for tracker in trackers:
            try:
                summary = get_tracker_summary(instance_name, tracker.filename)
                total_pending += summary.get('pending', 0)
                
                tracker_summaries.append({
                    'tracker': tracker,
                    'last_paid_date': summary.get('last_paid_date'),
                    'total_payments': summary['total_payments'],
                    'pending': summary.get('pending', 0),
                    'balance': summary.get('balance', 0),
                    'cumulative': summary.get('cumulative', 0),
                    'days_with_payments': summary['total_days'],
                    'total_days_count': summary['total_days_count']
                })
            except Exception as e:
                print(f"Error processing tracker {tracker.id}: {e}")
                tracker_summaries.append({
                    'tracker': tracker,
                    'error': str(e)
                })
        
        return render_template('moderator/my_trackers.html',
                             tracker_summaries=tracker_summaries,
                             total_pending=total_pending,
                             instance_name=instance_name)

