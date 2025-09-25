#!/bin/bash

# MedAssist AI Pro - Docker Build Script
# This script builds and optionally runs the Docker container

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to setup environment
setup_environment() {
    print_status "Setting up environment..."
    
    if [ ! -f .env ]; then
        if [ -f env.example ]; then
            print_status "Creating .env file from env.example..."
            cp env.example .env
            print_warning "Please edit .env file and add your GEMINI_API_KEY"
        else
            print_error "No env.example file found. Please create .env file manually."
            exit 1
        fi
    else
        print_success ".env file already exists"
    fi
}

# Function to build Docker image
build_image() {
    print_status "Building Docker image..."
    
    # Build the image
    docker build -t medassist-ai-pro:latest .
    
    if [ $? -eq 0 ]; then
        print_success "Docker image built successfully"
    else
        print_error "Docker image build failed"
        exit 1
    fi
}

# Function to run with docker-compose
run_with_compose() {
    print_status "Starting application with Docker Compose..."
    
    # Create necessary directories
    mkdir -p uploads logs
    
    # Start the application
    docker-compose up -d --build
    
    if [ $? -eq 0 ]; then
        print_success "Application started successfully"
        print_status "Application is available at: http://localhost:8502"
        print_status "To view logs: docker-compose logs -f"
        print_status "To stop: docker-compose down"
    else
        print_error "Failed to start application"
        exit 1
    fi
}

# Function to run with docker run
run_with_docker() {
    print_status "Starting application with Docker..."
    
    # Create necessary directories
    mkdir -p uploads logs
    
    # Stop existing container if running
    docker stop medassist-app 2>/dev/null || true
    docker rm medassist-app 2>/dev/null || true
    
    # Run the container
    docker run -d \
        --name medassist-app \
        --env-file .env \
        -p 8502:8502 \
        -v "$(pwd)/uploads:/app/uploads" \
        -v "$(pwd)/logs:/app/logs" \
        medassist-ai-pro:latest
    
    if [ $? -eq 0 ]; then
        print_success "Application started successfully"
        print_status "Application is available at: http://localhost:8502"
        print_status "To view logs: docker logs -f medassist-app"
        print_status "To stop: docker stop medassist-app"
    else
        print_error "Failed to start application"
        exit 1
    fi
}

# Function to show help
show_help() {
    echo "MedAssist AI Pro - Docker Build Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  build     Build Docker image only"
    echo "  run       Build and run with docker-compose"
    echo "  docker    Build and run with docker run"
    echo "  stop      Stop running containers"
    echo "  clean     Clean up Docker resources"
    echo "  logs      Show application logs"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build          # Build image only"
    echo "  $0 run            # Build and run with compose"
    echo "  $0 docker         # Build and run with docker run"
    echo "  $0 stop           # Stop containers"
    echo "  $0 clean          # Clean up resources"
}

# Function to stop containers
stop_containers() {
    print_status "Stopping containers..."
    
    # Stop docker-compose
    docker-compose down 2>/dev/null || true
    
    # Stop docker run container
    docker stop medassist-app 2>/dev/null || true
    docker rm medassist-app 2>/dev/null || true
    
    print_success "Containers stopped"
}

# Function to clean up
clean_up() {
    print_status "Cleaning up Docker resources..."
    
    # Stop containers first
    stop_containers
    
    # Remove image
    docker rmi medassist-ai-pro:latest 2>/dev/null || true
    
    # Clean up unused resources
    docker system prune -f
    
    print_success "Cleanup completed"
}

# Function to show logs
show_logs() {
    print_status "Showing application logs..."
    
    # Try docker-compose first
    if docker-compose ps | grep -q "medassist-app"; then
        docker-compose logs -f
    # Try docker run
    elif docker ps | grep -q "medassist-app"; then
        docker logs -f medassist-app
    else
        print_warning "No running containers found"
    fi
}

# Main script logic
main() {
    case "${1:-run}" in
        "build")
            check_prerequisites
            setup_environment
            build_image
            ;;
        "run")
            check_prerequisites
            setup_environment
            build_image
            run_with_compose
            ;;
        "docker")
            check_prerequisites
            setup_environment
            build_image
            run_with_docker
            ;;
        "stop")
            stop_containers
            ;;
        "clean")
            clean_up
            ;;
        "logs")
            show_logs
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
