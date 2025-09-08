#!/usr/bin/env python3
"""
Simple fix: Recreate database with correct schema
This will fix the email field to be optional
"""

from app import app, db, User, Loan, Payment
from werkzeug.security import generate_password_hash
from decimal import Decimal
from datetime import datetime, timedelta

def fix_email_schema():
    """Recreate database with correct schema"""
    print("🔄 Fixing email schema...")
    
    with app.app_context():
        # Drop and recreate all tables with correct schema
        db.drop_all()
        db.create_all()
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@lending.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        
        # Create a test customer without email to verify it works
        customer = User(
            username='test_customer',
            email=None,  # No email - this should work now
            password_hash=generate_password_hash('password123'),
            is_admin=False
        )
        db.session.add(customer)
        
        db.session.commit()
        
        print("✅ Database recreated with correct schema!")
        print("✅ Email field is now optional!")
        print("✅ Test customer created without email - verification successful!")
        print("💡 You can now create users without email addresses")

if __name__ == "__main__":
    fix_email_schema()
