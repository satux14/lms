"""
Application Scheduler Module
=============================

Handles scheduled tasks using APScheduler (BackgroundScheduler).
This runs within the Flask application process, eliminating the need for
external cron jobs or separate scheduler processes.

Features:
- Daily morning and evening report generation
- Timezone-aware scheduling
- Automatic retry on failure
- Runs in background thread
- No Docker/cron configuration needed

Author: LMS Development Team
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import atexit
import logging
import os

# Configure logging
logging.basicConfig()
scheduler_logger = logging.getLogger('apscheduler')
scheduler_logger.setLevel(logging.INFO)

# Create scheduler instance
scheduler = BackgroundScheduler(daemon=True, timezone='Asia/Kolkata')


def send_morning_reports_job(app):
    """
    Job function to send morning reports
    Runs with Flask app context
    """
    with app.app_context():
        try:
            print(f"\n{'='*60}")
            print(f"📊 Scheduled Morning Reports")
            print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}\n")
            
            from app_multi import db_manager, User, ReportPreference
            from app_reports import generate_daily_report, send_report_email
            
            # Valid instances
            instances = ['prod', 'dev', 'testing']
            total_sent = 0
            total_failed = 0
            
            for instance in instances:
                try:
                    session = db_manager.get_session_for_instance(instance)
                    
                    # Get all admins with reports enabled
                    admins = session.query(User).filter_by(is_admin=True).all()
                    
                    for admin in admins:
                        # Check report preferences
                        pref = session.query(ReportPreference).filter_by(
                            user_id=admin.id
                        ).first()
                        
                        # Skip if explicitly disabled or no email
                        if pref and not pref.enabled:
                            continue
                        
                        if not admin.email:
                            print(f"⚠️  {admin.username}: No email address")
                            continue
                        
                        try:
                            # Generate report
                            report_data = generate_daily_report(instance, 'morning')
                            
                            if report_data:
                                # Send email
                                success = send_report_email(admin, report_data, instance)
                                
                                if success:
                                    print(f"✓ Sent morning report to {admin.username} ({instance})")
                                    total_sent += 1
                                else:
                                    print(f"✗ Failed to send to {admin.username} ({instance})")
                                    total_failed += 1
                            else:
                                total_failed += 1
                        
                        except Exception as e:
                            print(f"✗ Error for {admin.username}: {e}")
                            total_failed += 1
                
                except Exception as e:
                    print(f"✗ Error processing instance {instance}: {e}")
            
            print(f"\n{'='*60}")
            print(f"✓ Successfully sent: {total_sent} reports")
            if total_failed > 0:
                print(f"✗ Failed: {total_failed} reports")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"✗ Fatal error in morning reports: {e}")
            import traceback
            traceback.print_exc()


def send_evening_reports_job(app):
    """
    Job function to send evening reports
    Runs with Flask app context
    """
    with app.app_context():
        try:
            print(f"\n{'='*60}")
            print(f"📊 Scheduled Evening Reports")
            print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}\n")
            
            from app_multi import db_manager, User, ReportPreference
            from app_reports import generate_daily_report, send_report_email
            
            # Valid instances
            instances = ['prod', 'dev', 'testing']
            total_sent = 0
            total_failed = 0
            
            for instance in instances:
                try:
                    session = db_manager.get_session_for_instance(instance)
                    
                    # Get all admins with reports enabled
                    admins = session.query(User).filter_by(is_admin=True).all()
                    
                    for admin in admins:
                        # Check report preferences
                        pref = session.query(ReportPreference).filter_by(
                            user_id=admin.id
                        ).first()
                        
                        # Skip if explicitly disabled or no email
                        if pref and not pref.enabled:
                            continue
                        
                        if not admin.email:
                            print(f"⚠️  {admin.username}: No email address")
                            continue
                        
                        try:
                            # Generate report
                            report_data = generate_daily_report(instance, 'evening')
                            
                            if report_data:
                                # Send email
                                success = send_report_email(admin, report_data, instance)
                                
                                if success:
                                    print(f"✓ Sent evening report to {admin.username} ({instance})")
                                    total_sent += 1
                                else:
                                    print(f"✗ Failed to send to {admin.username} ({instance})")
                                    total_failed += 1
                            else:
                                total_failed += 1
                        
                        except Exception as e:
                            print(f"✗ Error for {admin.username}: {e}")
                            total_failed += 1
                
                except Exception as e:
                    print(f"✗ Error processing instance {instance}: {e}")
            
            print(f"\n{'='*60}")
            print(f"✓ Successfully sent: {total_sent} reports")
            if total_failed > 0:
                print(f"✗ Failed: {total_failed} reports")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"✗ Fatal error in evening reports: {e}")
            import traceback
            traceback.print_exc()


def init_scheduler(app):
    """
    Initialize scheduler with Flask app
    
    Sets up scheduled jobs for morning and evening reports.
    The scheduler runs in a background thread within the Flask process.
    Schedule times are read from the first admin user's ReportPreference.
    
    In development mode with Flask's auto-reloader, this prevents duplicate
    scheduler initialization by only running in the main process.
    
    Args:
        app: Flask application instance
        
    Returns:
        scheduler: BackgroundScheduler instance
    """
    # In Flask development mode with auto-reload, skip initialization in reloader process
    # WERKZEUG_RUN_MAIN is set to 'true' only in the main process, not the reloader
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true' and app.debug:
        print("⏭️  Skipping scheduler initialization in Flask reloader process")
        return scheduler
    
    try:
        # Default times
        morning_hour = 8
        morning_minute = 0
        evening_hour = 20
        evening_minute = 0
        
        # Try to read schedule from database
        with app.app_context():
            try:
                from app_multi import db_manager, User, ReportPreference
                
                # Use 'prod' instance for configuration (you can change this)
                session = db_manager.get_session_for_instance('prod')
                
                # Get first admin user's preferences
                admin = session.query(User).filter_by(is_admin=True).first()
                
                if admin:
                    pref = session.query(ReportPreference).filter_by(user_id=admin.id).first()
                    if pref:
                        # Parse morning time (HH:MM format)
                        if pref.morning_time:
                            try:
                                morning_parts = pref.morning_time.split(':')
                                morning_hour = int(morning_parts[0])
                                morning_minute = int(morning_parts[1]) if len(morning_parts) > 1 else 0
                            except (ValueError, IndexError):
                                print(f"⚠️  Invalid morning_time format: {pref.morning_time}, using default 08:00")
                        
                        # Parse evening time (HH:MM format)
                        if pref.evening_time:
                            try:
                                evening_parts = pref.evening_time.split(':')
                                evening_hour = int(evening_parts[0])
                                evening_minute = int(evening_parts[1]) if len(evening_parts) > 1 else 0
                            except (ValueError, IndexError):
                                print(f"⚠️  Invalid evening_time format: {pref.evening_time}, using default 20:00")
                        
                        print(f"📅 Loaded schedule from admin preferences: {pref.morning_time} / {pref.evening_time}")
            
            except Exception as e:
                print(f"⚠️  Could not load schedule from database, using defaults: {e}")
        
        # Add morning report job with configured time
        scheduler.add_job(
            func=lambda: send_morning_reports_job(app),
            trigger=CronTrigger(hour=morning_hour, minute=morning_minute, timezone='Asia/Kolkata'),
            id='morning_reports',
            name='Send Daily Morning Reports',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=300  # Allow 5 minutes grace period
        )
        
        # Add evening report job with configured time
        scheduler.add_job(
            func=lambda: send_evening_reports_job(app),
            trigger=CronTrigger(hour=evening_hour, minute=evening_minute, timezone='Asia/Kolkata'),
            id='evening_reports',
            name='Send Daily Evening Reports',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=300  # Allow 5 minutes grace period
        )
        
        # Add job to process pending approval notifications every minute
        def process_approval_notifications_job():
            """Job function to process pending approval notifications"""
            with app.app_context():
                try:
                    from app_notifications import process_pending_approval_notifications
                    process_pending_approval_notifications()
                except Exception as e:
                    print(f"Error processing approval notifications: {e}")
                    import traceback
                    traceback.print_exc()
        
        scheduler.add_job(
            func=process_approval_notifications_job,
            trigger='interval',
            minutes=1,
            id='process_approval_notifications',
            name='Process Pending Approval Notifications',
            replace_existing=True,
            max_instances=1
        )
        
        # Start the scheduler
        if not scheduler.running:
            scheduler.start()
            print("\n" + "="*60)
            print("✅ Report Scheduler Initialized")
            print("="*60)
            print("📊 Daily Reports Schedule (IST):")
            print(f"   🌅 Morning Report: {morning_hour:02d}:{morning_minute:02d}")
            print(f"   🌙 Evening Report: {evening_hour:02d}:{evening_minute:02d}")
            print("📧 Approval Notifications: Processed every minute")
            print("="*60 + "\n")
        
        # Register shutdown hook
        atexit.register(lambda: scheduler.shutdown(wait=False))
        
        return scheduler
        
    except Exception as e:
        print(f"✗ Error initializing scheduler: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_next_run_times():
    """
    Get next scheduled run times for all jobs
    
    Returns:
        dict: Job names and their next run times
    """
    next_runs = {}
    for job in scheduler.get_jobs():
        next_runs[job.name] = job.next_run_time
    return next_runs


def trigger_job_now(job_id):
    """
    Manually trigger a scheduled job immediately
    
    Args:
        job_id: ID of the job to trigger ('morning_reports' or 'evening_reports')
        
    Returns:
        bool: True if triggered successfully
    """
    try:
        job = scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now())
            return True
        return False
    except Exception as e:
        print(f"Error triggering job {job_id}: {e}")
        return False


def list_scheduled_jobs():
    """
    List all scheduled jobs with their details
    
    Returns:
        list: List of job details
    """
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time,
            'trigger': str(job.trigger)
        })
    return jobs

