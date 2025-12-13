"""
Generic Notification System

This module provides a generic notification interface that can be extended
to support multiple channels (email, SMS, Slack, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime, timedelta


class NotificationChannel(Enum):
    """Notification channel types"""
    EMAIL = 'email'
    SMS = 'sms'
    SLACK = 'slack'
    PUSH = 'push'


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    URGENT = 'urgent'


@dataclass
class Notification:
    """Data class representing a notification"""
    channel: NotificationChannel
    recipient_id: int
    subject: str
    message: str
    template: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    priority: NotificationPriority = NotificationPriority.MEDIUM
    instance_name: Optional[str] = None
    
    def __post_init__(self):
        """Convert string values to enums if needed"""
        if isinstance(self.channel, str):
            self.channel = NotificationChannel(self.channel)
        if isinstance(self.priority, str):
            self.priority = NotificationPriority(self.priority)


class NotificationManager(ABC):
    """Abstract base class for notification providers"""
    
    @abstractmethod
    def send(self, notification: Notification) -> bool:
        """
        Send a notification
        
        Args:
            notification: Notification object to send
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def can_send(self, channel: NotificationChannel) -> bool:
        """
        Check if this manager can send notifications on the given channel
        
        Args:
            channel: NotificationChannel to check
            
        Returns:
            bool: True if supported, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate that the notification manager is properly configured
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        pass


def get_notification_manager(channel: NotificationChannel) -> Optional[NotificationManager]:
    """
    Factory function to get the appropriate notification manager for a channel
    
    Args:
        channel: NotificationChannel to get manager for
        
    Returns:
        NotificationManager instance or None if channel not supported
    """
    if channel == NotificationChannel.EMAIL:
        from app_notify_email import EmailNotificationProvider
        return EmailNotificationProvider()
    elif channel == NotificationChannel.SMS:
        # Future: SMS provider
        return None
    elif channel == NotificationChannel.SLACK:
        # Future: Slack provider
        return None
    else:
        return None


def send_notification(notification: Notification) -> bool:
    """
    Send a notification using the appropriate manager
    
    Args:
        notification: Notification object to send
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        manager = get_notification_manager(notification.channel)
        if manager is None:
            print(f"No notification manager available for channel: {notification.channel}")
            return False
        
        if not manager.validate_config():
            print(f"Notification manager not properly configured for channel: {notification.channel}")
            return False
        
        return manager.send(notification)
    except Exception as e:
        print(f"Error sending notification: {e}")
        return False


def send_approval_notification(
    instance_name: str,
    approval_type: str,
    item_id: int,
    item_details: Dict[str, Any],
    db_manager=None
) -> List[bool]:
    """
    Queue approval notifications for collation and delayed sending
    
    Args:
        instance_name: Name of the instance (prod, dev, etc.)
        approval_type: Type of approval ('payment' or 'tracker_entry')
        item_id: ID of the item requiring approval
        item_details: Dictionary with details about the item
        db_manager: Database manager instance
        
    Returns:
        List of bool values indicating success/failure for each recipient (queued)
    """
    from app_multi import User, db_manager as default_db_manager, PendingApprovalNotification
    
    if db_manager is None:
        db_manager = default_db_manager
    
    results = []
    
    try:
        # Get session for the instance
        session = db_manager.get_session_for_instance(instance_name)
        
        # Get NotificationPreference model
        from app_multi import NotificationPreference
        
        # Get all admins
        admins = session.query(User).filter_by(is_admin=True).all()
        
        for admin in admins:
            # Check if admin has email notifications enabled
            pref = session.query(NotificationPreference).filter_by(
                user_id=admin.id,
                channel='email'
            ).first()
            
            # Default: enabled for admins if no preference set
            if pref is None:
                enabled = True
                preferences = {'payment_approvals': True, 'tracker_approvals': True}
            else:
                enabled = pref.enabled
                preferences = pref.preferences or {}
            
            # Check if this specific notification type is enabled
            if approval_type == 'payment':
                type_enabled = preferences.get('payment_approvals', True)
            elif approval_type == 'tracker_entry':
                type_enabled = preferences.get('tracker_approvals', True)
            else:
                type_enabled = False
            
            if not enabled or not type_enabled:
                continue
            
            # Check if admin has an email address
            if not admin.email:
                print(f"Admin {admin.username} has no email address, skipping notification")
                continue
            
            # Check if notification already exists (prevent duplicates)
            existing_notification = session.query(PendingApprovalNotification).filter_by(
                instance_name=instance_name,
                recipient_id=admin.id,
                approval_type=approval_type,
                item_id=item_id,
                is_sent=False
            ).first()
            
            if existing_notification:
                print(f"⚠ Notification already queued for {admin.username} ({approval_type} #{item_id}), skipping duplicate")
                results.append(True)
                continue
            
            # Queue the notification instead of sending immediately
            pending_notification = PendingApprovalNotification(
                instance_name=instance_name,
                recipient_id=admin.id,
                approval_type=approval_type,
                item_id=item_id,
                item_details=item_details,
                is_sent=False
            )
            session.add(pending_notification)
            results.append(True)
            
            print(f"✓ Queued {approval_type} approval notification for {admin.username} ({admin.email})")
        
        session.commit()
    
    except Exception as e:
        print(f"Error queueing approval notifications: {e}")
        import traceback
        traceback.print_exc()
        if 'session' in locals():
            session.rollback()
    
    return results


