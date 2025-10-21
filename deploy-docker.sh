#!/bin/bash

# AMT Trading Bot - Docker Deployment Script
# Quick deployment automation

set -e

echo "=========================================="
echo "AMT Trading Bot - Docker Deployment"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed${NC}"
    echo "Please install Docker from https://www.docker.com/get-started"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}ERROR: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker found: $(docker --version)"
echo -e "${GREEN}✓${NC} Docker Compose found: $(docker-compose --version)"
echo ""

# Function to display menu
show_menu() {
    echo "What would you like to do?"
    echo ""
    echo "1) Build images"
    echo "2) Start application"
    echo "3) Stop application"
    echo "4) View logs"
    echo "5) Rebuild and restart"
    echo "6) Clean up (remove containers and volumes)"
    echo "7) Check status"
    echo "8) Exit"
    echo ""
}

# Build images
build_images() {
    echo -e "${YELLOW}Building Docker images...${NC}"
    docker-compose build
    echo -e "${GREEN}✓ Images built successfully${NC}"
}

# Start application
start_app() {
    echo -e "${YELLOW}Starting AMT Trading Bot...${NC}"
    docker-compose up -d
    echo ""
    echo -e "${GREEN}✓ Application started${NC}"
    echo ""
    echo "Access the application at:"
    echo "  Frontend: http://localhost"
    echo "  Backend API: http://localhost:8001"
    echo "  API Docs: http://localhost:8001/docs"
    echo ""
    echo "View logs with: docker-compose logs -f"
}

# Stop application
stop_app() {
    echo -e "${YELLOW}Stopping AMT Trading Bot...${NC}"
    docker-compose down
    echo -e "${GREEN}✓ Application stopped${NC}"
}

# View logs
view_logs() {
    echo -e "${YELLOW}Showing logs (Ctrl+C to exit)...${NC}"
    docker-compose logs -f
}

# Rebuild and restart
rebuild_restart() {
    echo -e "${YELLOW}Rebuilding and restarting...${NC}"
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    echo -e "${GREEN}✓ Application rebuilt and restarted${NC}"
}

# Clean up
cleanup() {
    echo -e "${RED}WARNING: This will remove all containers and data${NC}"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        echo -e "${YELLOW}Cleaning up...${NC}"
        docker-compose down -v
        docker system prune -f
        echo -e "${GREEN}✓ Cleanup complete${NC}"
    else
        echo "Cleanup cancelled"
    fi
}

# Check status
check_status() {
    echo -e "${YELLOW}Container Status:${NC}"
    docker-compose ps
    echo ""
    echo -e "${YELLOW}Resource Usage:${NC}"
    docker stats --no-stream
}

# Main loop
while true; do
    show_menu
    read -p "Enter your choice [1-8]: " choice
    echo ""
    
    case $choice in
        1)
            build_images
            ;;
        2)
            start_app
            ;;
        3)
            stop_app
            ;;
        4)
            view_logs
            ;;
        5)
            rebuild_restart
            ;;
        6)
            cleanup
            ;;
        7)
            check_status
            ;;
        8)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    echo ""
done
