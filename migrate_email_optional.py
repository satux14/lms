#!/usr/bin/env python3
"""
Migration script to make email optional in the database
This script updates the existing database schema to allow NULL emails
"""

from app import app, db
import sqlite3

def migrate_email_optional():
    """Make email field optional in the database"""
    print("🔄 Migrating email field to be optional...")
    
    with app.app_context():
        try:
            # Get the database connection
            conn = db.engine.connect()
            
            # Check if the table exists and get its schema
            cursor = conn.execute(db.text("PRAGMA table_info(user)"))
            columns = cursor.fetchall()
            
            # Find the email column
            email_column = None
            for col in columns:
                if col[1] == 'email':  # col[1] is the column name
                    email_column = col
                    break
            
            if email_column:
                print(f"📧 Found email column: {email_column}")
                
                # Check if email is already nullable
                if email_column[3] == 0:  # col[3] is notnull (0 = nullable, 1 = not null)
                    print("✅ Email column is already nullable")
                    return
                
                print("🔧 Email column is currently NOT NULL, updating...")
                
                # SQLite doesn't support ALTER COLUMN directly, so we need to:
                # 1. Create a new table with the correct schema
                # 2. Copy data from old table to new table
                # 3. Drop old table
                # 4. Rename new table
                
                # Step 1: Create new table with nullable email
                conn.execute(db.text("""
                    CREATE TABLE user_new (
                        id INTEGER PRIMARY KEY,
                        username VARCHAR(80) NOT NULL UNIQUE,
                        email VARCHAR(120) UNIQUE,
                        password_hash VARCHAR(120) NOT NULL,
                        is_admin BOOLEAN DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Step 2: Copy data from old table to new table
                conn.execute(db.text("""
                    INSERT INTO user_new (id, username, email, password_hash, is_admin, created_at)
                    SELECT id, username, email, password_hash, is_admin, created_at
                    FROM user
                """))
                
                # Step 3: Drop old table
                conn.execute(db.text("DROP TABLE user"))
                
                # Step 4: Rename new table
                conn.execute(db.text("ALTER TABLE user_new RENAME TO user"))
                
                # Commit the changes
                conn.commit()
                
                print("✅ Email field is now optional!")
                print("💡 Users can now be created without email addresses")
                
            else:
                print("❌ Email column not found in user table")
                
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            print("💡 You may need to recreate the database")
            
        finally:
            conn.close()

if __name__ == "__main__":
    migrate_email_optional()