def process_pending_approval_notifications(instance_name: str = None):
    """
    Process pending approval notifications and send collated emails
    
    This function:
    1. Finds all pending notifications older than the configured delay
    2. Groups them by recipient and approval type
    3. Sends collated emails
    
    Args:
        instance_name: Optional instance name to process. If None, processes all instances.
    """
    from app_multi import db_manager, User, NotificationPreference, PendingApprovalNotification
    from app_notify_email import EmailNotificationProvider
    import os
    
    instances = [instance_name] if instance_name else ['prod', 'dev', 'testing']
    base_url = os.environ.get('BASE_URL', 'http://127.0.0.1:9090')
    
    for instance in instances:
        try:
            session = db_manager.get_session_for_instance(instance)
            
            # Get delay time from first admin's preferences (default 5 minutes)
            # Use the first admin's preference as system-wide setting
            delay_minutes = 5
            admin = session.query(User).filter_by(is_admin=True).first()
            if admin:
                pref = session.query(NotificationPreference).filter_by(
                    user_id=admin.id,
                    channel='email'
                ).first()
                if pref and pref.preferences:
                    delay_minutes = pref.preferences.get('approval_email_delay_minutes', 5)
                elif not pref:
                    # No preference set, use default
                    delay_minutes = 5
            
            # Calculate cutoff time
            cutoff_time = datetime.utcnow() - timedelta(minutes=delay_minutes)
            
            # Get all pending notifications older than cutoff
            pending_notifications = session.query(PendingApprovalNotification).filter(
                PendingApprovalNotification.instance_name == instance,
                PendingApprovalNotification.is_sent == False,
                PendingApprovalNotification.created_at <= cutoff_time
            ).all()
            
            if not pending_notifications:
                continue
            
            # Group by recipient
            notifications_by_recipient = {}
            for notification in pending_notifications:
                recipient_id = notification.recipient_id
                if recipient_id not in notifications_by_recipient:
                    notifications_by_recipient[recipient_id] = []
                notifications_by_recipient[recipient_id].append(notification)
            
            # Process each recipient
            email_provider = EmailNotificationProvider(instance_name=instance)
            if not email_provider.validate_config():
                print(f"Email provider not configured for {instance}, skipping")
                continue
            
            for recipient_id, notifications in notifications_by_recipient.items():
                recipient = session.query(User).get(recipient_id)
                if not recipient or not recipient.email:
                    continue
                
                # Group by approval type
                payments = [n for n in notifications if n.approval_type == 'payment']
                tracker_entries = [n for n in notifications if n.approval_type == 'tracker_entry']
                
                # Send collated email
                success = send_collated_approval_email(
                    recipient=recipient,
                    payments=payments,
                    tracker_entries=tracker_entries,
                    instance_name=instance,
                    base_url=base_url,
                    email_provider=email_provider
                )
                
                if success:
                    # Mark notifications as sent
                    for notification in notifications:
                        notification.is_sent = True
                        notification.sent_at = datetime.utcnow()
                    session.commit()
                    print(f"✓ Sent collated approval email to {recipient.username} ({instance}): {len(payments)} payments, {len(tracker_entries)} tracker entries")
                else:
                    print(f"✗ Failed to send collated approval email to {recipient.username} ({instance})")
                    session.rollback()
        
        except Exception as e:
            print(f"Error processing pending notifications for {instance}: {e}")
            import traceback
            traceback.print_exc()


def send_collated_approval_email(
    recipient: 'User',
    payments: List,
    tracker_entries: List,
    instance_name: str,
    base_url: str,
    email_provider: 'EmailNotificationProvider'
) -> bool:
    """
    Send a collated approval email with multiple requests
    
    Args:
        recipient: User to send email to
        payments: List of PendingApprovalNotification objects for payments
        tracker_entries: List of PendingApprovalNotification objects for tracker entries
        instance_name: Instance name
        base_url: Base URL for links
        email_provider: EmailNotificationProvider instance
        
    Returns:
        bool: True if sent successfully
    """
    from app_notifications import Notification, NotificationChannel, NotificationPriority
    
    # Build email content
    total_count = len(payments) + len(tracker_entries)
    
    if total_count == 0:
        return False
    
    # Determine subject
    if len(payments) > 0 and len(tracker_entries) > 0:
        subject = f"{total_count} Approval Requests Pending - Payments & Tracker Entries"
    elif len(payments) > 0:
        subject = f"{len(payments)} Payment Approval Request{'s' if len(payments) > 1 else ''} Pending"
    else:
        subject = f"{len(tracker_entries)} Tracker Entry Approval Request{'s' if len(tracker_entries) > 1 else ''} Pending"
    
    # Create notification with collated template
    notification = Notification(
        channel=NotificationChannel.EMAIL,
        recipient_id=recipient.id,
        subject=subject,
        message="",
        template='approval_request_collated',
        context={
            'admin': recipient,
            'payments': [{'id': p.item_id, 'details': p.item_details} for p in payments],
            'tracker_entries': [{'id': t.item_id, 'details': t.item_details} for t in tracker_entries],
            'instance_name': instance_name,
            'base_url': base_url,
            'total_count': total_count
        },
        priority=NotificationPriority.HIGH,
        instance_name=instance_name
    )
    
    return email_provider.send(notification)
