# Multi-Instance Lending Management System

## Overview

The Lending Management System now supports multiple instances for different environments:
- **Production (prod)**: Live environment with real customer data
- **Development (dev)**: Development environment for testing new features
- **Testing (testing)**: Quality assurance environment for testing

Each instance has its own database, uploads, and backups, ensuring complete data isolation.

## Quick Start

### 1. Start the Multi-Instance Application

```bash
python3 run_multi.py
```

### 2. Access the Application

- **Instance Selector**: http://localhost:8080/
- **Production**: http://localhost:8080/prod/
- **Development**: http://localhost:8080/dev/
- **Testing**: http://localhost:8080/testing/

### 3. Default Login Credentials

All instances start with the same default admin user:
- **Username**: `admin`
- **Password**: `admin123`

## Instance Management

### Instance Management Commands

```bash
# List all instances and their status
python3 manage_instances.py list

# Show detailed information about an instance
python3 manage_instances.py info prod

# Create a new instance (if needed)
python3 manage_instances.py create dev

# Reset an instance (delete all data)
python3 manage_instances.py reset testing

# Create backup of an instance
python3 manage_instances.py backup prod
```

### Instance Status

Each instance shows:
- Database existence and size
- Number of upload files
- Number of backup files
- Last modification date

## File Structure

```
lending_app/
├── instances/                    # Instance data directory
│   ├── prod/                    # Production instance
│   │   ├── database/           # Production database
│   │   │   └── lending_app_prod.db
│   │   ├── uploads/            # Production file uploads
│   │   └── backups/            # Production backups
│   ├── dev/                    # Development instance
│   │   ├── database/
│   │   │   └── lending_app_dev.db
│   │   ├── uploads/
│   │   └── backups/
│   └── testing/                # Testing instance
│       ├── database/
│       │   └── lending_app_testing.db
│       ├── uploads/
│       └── backups/
├── app_multi.py                # Multi-instance Flask application
├── run_multi.py                # Run script for multi-instance app
├── manage_instances.py         # Instance management utilities
├── create_instances.py         # Instance creation script
├── instance_manager.py         # Instance management module
└── templates/
    └── instance_selector.html  # Instance selection page
```

## URL Structure

### Instance URLs

- **Root**: `/` - Instance selector page
- **Production**: `/prod/` - Production instance
- **Development**: `/dev/` - Development instance
- **Testing**: `/testing/` - Testing instance

### Example URLs

```
http://localhost:8080/                    # Instance selector
http://localhost:8080/prod/login          # Production login
http://localhost:8080/dev/admin           # Development admin dashboard
http://localhost:8080/testing/customer    # Testing customer dashboard
```

## Instance Features

### Data Isolation

Each instance has completely separate:
- **Database**: SQLite database with instance-specific name
- **File Uploads**: Separate upload directories
- **Backups**: Instance-specific backup storage
- **Configuration**: Instance-specific settings

### Instance Identification

- **Visual Badge**: Each page shows the current instance (PROD/DEV/TESTING)
- **Color Coding**: 
  - Production: Red badge
  - Development: Yellow badge
  - Testing: Blue badge

### Shared Codebase

All instances share the same:
- Application code
- Templates
- Static files
- Business logic

## Development Workflow

### 1. Development Process

1. **Work in Development**: Use `/dev/` for feature development
2. **Test in Testing**: Use `/testing/` for quality assurance
3. **Deploy to Production**: Use `/prod/` for live environment

### 2. Data Management

```bash
# Copy production data to development for testing
cp instances/prod/database/lending_app_prod.db instances/dev/database/lending_app_dev.db

# Reset development environment
python3 manage_instances.py reset dev

# Create backup before major changes
python3 manage_instances.py backup prod
```

### 3. Testing Workflow

1. Develop features in `/dev/`
2. Test thoroughly in `/testing/`
3. Deploy to `/prod/` when ready

## Backup and Recovery

### Instance-Specific Backups

Each instance has its own backup system:

```bash
# Backup production instance
python3 manage_instances.py backup prod

# Backup development instance
python3 manage_instances.py backup dev
```

### Backup Locations

- Production backups: `instances/prod/backups/`
- Development backups: `instances/dev/backups/`
- Testing backups: `instances/testing/backups/`

## Configuration

### Instance Configuration

Each instance can have different configurations:

```python
# In app_multi.py
def configure_app_for_instance(instance):
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri(instance)
    app.config['UPLOAD_FOLDER'] = get_uploads_folder(instance)
    app.config['INSTANCE_NAME'] = instance
```

### Environment Variables

You can set different configurations per instance:

```bash
# Production
export FLASK_ENV=production
python3 run_multi.py

# Development
export FLASK_ENV=development
python3 run_multi.py
```

## Security Considerations

### Instance Isolation

- **Database**: Complete separation between instances
- **File System**: Separate directories for uploads and backups
- **Sessions**: Instance-specific session handling

### Access Control

- Same authentication system across all instances
- Instance-specific admin users (can be different per instance)
- Instance identification in UI to prevent confusion

## Troubleshooting

### Common Issues

#### Instance Not Loading
```bash
# Check instance status
python3 manage_instances.py list

# Recreate instance if needed
python3 manage_instances.py reset dev
```

#### Database Issues
```bash
# Check database file
ls -la instances/prod/database/

# Recreate database
python3 manage_instances.py reset prod
```

#### Permission Issues
```bash
# Fix directory permissions
chmod -R 755 instances/
```

### Debug Mode

Run with debug information:

```bash
# Enable Flask debug mode
export FLASK_DEBUG=1
python3 run_multi.py
```

## Migration from Single Instance

### From Original App

If you have an existing single-instance setup:

1. **Copy existing database**:
   ```bash
   cp lending_app.db instances/prod/database/lending_app_prod.db
   ```

2. **Start multi-instance app**:
   ```bash
   python3 run_multi.py
   ```

3. **Access production instance**:
   ```
   http://localhost:8080/prod/
   ```

### Data Migration

```bash
# Copy production data to other instances
cp instances/prod/database/lending_app_prod.db instances/dev/database/lending_app_dev.db
cp instances/prod/database/lending_app_prod.db instances/testing/database/lending_app_testing.db
```

## Best Practices

### Development

1. **Always develop in `/dev/`** first
2. **Test in `/testing/`** before production
3. **Use version control** for code changes
4. **Backup before major changes**

### Production

1. **Regular backups** of production instance
2. **Monitor instance status** regularly
3. **Test changes** in dev/testing first
4. **Document changes** and deployments

### Testing

1. **Use realistic test data** in testing instance
2. **Test all features** before production deployment
3. **Verify data integrity** after changes
4. **Document test results**

## Support

### Getting Help

1. Check instance status: `python3 manage_instances.py list`
2. Review logs for error messages
3. Verify file permissions and directory structure
4. Test with a fresh instance: `python3 manage_instances.py reset dev`

### Emergency Recovery

```bash
# Stop all instances
pkill -f "python3 run_multi.py"

# Restore from backup
cp instances/prod/backups/latest_backup.zip /tmp/
cd /tmp && unzip latest_backup.zip

# Restart application
python3 run_multi.py
```

---

**Version**: 1.0.1  
**Last Updated**: 2025-09-08  
**Compatible with**: Lending Management System v1.0.1+
