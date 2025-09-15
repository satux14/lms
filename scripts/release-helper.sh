#!/bin/bash
# Release Helper Script - Interactive release management
# Usage: ./scripts/release-helper.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Get current version
CURRENT_VERSION=$(cat VERSION)
echo -e "${BLUE}🚀 Lending Management System - Release Helper${NC}"
echo "=============================================="
echo -e "${BLUE}Current version: ${CURRENT_VERSION}${NC}"
echo ""

# Function to show menu
show_menu() {
    echo -e "${YELLOW}What would you like to do?${NC}"
    echo "1. Bump version (patch/minor/major)"
    echo "2. Validate release"
    echo "3. Create release"
    echo "4. Rollback to previous version"
    echo "5. Show release history"
    echo "6. Show current status"
    echo "7. Exit"
    echo ""
}

# Function to bump version
bump_version() {
    echo -e "${YELLOW}Select version bump type:${NC}"
    echo "1. Patch (bug fixes) - ${CURRENT_VERSION} → $(echo $CURRENT_VERSION | awk -F. '{$NF = $NF + 1;} 1' | sed 's/ /./g')"
    echo "2. Minor (new features) - ${CURRENT_VERSION} → $(echo $CURRENT_VERSION | awk -F. '{$2 = $2 + 1; $3 = 0;} 1' | sed 's/ /./g')"
    echo "3. Major (breaking changes) - ${CURRENT_VERSION} → $(echo $CURRENT_VERSION | awk -F. '{$1 = $1 + 1; $2 = 0; $3 = 0;} 1' | sed 's/ /./g')"
    echo "4. Back to main menu"
    echo ""
    read -p "Enter your choice (1-4): " choice
    
    case $choice in
        1) ./scripts/bump-version.sh patch ;;
        2) ./scripts/bump-version.sh minor ;;
        3) ./scripts/bump-version.sh major ;;
        4) return ;;
        *) echo -e "${RED}Invalid choice${NC}" && bump_version ;;
    esac
}

# Function to validate release
validate_release() {
    echo -e "${YELLOW}Running release validation...${NC}"
    ./scripts/validate-release.sh
}

# Function to create release
create_release() {
    echo -e "${YELLOW}Creating release...${NC}"
    read -p "Enter release notes (optional): " release_notes
    if [ -n "$release_notes" ]; then
        ./scripts/create-release.sh "$release_notes"
    else
        ./scripts/create-release.sh
    fi
}

# Function to rollback
rollback_release() {
    echo -e "${YELLOW}Available versions for rollback:${NC}"
    git tag -l | sort -V | tail -10
    echo ""
    read -p "Enter version to rollback to (e.g., v2.0.0): " rollback_version
    if [ -n "$rollback_version" ]; then
        ./scripts/rollback-release.sh "$rollback_version"
    else
        echo -e "${RED}No version specified${NC}"
    fi
}

# Function to show release history
show_history() {
    echo -e "${YELLOW}Release History:${NC}"
    echo "================"
    git tag -l | sort -V -r | head -10
    echo ""
    echo -e "${BLUE}Recent commits:${NC}"
    git log --oneline -5
}

# Function to show current status
show_status() {
    echo -e "${YELLOW}Current Status:${NC}"
    echo "==============="
    echo -e "Version: ${CURRENT_VERSION}"
    echo -e "Branch: $(git branch --show-current)"
    echo -e "Last commit: $(git log -1 --pretty=format:'%h - %s (%cr)')"
    echo -e "Uncommitted changes: $(if git diff-index --quiet HEAD --; then echo 'None'; else echo 'Yes'; fi)"
    echo ""
    echo -e "${BLUE}Recent tags:${NC}"
    git tag -l | sort -V -r | head -5
}

# Main menu loop
while true; do
    show_menu
    read -p "Enter your choice (1-7): " choice
    echo ""
    
    case $choice in
        1) bump_version ;;
        2) validate_release ;;
        3) create_release ;;
        4) rollback_release ;;
        5) show_history ;;
        6) show_status ;;
        7) echo -e "${GREEN}Goodbye!${NC}" && exit 0 ;;
        *) echo -e "${RED}Invalid choice. Please try again.${NC}" ;;
    esac
    
    echo ""
    echo "Press Enter to continue..."
    read
    clear
done
