#!/usr/bin/env python3
"""
Demo script to showcase the Lending Management System features
This script demonstrates the core functionality without running the web server.
"""

from app import app, db, User, Loan, Payment
from werkzeug.security import generate_password_hash
from decimal import Decimal
from datetime import datetime, timedelta

def create_demo_data():
    """Create demo data to showcase the system"""
    print("🏦 Creating demo data for Lending Management System...")
    
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@lendingapp.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        
        # Create demo customers
        customers = [
            User(username='john_doe', email='john@example.com', password_hash=generate_password_hash('password123')),
            User(username='jane_smith', email='jane@example.com', password_hash=generate_password_hash('password123')),
            User(username='bob_wilson', email='bob@example.com', password_hash=generate_password_hash('password123'))
        ]
        
        for customer in customers:
            db.session.add(customer)
        
        # Commit users first to get their IDs
        db.session.commit()
        
        # Note: Interest rates are now stored directly in loans
        
        # Create demo loans with different rates
        loans = [
            Loan(
                customer_id=customers[0].id,
                loan_name="Personal Loan",
                principal_amount=Decimal('50000.00'),
                remaining_principal=Decimal('42500.00'),
                interest_rate=Decimal('0.21'),  # 21%
                payment_frequency='daily',
                loan_type='regular',
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
                loan_type='regular',
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
                loan_type='regular',
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
                loan_type='regular',
                admin_notes="High-risk loan. No collateral provided. Monitor closely. Customer has irregular income.",
                customer_notes="Emergency fund loan. Please ensure timely payments to maintain good credit standing.",
                created_at=datetime.utcnow() - timedelta(days=5)
            ),
            Loan(
                customer_id=customers[1].id,
                loan_name="Interest-Only Investment",
                principal_amount=Decimal('200000.00'),
                remaining_principal=Decimal('200000.00'),
                interest_rate=Decimal('0.12'),  # 12%
                payment_frequency='daily',
                loan_type='interest_only',
                admin_notes="Investment loan with interest-only payments. Principal remains fixed. Customer plans to pay off in 2 years.",
                customer_notes="Investment loan - interest only. Principal amount stays fixed until final payment.",
                created_at=datetime.utcnow() - timedelta(days=10)
            )
        ]
        
        for loan in loans:
            db.session.add(loan)
        db.session.commit()
        
        # Create demo payments
        payments = [
            Payment(
                loan_id=loans[0].id,
                amount=Decimal('1000.00'),
                payment_date=datetime.utcnow() - timedelta(days=1),
                payment_type='both',
                interest_amount=Decimal('164.38'),
                principal_amount=Decimal('835.62'),
                transaction_id='UPI123456789',
                payment_method='gpay',
                status='verified'
            ),
            Payment(
                loan_id=loans[1].id,
                amount=Decimal('2000.00'),
                payment_date=datetime.utcnow() - timedelta(days=2),
                payment_type='both',
                interest_amount=Decimal('410.96'),
                principal_amount=Decimal('1589.04'),
                transaction_id='TXN987654321',
                payment_method='upi',
                status='verified'
            ),
            Payment(
                loan_id=loans[2].id,
                amount=Decimal('1500.00'),
                payment_date=datetime.utcnow() - timedelta(days=10),
                payment_type='both',
                interest_amount=Decimal('246.58'),
                principal_amount=Decimal('1253.42'),
                transaction_id='PHONEPE456789',
                payment_method='phonepay',
                status='pending'
            ),
            Payment(
                loan_id=loans[3].id,
                amount=Decimal('500.00'),
                payment_date=datetime.utcnow() - timedelta(days=5),
                payment_type='both',
                interest_amount=Decimal('61.64'),
                principal_amount=Decimal('438.36'),
                transaction_id='BANK789123456',
                payment_method='bank_transfer',
                status='verified'
            )
        ]
        
        for payment in payments:
            db.session.add(payment)
        db.session.commit()
        
        print("✅ Demo data created successfully!")
        
        # Display summary
        print("\n📊 Demo Data Summary:")
        print(f"   👤 Admin users: {User.query.filter_by(is_admin=True).count()}")
        print(f"   👥 Customer users: {User.query.filter_by(is_admin=False).count()}")
        print(f"   💰 Active loans: {Loan.query.filter_by(is_active=True).count()}")
        print(f"   💳 Total payments: {Payment.query.count()}")
        print(f"   💵 Currency: Indian Rupees (₹)")
        
        print("\n🔑 Demo Login Credentials:")
        print("   Admin: admin / admin123")
        print("   Customer 1: john_doe / password123")
        print("   Customer 2: jane_smith / password123")
        print("   Customer 3: bob_wilson / password123")
        
        # Show interest calculation example
        print("\n🧮 Interest Calculation Demo:")
        print("----------------------------------------")
        principal = Decimal('50000.00')
        annual_rate = Decimal('0.21')  # 21%
        
        daily_interest = principal * (annual_rate / 365)
        monthly_interest = principal * (annual_rate / 12)
        
        print(f"Principal Amount: ₹{principal}")
        print(f"Annual Interest Rate: {annual_rate * 100}%")
        print()
        print(f"Daily Interest: ₹{daily_interest:.2f}")
        print(f"Monthly Interest: ₹{monthly_interest:.2f}")
        print()
        print("💡 This means:")
        print(f"   - Customer pays ₹{daily_interest:.2f} per day, OR")
        print(f"   - Customer pays ₹{monthly_interest:.2f} per month")
        print()
        print("🎯 Smart Payment Example:")
        smart_payment = daily_interest + Decimal('50.00')
        print(f"   If customer pays ₹{smart_payment:.2f} today:")
        print(f"   - ₹{daily_interest:.2f} goes to interest")
        print(f"   - ₹50.00 reduces the principal")
        print(f"   - New principal: ₹{principal - Decimal('50.00')}")
        
        print("\n============================================================")
        print("🚀 Ready to start the application!")
        print("Run: python3 run.py")
        print("Then visit: http://localhost:8080")
        print("============================================================")

if __name__ == '__main__':
    create_demo_data()