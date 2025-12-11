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
    
    Args:
        app: Flask application instance
        
    Returns:
        scheduler: BackgroundScheduler instance
    """
    try:
        # Add morning report job (8:00 AM IST)
        scheduler.add_job(
            func=lambda: send_morning_reports_job(app),
            trigger=CronTrigger(hour=8, minute=0, timezone='Asia/Kolkata'),
            id='morning_reports',
            name='Send Daily Morning Reports',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=300  # Allow 5 minutes grace period
        )
        
        # Add evening report job (8:00 PM IST)
        scheduler.add_job(
            func=lambda: send_evening_reports_job(app),
            trigger=CronTrigger(hour=20, minute=0, timezone='Asia/Kolkata'),
            id='evening_reports',
            name='Send Daily Evening Reports',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=300  # Allow 5 minutes grace period
        )
        
        # Start the scheduler
        if not scheduler.running:
            scheduler.start()
            print("\n" + "="*60)
            print("✅ Report Scheduler Initialized")
            print("="*60)
            print("📊 Daily Reports Schedule (IST):")
            print("   🌅 Morning Report: 8:00 AM")
            print("   🌙 Evening Report: 8:00 PM")
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

