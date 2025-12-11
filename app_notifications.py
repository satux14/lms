"""
Generic Notification System

This module provides a generic notification interface that can be extended
to support multiple channels (email, SMS, Slack, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum


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
    Send approval notifications to all admins with email notifications enabled
    
    Args:
        instance_name: Name of the instance (prod, dev, etc.)
        approval_type: Type of approval ('payment' or 'tracker_entry')
        item_id: ID of the item requiring approval
        item_details: Dictionary with details about the item
        db_manager: Database manager instance
        
    Returns:
        List of bool values indicating success/failure for each recipient
    """
    from app_multi import User, db_manager as default_db_manager
    
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
            
            # Create notification
            if approval_type == 'payment':
                template = 'approval_request_payment'
                subject = f"Payment Approval Required - {item_details.get('loan_name', 'Unknown Loan')}"
            elif approval_type == 'tracker_entry':
                template = 'approval_request_tracker'
                subject = f"Tracker Entry Approval Required - {item_details.get('tracker_name', 'Unknown Tracker')}"
            else:
                print(f"Unknown approval type: {approval_type}")
                continue
            
            notification = Notification(
                channel=NotificationChannel.EMAIL,
                recipient_id=admin.id,
                subject=subject,
                message="",  # Will be rendered from template
                template=template,
                context={
                    'admin': admin,
                    'item_id': item_id,
                    'item_details': item_details,
                    'instance_name': instance_name,
                    'approval_type': approval_type
                },
                priority=NotificationPriority.HIGH,
                instance_name=instance_name
            )
            
            # Send notification
            success = send_notification(notification)
            results.append(success)
            
            if success:
                print(f"✓ Sent {approval_type} approval notification to {admin.username} ({admin.email})")
            else:
                print(f"✗ Failed to send {approval_type} approval notification to {admin.username}")
    
    except Exception as e:
        print(f"Error sending approval notifications: {e}")
        import traceback
        traceback.print_exc()
    
    return results

