#!/bin/bash
# Release Validation Script for Lending Management System
# Usage: ./scripts/validate-release.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Running release validation...${NC}"
echo "=================================="

VALIDATION_PASSED=true

# Check 1: Git status
echo -e "${YELLOW}1. Checking git status...${NC}"
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}❌ Uncommitted changes detected${NC}"
    git status --short
    VALIDATION_PASSED=false
else
    echo -e "${GREEN}✓ No uncommitted changes${NC}"
fi

# Check 2: Current branch
echo -e "${YELLOW}2. Checking current branch...${NC}"
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${RED}❌ Not on main branch (current: $CURRENT_BRANCH)${NC}"
    VALIDATION_PASSED=false
else
    echo -e "${GREEN}✓ On main branch${NC}"
fi

# Check 3: Version file exists
echo -e "${YELLOW}3. Checking VERSION file...${NC}"
if [ ! -f "VERSION" ]; then
    echo -e "${RED}❌ VERSION file not found${NC}"
    VALIDATION_PASSED=false
else
    VERSION=$(cat VERSION)
    echo -e "${GREEN}✓ VERSION file found: $VERSION${NC}"
fi

# Check 4: Version format
echo -e "${YELLOW}4. Validating version format...${NC}"
if [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${GREEN}✓ Version format is valid${NC}"
else
    echo -e "${RED}❌ Invalid version format: $VERSION${NC}"
    echo "Expected format: X.Y.Z (e.g., 2.1.0)"
    VALIDATION_PASSED=false
fi

# Check 5: Tag doesn't exist
echo -e "${YELLOW}5. Checking if tag already exists...${NC}"
if git tag -l | grep -q "^v${VERSION}$"; then
    echo -e "${RED}❌ Tag v${VERSION} already exists${NC}"
    VALIDATION_PASSED=false
else
    echo -e "${GREEN}✓ Tag v${VERSION} does not exist${NC}"
fi

# Check 6: Python syntax
echo -e "${YELLOW}6. Checking Python syntax...${NC}"
if [ -f "app_multi.py" ]; then
    if python3 -m py_compile app_multi.py; then
        echo -e "${GREEN}✓ app_multi.py syntax is valid${NC}"
    else
        echo -e "${RED}❌ app_multi.py has syntax errors${NC}"
        VALIDATION_PASSED=false
    fi
fi

if [ -f "run_multi.py" ]; then
    if python3 -m py_compile run_multi.py; then
        echo -e "${GREEN}✓ run_multi.py syntax is valid${NC}"
    else
        echo -e "${RED}❌ run_multi.py has syntax errors${NC}"
        VALIDATION_PASSED=false
    fi
fi

# Check 7: Database files exist
echo -e "${YELLOW}7. Checking database files...${NC}"
DB_FILES_FOUND=0
for db_path in "instances/*/database/*.db" "instance/*/database/*.db"; do
    if ls $db_path 1> /dev/null 2>&1; then
        DB_FILES_FOUND=1
        break
    fi
done

if [ $DB_FILES_FOUND -eq 1 ]; then
    echo -e "${GREEN}✓ Database files found${NC}"
else
    echo -e "${YELLOW}⚠ No database files found (this might be normal for new installations)${NC}"
fi

# Check 8: Required files exist
echo -e "${YELLOW}8. Checking required files...${NC}"
REQUIRED_FILES=("app_multi.py" "run_multi.py" "requirements.txt")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ $file exists${NC}"
    else
        echo -e "${RED}❌ Required file missing: $file${NC}"
        VALIDATION_PASSED=false
    fi
done

# Check 9: Docker files (optional)
echo -e "${YELLOW}9. Checking Docker files...${NC}"
if [ -f "Dockerfile" ] && [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✓ Docker files present${NC}"
else
    echo -e "${YELLOW}⚠ Docker files not found (optional)${NC}"
fi

# Check 10: Documentation
echo -e "${YELLOW}10. Checking documentation...${NC}"
if [ -f "README.md" ]; then
    echo -e "${GREEN}✓ README.md exists${NC}"
else
    echo -e "${YELLOW}⚠ README.md not found${NC}"
fi

# Summary
echo ""
echo "=================================="
if [ "$VALIDATION_PASSED" = true ]; then
    echo -e "${GREEN}✅ All validations passed! Ready for release.${NC}"
    exit 0
else
    echo -e "${RED}❌ Validation failed. Please fix the issues above.${NC}"
    exit 1
fi
