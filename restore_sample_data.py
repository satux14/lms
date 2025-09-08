#!/usr/bin/env python3
"""
Restore sample data with two-notes system
This adds back the demo users and loans without destroying existing data
"""

from app import app, db, User, Loan, Payment
from werkzeug.security import generate_password_hash
from decimal import Decimal
from datetime import datetime, timedelta

def restore_sample_data():
    """Add sample users and loans back to the database"""
    print("🔄 Restoring sample data...")
    
    with app.app_context():
        # Check if we already have enough customers
        existing_customers = User.query.filter_by(is_admin=False).count()
        if existing_customers >= 3:
            print(f"✅ Found {existing_customers} existing customers, skipping user creation")
        else:
            # Create sample customers
            customers = [
                User(
                    username='john_doe',
                    email='john@example.com',
                    password_hash=generate_password_hash('password123'),
                    is_admin=False
                ),
                User(
                    username='jane_smith',
                    email='jane@example.com',
                    password_hash=generate_password_hash('password123'),
                    is_admin=False
                ),
                User(
                    username='bob_wilson',
                    email='bob@example.com',
                    password_hash=generate_password_hash('password123'),
                    is_admin=False
                )
            ]
            
            for customer in customers:
                db.session.add(customer)
            
            db.session.commit()
            print(f"✅ Added {len(customers)} sample customers")
        
        # Check if we already have loans
        existing_loans = Loan.query.count()
        if existing_loans > 0:
            print(f"✅ Found {existing_loans} existing loans, skipping loan creation")
        else:
            # Get customers for loan creation
            customers = User.query.filter_by(is_admin=False).all()
            if not customers:
                print("❌ No customers found, cannot create loans")
                return
            
            # Create sample loans with two-notes system
            loans = [
                Loan(
                    customer_id=customers[0].id,
                    loan_name="Personal Loan",
                    principal_amount=Decimal('50000.00'),
                    remaining_principal=Decimal('42500.00'),
                    interest_rate=Decimal('0.21'),  # 21%
                    payment_frequency='daily',
                    admin_notes="Customer requested for medical expenses. Good payment history. Monitor for any payment delays.",
                    customer_notes="This loan is for medical expenses. Please make payments on time to avoid additional charges.",
                    created_at=datetime.utcnow() - timedelta(days=30)
                ),
                Loan(
                    customer_id=customers[1].id,
                    loan_name="Business Loan",
                    principal_amount=Decimal('100000.00'),
                    remaining_principal=Decimal('95000.00'),
                    interest_rate=Decimal('0.15'),  # 15%
                    payment_frequency='monthly',
                    admin_notes="For expanding restaurant business. Collateral: Property documents submitted. High-value loan, monitor closely.",
                    customer_notes="Business expansion loan. Property documents have been submitted as collateral.",
                    created_at=datetime.utcnow() - timedelta(days=20)
                ),
                Loan(
                    customer_id=customers[2].id,
                    loan_name="Home Improvement",
                    principal_amount=Decimal('75000.00'),
                    remaining_principal=Decimal('72000.00'),
                    interest_rate=Decimal('0.21'),  # 21%
                    payment_frequency='daily',
                    admin_notes="Kitchen renovation project. Contractor: ABC Construction. Verify work completion before final payment.",
                    customer_notes="Home improvement loan for kitchen renovation. Contractor: ABC Construction.",
                    created_at=datetime.utcnow() - timedelta(days=15)
                ),
                Loan(
                    customer_id=customers[0].id,
                    loan_name="Emergency Fund",
                    principal_amount=Decimal('25000.00'),
                    remaining_principal=Decimal('25000.00'),
                    interest_rate=Decimal('0.18'),  # 18%
                    payment_frequency='monthly',
                    admin_notes="High-risk loan. No collateral provided. Monitor closely. Customer has irregular income.",
                    customer_notes="Emergency fund loan. Please ensure timely payments to maintain good credit standing.",
                    created_at=datetime.utcnow() - timedelta(days=5)
                )
            ]
            
            for loan in loans:
                db.session.add(loan)
            
            db.session.commit()
            print(f"✅ Added {len(loans)} sample loans with two-notes system")
        
        # Check if we already have payments
        existing_payments = Payment.query.count()
        if existing_payments > 0:
            print(f"✅ Found {existing_payments} existing payments, skipping payment creation")
        else:
            # Get loans for payment creation
            loans = Loan.query.all()
            if not loans:
                print("❌ No loans found, cannot create payments")
                return
            
            # Create sample payments
            payments = [
                Payment(
                    loan_id=loans[0].id,
                    amount=Decimal('1000.00'),
                    interest_amount=Decimal('500.00'),
                    principal_amount=Decimal('500.00'),
                    payment_type='both',
                    transaction_id='TXN001',
                    payment_method='gpay',
                    payment_date=datetime.utcnow() - timedelta(days=1),
                    status='verified'
                ),
                Payment(
                    loan_id=loans[1].id,
                    amount=Decimal('2000.00'),
                    interest_amount=Decimal('1500.00'),
                    principal_amount=Decimal('500.00'),
                    payment_type='both',
                    transaction_id='TXN002',
                    payment_method='upi',
                    payment_date=datetime.utcnow() - timedelta(days=2),
                    status='verified'
                ),
                Payment(
                    loan_id=loans[2].id,
                    amount=Decimal('3000.00'),
                    interest_amount=Decimal('2000.00'),
                    principal_amount=Decimal('1000.00'),
                    payment_type='both',
                    transaction_id='TXN003',
                    payment_method='bank_transfer',
                    payment_date=datetime.utcnow() - timedelta(days=10),
                    status='verified'
                ),
                Payment(
                    loan_id=loans[3].id,
                    amount=Decimal('500.00'),
                    interest_amount=Decimal('500.00'),
                    principal_amount=Decimal('0.00'),
                    payment_type='interest',
                    transaction_id='TXN004',
                    payment_method='cash',
                    payment_date=datetime.utcnow() - timedelta(days=5),
                    status='pending'
                )
            ]
            
            for payment in payments:
                db.session.add(payment)
            
            db.session.commit()
            print(f"✅ Added {len(payments)} sample payments")
        
        print("🎉 Sample data restored successfully!")
        print("📊 Data Summary:")
        print(f"   👤 Admin users: {User.query.filter_by(is_admin=True).count()}")
        print(f"   👥 Customer users: {User.query.filter_by(is_admin=False).count()}")
        print(f"   💰 Active loans: {Loan.query.count()}")
        print(f"   💳 Total payments: {Payment.query.count()}")
        print("🔑 Login Credentials:")
        print("   Admin: admin / admin123")
        print("   Customer 1: john_doe / password123")
        print("   Customer 2: jane_smith / password123")
        print("   Customer 3: bob_wilson / password123")

if __name__ == "__main__":
    restore_sample_data()
