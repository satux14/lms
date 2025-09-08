# 🏷️ Version Management Guide

This guide explains how to manage versions and create milestones for the Lending Management System.

## 🚀 Quick Start

### Check Current Version
```bash
python3 version_manager.py info
```

### Create New Versions
```bash
# Patch version (bug fixes): 1.0.0 -> 1.0.1
python3 version_manager.py patch "Fixed interest calculation bug"

# Minor version (new features): 1.0.0 -> 1.1.0
python3 version_manager.py minor "Added advanced filtering features"

# Major version (breaking changes): 1.0.0 -> 2.0.0
python3 version_manager.py major "Complete UI redesign"

# Custom version
python3 version_manager.py custom v1.5.0 "Special milestone release"
```

## 📋 Version Types

### Patch Version (x.x.X)
- **When to use**: Bug fixes, small improvements
- **Examples**: 
  - Fixed payment calculation error
  - Resolved login issue
  - Updated documentation

### Minor Version (x.X.x)
- **When to use**: New features, enhancements
- **Examples**:
  - Added new payment methods
  - Enhanced filtering capabilities
  - New reporting features

### Major Version (X.x.x)
- **When to use**: Breaking changes, major redesigns
- **Examples**:
  - Complete UI overhaul
  - Database schema changes
  - API restructuring

## 🔄 Workflow

### 1. Make Changes
```bash
# Make your code changes
# Test thoroughly
# Update documentation if needed
```

### 2. Commit Changes
```bash
git add .
git commit -m "Descriptive commit message"
```

### 3. Create Version Tag
```bash
# Choose appropriate version type
python3 version_manager.py patch "Description of changes"
```

### 4. Push to Remote (if using remote repository)
```bash
git push origin master
git push origin --tags
```

## 📊 Current Versions

| Version | Date | Description |
|---------|------|-------------|
| v1.0.0 | 2025-09-08 | Initial release with complete lending management system |

## 🎯 Milestone Examples

### v1.1.0 - Enhanced Features
- Advanced loan filtering
- Excel export improvements
- Better user interface

### v1.2.0 - Payment Enhancements
- New payment methods
- Payment scheduling
- Automated reminders

### v2.0.0 - Major Redesign
- Complete UI overhaul
- Mobile responsive design
- API integration

## 🛠️ Manual Git Commands

If you prefer manual Git commands:

### Create Tag
```bash
git tag -a v1.1.0 -m "Version 1.1.0 - Enhanced Features"
```

### List Tags
```bash
git tag -l
```

### Show Tag Details
```bash
git show v1.1.0
```

### Delete Tag (if needed)
```bash
git tag -d v1.1.0
```

## 📝 Best Practices

1. **Semantic Versioning**: Follow MAJOR.MINOR.PATCH format
2. **Descriptive Messages**: Always include meaningful version messages
3. **Test Before Tagging**: Ensure all features work before creating tags
4. **Document Changes**: Update README.md and CHANGELOG.md
5. **Consistent Naming**: Use consistent tag naming conventions

## 🔍 Troubleshooting

### Tag Already Exists
```bash
# Delete existing tag
git tag -d v1.1.0
# Create new tag
python3 version_manager.py custom v1.1.0 "Updated message"
```

### View Tag History
```bash
git log --oneline --decorate --graph
```

### Compare Versions
```bash
git diff v1.0.0..v1.1.0
```

## 📚 Additional Resources

- [Semantic Versioning](https://semver.org/)
- [Git Tagging Best Practices](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
- [Version Management Strategies](https://nvie.com/posts/a-successful-git-branching-model/)
