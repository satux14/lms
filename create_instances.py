#!/usr/bin/env python3
"""
Simple Instance Creation Script
==============================

This script creates all three instances (prod, dev, testing) with their databases.
"""

import os
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash
from decimal import Decimal

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_all_instances():
    """Create all instances"""
    instances = ['prod', 'dev', 'testing']
    
    for instance in instances:
        print(f"🔄 Creating {instance} instance...")
        
        # Create directory structure
        instance_path = Path("instances") / instance
        instance_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (instance_path / "database").mkdir(exist_ok=True)
        (instance_path / "uploads").mkdir(exist_ok=True)
        (instance_path / "backups").mkdir(exist_ok=True)
        
        # Create database file
        db_path = instance_path / "database" / f"lending_app_{instance}.db"
        
        # Import and configure Flask app
        from app_multi import app, db, User, InterestRate
        
        # Configure app for this instance
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
        app.config['UPLOAD_FOLDER'] = str(instance_path / "uploads")
        
        # Create database and tables
        with app.app_context():
            db.create_all()
            
            # Create default admin user
            if not User.query.filter_by(username='admin').first():
                admin = User(
                    username='admin',
                    email=f'admin@{instance}.lendingapp.com',
                    password_hash=generate_password_hash('admin123'),
                    is_admin=True
                )
                db.session.add(admin)
                
                # Create default interest rate
                default_rate = InterestRate(rate=Decimal('0.21'))  # 21%
                db.session.add(default_rate)
                
                db.session.commit()
                print(f"✅ Created {instance} instance with admin user")
            else:
                print(f"✅ {instance} instance already exists")
    
    print("\n🎉 All instances created successfully!")
    print("\n📋 Instance URLs:")
    print("   • Production:  http://localhost:8080/prod/")
    print("   • Development: http://localhost:8080/dev/")
    print("   • Testing:     http://localhost:8080/testing/")
    print("\n🔑 Default Admin Login:")
    print("   Username: admin")
    print("   Password: admin123")

if __name__ == "__main__":
    create_all_instances()
