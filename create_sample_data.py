#!/usr/bin/env python3
"""
Sample Data Creation Script for Multi-Instance Lending Management System
======================================================================

This script creates comprehensive sample data for the dev instance including:
- 5 sample customers with realistic profiles
- 7 diverse loans with different types and interest rates
- 10 sample payments with different statuses and payment methods

Usage:
    python3 create_sample_data.py

The data will be created in the dev instance only, keeping prod and testing clean.
"""

from app_multi import init_app, db_manager, User, Loan, Payment
from werkzeug.security import generate_password_hash
from decimal import Decimal
from datetime import datetime, timedelta

def create_sample_data():
    """Create comprehensive sample data for dev instance"""
    print("Creating sample data for dev instance...")
    
    # Initialize the app
    app = init_app()
    
    with app.app_context():
        from flask import g
        g.current_instance = 'dev'
        
        # Create sample customers
        customers_data = [
            {
                'username': 'john_doe',
                'email': 'john@example.com',
                'password': 'password123',
                'is_admin': False
            },
            {
                'username': 'jane_smith',
                'email': 'jane@example.com', 
                'password': 'password123',
                'is_admin': False
            },
            {
                'username': 'mike_wilson',
                'email': 'mike@example.com',
                'password': 'password123',
                'is_admin': False
            },
            {
                'username': 'sarah_jones',
                'email': 'sarah@example.com',
                'password': 'password123',
                'is_admin': False
            },
            {
                'username': 'david_brown',
                'email': 'david@example.com',
                'password': 'password123',
                'is_admin': False
            }
        ]
        
        # Create customers
        created_users = []
        for customer_data in customers_data:
            # Check if user already exists
            existing_user = db_manager.get_query_for_instance('dev', User).filter_by(username=customer_data['username']).first()
            if existing_user:
                print(f"User {customer_data['username']} already exists, skipping...")
                created_users.append(existing_user)
                continue
                
            user = User(
                username=customer_data['username'],
                email=customer_data['email'],
                password_hash=generate_password_hash(customer_data['password']),
                is_admin=customer_data['is_admin']
            )
            db_manager.add_to_instance('dev', user)
            created_users.append(user)
            print(f'Created user: {user.username} (ID: {user.id})')
        
        # Create sample loans
        loans_data = [
            {
                'customer': created_users[0],  # john_doe
                'loan_name': 'Home Renovation Loan',
                'principal': 50000,
                'interest_rate': 0.18,  # 18%
                'payment_frequency': 'monthly',
                'loan_type': 'regular',
                'created_at': datetime.now() - timedelta(days=30)
            },
            {
                'customer': created_users[0],  # john_doe
                'loan_name': 'Emergency Fund',
                'principal': 15000,
                'interest_rate': 0.24,  # 24%
                'payment_frequency': 'daily',
                'loan_type': 'regular',
                'created_at': datetime.now() - timedelta(days=15)
            },
            {
                'customer': created_users[1],  # jane_smith
                'loan_name': 'Business Expansion',
                'principal': 100000,
                'interest_rate': 0.15,  # 15%
                'payment_frequency': 'monthly',
                'loan_type': 'regular',
                'created_at': datetime.now() - timedelta(days=45)
            },
            {
                'customer': created_users[1],  # jane_smith
                'loan_name': 'Equipment Purchase',
                'principal': 25000,
                'interest_rate': 0.21,  # 21%
                'payment_frequency': 'daily',
                'loan_type': 'interest_only',
                'created_at': datetime.now() - timedelta(days=20)
            },
            {
                'customer': created_users[2],  # mike_wilson
                'loan_name': 'Vehicle Loan',
                'principal': 30000,
                'interest_rate': 0.12,  # 12%
                'payment_frequency': 'monthly',
                'loan_type': 'regular',
                'created_at': datetime.now() - timedelta(days=60)
            },
            {
                'customer': created_users[3],  # sarah_jones
                'loan_name': 'Education Fund',
                'principal': 40000,
                'interest_rate': 0.09,  # 9%
                'payment_frequency': 'monthly',
                'loan_type': 'regular',
                'created_at': datetime.now() - timedelta(days=90)
            },
            {
                'customer': created_users[4],  # david_brown
                'loan_name': 'Investment Property',
                'principal': 200000,
                'interest_rate': 0.16,  # 16%
                'payment_frequency': 'monthly',
                'loan_type': 'regular',
                'created_at': datetime.now() - timedelta(days=120)
            }
        ]
        
        # Create loans
        created_loans = []
        for loan_data in loans_data:
            # Check if loan already exists
            existing_loan = db_manager.get_query_for_instance('dev', Loan).filter_by(
                customer_id=loan_data['customer'].id,
                loan_name=loan_data['loan_name']
            ).first()
            if existing_loan:
                print(f"Loan {loan_data['loan_name']} for {loan_data['customer'].username} already exists, skipping...")
                created_loans.append(existing_loan)
                continue
                
            loan = Loan(
                customer_id=loan_data['customer'].id,
                loan_name=loan_data['loan_name'],
                principal_amount=Decimal(str(loan_data['principal'])),
                remaining_principal=Decimal(str(loan_data['principal'])),
                interest_rate=loan_data['interest_rate'],
                payment_frequency=loan_data['payment_frequency'],
                loan_type=loan_data['loan_type'],
                is_active=True,
                created_at=loan_data['created_at']
            )
            db_manager.add_to_instance('dev', loan)
            created_loans.append(loan)
            print(f'Created loan: {loan.loan_name} for {loan_data["customer"].username} (₹{loan.principal_amount})')
        
        # Create sample payments
        payments_data = [
            # Payments for Home Renovation Loan
            {
                'loan_name': 'Home Renovation Loan',
                'amount': 5000,
                'payment_date': datetime.now() - timedelta(days=25),
                'payment_method': 'bank_transfer',
                'transaction_id': 'TXN001',
                'status': 'verified'
            },
            {
                'loan_name': 'Home Renovation Loan',
                'amount': 3000,
                'payment_date': datetime.now() - timedelta(days=15),
                'payment_method': 'gpay',
                'transaction_id': 'TXN002',
                'status': 'verified'
            },
            {
                'loan_name': 'Home Renovation Loan',
                'amount': 2000,
                'payment_date': datetime.now() - timedelta(days=5),
                'payment_method': 'upi',
                'transaction_id': 'TXN003',
                'status': 'pending'
            },
            # Payments for Emergency Fund
            {
                'loan_name': 'Emergency Fund',
                'amount': 1000,
                'payment_date': datetime.now() - timedelta(days=10),
                'payment_method': 'cash',
                'transaction_id': 'TXN004',
                'status': 'verified'
            },
            {
                'loan_name': 'Emergency Fund',
                'amount': 500,
                'payment_date': datetime.now() - timedelta(days=3),
                'payment_method': 'phonepe',
                'transaction_id': 'TXN005',
                'status': 'verified'
            },
            # Payments for Business Expansion
            {
                'loan_name': 'Business Expansion',
                'amount': 10000,
                'payment_date': datetime.now() - timedelta(days=40),
                'payment_method': 'bank_transfer',
                'transaction_id': 'TXN006',
                'status': 'verified'
            },
            {
                'loan_name': 'Business Expansion',
                'amount': 15000,
                'payment_date': datetime.now() - timedelta(days=20),
                'payment_method': 'bank_transfer',
                'transaction_id': 'TXN007',
                'status': 'verified'
            },
            # Payments for Vehicle Loan
            {
                'loan_name': 'Vehicle Loan',
                'amount': 3000,
                'payment_date': datetime.now() - timedelta(days=55),
                'payment_method': 'bank_transfer',
                'transaction_id': 'TXN008',
                'status': 'verified'
            },
            {
                'loan_name': 'Vehicle Loan',
                'amount': 3000,
                'payment_date': datetime.now() - timedelta(days=25),
                'payment_method': 'bank_transfer',
                'transaction_id': 'TXN009',
                'status': 'verified'
            },
            {
                'loan_name': 'Vehicle Loan',
                'amount': 3000,
                'payment_date': datetime.now() - timedelta(days=5),
                'payment_method': 'gpay',
                'transaction_id': 'TXN010',
                'status': 'pending'
            }
        ]
        
        # Create payments
        for payment_data in payments_data:
            # Find the loan
            loan = next((l for l in created_loans if l.loan_name == payment_data['loan_name']), None)
            if not loan:
                print(f"Loan {payment_data['loan_name']} not found, skipping payment...")
                continue
                
            # Check if payment already exists
            existing_payment = db_manager.get_query_for_instance('dev', Payment).filter_by(
                loan_id=loan.id,
                transaction_id=payment_data['transaction_id']
            ).first()
            if existing_payment:
                print(f"Payment {payment_data['transaction_id']} already exists, skipping...")
                continue
            
            # Calculate interest and principal amounts
            amount = Decimal(str(payment_data['amount']))
            
            if loan.loan_type == 'interest_only':
                # For interest-only loans, all payment goes to interest
                interest_amount = amount
                principal_amount = Decimal('0')
                payment_type = 'interest'
            else:
                # For regular loans, calculate based on daily interest
                daily_interest = loan.remaining_principal * loan.interest_rate / 360
                if amount >= daily_interest:
                    interest_amount = daily_interest
                    principal_amount = amount - daily_interest
                    payment_type = 'both'
                else:
                    interest_amount = amount
                    principal_amount = Decimal('0')
                    payment_type = 'interest'
            
            payment = Payment(
                loan_id=loan.id,
                amount=amount,
                payment_type=payment_type,
                interest_amount=interest_amount,
                principal_amount=principal_amount,
                payment_date=payment_data['payment_date'],
                payment_method=payment_data['payment_method'],
                transaction_id=payment_data['transaction_id'],
                status=payment_data['status']
            )
            
            db_manager.add_to_instance('dev', payment)
            print(f'Created payment: ₹{amount} for {loan.loan_name} ({payment_data["status"]})')
        
        # Show final summary
        final_users = db_manager.get_query_for_instance('dev', User).all()
        final_loans = db_manager.get_query_for_instance('dev', Loan).all()
        final_payments = db_manager.get_query_for_instance('dev', Payment).all()
        
        print(f'\n=== DEV INSTANCE SUMMARY ===')
        print(f'Users: {len(final_users)} (1 admin + {len([u for u in final_users if not u.is_admin])} customers)')
        print(f'Loans: {len(final_loans)}')
        print(f'Payments: {len(final_payments)}')
        print(f'Verified Payments: {len([p for p in final_payments if p.status == "verified"])}')
        print(f'Pending Payments: {len([p for p in final_payments if p.status == "pending"])}')
        
        print(f'\n=== LOGIN CREDENTIALS ===')
        print(f'Admin: username=admin, password=admin123')
        print(f'Customers: username=<customer_name>, password=password123')
        print(f'Available customers: {[u.username for u in final_users if not u.is_admin]}')
        
        print(f'\nSample data creation completed successfully!')
        print(f'Access the dev instance at: http://localhost:8080/dev/')

if __name__ == '__main__':
    create_sample_data()
