#!/bin/bash
# Release Creation Script for Lending Management System
# Usage: ./scripts/create-release.sh [release-notes]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get current version
VERSION=$(cat VERSION)
echo -e "${BLUE}Creating release v${VERSION}${NC}"

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${RED}Error: Must be on main branch to create release${NC}"
    echo "Current branch: $CURRENT_BRANCH"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}Error: Uncommitted changes detected${NC}"
    echo "Please commit or stash your changes before creating a release"
    git status --short
    exit 1
fi

# Check if tag already exists
if git tag -l | grep -q "^v${VERSION}$"; then
    echo -e "${RED}Error: Tag v${VERSION} already exists${NC}"
    exit 1
fi

# Run validation
echo -e "${YELLOW}Running pre-release validation...${NC}"
if [ -f "scripts/validate-release.sh" ]; then
    ./scripts/validate-release.sh
    if [ $? -ne 0 ]; then
        echo -e "${RED}Validation failed. Aborting release.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Warning: validate-release.sh not found. Skipping validation.${NC}"
fi

# Generate release notes
RELEASE_NOTES=""
if [ -n "$1" ]; then
    RELEASE_NOTES="$1"
else
    # Auto-generate release notes from recent commits
    LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
    if [ -n "$LAST_TAG" ]; then
        RELEASE_NOTES=$(git log --pretty=format:"- %s" ${LAST_TAG}..HEAD)
    else
        RELEASE_NOTES=$(git log --pretty=format:"- %s" -10)
    fi
fi

# Create tag
TAG_MESSAGE="Release v${VERSION}

${RELEASE_NOTES}

Generated on $(date)"
echo -e "${YELLOW}Creating tag v${VERSION}...${NC}"
git tag -a "v${VERSION}" -m "$TAG_MESSAGE"

# Push tag to remote
echo -e "${YELLOW}Pushing tag to remote...${NC}"
git push origin "v${VERSION}"

# Create GitHub release (if gh CLI is available)
if command -v gh &> /dev/null; then
    echo -e "${YELLOW}Creating GitHub release...${NC}"
    gh release create "v${VERSION}" \
        --title "Release v${VERSION}" \
        --notes "$RELEASE_NOTES" \
        --latest
    echo -e "${GREEN}✓ GitHub release created${NC}"
else
    echo -e "${YELLOW}GitHub CLI not found. Skipping GitHub release creation.${NC}"
    echo "You can create a release manually at: https://github.com/satux14/lms/releases"
fi

echo -e "${GREEN}✓ Release v${VERSION} created successfully!${NC}"
echo -e "${BLUE}Release details:${NC}"
echo "  Tag: v${VERSION}"
echo "  Commit: $(git rev-parse HEAD)"
echo "  Branch: $CURRENT_BRANCH"
echo "  Remote: origin"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Verify release: git tag -l | grep v${VERSION}"
echo "  2. Check GitHub: https://github.com/satux14/lms/releases"
echo "  3. Deploy to production (if applicable)"
echo "  4. Update changelog: CHANGELOG.md"
