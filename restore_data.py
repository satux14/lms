#!/usr/bin/env python3
"""
Data restoration script
Use this to manually add back your customers and loans
"""

from app import app, db, User, Loan, Payment
from werkzeug.security import generate_password_hash
from decimal import Decimal
from datetime import datetime, timedelta

def restore_customers_and_loans():
    """Restore your original customers and loans"""
    print("🔄 Restoring your original data...")
    
    with app.app_context():
        # Clear the demo data first
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
        
        # Add your customers here - replace with your actual customer data
        customers = [
            # Add your customers here like this:
            # User(
            #     username='your_customer_username',
            #     email='customer@email.com',
            #     password_hash=generate_password_hash('password123'),
            #     is_admin=False
            # ),
        ]
        
        for customer in customers:
            db.session.add(customer)
        
        db.session.commit()
        print(f"✅ Added {len(customers)} customers")
        
        # Add your loans here - replace with your actual loan data
        loans = [
            # Add your loans here like this:
            # Loan(
            #     customer_id=customers[0].id,  # Reference to customer
            #     loan_name='Your Loan Name',
            #     principal_amount=Decimal('50000.00'),
            #     remaining_principal=Decimal('45000.00'),
            #     interest_rate=Decimal('0.12'),  # 12%
            #     payment_frequency='daily',  # or 'monthly'
            #     notes='Your notes here',
            #     created_at=datetime.utcnow() - timedelta(days=30)
            # ),
        ]
        
        for loan in loans:
            db.session.add(loan)
        
        db.session.commit()
        print(f"✅ Added {len(loans)} loans")
        
        print("🎉 Data restoration completed!")
        print("💡 Please edit this script to add your actual customer and loan data")

if __name__ == "__main__":
    restore_customers_and_loans()
