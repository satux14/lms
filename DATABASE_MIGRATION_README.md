# Database Migration System

## ⚠️ **IMPORTANT: Never Delete Databases Without Approval**

This system provides safe database updates without data loss.

## 🔧 **Migration System**

### **Files:**
- `database_migration.py` - Main migration system
- `safe_db_update.py` - Safe database update utilities
- `DATABASE_MIGRATION_README.md` - This documentation

### **Key Principles:**
1. **Always backup before changes**
2. **Use migrations, not database recreation**
3. **Preserve all existing data**
4. **Ask for user confirmation before destructive operations**

## 📋 **Usage**

### **Check Migration Status:**
```bash
# Check all instances
python database_migration.py status

# Check specific instance
python database_migration.py check prod
python database_migration.py check dev
python database_migration.py check testing
```

### **Run Migrations:**
```bash
# Migrate specific instance
python database_migration.py migrate prod

# Migrate all instances
python database_migration.py migrate-all

# Dry run (see what would be changed)
python database_migration.py migrate-all --dry-run
```

### **Create Backups:**
```bash
# Backup specific instance
python database_migration.py backup prod
python safe_db_update.py backup testing
```

### **Check Database Health:**
```bash
# Check database integrity
python safe_db_update.py check prod

# Get database information
python safe_db_update.py info dev
```

## 🛡️ **Safety Features**

### **Automatic Backups:**
- Every migration creates a timestamped backup
- Backups stored in `backups/{instance}/database/`
- Original database preserved until migration succeeds

### **Dry Run Mode:**
- Test migrations without making changes
- See exactly what will be modified
- Safe to run on production data

### **Rollback Capability:**
- If migration fails, original database is preserved
- Can restore from backup if needed
- No data loss during failed migrations

## 📝 **Adding New Migrations**

To add a new migration, edit `database_migration.py`:

```python
self.migrations = [
    {
        'version': 1,
        'description': 'Add password reset fields',
        'sql': [
            "ALTER TABLE user ADD COLUMN reset_token VARCHAR(100)",
            "ALTER TABLE user ADD COLUMN reset_token_expires DATETIME"
        ]
    },
    {
        'version': 2,
        'description': 'Add new feature fields',
        'sql': [
            "ALTER TABLE loan ADD COLUMN new_field VARCHAR(50)",
            "ALTER TABLE payment ADD COLUMN new_field INTEGER DEFAULT 0"
        ]
    }
    # Add more migrations here
]
```

## 🚨 **Emergency Procedures**

### **If Migration Fails:**
1. Check the error message
2. Restore from backup if needed
3. Fix the migration SQL
4. Try again

### **If Database is Corrupted:**
1. Find the most recent backup
2. Restore the backup
3. Re-run migrations from that point

### **If Data is Lost:**
1. Check backup directories
2. Restore from most recent backup
3. Contact administrator immediately

## 📊 **Migration History**

The system tracks all applied migrations in a `schema_migrations` table:

```sql
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 🔍 **Best Practices**

1. **Always test migrations on dev instance first**
2. **Create manual backups before major changes**
3. **Use dry-run mode to preview changes**
4. **Never delete database files manually**
5. **Keep migration scripts in version control**

## 📞 **Support**

If you encounter issues:
1. Check the migration status
2. Review the error messages
3. Restore from backup if needed
4. Contact the development team

---

**Remember: Your data is precious. Always backup before making changes!**
