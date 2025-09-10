#!/usr/bin/env python3
"""
Debug script to calculate accumulated interest for a specific loan
"""

import sys
import os
from decimal import Decimal
from datetime import date, datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_multi import init_app, db_manager

def debug_accumulated_interest(instance_name, loan_id):
    """Debug accumulated interest calculation for a specific loan"""
    
    # Initialize the app
    app = init_app()
    
    with app.app_context():
        # Set the instance in g object
        from flask import g
        g.current_instance = instance_name
        
        # Get the loan
        from app_multi import Loan, Payment, get_loan_query, get_payment_query
        
        loan = get_loan_query().filter_by(id=loan_id).first()
        if not loan:
            print(f"Loan {loan_id} not found in instance {instance_name}")
            return
        
        print(f"=== LOAN DETAILS ===")
        print(f"Loan ID: {loan.id}")
        print(f"Loan Name: {loan.loan_name}")
        print(f"Principal Amount: ₹{loan.principal_amount}")
        print(f"Interest Rate: {loan.interest_rate * 100:.2f}% (stored as {loan.interest_rate})")
        print(f"Loan Type: {loan.loan_type}")
        print(f"Created At: {loan.created_at}")
        print(f"Today's Date: {date.today()}")
        
        if loan.loan_type == 'interest_only':
            print(f"\n=== INTEREST-ONLY LOAN CALCULATION ===")
            
            # Calculate days since creation
            days = (date.today() - loan.created_at.date()).days
            print(f"Days since creation: {days}")
            
            # Calculate daily rate
            daily_rate = loan.interest_rate / 365
            print(f"Daily rate: {daily_rate:.8f} ({loan.interest_rate * 100:.2f}% / 365)")
            
            # Calculate total interest
            total_interest = loan.principal_amount * daily_rate * days
            print(f"Total interest calculated: ₹{total_interest:.2f}")
            print(f"  Formula: ₹{loan.principal_amount} × {daily_rate:.8f} × {days} = ₹{total_interest:.2f}")
            
            # Get verified interest payments
            verified_payments = get_payment_query().filter_by(
                loan_id=loan.id, 
                status='verified'
            ).all()
            
            total_verified_interest = sum(payment.interest_amount for payment in verified_payments)
            print(f"\n=== VERIFIED PAYMENTS ===")
            print(f"Number of verified payments: {len(verified_payments)}")
            print(f"Total verified interest paid: ₹{total_verified_interest:.2f}")
            
            for i, payment in enumerate(verified_payments, 1):
                print(f"  Payment {i}: ₹{payment.amount:.2f} (Interest: ₹{payment.interest_amount:.2f}) on {payment.payment_date.date()}")
            
            # Calculate accumulated interest
            accumulated_interest = total_interest - total_verified_interest
            print(f"\n=== FINAL CALCULATION ===")
            print(f"Total interest: ₹{total_interest:.2f}")
            print(f"Minus verified payments: -₹{total_verified_interest:.2f}")
            print(f"Accumulated interest: ₹{accumulated_interest:.2f}")
            
        else:
            print(f"\n=== REGULAR LOAN CALCULATION ===")
            print("This is a regular loan - accumulated interest calculation is different")
            print("It calculates interest on remaining principal from last payment date")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python debug_interest.py <instance_name> <loan_id>")
        print("Example: python debug_interest.py testing 1")
        sys.exit(1)
    
    instance_name = sys.argv[1]
    loan_id = int(sys.argv[2])
    
    debug_accumulated_interest(instance_name, loan_id)
