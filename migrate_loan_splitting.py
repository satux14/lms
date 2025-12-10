#!/usr/bin/env python3
"""
Migration script to add loan splitting functionality
Adds split_loan_id and original_principal_amount to Payment table
Creates loan_split table
"""

#!/usr/bin/env python3
"""
Migration script to add loan splitting functionality
Adds split_loan_id and original_principal_amount to Payment table
Creates loan_split table
"""

import sqlite3
import sys
from pathlib import Path

# Instance configuration
VALID_INSTANCES = ['prod', 'dev', 'testing']
INSTANCES_DIR = Path('instances')

def get_database_path(instance):
    """Get database path for instance"""
    return INSTANCES_DIR / instance / 'database' / f'lending_app_{instance}.db'

def check_column_exists(conn, table_name, column_name):
    """Check if a column exists in a table"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def check_table_exists(conn, table_name):
    """Check if a table exists"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def migrate_instance(instance_name, dry_run=True):
    """Migrate a specific instance"""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating {instance_name} instance...")
    
    db_path = get_database_path(instance_name)
    if not db_path.exists():
        print(f"✗ Database not found: {db_path}")
        return False
    
    print(f"Database: {db_path}")
    
    changes_made = []
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check and add split_loan_id column to payment table
        if not check_column_exists(conn, 'payment', 'split_loan_id'):
            if not dry_run:
                cursor.execute('ALTER TABLE payment ADD COLUMN split_loan_id INTEGER')
                cursor.execute('ALTER TABLE payment ADD COLUMN original_principal_amount NUMERIC(15, 2)')
                conn.commit()
            print("✓ Would add split_loan_id and original_principal_amount columns to payment table")
            changes_made.append("Added split_loan_id and original_principal_amount to payment")
        else:
            print("✓ split_loan_id column already exists in payment table")
            if not check_column_exists(conn, 'payment', 'original_principal_amount'):
                if not dry_run:
                    cursor.execute('ALTER TABLE payment ADD COLUMN original_principal_amount NUMERIC(15, 2)')
                    conn.commit()
                print("✓ Would add original_principal_amount column to payment table")
                changes_made.append("Added original_principal_amount to payment")
            else:
                print("✓ original_principal_amount column already exists in payment table")
        
        # Check and create loan_split table
        if not check_table_exists(conn, 'loan_split'):
            if not dry_run:
                cursor.execute('''
                    CREATE TABLE loan_split (
                        id INTEGER NOT NULL PRIMARY KEY,
                        original_loan_id INTEGER NOT NULL,
                        split_loan_id INTEGER NOT NULL,
                        split_principal_amount NUMERIC(15, 2) NOT NULL,
                        created_at DATETIME,
                        created_by_user_id INTEGER NOT NULL,
                        FOREIGN KEY(original_loan_id) REFERENCES loan (id),
                        FOREIGN KEY(split_loan_id) REFERENCES loan (id),
                        FOREIGN KEY(created_by_user_id) REFERENCES user (id)
                    )
                ''')
                conn.commit()
            print("✓ Would create loan_split table")
            changes_made.append("Created loan_split table")
        else:
            print("✓ loan_split table already exists")
        
        conn.close()
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    if dry_run:
        print(f"\n[DRY RUN SUMMARY]")
        print(f"Changes that would be made: {len(changes_made)}")
        for change in changes_made:
            print(f"  - {change}")
    else:
        print(f"\n[MIGRATION SUMMARY]")
        print(f"Changes made: {len(changes_made)}")
        for change in changes_made:
            print(f"  ✓ {change}")
    
    return True

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Migrate loan splitting functionality')
    parser.add_argument('--instance', help='Specific instance to migrate', default=None)
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry-run)')
    args = parser.parse_args()
    
    dry_run = not args.apply
    
    if args.instance:
        if args.instance not in VALID_INSTANCES:
            print(f"Error: Invalid instance '{args.instance}'")
            sys.exit(1)
        migrate_instance(args.instance, dry_run=dry_run)
    else:
        for instance in VALID_INSTANCES:
            migrate_instance(instance, dry_run=dry_run)
    
    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN COMPLETE - No changes were made")
        print("Run with --apply to make changes")
        print("="*60)

