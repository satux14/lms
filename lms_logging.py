"""
Logging module for LMS
Handles structured logging and activity tracking
Uses same database, different tables for isolation
"""
import logging
import json
import os
from datetime import datetime
from flask import request
from flask_login import current_user
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base

# Base for logging models - separate from main app models
LoggingBase = declarative_base()

class ActivityLog(LoggingBase):
    """Store user activities for admin review - separate table in same DB"""
    __tablename__ = 'activity_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(80), nullable=False)
    action = Column(String(100), nullable=False)  # 'login', 'logout', 'add_payment', etc.
    resource_type = Column(String(50), nullable=True)  # 'loan', 'payment', 'tracker', etc.
    resource_id = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes for faster queries
    __table_args__ = (
        Index('idx_action_date', 'action', 'created_at'),
        Index('idx_username_date', 'username', 'created_at'),
        Index('idx_resource', 'resource_type', 'resource_id'),
    )

class SystemConfig(LoggingBase):
    """Store system configuration like interest payment threshold"""
    __tablename__ = 'system_config'
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, nullable=True)


class LoggingManager:
    """Manages logging using same database, different tables"""
    
    def __init__(self, db_engine, instance_name):
        """
        Initialize logging manager
        
        Args:
            db_engine: SQLAlchemy engine from main database
            instance_name: Instance name (prod, dev, testing)
        """
        self.engine = db_engine
        self.instance_name = instance_name
        
        # Create logging tables in the same database
        LoggingBase.metadata.create_all(self.engine)
        
        # Setup file logging
        self.logger = self._setup_file_logging(instance_name)
    
    def _setup_file_logging(self, instance_name):
        """Setup file-based logging"""
        log_dir = f"instances/{instance_name}/logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = f"{log_dir}/lms_{instance_name}.log"
        
        # Configure logging
        logger = logging.getLogger(f"lms.{instance_name}")
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        if logger.handlers:
            logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(file_formatter)
        logger.addHandler(console_handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        return logger
    
    def _get_user_info(self):
        """Get current user info from Flask context"""
        try:
            user = current_user if hasattr(current_user, 'id') else None
            username = user.username if user else 'anonymous'
            user_id = user.id if user else None
            return username, user_id
        except:
            return 'anonymous', None
    
    def _get_request_info(self):
        """Get request info (IP, user agent)"""
        try:
            ip_address = request.remote_addr
            if request.headers.get('X-Forwarded-For'):
                ip_address = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            user_agent = request.headers.get('User-Agent', '')
            return ip_address, user_agent
        except:
            return None, None
    
    def log_activity(self, action, username=None, user_id=None, 
                    resource_type=None, resource_id=None, details=None, 
                    ip_address=None, user_agent=None):
        """Log user activity to database and file"""
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            # Get user info if not provided
            if username is None:
                username, user_id = self._get_user_info()
            
            # Get request info if not provided
            if ip_address is None:
                ip_address, user_agent = self._get_request_info()
            
            # Log to database
            activity = ActivityLog(
                user_id=user_id,
                username=username,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=json.dumps(details) if details else None
            )
            session.add(activity)
            session.commit()
            
            # Log to file
            log_message = f"Action: {action} | User: {username}"
            if ip_address:
                log_message += f" | IP: {ip_address}"
            if resource_type:
                log_message += f" | Resource: {resource_type}:{resource_id}"
            if details:
                log_message += f" | Details: {json.dumps(details)}"
            
            self.logger.info(log_message)
            
            return activity
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error logging activity: {e}", exc_info=True)
            raise
        finally:
            session.close()
    
    def log_login(self, username, success=True, reason=None):
        """Log login attempts"""
        action = 'login_success' if success else 'login_failed'
        details = {'reason': reason} if reason else None
        self.log_activity(action, username=username, details=details)
        
        if success:
            self.logger.info(f"User '{username}' logged in successfully")
        else:
            self.logger.warning(f"Failed login attempt for '{username}': {reason}")
    
    def log_logout(self, username):
        """Log logout"""
        self.log_activity('logout', username=username)
        self.logger.info(f"User '{username}' logged out")
    
    def log_payment(self, action, loan_id, payment_id=None, amount=None, username=None):
        """Log payment-related actions"""
        details = {
            'loan_id': loan_id,
            'payment_id': payment_id,
            'amount': str(amount) if amount else None
        }
        self.log_activity(action, username=username, resource_type='payment', 
                         resource_id=payment_id, details=details)
        self.logger.info(f"Payment {action} | Loan: {loan_id} | Amount: {amount} | User: {username}")
    
    def log_admin_action(self, action, resource_type, resource_id, username=None, details=None):
        """Log admin actions"""
        self.log_activity(action, username=username, resource_type=resource_type, 
                         resource_id=resource_id, details=details)
        self.logger.info(f"Admin action: {action} | {resource_type}:{resource_id}")
    
    def log_moderator_action(self, action, resource_type, resource_id, username=None, details=None):
        """Log moderator actions"""
        self.log_activity(action, username=username, resource_type=resource_type, 
                         resource_id=resource_id, details=details)
        self.logger.info(f"Moderator action: {action} | {resource_type}:{resource_id}")
    
    def get_config(self, config_key, default=None):
        """Get configuration value"""
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self.engine)
        session = Session()
        try:
            config = session.query(SystemConfig).filter_by(config_key=config_key).first()
            return config.config_value if config else default
        finally:
            session.close()
    
    def set_config(self, config_key, config_value, description=None, updated_by=None):
        """Set configuration value"""
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self.engine)
        session = Session()
        try:
            config = session.query(SystemConfig).filter_by(config_key=config_key).first()
            if config:
                config.config_value = config_value
                config.updated_by = updated_by
                config.updated_at = datetime.utcnow()
            else:
                config = SystemConfig(
                    config_key=config_key,
                    config_value=config_value,
                    description=description,
                    updated_by=updated_by
                )
                session.add(config)
            session.commit()
            return config
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error setting config: {e}", exc_info=True)
            raise
        finally:
            session.close()
    
    def get_activity_logs(self, action=None, username=None, resource_type=None, 
                         start_date=None, end_date=None, limit=100):
        """Get activity logs with filters"""
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            query = session.query(ActivityLog)
            
            if action:
                query = query.filter_by(action=action)
            if username:
                query = query.filter_by(username=username)
            if resource_type:
                query = query.filter_by(resource_type=resource_type)
            if start_date:
                query = query.filter(ActivityLog.created_at >= start_date)
            if end_date:
                query = query.filter(ActivityLog.created_at <= end_date)
            
            return query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
        finally:
            session.close()


# Global logging managers per instance
_logging_managers = {}

def init_logging(instance_name, db_engine):
    """Initialize logging for an instance"""
    _logging_managers[instance_name] = LoggingManager(db_engine, instance_name)
    return _logging_managers[instance_name]

def get_logging_manager(instance_name):
    """Get the logging manager for an instance"""
    if instance_name not in _logging_managers:
        raise RuntimeError(f"Logging not initialized for instance '{instance_name}'. Call init_logging() first.")
    return _logging_managers[instance_name]

