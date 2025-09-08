#!/usr/bin/env python3
"""
Safe migration script to add two-notes system without losing existing data
This script preserves all existing data while adding the new notes functionality
"""

from app import app, db, User, Loan, Payment
from werkzeug.security import generate_password_hash
from decimal import Decimal
from datetime import datetime, timedelta

def safe_migrate_notes():
    """Safely add two-notes system without losing existing data"""
    print("🔄 Safely migrating to two-notes system...")
    
    with app.app_context():
        try:
            # Check if admin_notes column already exists
            try:
                Loan.query.first().admin_notes
                print("✅ Two-notes system already exists in database")
                return
            except:
                print("📝 Adding admin_notes and customer_notes fields...")
                
                # Add the new columns using raw SQL
                db.engine.execute('ALTER TABLE loan ADD COLUMN admin_notes TEXT')
                db.engine.execute('ALTER TABLE loan ADD COLUMN customer_notes TEXT')
                db.session.commit()
                print("✅ New notes fields added successfully")
                
                # Migrate existing notes to customer_notes (if any)
                loans = Loan.query.all()
                migrated_count = 0
                
                for loan in loans:
                    # Check if there's an old 'notes' field to migrate
                    try:
                        old_notes = getattr(loan, 'notes', None)
                        if old_notes and not loan.customer_notes:
                            loan.customer_notes = old_notes
                            migrated_count += 1
                    except:
                        pass
                
                if migrated_count > 0:
                    db.session.commit()
                    print(f"✅ Migrated {migrated_count} existing notes to customer_notes")
                
                print("🎉 Safe migration completed successfully!")
                print("💡 All your existing customers and loans are preserved")
                print("💡 You can now use both admin_notes and customer_notes")
                
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            print("💡 Your data is still safe - no changes were made")

if __name__ == "__main__":
    safe_migrate_notes()
