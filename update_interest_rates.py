#!/usr/bin/env python3
"""
Update existing loans to use 21% interest rate
"""

from app import app, db, Loan
from decimal import Decimal

def update_interest_rates():
    """Update all existing loans to use 21% interest rate"""
    print("🔄 Updating interest rates to 21%...")
    
    with app.app_context():
        # Get all loans
        loans = Loan.query.all()
        
        if not loans:
            print("❌ No loans found")
            return
        
        updated_count = 0
        for loan in loans:
            if loan.interest_rate != Decimal('0.21'):
                old_rate = loan.interest_rate * 100
                loan.interest_rate = Decimal('0.21')
                updated_count += 1
                print(f"✅ Updated {loan.loan_name} from {old_rate:.1f}% to 21.0%")
        
        if updated_count > 0:
            db.session.commit()
            print(f"🎉 Updated {updated_count} loans to 21% interest rate!")
        else:
            print("✅ All loans already have 21% interest rate")

if __name__ == "__main__":
    update_interest_rates()
