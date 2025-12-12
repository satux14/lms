"""
Email Notification Provider

This module implements email notifications using SMTP.
Supports Gmail, Outlook, and custom SMTP servers.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from flask import render_template_string
from app_notifications import NotificationManager, Notification, NotificationChannel


class EmailConfig:
    """Email configuration loader"""
    
    def __init__(self):
        """Load email configuration from environment variables or defaults"""
        self.smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_user = os.environ.get('SMTP_USER', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.smtp_from_email = os.environ.get('SMTP_FROM_EMAIL', self.smtp_user)
        self.smtp_from_name = os.environ.get('SMTP_FROM_NAME', 'LMS Notification System')
        self.smtp_use_tls = os.environ.get('SMTP_USE_TLS', 'True').lower() == 'true'
        self.notifications_enabled = os.environ.get('NOTIFICATIONS_ENABLED', 'True').lower() == 'true'
        self.dev_mode = os.environ.get('FLASK_ENV', 'production') == 'development'
    
    def is_valid(self) -> bool:
        """Check if configuration is valid"""
        if not self.notifications_enabled:
            return False
        
        # If in dev mode and credentials not set, use console output
        if self.dev_mode and not self.smtp_user:
            return True
        
        # In production, require all SMTP settings
        return bool(self.smtp_host and self.smtp_port and self.smtp_user and self.smtp_password)
    
    def __repr__(self):
        """String representation for debugging (hide password)"""
        return (f"EmailConfig(host={self.smtp_host}, port={self.smtp_port}, "
                f"user={self.smtp_user}, enabled={self.notifications_enabled})")


class EmailNotificationProvider(NotificationManager):
    """Email notification provider using SMTP"""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        """Initialize email provider with configuration"""
        self.config = config or EmailConfig()
    
    def can_send(self, channel: NotificationChannel) -> bool:
        """Check if this provider can send to the given channel"""
        return channel == NotificationChannel.EMAIL
    
    def validate_config(self) -> bool:
        """Validate email configuration"""
        return self.config.is_valid()
    
    def send(self, notification: Notification) -> bool:
        """
        Send email notification
        
        Args:
            notification: Notification object to send
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.can_send(notification.channel):
            print(f"Email provider cannot send to channel: {notification.channel}")
            return False
        
        if not self.validate_config():
            print("Email configuration is invalid or notifications are disabled")
            return False
        
        try:
            # Get recipient email from notification context
            recipient_email = self._get_recipient_email(notification)
            if not recipient_email:
                print(f"No email address found for recipient {notification.recipient_id}")
                return False
            
            # Render email body from template
            body_html, body_text = self._render_email_body(notification)
            
            # Create email message
            msg = self._create_message(
                to_email=recipient_email,
                subject=notification.subject,
                body_html=body_html,
                body_text=body_text
            )
            
            # Send email
            if self.config.dev_mode and not self.config.smtp_user:
                # Development mode: print to console
                self._print_to_console(recipient_email, notification.subject, body_text)
                return True
            else:
                # Production mode: send via SMTP
                return self._send_via_smtp(msg, recipient_email)
        
        except Exception as e:
            print(f"Error sending email notification: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_recipient_email(self, notification: Notification) -> Optional[str]:
        """Get recipient email address from notification context or database"""
        # Try to get from context first (for backward compatibility)
        if notification.context:
            # Check for 'admin' key (used in approval notifications)
            if 'admin' in notification.context:
                admin = notification.context['admin']
                email = getattr(admin, 'email', None)
                if email:
                    return email
            
            # Check for 'user' key (used in daily reports)
            if 'user' in notification.context:
                user = notification.context['user']
                email = getattr(user, 'email', None)
                if email:
                    return email
        
        # Fallback: Fetch from database using recipient_id
        if notification.recipient_id:
            try:
                from app_multi import db_manager, User
                session = db_manager.get_session_for_instance(self.instance_name)
                user = session.query(User).filter_by(id=notification.recipient_id).first()
                if user and user.email:
                    return user.email
            except Exception as e:
                self.logger.warning(f"Could not fetch email from database for user {notification.recipient_id}: {e}")
        
        return None
    
    def _render_email_body(self, notification: Notification) -> tuple:
        """
        Render email body from template
        
        Returns:
            tuple: (html_body, text_body)
        """
        if notification.template:
            # Load template file and render
            html_body = self._render_template_file(
                f"{notification.template}.html",
                notification.context or {}
            )
            text_body = self._render_template_file(
                f"{notification.template}.txt",
                notification.context or {}
            )
        else:
            # Use message directly
            html_body = f"<html><body><p>{notification.message}</p></body></html>"
            text_body = notification.message
        
        return html_body, text_body
    
    def _render_template_file(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email template from file"""
        try:
            from flask import current_app
            with current_app.app_context():
                # Try to load template from templates/emails/
                template_path = os.path.join('templates', 'emails', template_name)
                if os.path.exists(template_path):
                    with open(template_path, 'r') as f:
                        template_content = f.read()
                    return render_template_string(template_content, **context)
                else:
                    # Template not found, use fallback
                    return self._get_fallback_template(template_name, context)
        except Exception as e:
            print(f"Error rendering template {template_name}: {e}")
            return self._get_fallback_template(template_name, context)
    
    def _get_fallback_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Get fallback template if file template doesn't exist"""
        item_details = context.get('item_details', {})
        instance_name = context.get('instance_name', 'prod')
        item_id = context.get('item_id', 0)
        approval_type = context.get('approval_type', '')
        
        if 'payment' in template_name:
            if template_name.endswith('.html'):
                return f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #2c3e50;">Payment Approval Required</h2>
                        <p>Hello,</p>
                        <p>A new payment requires your approval:</p>
                        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p><strong>Loan:</strong> {item_details.get('loan_name', 'N/A')}</p>
                            <p><strong>Customer:</strong> {item_details.get('customer_name', 'N/A')}</p>
                            <p><strong>Amount:</strong> ₹{item_details.get('amount', 'N/A')}</p>
                            <p><strong>Payment Date:</strong> {item_details.get('payment_date', 'N/A')}</p>
                        </div>
                        <p>
                            <a href="http://127.0.0.1:9090/{instance_name}/admin/payments" 
                               style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                                Review Payment
                            </a>
                        </p>
                        <p style="color: #666; font-size: 12px; margin-top: 30px;">
                            This is an automated notification from the Lending Management System.
                        </p>
                    </div>
                </body>
                </html>
                """
            else:  # .txt
                return f"""
Payment Approval Required

Hello,

A new payment requires your approval:

Loan: {item_details.get('loan_name', 'N/A')}
Customer: {item_details.get('customer_name', 'N/A')}
Amount: ₹{item_details.get('amount', 'N/A')}
Payment Date: {item_details.get('payment_date', 'N/A')}

Review and approve this payment at:
http://127.0.0.1:9090/{instance_name}/admin/payments

---
This is an automated notification from the Lending Management System.
                """
        
        elif 'tracker' in template_name:
            if template_name.endswith('.html'):
                return f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #2c3e50;">Tracker Entry Approval Required</h2>
                        <p>Hello,</p>
                        <p>A new tracker entry requires your approval:</p>
                        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p><strong>Tracker:</strong> {item_details.get('tracker_name', 'N/A')}</p>
                            <p><strong>User:</strong> {item_details.get('user_name', 'N/A')}</p>
                            <p><strong>Day:</strong> {item_details.get('day', 'N/A')}</p>
                            <p><strong>Amount:</strong> ₹{item_details.get('amount', 'N/A')}</p>
                        </div>
                        <p>
                            <a href="http://127.0.0.1:9090/{instance_name}/admin/daily-trackers/pending-entries" 
                               style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                                Review Entry
                            </a>
                        </p>
                        <p style="color: #666; font-size: 12px; margin-top: 30px;">
                            This is an automated notification from the Lending Management System.
                        </p>
                    </div>
                </body>
                </html>
                """
            else:  # .txt
                return f"""
Tracker Entry Approval Required

Hello,

A new tracker entry requires your approval:

Tracker: {item_details.get('tracker_name', 'N/A')}
User: {item_details.get('user_name', 'N/A')}
Day: {item_details.get('day', 'N/A')}
Amount: ₹{item_details.get('amount', 'N/A')}

Review and approve this entry at:
http://127.0.0.1:9090/{instance_name}/admin/daily-trackers/pending-entries

---
This is an automated notification from the Lending Management System.
                """
        
        return "Notification"
    
    def _create_message(self, to_email: str, subject: str, body_html: str, body_text: str) -> MIMEMultipart:
        """Create email message"""
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{self.config.smtp_from_name} <{self.config.smtp_from_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach text and HTML versions
        msg.attach(MIMEText(body_text, 'plain'))
        msg.attach(MIMEText(body_html, 'html'))
        
        return msg
    
    def _send_via_smtp(self, msg: MIMEMultipart, to_email: str) -> bool:
        """Send email via SMTP server"""
        try:
            # Connect to SMTP server
            server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
            
            # Use TLS if configured
            if self.config.smtp_use_tls:
                server.starttls()
            
            # Login
            server.login(self.config.smtp_user, self.config.smtp_password)
            
            # Send email
            server.sendmail(self.config.smtp_from_email, to_email, msg.as_string())
            
            # Close connection
            server.quit()
            
            return True
        
        except smtplib.SMTPException as e:
            print(f"SMTP error sending email to {to_email}: {e}")
            return False
        except Exception as e:
            print(f"Error sending email to {to_email}: {e}")
            return False
    
    def _print_to_console(self, to_email: str, subject: str, body: str):
        """Print email to console (for development)"""
        print("\n" + "="*60)
        print("📧 EMAIL NOTIFICATION (Development Mode)")
        print("="*60)
        print(f"To: {to_email}")
        print(f"From: {self.config.smtp_from_name} <{self.config.smtp_from_email}>")
        print(f"Subject: {subject}")
        print("-"*60)
        print(body)
        print("="*60 + "\n")

