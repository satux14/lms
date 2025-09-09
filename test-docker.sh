#!/bin/bash
# Docker Test Script for Lending Management System
# ===============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Testing Docker Setup${NC}"
echo "======================="

# Test 1: Check if Docker is available
echo -e "\n${BLUE}Test 1: Docker Availability${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker is installed"
    docker --version
else
    echo -e "${RED}✗${NC} Docker is not installed"
    exit 1
fi

# Test 2: Check if Docker daemon is running
echo -e "\n${BLUE}Test 2: Docker Daemon${NC}"
if docker info &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker daemon is running"
else
    echo -e "${RED}✗${NC} Docker daemon is not running"
    exit 1
fi

# Test 3: Check if required files exist
echo -e "\n${BLUE}Test 3: Required Files${NC}"
required_files=("Dockerfile" "docker-compose.yml" "requirements.txt" "run_multi.py" "app_multi.py")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file exists"
    else
        echo -e "${RED}✗${NC} $file is missing"
        exit 1
    fi
done

# Test 4: Validate Dockerfile syntax
echo -e "\n${BLUE}Test 4: Dockerfile Syntax${NC}"
if docker build --no-cache -t test-lending-app . > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Dockerfile syntax is valid"
    # Clean up test image
    docker rmi test-lending-app > /dev/null 2>&1 || true
else
    echo -e "${RED}✗${NC} Dockerfile has syntax errors"
    exit 1
fi

# Test 5: Validate docker-compose.yml
echo -e "\n${BLUE}Test 5: Docker Compose Configuration${NC}"
if docker-compose config > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} docker-compose.yml is valid"
else
    echo -e "${RED}✗${NC} docker-compose.yml has errors"
    exit 1
fi

# Test 6: Check Python dependencies
echo -e "\n${BLUE}Test 6: Python Dependencies${NC}"
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}✓${NC} requirements.txt found"
    echo "Dependencies:"
    cat requirements.txt | sed 's/^/  - /'
else
    echo -e "${RED}✗${NC} requirements.txt not found"
    exit 1
fi

# Test 7: Check application entry point
echo -e "\n${BLUE}Test 7: Application Entry Point${NC}"
if [ -f "run_multi.py" ] && [ -x "run_multi.py" ]; then
    echo -e "${GREEN}✓${NC} run_multi.py is executable"
else
    echo -e "${RED}✗${NC} run_multi.py is not executable"
    chmod +x run_multi.py
    echo -e "${YELLOW}⚠${NC} Made run_multi.py executable"
fi

# Test 8: Check health check script
echo -e "\n${BLUE}Test 8: Health Check Script${NC}"
if [ -f "healthcheck.sh" ] && [ -x "healthcheck.sh" ]; then
    echo -e "${GREEN}✓${NC} healthcheck.sh is executable"
else
    echo -e "${RED}✗${NC} healthcheck.sh is not executable"
    chmod +x healthcheck.sh
    echo -e "${YELLOW}⚠${NC} Made healthcheck.sh executable"
fi

# Test 9: Check deployment script
echo -e "\n${BLUE}Test 9: Deployment Script${NC}"
if [ -f "docker-deploy.sh" ] && [ -x "docker-deploy.sh" ]; then
    echo -e "${GREEN}✓${NC} docker-deploy.sh is executable"
else
    echo -e "${RED}✗${NC} docker-deploy.sh is not executable"
    chmod +x docker-deploy.sh
    echo -e "${YELLOW}⚠${NC} Made docker-deploy.sh executable"
fi

# Summary
echo -e "\n${GREEN}🎉 All Tests Passed!${NC}"
echo "=================="
echo -e "${BLUE}Your Docker setup is ready for deployment.${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Run: ./docker-deploy.sh deploy"
echo "2. Access: http://localhost:8080/"
echo "3. Or use: docker-compose up -d"
echo ""
echo -e "${BLUE}For more information, see DOCKER_README.md${NC}"
