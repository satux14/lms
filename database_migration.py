#!/usr/bin/env python3
"""
Database Migration System
========================

This script handles database schema migrations without data loss.
It adds new columns, modifies existing ones, and preserves all data.

Usage:
    python database_migration.py migrate <instance_name>
    python database_migration.py check <instance_name>
    python database_migration.py backup <instance_name>
"""

import sqlite3
import os
import shutil
from datetime import datetime
from pathlib import Path

class DatabaseMigrator:
    def __init__(self):
        self.instances = ['prod', 'dev', 'testing']
        self.migrations = [
            {
                'version': 1,
                'description': 'Add password reset fields',
                'sql': [
                    "ALTER TABLE user ADD COLUMN reset_token VARCHAR(100)",
                    "ALTER TABLE user ADD COLUMN reset_token_expires DATETIME"
                ]
            }
            # Add future migrations here
        ]
    
    def get_database_path(self, instance_name):
        """Get the database path for an instance"""
        return f"instances/{instance_name}/database/lending_app_{instance_name}.db"
    
    def backup_database(self, instance_name):
        """Create a backup of the database before migration"""
        db_path = self.get_database_path(instance_name)
        if not os.path.exists(db_path):
            print(f"❌ Database not found: {db_path}")
            return None
        
        # Create backup directory
        backup_dir = Path(f"backups/{instance_name}/database")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{instance_name}_lending_app_backup_{timestamp}.db"
        
        # Copy database
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup created: {backup_path}")
        return str(backup_path)
    
    def check_migration_status(self, instance_name):
        """Check what migrations have been applied"""
        db_path = self.get_database_path(instance_name)
        if not os.path.exists(db_path):
            print(f"❌ Database not found: {db_path}")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if migration table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='schema_migrations'
        """)
        
        if not cursor.fetchone():
            print(f"📋 No migration history found for {instance_name}")
            print("   This appears to be a fresh database or pre-migration system")
        else:
            # Get applied migrations
            cursor.execute("SELECT version, description, applied_at FROM schema_migrations ORDER BY version")
            migrations = cursor.fetchall()
            
            print(f"📋 Migration history for {instance_name}:")
            for version, description, applied_at in migrations:
                print(f"   ✅ v{version}: {description} ({applied_at})")
        
        conn.close()
    
    def create_migration_table(self, cursor):
        """Create the migration tracking table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def get_applied_migrations(self, cursor):
        """Get list of applied migration versions"""
        cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
        return [row[0] for row in cursor.fetchall()]
    
    def migrate_database(self, instance_name, dry_run=False):
        """Apply pending migrations to the database"""
        db_path = self.get_database_path(instance_name)
        if not os.path.exists(db_path):
            print(f"❌ Database not found: {db_path}")
            return False
        
        print(f"🔄 {'DRY RUN: ' if dry_run else ''}Migrating {instance_name} database...")
        
        # Create backup before migration
        if not dry_run:
            backup_path = self.backup_database(instance_name)
            if not backup_path:
                return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Create migration table if it doesn't exist
            self.create_migration_table(cursor)
            
            # Get applied migrations
            applied_versions = self.get_applied_migrations(cursor)
            
            # Find pending migrations
            pending_migrations = [m for m in self.migrations if m['version'] not in applied_versions]
            
            if not pending_migrations:
                print(f"✅ No pending migrations for {instance_name}")
                return True
            
            print(f"📋 Found {len(pending_migrations)} pending migrations:")
            for migration in pending_migrations:
                print(f"   - v{migration['version']}: {migration['description']}")
            
            if dry_run:
                print("🔍 Dry run completed - no changes made")
                return True
            
            # Apply migrations
            for migration in pending_migrations:
                print(f"🔄 Applying migration v{migration['version']}: {migration['description']}")
                
                for sql in migration['sql']:
                    try:
                        cursor.execute(sql)
                        print(f"   ✅ Executed: {sql}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" in str(e):
                            print(f"   ⚠️  Column already exists: {sql}")
                        else:
                            print(f"   ❌ Error: {e}")
                            raise
                
                # Record migration
                cursor.execute("""
                    INSERT INTO schema_migrations (version, description) 
                    VALUES (?, ?)
                """, (migration['version'], migration['description']))
            
            conn.commit()
            print(f"✅ Migration completed successfully for {instance_name}")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def migrate_all_instances(self, dry_run=False):
        """Migrate all instances"""
        print(f"🔄 {'DRY RUN: ' if dry_run else ''}Migrating all instances...")
        
        for instance in self.instances:
            print(f"\n--- Migrating {instance.upper()} ---")
            self.migrate_database(instance, dry_run)
    
    def show_status(self):
        """Show migration status for all instances"""
        print("📊 Migration Status for All Instances:")
        print("=" * 50)
        
        for instance in self.instances:
            print(f"\n--- {instance.upper()} ---")
            self.check_migration_status(instance)

def main():
    import sys
    
    migrator = DatabaseMigrator()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python database_migration.py status                    # Show status of all instances")
        print("  python database_migration.py check <instance>         # Check specific instance")
        print("  python database_migration.py migrate <instance>       # Migrate specific instance")
        print("  python database_migration.py migrate-all              # Migrate all instances")
        print("  python database_migration.py migrate-all --dry-run    # Dry run all instances")
        print("  python database_migration.py backup <instance>        # Backup specific instance")
        return
    
    command = sys.argv[1]
    
    if command == "status":
        migrator.show_status()
    elif command == "check":
        if len(sys.argv) < 3:
            print("❌ Please specify instance name")
            return
        migrator.check_migration_status(sys.argv[2])
    elif command == "migrate":
        if len(sys.argv) < 3:
            print("❌ Please specify instance name")
            return
        migrator.migrate_database(sys.argv[2])
    elif command == "migrate-all":
        dry_run = "--dry-run" in sys.argv
        migrator.migrate_all_instances(dry_run)
    elif command == "backup":
        if len(sys.argv) < 3:
            print("❌ Please specify instance name")
            return
        migrator.backup_database(sys.argv[2])
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()
