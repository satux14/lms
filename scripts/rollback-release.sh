#!/bin/bash
# Release Rollback Script for Lending Management System
# Usage: ./scripts/rollback-release.sh <version-to-rollback-to>

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if version is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: Version required${NC}"
    echo "Usage: $0 <version-to-rollback-to>"
    echo "Example: $0 v2.0.0"
    echo ""
    echo "Available versions:"
    git tag -l | sort -V
    exit 1
fi

ROLLBACK_VERSION=$1
CURRENT_VERSION=$(cat VERSION)

echo -e "${BLUE}🔄 Rolling back from v${CURRENT_VERSION} to ${ROLLBACK_VERSION}${NC}"
echo "=============================================="

# Check if rollback version exists
if ! git tag -l | grep -q "^${ROLLBACK_VERSION}$"; then
    echo -e "${RED}❌ Tag ${ROLLBACK_VERSION} not found${NC}"
    echo "Available versions:"
    git tag -l | sort -V
    exit 1
fi

# Confirm rollback
echo -e "${YELLOW}⚠️  WARNING: This will rollback to ${ROLLBACK_VERSION}${NC}"
echo -e "${YELLOW}Current version: v${CURRENT_VERSION}${NC}"
echo -e "${YELLOW}Rollback version: ${ROLLBACK_VERSION}${NC}"
echo ""
read -p "Are you sure you want to proceed? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Rollback cancelled${NC}"
    exit 0
fi

# Create backup of current state
echo -e "${YELLOW}Creating backup of current state...${NC}"
BACKUP_BRANCH="backup-before-rollback-$(date +%Y%m%d-%H%M%S)"
git checkout -b "$BACKUP_BRANCH"
git checkout main
echo -e "${GREEN}✓ Backup created: $BACKUP_BRANCH${NC}"

# Rollback to specified version
echo -e "${YELLOW}Rolling back to ${ROLLBACK_VERSION}...${NC}"
git reset --hard "$ROLLBACK_VERSION"

# Update VERSION file
echo "$ROLLBACK_VERSION" | sed 's/v//' > VERSION
echo -e "${GREEN}✓ Updated VERSION file${NC}"

# Check for database migration needs
echo -e "${YELLOW}Checking database migration needs...${NC}"
if [ -f "migrate_add_loan_status.py" ]; then
    echo -e "${YELLOW}⚠ Database migration script found. You may need to run migrations.${NC}"
    echo "Check if database schema changes are needed for this version."
fi

# Create rollback commit
git add VERSION
git commit -m "Rollback to ${ROLLBACK_VERSION}

- Rolled back from v${CURRENT_VERSION} to ${ROLLBACK_VERSION}
- Created backup branch: $BACKUP_BRANCH
- Updated VERSION file

This rollback was performed on $(date)"

echo -e "${GREEN}✓ Rollback completed${NC}"

# Summary
echo ""
echo "=============================================="
echo -e "${GREEN}✅ Rollback Summary:${NC}"
echo "  From: v${CURRENT_VERSION}"
echo "  To: ${ROLLBACK_VERSION}"
echo "  Backup: $BACKUP_BRANCH"
echo "  Date: $(date)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Test the application thoroughly"
echo "  2. Check database compatibility"
echo "  3. Deploy to production (if applicable)"
echo "  4. Monitor for issues"
echo "  5. If issues found, restore from backup:"
echo "     git checkout $BACKUP_BRANCH"
echo ""
echo -e "${BLUE}To restore from backup:${NC}"
echo "  git checkout $BACKUP_BRANCH"
echo "  git checkout main"
echo "  git reset --hard $BACKUP_BRANCH"
