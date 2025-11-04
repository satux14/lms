#!/usr/bin/env python3
"""
Transfer Loans Between Users
Moves loans from one user to another while preserving all payment history and metadata
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_multi import app, db, User, Loan, Payment, db_manager

def get_db_path(instance_name):
    """Get the database path for the instance"""
    base_dir = Path(__file__).parent
    db_path = base_dir / 'instance' / instance_name / 'database' / f'lending_app_{instance_name}.db'
    
    if not db_path.exists():
        # Try alternate path
        db_path = base_dir / 'instances' / instance_name / 'database' / f'lending_app_{instance_name}.db'
    
    return str(db_path) if db_path.exists() else None


def list_users(instance_name):
    """List all users in the instance"""
    print(f"\n{'='*80}")
    print(f"Users in instance: {instance_name}")
    print(f"{'='*80}\n")
    
    with app.app_context():
        if not db_manager.initialized:
            db_manager.initialize_all_databases()
        
        users = db_manager.get_query_for_instance(instance_name, User).filter_by(is_admin=False).all()
        
        if not users:
            print("No users found!")
            return []
        
        print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Loans':<10}")
        print("-" * 80)
        
        for user in users:
            loan_count = db_manager.get_query_for_instance(instance_name, Loan).filter_by(customer_id=user.id).count()
            email = user.email or "N/A"
            print(f"{user.id:<5} {user.username:<20} {email:<30} {loan_count:<10}")
        
        print()
        return users


def list_user_loans(instance_name, user_id):
    """List all loans for a specific user"""
    with app.app_context():
        if not db_manager.initialized:
            db_manager.initialize_all_databases()
        
        user = db_manager.get_query_for_instance(instance_name, User).filter_by(id=user_id).first()
        if not user:
            print(f"User ID {user_id} not found!")
            return []
        
        loans = db_manager.get_query_for_instance(instance_name, Loan).filter_by(customer_id=user_id).all()
        
        if not loans:
            print(f"\nNo loans found for user: {user.username}")
            return []
        
        print(f"\n{'='*100}")
        print(f"Loans for user: {user.username} (ID: {user.id})")
        print(f"{'='*100}\n")
        
        print(f"{'ID':<5} {'Loan Name':<30} {'Principal':<15} {'Remaining':<15} {'Rate':<8} {'Payments':<10}")
        print("-" * 100)
        
        for loan in loans:
            payment_count = db_manager.get_query_for_instance(instance_name, Payment).filter_by(loan_id=loan.id).count()
            print(f"{loan.id:<5} {loan.loan_name[:28]:<30} ₹{loan.principal_amount:<13.2f} "
                  f"₹{loan.remaining_principal:<13.2f} {loan.interest_rate:<7.2f}% {payment_count:<10}")
        
        print()
        return loans


def transfer_loans(instance_name, from_user_id, to_user_id, loan_ids=None):
    """
    Transfer loans from one user to another
    
    Args:
        instance_name: Instance name (prod, dev, testing)
        from_user_id: Source user ID
        to_user_id: Target user ID
        loan_ids: List of specific loan IDs to transfer (None = all loans)
    """
    with app.app_context():
        if not db_manager.initialized:
            db_manager.initialize_all_databases()
        
        # Get users
        from_user = db_manager.get_query_for_instance(instance_name, User).filter_by(id=from_user_id).first()
        to_user = db_manager.get_query_for_instance(instance_name, User).filter_by(id=to_user_id).first()
        
        if not from_user:
            print(f"❌ Source user ID {from_user_id} not found!")
            return False
        
        if not to_user:
            print(f"❌ Target user ID {to_user_id} not found!")
            return False
        
        # Get loans to transfer
        query = db_manager.get_query_for_instance(instance_name, Loan).filter_by(customer_id=from_user_id)
        if loan_ids:
            query = query.filter(Loan.id.in_(loan_ids))
        
        loans = query.all()
        
        if not loans:
            print(f"❌ No loans found to transfer!")
            return False
        
        # Confirm transfer
        print(f"\n{'='*80}")
        print(f"TRANSFER CONFIRMATION")
        print(f"{'='*80}")
        print(f"From: {from_user.username} (ID: {from_user.id})")
        print(f"To:   {to_user.username} (ID: {to_user.id})")
        print(f"Loans to transfer: {len(loans)}")
        print(f"\nLoans:")
        for loan in loans:
            payment_count = db_manager.get_query_for_instance(instance_name, Payment).filter_by(loan_id=loan.id).count()
            print(f"  - Loan ID {loan.id}: {loan.loan_name} (₹{loan.principal_amount:.2f}, {payment_count} payments)")
        print(f"{'='*80}\n")
        
        confirm = input("Type 'YES' to confirm transfer: ")
        if confirm != 'YES':
            print("❌ Transfer cancelled.")
            return False
        
        # Perform transfer
        try:
            session = db_manager.get_session_for_instance(instance_name)
            
            transferred_count = 0
            for loan in loans:
                # Update loan customer_id
                loan.customer_id = to_user_id
                session.add(loan)
                transferred_count += 1
                
                # Get payment count for logging
                payment_count = db_manager.get_query_for_instance(instance_name, Payment).filter_by(loan_id=loan.id).count()
                print(f"✓ Transferred Loan ID {loan.id}: {loan.loan_name} ({payment_count} payments)")
            
            session.commit()
            
            print(f"\n{'='*80}")
            print(f"✅ Successfully transferred {transferred_count} loan(s) from {from_user.username} to {to_user.username}")
            print(f"{'='*80}\n")
            
            return True
            
        except Exception as e:
            session.rollback()
            print(f"\n❌ Error during transfer: {e}")
            return False


def main():
    """Main function"""
    print("\n" + "="*80)
    print("LOAN TRANSFER UTILITY")
    print("="*80)
    
    # Get instance
    print("\nAvailable instances: prod, dev, testing")
    instance_name = input("Enter instance name (default: prod): ").strip() or 'prod'
    
    if instance_name not in ['prod', 'dev', 'testing']:
        print("❌ Invalid instance name!")
        return
    
    # Check database exists
    db_path = get_db_path(instance_name)
    if not db_path:
        print(f"❌ Database not found for instance: {instance_name}")
        return
    
    print(f"✓ Using database: {db_path}")
    
    while True:
        print("\n" + "="*80)
        print("MENU")
        print("="*80)
        print("1. List all users")
        print("2. List loans for a user")
        print("3. Transfer loans between users")
        print("4. Exit")
        print("="*80)
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            list_users(instance_name)
        
        elif choice == '2':
            user_id = input("Enter user ID: ").strip()
            try:
                user_id = int(user_id)
                list_user_loans(instance_name, user_id)
            except ValueError:
                print("❌ Invalid user ID!")
        
        elif choice == '3':
            # List users first
            list_users(instance_name)
            
            try:
                from_user_id = int(input("\nEnter source user ID (FROM): ").strip())
                
                # Show source user's loans
                loans = list_user_loans(instance_name, from_user_id)
                if not loans:
                    continue
                
                to_user_id = int(input("\nEnter target user ID (TO): ").strip())
                
                # Ask if specific loans or all
                transfer_all = input("\nTransfer ALL loans? (y/n, default: y): ").strip().lower()
                
                loan_ids = None
                if transfer_all == 'n':
                    loan_ids_input = input("Enter loan IDs to transfer (comma-separated): ").strip()
                    try:
                        loan_ids = [int(x.strip()) for x in loan_ids_input.split(',')]
                    except ValueError:
                        print("❌ Invalid loan IDs!")
                        continue
                
                # Perform transfer
                transfer_loans(instance_name, from_user_id, to_user_id, loan_ids)
                
            except ValueError:
                print("❌ Invalid input!")
            except KeyboardInterrupt:
                print("\n\n❌ Transfer cancelled by user.")
        
        elif choice == '4':
            print("\nGoodbye!\n")
            break
        
        else:
            print("❌ Invalid option!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user. Exiting...\n")
        sys.exit(0)

