"""
Daily Report Generation Module
===============================

Generates comprehensive daily reports for admins including:
- Loan performance metrics
- Tracker activity
- Cashback transactions
- User activity
- Trends and comparisons
- Priority alerts

Author: LMS Development Team
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func, and_, or_
import json

# Import models and utilities
from app_multi import (
    db_manager, User, Loan, Payment, DailyTracker, CashbackTransaction,
    CashbackRedemption, ReportHistory, get_user_cashback_balance
)


def get_date_range(report_date=None):
    """Get start and end datetime for the report date"""
    if report_date is None:
        report_date = date.today()
    
    start_datetime = datetime.combine(report_date, datetime.min.time())
    end_datetime = datetime.combine(report_date, datetime.max.time())
    
    return start_datetime, end_datetime


def get_executive_summary(instance_name, report_date=None):
    """Generate executive summary with key metrics"""
    session = db_manager.get_session_for_instance(instance_name)
    start_dt, end_dt = get_date_range(report_date)
    
    # Today's collections
    todays_payments = session.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.payment_date >= start_dt,
            Payment.payment_date <= end_dt,
            Payment.status == 'verified'
        )
    ).scalar() or Decimal('0')
    
    # Pending approvals count
    pending_payments = session.query(Payment).filter_by(status='pending').count()
    
    from app_trackers import TrackerEntry
    pending_entries = session.query(TrackerEntry).filter_by(status='pending').count()
    
    # Active users today
    from app_cashback import get_cashback_transaction_query
    active_users_today = session.query(func.count(func.distinct(Payment.loan_id))).filter(
        and_(
            Payment.payment_date >= start_dt,
            Payment.payment_date <= end_dt
        )
    ).scalar() or 0
    
    # Overdue payments (accumulated interest > 30 days old)
    overdue_count = 0  # Simplified for now
    
    return {
        'todays_collections': float(todays_payments),
        'pending_approvals': pending_payments + pending_entries,
        'overdue_payments': overdue_count,
        'active_users_today': active_users_today,
        'report_date': report_date or date.today()
    }


def get_loan_performance(instance_name, report_date=None):
    """Generate loan performance metrics"""
    session = db_manager.get_session_for_instance(instance_name)
    start_dt, end_dt = get_date_range(report_date)
    
    # Today's payments
    todays_payments_query = session.query(Payment).filter(
        and_(
            Payment.payment_date >= start_dt,
            Payment.payment_date <= end_dt,
            Payment.status == 'verified'
        )
    )
    
    payment_count = todays_payments_query.count()
    total_amount = session.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.payment_date >= start_dt,
            Payment.payment_date <= end_dt,
            Payment.status == 'verified'
        )
    ).scalar() or Decimal('0')
    
    interest_amount = session.query(func.sum(Payment.interest_amount)).filter(
        and_(
            Payment.payment_date >= start_dt,
            Payment.payment_date <= end_dt,
            Payment.status == 'verified'
        )
    ).scalar() or Decimal('0')
    
    principal_amount = session.query(func.sum(Payment.principal_amount)).filter(
        and_(
            Payment.payment_date >= start_dt,
            Payment.payment_date <= end_dt,
            Payment.status == 'verified'
        )
    ).scalar() or Decimal('0')
    
    # Pending payments
    pending_payments = session.query(Payment).filter_by(status='pending')
    pending_count = pending_payments.count()
    pending_amount = session.query(func.sum(Payment.amount)).filter(
        Payment.status == 'pending'
    ).scalar() or Decimal('0')
    
    # New loans created today
    new_loans = session.query(Loan).filter(
        and_(
            Loan.created_at >= start_dt,
            Loan.created_at <= end_dt
        )
    ).all()
    
    new_loans_count = len(new_loans)
    new_loans_principal = sum(loan.principal_amount for loan in new_loans)
    
    # Top paying customers
    top_customers = session.query(
        Loan.customer_id,
        func.sum(Payment.amount).label('total_paid')
    ).join(Payment, Loan.id == Payment.loan_id).filter(
        and_(
            Payment.payment_date >= start_dt,
            Payment.payment_date <= end_dt,
            Payment.status == 'verified'
        )
    ).group_by(Loan.customer_id).order_by(func.sum(Payment.amount).desc()).limit(5).all()
    
    top_customers_list = []
    for customer_id, amount in top_customers:
        user = session.query(User).get(customer_id)
        if user:
            top_customers_list.append({
                'username': user.username,
                'amount': float(amount)
            })
    
    return {
        'todays_payments': {
            'count': payment_count,
            'total_amount': float(total_amount),
            'interest_amount': float(interest_amount),
            'principal_amount': float(principal_amount)
        },
        'pending_payments': {
            'count': pending_count,
            'amount': float(pending_amount)
        },
        'new_loans': {
            'count': new_loans_count,
            'principal': float(new_loans_principal)
        },
        'top_customers': top_customers_list
    }


def get_tracker_performance(instance_name, report_date=None):
    """Generate tracker performance metrics"""
    session = db_manager.get_session_for_instance(instance_name)
    start_dt, end_dt = get_date_range(report_date)
    
    from app_trackers import TrackerEntry, get_tracker_data
    
    # Today's verified entries
    todays_entries = session.query(TrackerEntry).filter(
        and_(
            TrackerEntry.verified_at >= start_dt,
            TrackerEntry.verified_at <= end_dt,
            TrackerEntry.status == 'verified'
        )
    ).all()
    
    entry_count = len(todays_entries)
    
    # Calculate total amount from entries
    total_amount = Decimal('0')
    for entry in todays_entries:
        entry_data = json.loads(entry.entry_data)
        daily_payment = entry_data.get('daily_payments', 0)
        try:
            total_amount += Decimal(str(daily_payment))
        except:
            pass
    
    # Pending entries
    pending_entries = session.query(TrackerEntry).filter_by(status='pending')
    pending_count = pending_entries.count()
    
    # Active trackers
    active_trackers = session.query(DailyTracker).filter_by(
        is_active=True,
        is_closed_by_user=False
    ).count()
    
    total_trackers = session.query(DailyTracker).count()
    
    return {
        'todays_entries': {
            'count': entry_count,
            'total_amount': float(total_amount)
        },
        'pending_entries': {
            'count': pending_count
        },
        'active_trackers': active_trackers,
        'total_trackers': total_trackers,
        'completion_rate': round((entry_count / active_trackers * 100) if active_trackers > 0 else 0, 1)
    }


def get_cashback_activity(instance_name, report_date=None):
    """Generate cashback activity metrics"""
    session = db_manager.get_session_for_instance(instance_name)
    start_dt, end_dt = get_date_range(report_date)
    
    # Distributed today
    auto_loan = session.query(func.sum(CashbackTransaction.points)).filter(
        and_(
            CashbackTransaction.created_at >= start_dt,
            CashbackTransaction.created_at <= end_dt,
            CashbackTransaction.transaction_type.in_(['loan_interest_auto', 'loan_interest_manual'])
        )
    ).scalar() or Decimal('0')
    
    auto_loan_count = session.query(CashbackTransaction).filter(
        and_(
            CashbackTransaction.created_at >= start_dt,
            CashbackTransaction.created_at <= end_dt,
            CashbackTransaction.transaction_type.in_(['loan_interest_auto', 'loan_interest_manual'])
        )
    ).count()
    
    auto_tracker = session.query(func.sum(CashbackTransaction.points)).filter(
        and_(
            CashbackTransaction.created_at >= start_dt,
            CashbackTransaction.created_at <= end_dt,
            CashbackTransaction.transaction_type == 'tracker_entry'
        )
    ).scalar() or Decimal('0')
    
    auto_tracker_count = session.query(CashbackTransaction).filter(
        and_(
            CashbackTransaction.created_at >= start_dt,
            CashbackTransaction.created_at <= end_dt,
            CashbackTransaction.transaction_type == 'tracker_entry'
        )
    ).count()
    
    manual = session.query(func.sum(CashbackTransaction.points)).filter(
        and_(
            CashbackTransaction.created_at >= start_dt,
            CashbackTransaction.created_at <= end_dt,
            CashbackTransaction.transaction_type == 'unconditional'
        )
    ).scalar() or Decimal('0')
    
    manual_count = session.query(CashbackTransaction).filter(
        and_(
            CashbackTransaction.created_at >= start_dt,
            CashbackTransaction.created_at <= end_dt,
            CashbackTransaction.transaction_type == 'unconditional'
        )
    ).count()
    
    # Redeemed today
    redeemed = session.query(func.sum(CashbackTransaction.points)).filter(
        and_(
            CashbackTransaction.created_at >= start_dt,
            CashbackTransaction.created_at <= end_dt,
            CashbackTransaction.transaction_type == 'redemption'
        )
    ).scalar() or Decimal('0')
    
    redeemed_count = session.query(CashbackTransaction).filter(
        and_(
            CashbackTransaction.created_at >= start_dt,
            CashbackTransaction.created_at <= end_dt,
            CashbackTransaction.transaction_type == 'redemption'
        )
    ).count()
    
    # Pending redemptions
    pending_redemptions = session.query(CashbackRedemption).filter_by(status='pending')
    pending_count = pending_redemptions.count()
    pending_amount = session.query(func.sum(CashbackRedemption.amount)).filter(
        CashbackRedemption.status == 'pending'
    ).scalar() or Decimal('0')
    
    # Total cashback balance across all users
    all_users = session.query(User).all()
    total_balance = sum(get_user_cashback_balance(user.id, instance_name) for user in all_users)
    
    # Top earners
    top_earners_query = session.query(
        CashbackTransaction.to_user_id,
        func.sum(CashbackTransaction.points).label('total_earned')
    ).filter(
        and_(
            CashbackTransaction.created_at >= start_dt,
            CashbackTransaction.created_at <= end_dt,
            CashbackTransaction.to_user_id.isnot(None)
        )
    ).group_by(CashbackTransaction.to_user_id).order_by(func.sum(CashbackTransaction.points).desc()).limit(5).all()
    
    top_earners = []
    for user_id, points in top_earners_query:
        user = session.query(User).get(user_id)
        if user:
            top_earners.append({
                'username': user.username,
                'points': float(points)
            })
    
    return {
        'distributed_today': {
            'automatic_loan': {'points': float(auto_loan), 'count': auto_loan_count},
            'automatic_tracker': {'points': float(auto_tracker), 'count': auto_tracker_count},
            'manual_admin': {'points': float(manual), 'count': manual_count}
        },
        'redeemed_today': {
            'points': float(redeemed),
            'count': redeemed_count
        },
        'pending_redemptions': {
            'count': pending_count,
            'amount': float(pending_amount)
        },
        'total_balance': float(total_balance),
        'top_earners': top_earners
    }


def get_user_activity(instance_name, report_date=None):
    """Generate user activity metrics"""
    session = db_manager.get_session_for_instance(instance_name)
    start_dt, end_dt = get_date_range(report_date)
    
    # New users created today
    new_users = session.query(User).filter(
        and_(
            User.created_at >= start_dt,
            User.created_at <= end_dt
        )
    ).count()
    
    # Total active users
    total_users = session.query(User).count()
    
    # Users with activity today (payments or tracker entries)
    active_user_ids = set()
    
    # From payments
    payment_users = session.query(Loan.customer_id).join(Payment, Loan.id == Payment.loan_id).filter(
        and_(
            Payment.payment_date >= start_dt,
            Payment.payment_date <= end_dt
        )
    ).distinct().all()
    active_user_ids.update([u[0] for u in payment_users])
    
    # From tracker entries
    from app_trackers import TrackerEntry
    tracker_users = session.query(TrackerEntry.submitted_by_user_id).filter(
        and_(
            TrackerEntry.submitted_at >= start_dt,
            TrackerEntry.submitted_at <= end_dt
        )
    ).distinct().all()
    active_user_ids.update([u[0] for u in tracker_users])
    
    unique_active_users = len(active_user_ids)
    
    return {
        'new_users': new_users,
        'total_users': total_users,
        'active_users_today': unique_active_users
    }


def get_action_items(instance_name):
    """Generate priority action items for admin attention"""
    session = db_manager.get_session_for_instance(instance_name)
    
    urgent = []
    review = []
    
    # Urgent: Old pending payments
    old_payments = session.query(Payment).filter(
        and_(
            Payment.status == 'pending',
            Payment.payment_date < datetime.now() - timedelta(days=2)
        )
    ).all()
    
    if old_payments:
        urgent.append(f"{len(old_payments)} payments pending approval (>2 days old)")
    
    # Urgent: Pending redemptions
    pending_redemptions = session.query(CashbackRedemption).filter_by(status='pending').count()
    if pending_redemptions > 0:
        urgent.append(f"{pending_redemptions} redemption request{'s' if pending_redemptions != 1 else ''} waiting")
    
    # Review: Pending tracker entries
    from app_trackers import TrackerEntry
    pending_entries = session.query(TrackerEntry).filter_by(status='pending').count()
    if pending_entries > 0:
        review.append(f"{pending_entries} tracker entries pending approval")
    
    return {
        'urgent': urgent,
        'review': review
    }


def get_trends_comparison(instance_name, report_date=None):
    """Generate trends and comparisons"""
    session = db_manager.get_session_for_instance(instance_name)
    
    if report_date is None:
        report_date = date.today()
    
    today_start, today_end = get_date_range(report_date)
    yesterday_start, yesterday_end = get_date_range(report_date - timedelta(days=1))
    
    # Today's collections
    today_collections = session.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.payment_date >= today_start,
            Payment.payment_date <= today_end,
            Payment.status == 'verified'
        )
    ).scalar() or Decimal('0')
    
    # Yesterday's collections
    yesterday_collections = session.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.payment_date >= yesterday_start,
            Payment.payment_date <= yesterday_end,
            Payment.status == 'verified'
        )
    ).scalar() or Decimal('0')
    
    # Calculate percentage change
    if yesterday_collections > 0:
        collections_change = ((today_collections - yesterday_collections) / yesterday_collections) * 100
    else:
        collections_change = 0 if today_collections == 0 else 100
    
    # Weekly average
    week_start = datetime.now() - timedelta(days=7)
    weekly_collections = session.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.payment_date >= week_start,
            Payment.status == 'verified'
        )
    ).scalar() or Decimal('0')
    
    weekly_avg = float(weekly_collections) / 7 if weekly_collections > 0 else 0
    
    return {
        'vs_yesterday': {
            'collections_change_percent': round(float(collections_change), 1)
        },
        'vs_last_week': {
            'weekly_avg': round(weekly_avg, 2)
        }
    }


def get_quick_stats(instance_name):
    """Generate quick statistics"""
    session = db_manager.get_session_for_instance(instance_name)
    
    # Total active loans
    active_loans = session.query(Loan).filter_by(status='active', is_active=True).count()
    
    # Total principal
    total_principal = session.query(func.sum(Loan.principal_amount)).filter_by(
        status='active',
        is_active=True
    ).scalar() or Decimal('0')
    
    # Total active trackers
    active_trackers = session.query(DailyTracker).filter_by(
        is_active=True,
        is_closed_by_user=False
    ).count()
    
    # Total tracker investment
    total_investment = session.query(func.sum(DailyTracker.investment)).filter_by(
        is_active=True,
        is_closed_by_user=False
    ).scalar() or Decimal('0')
    
    return {
        'total_loans': active_loans,
        'total_principal': float(total_principal),
        'total_trackers': active_trackers,
        'total_investment': float(total_investment)
    }


def generate_daily_report(instance_name, report_type='on_demand', report_date=None):
    """
    Generate comprehensive daily report
    
    Args:
        instance_name: Instance to generate report for
        report_type: Type of report ('morning', 'evening', 'on_demand')
        report_date: Date for the report (defaults to today)
    
    Returns:
        dict: Complete report data
    """
    try:
        report_data = {
            'report_type': report_type,
            'instance_name': instance_name,
            'generated_at': datetime.now().isoformat(),
            'executive_summary': get_executive_summary(instance_name, report_date),
            'loan_performance': get_loan_performance(instance_name, report_date),
            'tracker_performance': get_tracker_performance(instance_name, report_date),
            'cashback_activity': get_cashback_activity(instance_name, report_date),
            'user_activity': get_user_activity(instance_name, report_date),
            'action_items': get_action_items(instance_name),
            'trends': get_trends_comparison(instance_name, report_date),
            'quick_stats': get_quick_stats(instance_name)
        }
        
        return report_data
        
    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return None


def send_report_email(user, report_data, instance_name):
    """Send report email to user"""
    from app_notify_email import EmailNotificationProvider
    from app_notifications import Notification, NotificationChannel
    
    try:
        # Create notification
        notification = Notification(
            channel=NotificationChannel.EMAIL,
            recipient_id=user.id,
            subject=f"Daily Report - {report_data['executive_summary']['report_date']} ({report_data['report_type'].title()})",
            message="",
            template='daily_report',
            context={
                'user': user,
                'report_data': report_data,
                'instance_name': instance_name
            },
            instance_name=instance_name
        )
        
        # Send via email provider
        provider = EmailNotificationProvider()
        success = provider.send(notification)
        
        # Log to report history
        session = db_manager.get_session_for_instance(instance_name)
        history = ReportHistory(
            user_id=user.id,
            report_type=report_data['report_type'],
            sent_successfully=success,
            report_data=report_data
        )
        session.add(history)
        session.commit()
        
        return success
        
    except Exception as e:
        print(f"Error sending report email: {e}")
        import traceback
        traceback.print_exc()
        return False

