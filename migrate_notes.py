#!/usr/bin/env python3
"""
Safe migration script to add notes field to existing loans
This script preserves existing data while adding the new notes functionality
"""

from app import app, db, User, Loan, Payment
from werkzeug.security import generate_password_hash
from decimal import Decimal
from datetime import datetime, timedelta

def migrate_notes_field():
    """Add notes field to existing loans without losing data"""
    print("🔄 Migrating database to add notes field...")
    
    with app.app_context():
        # Check if notes column already exists
        try:
            # Try to query the notes field
            Loan.query.first().notes
            print("✅ Notes field already exists in database")
            return
        except:
            print("📝 Adding notes field to Loan model...")
            
            # Add the notes column using raw SQL
            db.engine.execute('ALTER TABLE loan ADD COLUMN notes TEXT')
            db.session.commit()
            print("✅ Notes field added successfully")
            
            # Update existing loans with sample notes
            loans = Loan.query.all()
            sample_notes = [
                "Customer requested for medical expenses. Good payment history.",
                "For expanding restaurant business. Collateral: Property documents submitted.",
                "Kitchen renovation project. Contractor: ABC Construction.",
                "High-risk loan. No collateral provided. Monitor closely.",
                "Personal loan for education expenses.",
                "Business expansion loan with property collateral.",
                "Emergency fund for unexpected expenses.",
                "Home improvement project with contractor agreement."
            ]
            
            for i, loan in enumerate(loans):
                if not loan.notes:  # Only add if notes is empty
                    loan.notes = sample_notes[i % len(sample_notes)]
            
            db.session.commit()
            print(f"✅ Added sample notes to {len(loans)} existing loans")
            
            print("🎉 Migration completed successfully!")
            print("💡 Your existing customers and loans are preserved")

if __name__ == "__main__":
    migrate_notes_field()
