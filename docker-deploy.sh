#!/bin/bash
# Docker Deployment Script for Lending Management System
# =====================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="lending-app"
CONTAINER_NAME="lending-management-system"
EXTERNAL_PORT="8080"
INTERNAL_PORT="8080"

echo -e "${BLUE}🏦 Lending Management System - Docker Deployment${NC}"
echo "=================================================="

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if Docker is installed and running
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    print_status "Docker is installed and running"
}

# Build the Docker image
build_image() {
    echo -e "\n${BLUE}Building Docker image...${NC}"
    docker build -t $IMAGE_NAME .
    print_status "Docker image built successfully"
}

# Stop and remove existing container
cleanup_container() {
    if docker ps -a --format 'table {{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
        echo -e "\n${YELLOW}Stopping existing container...${NC}"
        docker stop $CONTAINER_NAME || true
        docker rm $CONTAINER_NAME || true
        print_status "Existing container removed"
    fi
}

# Create necessary volumes
create_volumes() {
    echo -e "\n${BLUE}Creating Docker volumes...${NC}"
    docker volume create lending_data 2>/dev/null || true
    docker volume create lending_backups 2>/dev/null || true
    docker volume create lending_uploads 2>/dev/null || true
    print_status "Docker volumes created/verified"
}

# Run the container
run_container() {
    echo -e "\n${BLUE}Starting container...${NC}"
    docker run -d \
        --name $CONTAINER_NAME \
        -p $EXTERNAL_PORT:$INTERNAL_PORT \
        -v lending_data:/app/instances \
        -v lending_backups:/app/backups \
        -v lending_uploads:/app/uploads \
        --restart unless-stopped \
        $IMAGE_NAME
    
    print_status "Container started successfully"
}

# Wait for application to be ready
wait_for_ready() {
    echo -e "\n${BLUE}Waiting for application to be ready...${NC}"
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:$EXTERNAL_PORT/ > /dev/null 2>&1; then
            print_status "Application is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    print_error "Application failed to start within expected time"
    echo -e "\n${YELLOW}Container logs:${NC}"
    docker logs $CONTAINER_NAME
    exit 1
}

# Show application information
show_info() {
    echo -e "\n${GREEN}🎉 Deployment Complete!${NC}"
    echo "========================"
    echo -e "${BLUE}Application URLs:${NC}"
    echo "  • Instance Selector: http://localhost:$EXTERNAL_PORT/"
    echo "  • Production:        http://localhost:$EXTERNAL_PORT/prod/"
    echo "  • Development:       http://localhost:$EXTERNAL_PORT/dev/"
    echo "  • Testing:           http://localhost:$EXTERNAL_PORT/testing/"
    echo ""
    echo -e "${BLUE}Management Commands:${NC}"
    echo "  • View logs:         docker logs $CONTAINER_NAME"
    echo "  • Stop container:    docker stop $CONTAINER_NAME"
    echo "  • Start container:   docker start $CONTAINER_NAME"
    echo "  • Remove container:  docker rm $CONTAINER_NAME"
    echo "  • Access shell:      docker exec -it $CONTAINER_NAME /bin/bash"
    echo ""
    echo -e "${BLUE}Data Persistence:${NC}"
    echo "  • Database files:    lending_data volume"
    echo "  • Backup files:      lending_backups volume"
    echo "  • Upload files:      lending_uploads volume"
}

# Main deployment function
deploy() {
    check_docker
    build_image
    cleanup_container
    create_volumes
    run_container
    wait_for_ready
    show_info
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "build")
        check_docker
        build_image
        ;;
    "start")
        check_docker
        cleanup_container
        create_volumes
        run_container
        wait_for_ready
        show_info
        ;;
    "stop")
        echo -e "${YELLOW}Stopping container...${NC}"
        docker stop $CONTAINER_NAME || true
        print_status "Container stopped"
        ;;
    "restart")
        echo -e "${YELLOW}Restarting container...${NC}"
        docker restart $CONTAINER_NAME || true
        wait_for_ready
        show_info
        ;;
    "logs")
        docker logs -f $CONTAINER_NAME
        ;;
    "shell")
        docker exec -it $CONTAINER_NAME /bin/bash
        ;;
    "clean")
        echo -e "${YELLOW}Cleaning up...${NC}"
        docker stop $CONTAINER_NAME 2>/dev/null || true
        docker rm $CONTAINER_NAME 2>/dev/null || true
        docker rmi $IMAGE_NAME 2>/dev/null || true
        print_status "Cleanup complete"
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  deploy   - Full deployment (default)"
        echo "  build    - Build Docker image only"
        echo "  start    - Start container (assumes image exists)"
        echo "  stop     - Stop container"
        echo "  restart  - Restart container"
        echo "  logs     - Show container logs"
        echo "  shell    - Access container shell"
        echo "  clean    - Remove container and image"
        echo "  help     - Show this help"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for available commands"
        exit 1
        ;;
esac
