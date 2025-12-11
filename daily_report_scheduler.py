#!/usr/bin/env python3
"""
Daily Report Scheduler
======================

This script sends scheduled daily reports to admins.
Designed to be run via cron jobs for automated report delivery.

Usage:
    python3 daily_report_scheduler.py <report_type> [instance]
    
Arguments:
    report_type: 'morning' or 'evening'
    instance: (optional) Specific instance to process (default: all instances)

Examples:
    python3 daily_report_scheduler.py morning
    python3 daily_report_scheduler.py evening
    python3 daily_report_scheduler.py morning prod

Cron Setup:
    # Morning report at 8:00 AM IST
    0 8 * * * cd /path/to/lms && python3 daily_report_scheduler.py morning >> logs/reports.log 2>&1
    
    # Evening report at 8:00 PM IST
    0 20 * * * cd /path/to/lms && python3 daily_report_scheduler.py evening >> logs/reports.log 2>&1
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import after path setup
from instance_manager import DatabaseManager

# Valid instances
VALID_INSTANCES = ['prod', 'dev', 'testing']


def send_scheduled_reports(report_type, target_instance=None):
    """
    Send reports to all admins with reports enabled
    
    Args:
        report_type: 'morning' or 'evening'
        target_instance: Specific instance or None for all
    """
    print(f"\n{'='*60}")
    print(f"📊 Daily Report Scheduler - {report_type.upper()}")
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    try:
        # Initialize database manager
        from app_multi import db_manager, User, ReportPreference
        from app_reports import generate_daily_report, send_report_email
        
        instances_to_process = [target_instance] if target_instance else VALID_INSTANCES
        
        total_sent = 0
        total_failed = 0
        
        for instance in instances_to_process:
            print(f"\n📌 Processing instance: {instance}")
            print("-" * 40)
            
            try:
                session = db_manager.get_session_for_instance(instance)
                
                # Get all admins with reports enabled
                admins = session.query(User).filter_by(is_admin=True).all()
                
                for admin in admins:
                    # Check if they have reports enabled
                    pref = session.query(ReportPreference).filter_by(
                        user_id=admin.id
                    ).first()
                    
                    # Skip if reports disabled or no email
                    if pref and not pref.enabled:
                        print(f"  ⏭️  {admin.username}: Reports disabled")
                        continue
                    
                    if not admin.email:
                        print(f"  ⚠️  {admin.username}: No email address")
                        continue
                    
                    # Default to enabled if no preference set
                    if pref is None:
                        pref_enabled = True
                    else:
                        pref_enabled = pref.enabled
                    
                    if pref_enabled:
                        try:
                            # Generate report
                            print(f"  📊 Generating report for {admin.username}...")
                            report_data = generate_daily_report(instance, report_type)
                            
                            if report_data is None:
                                print(f"  ✗ Failed to generate report for {admin.username}")
                                total_failed += 1
                                continue
                            
                            # Send email
                            print(f"  📧 Sending to {admin.email}...")
                            success = send_report_email(admin, report_data, instance)
                            
                            if success:
                                print(f"  ✓ Sent {report_type} report to {admin.username} ({instance})")
                                total_sent += 1
                            else:
                                print(f"  ✗ Failed to send to {admin.username}")
                                total_failed += 1
                        
                        except Exception as e:
                            print(f"  ✗ Error processing {admin.username}: {e}")
                            total_failed += 1
            
            except Exception as e:
                print(f"✗ Error processing instance {instance}: {e}")
                import traceback
                traceback.print_exc()
        
        # Summary
        print(f"\n{'='*60}")
        print(f"📊 Report Summary")
        print(f"{'='*60}")
        print(f"✓ Successfully sent:  {total_sent} reports")
        if total_failed > 0:
            print(f"✗ Failed to send:    {total_failed} reports")
        print(f"{'='*60}\n")
        
        return total_sent > 0
    
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 daily_report_scheduler.py <report_type> [instance]")
        print("  report_type: 'morning' or 'evening'")
        print("  instance: (optional) 'prod', 'dev', or 'testing'")
        sys.exit(1)
    
    report_type = sys.argv[1].lower()
    target_instance = sys.argv[2] if len(sys.argv) > 2 else None
    
    if report_type not in ['morning', 'evening']:
        print(f"Error: Invalid report type '{report_type}'. Use 'morning' or 'evening'")
        sys.exit(1)
    
    if target_instance and target_instance not in VALID_INSTANCES:
        print(f"Error: Invalid instance '{target_instance}'. Use {', '.join(VALID_INSTANCES)}")
        sys.exit(1)
    
    success = send_scheduled_reports(report_type, target_instance)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

