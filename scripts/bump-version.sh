#!/bin/bash
# Version Bumping Script for Lending Management System
# Usage: ./scripts/bump-version.sh [patch|minor|major]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get current version
CURRENT_VERSION=$(cat VERSION)
echo -e "${BLUE}Current version: ${CURRENT_VERSION}${NC}"

# Parse version components
IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR=${VERSION_PARTS[0]}
MINOR=${VERSION_PARTS[1]}
PATCH=${VERSION_PARTS[2]}

# Determine bump type
BUMP_TYPE=${1:-patch}

case $BUMP_TYPE in
    patch)
        NEW_PATCH=$((PATCH + 1))
        NEW_VERSION="${MAJOR}.${MINOR}.${NEW_PATCH}"
        echo -e "${YELLOW}Bumping PATCH version: ${CURRENT_VERSION} → ${NEW_VERSION}${NC}"
        ;;
    minor)
        NEW_MINOR=$((MINOR + 1))
        NEW_VERSION="${MAJOR}.${NEW_MINOR}.0"
        echo -e "${YELLOW}Bumping MINOR version: ${CURRENT_VERSION} → ${NEW_VERSION}${NC}"
        ;;
    major)
        NEW_MAJOR=$((MAJOR + 1))
        NEW_VERSION="${NEW_MAJOR}.0.0"
        echo -e "${YELLOW}Bumping MAJOR version: ${CURRENT_VERSION} → ${NEW_VERSION}${NC}"
        ;;
    *)
        echo -e "${RED}Error: Invalid bump type. Use 'patch', 'minor', or 'major'${NC}"
        echo "Usage: $0 [patch|minor|major]"
        exit 1
        ;;
esac

# Update VERSION file
echo "$NEW_VERSION" > VERSION
echo -e "${GREEN}✓ Updated VERSION file${NC}"

# Update version in app_multi.py if it exists
if [ -f "app_multi.py" ]; then
    # Look for version string in app_multi.py and update it
    if grep -q "__version__" app_multi.py; then
        sed -i.bak "s/__version__ = .*/__version__ = '${NEW_VERSION}'/" app_multi.py
        rm -f app_multi.py.bak
        echo -e "${GREEN}✓ Updated version in app_multi.py${NC}"
    else
        # Add version if it doesn't exist
        echo "__version__ = '${NEW_VERSION}'" >> app_multi.py
        echo -e "${GREEN}✓ Added version to app_multi.py${NC}"
    fi
fi

# Update version in run_multi.py if it exists
if [ -f "run_multi.py" ]; then
    if grep -q "__version__" run_multi.py; then
        sed -i.bak "s/__version__ = .*/__version__ = '${NEW_VERSION}'/" run_multi.py
        rm -f run_multi.py.bak
        echo -e "${GREEN}✓ Updated version in run_multi.py${NC}"
    fi
fi

# Create commit
git add VERSION
if [ -f "app_multi.py" ]; then
    git add app_multi.py
fi
if [ -f "run_multi.py" ]; then
    git add run_multi.py
fi

git commit -m "Bump version to ${NEW_VERSION}

- Updated VERSION file
- Updated version references in source files
- Ready for release v${NEW_VERSION}"

echo -e "${GREEN}✓ Created commit for version bump${NC}"
echo -e "${BLUE}New version: ${NEW_VERSION}${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Review changes: git log --oneline -1"
echo "  2. Push changes: git push origin main"
echo "  3. Create release: ./scripts/create-release.sh"
