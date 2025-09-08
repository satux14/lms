"""
Instance Manager for Lending Management System
============================================

This module manages multiple instances (prod, dev, testing) of the lending application.
Each instance has its own database and configuration.

Author: Lending Management System
Version: 1.0.1
"""

import os
from pathlib import Path
from flask import request, g
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InstanceManager:
    """Manages multiple instances of the lending application"""
    
    # Valid instances
    VALID_INSTANCES = ['prod', 'dev', 'testing']
    
    # Default instance
    DEFAULT_INSTANCE = 'prod'
    
    def __init__(self, app=None):
        """Initialize instance manager"""
        self.app = app
        self.instances_dir = Path("instances")
        self.instances_dir.mkdir(exist_ok=True)
        
        # Create instance directories
        for instance in self.VALID_INSTANCES:
            instance_dir = self.instances_dir / instance
            instance_dir.mkdir(exist_ok=True)
            
            # Create database directory
            db_dir = instance_dir / "database"
            db_dir.mkdir(exist_ok=True)
            
            # Create uploads directory
            uploads_dir = instance_dir / "uploads"
            uploads_dir.mkdir(exist_ok=True)
            
            # Create backups directory
            backups_dir = instance_dir / "backups"
            backups_dir.mkdir(exist_ok=True)
    
    def get_instance_from_url(self):
        """Extract instance name from URL path"""
        try:
            # Get the first path segment after the domain
            path_parts = request.path.strip('/').split('/')
            if path_parts and path_parts[0] in self.VALID_INSTANCES:
                return path_parts[0]
            return self.DEFAULT_INSTANCE
        except Exception as e:
            logger.warning(f"Error extracting instance from URL: {e}")
            return self.DEFAULT_INSTANCE
    
    def get_database_uri(self, instance=None):
        """Get database URI for specific instance"""
        if instance is None:
            instance = self.get_instance_from_url()
        
        if instance not in self.VALID_INSTANCES:
            instance = self.DEFAULT_INSTANCE
        
        db_path = self.instances_dir / instance / "database" / f"lending_app_{instance}.db"
        return f"sqlite:///{db_path}"
    
    def get_uploads_folder(self, instance=None):
        """Get uploads folder for specific instance"""
        if instance is None:
            instance = self.get_instance_from_url()
        
        if instance not in self.VALID_INSTANCES:
            instance = self.DEFAULT_INSTANCE
        
        return str(self.instances_dir / instance / "uploads")
    
    def get_backups_folder(self, instance=None):
        """Get backups folder for specific instance"""
        if instance is None:
            instance = self.get_instance_from_url()
        
        if instance not in self.VALID_INSTANCES:
            instance = self.DEFAULT_INSTANCE
        
        return str(self.instances_dir / instance / "backups")
    
    def get_instance_info(self, instance=None):
        """Get information about an instance"""
        if instance is None:
            instance = self.get_instance_from_url()
        
        if instance not in self.VALID_INSTANCES:
            instance = self.DEFAULT_INSTANCE
        
        instance_dir = self.instances_dir / instance
        db_path = instance_dir / "database" / f"lending_app_{instance}.db"
        
        info = {
            'name': instance,
            'database_path': str(db_path),
            'database_exists': db_path.exists(),
            'uploads_folder': str(instance_dir / "uploads"),
            'backups_folder': str(instance_dir / "backups"),
            'instance_dir': str(instance_dir)
        }
        
        if db_path.exists():
            info['database_size'] = db_path.stat().st_size
        else:
            info['database_size'] = 0
        
        return info
    
    def get_all_instances_info(self):
        """Get information about all instances"""
        instances_info = {}
        for instance in self.VALID_INSTANCES:
            instances_info[instance] = self.get_instance_info(instance)
        return instances_info
    
    def create_instance_database(self, instance=None):
        """Create database for specific instance"""
        if instance is None:
            instance = self.get_instance_from_url()
        
        if instance not in self.VALID_INSTANCES:
            instance = self.DEFAULT_INSTANCE
        
        db_path = self.instances_dir / instance / "database" / f"lending_app_{instance}.db"
        
        # Create database directory if it doesn't exist
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Database path for {instance}: {db_path}")
        return str(db_path)
    
    def switch_instance(self, instance):
        """Switch to a different instance"""
        if instance not in self.VALID_INSTANCES:
            raise ValueError(f"Invalid instance: {instance}. Valid instances: {self.VALID_INSTANCES}")
        
        # Store current instance in Flask g object
        g.current_instance = instance
        return instance
    
    def get_current_instance(self):
        """Get current instance name"""
        return getattr(g, 'current_instance', self.get_instance_from_url())
    
    def is_production(self):
        """Check if current instance is production"""
        return self.get_current_instance() == 'prod'
    
    def is_development(self):
        """Check if current instance is development"""
        return self.get_current_instance() == 'dev'
    
    def is_testing(self):
        """Check if current instance is testing"""
        return self.get_current_instance() == 'testing'

# Global instance manager
instance_manager = InstanceManager()

def get_instance_manager():
    """Get the global instance manager"""
    return instance_manager

def init_instance_manager(app):
    """Initialize instance manager with Flask app"""
    global instance_manager
    instance_manager = InstanceManager(app)
    return instance_manager
