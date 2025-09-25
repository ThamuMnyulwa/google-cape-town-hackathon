#!/bin/bash

# MedAssist AI Pro - GCP Deployment Script
# This script automates the deployment process to Google Cloud Platform

set -e

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
    
    if ! command_exists gcloud; then
        print_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! command_exists terraform; then
        print_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    print_success "All prerequisites are installed"
}

# Function to authenticate with GCP
authenticate_gcp() {
    print_status "Authenticating with Google Cloud Platform..."
    
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_warning "No active GCP authentication found. Please run 'gcloud auth login'"
        exit 1
    fi
    
    print_success "GCP authentication verified"
}

# Function to set up Terraform
setup_terraform() {
    print_status "Setting up Terraform..."
    
    cd terraform
    
    # Check if terraform.tfvars exists
    if [ ! -f "terraform.tfvars" ]; then
        print_warning "terraform.tfvars not found. Please create it from terraform.tfvars.example"
        print_status "Required variables:"
        echo "  - project_id"
        echo "  - region"
        echo "  - zone"
        echo "  - gemini_api_key"
        echo "  - db_password"
        echo "  - github_owner"
        echo "  - github_repo"
        exit 1
    fi
    
    # Check if backend.tf exists
    if [ ! -f "backend.tf" ]; then
        print_warning "backend.tf not found. Please create it from backend.tf.example"
        exit 1
    fi
    
    # Initialize Terraform
    terraform init
    
    print_success "Terraform initialized"
}

# Function to deploy infrastructure
deploy_infrastructure() {
    print_status "Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Plan the deployment
    print_status "Planning Terraform deployment..."
    terraform plan -out=tfplan
    
    # Ask for confirmation
    echo
    read -p "Do you want to apply this plan? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Deployment cancelled by user"
        exit 0
    fi
    
    # Apply the plan
    print_status "Applying Terraform plan..."
    terraform apply tfplan
    
    print_success "Infrastructure deployed successfully"
}

# Function to build and push Docker image
build_and_push_image() {
    print_status "Building and pushing Docker image..."
    
    # Get project ID from terraform.tfvars
    PROJECT_ID=$(grep 'project_id' terraform/terraform.tfvars | cut -d'"' -f2)
    REGION=$(grep 'region' terraform/terraform.tfvars | cut -d'"' -f2)
    REPO_NAME="medassist-ai-pro"
    
    if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ]; then
        print_error "Could not extract project_id or region from terraform.tfvars"
        exit 1
    fi
    
    # Build the image
    print_status "Building Docker image..."
    docker build -t "${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/medassist-ai-pro:latest" .
    
    # Configure Docker to use gcloud as a credential helper
    gcloud auth configure-docker "${REGION}-docker.pkg.dev"
    
    # Push the image
    print_status "Pushing Docker image to Artifact Registry..."
    docker push "${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/medassist-ai-pro:latest"
    
    print_success "Docker image built and pushed successfully"
}

# Function to deploy to Cloud Run
deploy_to_cloud_run() {
    print_status "Deploying to Cloud Run..."
    
    # Get project ID and region from terraform.tfvars
    PROJECT_ID=$(grep 'project_id' terraform/terraform.tfvars | cut -d'"' -f2)
    REGION=$(grep 'region' terraform/terraform.tfvars | cut -d'"' -f2)
    REPO_NAME="medassist-ai-pro"
    
    # Deploy to Cloud Run
    gcloud run deploy medassist-ai-pro \
        --image "${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/medassist-ai-pro:latest" \
        --region "${REGION}" \
        --platform managed \
        --allow-unauthenticated \
        --port 8502 \
        --memory 4Gi \
        --cpu 2 \
        --min-instances 0 \
        --max-instances 10 \
        --timeout 300 \
        --set-env-vars "STREAMLIT_SERVER_PORT=8502,STREAMLIT_SERVER_ADDRESS=0.0.0.0,STREAMLIT_SERVER_HEADLESS=true" \
        --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,DB_PASSWORD=db-password:latest" \
        --vpc-connector "medassist-connector" \
        --vpc-egress "PRIVATE_RANGES_ONLY"
    
    print_success "Application deployed to Cloud Run successfully"
}

# Function to show deployment information
show_deployment_info() {
    print_status "Deployment completed successfully!"
    echo
    print_status "Application Information:"
    
    # Get project ID and region
    PROJECT_ID=$(grep 'project_id' terraform/terraform.tfvars | cut -d'"' -f2)
    REGION=$(grep 'region' terraform/terraform.tfvars | cut -d'"' -f2)
    
    # Get Cloud Run service URL
    SERVICE_URL=$(gcloud run services describe medassist-ai-pro --region "${REGION}" --format="value(status.url)")
    
    echo "  Project ID: ${PROJECT_ID}"
    echo "  Region: ${REGION}"
    echo "  Service URL: ${SERVICE_URL}"
    echo
    print_status "Next Steps:"
    echo "  1. Visit your application at: ${SERVICE_URL}"
    echo "  2. Check the Cloud Console: https://console.cloud.google.com/run/detail/${REGION}/medassist-ai-pro"
    echo "  3. Monitor logs: gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=medassist-ai-pro' --limit 50"
    echo
    print_success "MedAssist AI Pro is now running on Google Cloud Platform!"
}

# Main deployment function
main() {
    echo "=========================================="
    echo "MedAssist AI Pro - GCP Deployment Script"
    echo "=========================================="
    echo
    
    # Check prerequisites
    check_prerequisites
    
    # Authenticate with GCP
    authenticate_gcp
    
    # Set up Terraform
    setup_terraform
    
    # Deploy infrastructure
    deploy_infrastructure
    
    # Build and push Docker image
    build_and_push_image
    
    # Deploy to Cloud Run
    deploy_to_cloud_run
    
    # Show deployment information
    show_deployment_info
}

# Handle script arguments
case "${1:-}" in
    "infrastructure")
        check_prerequisites
        authenticate_gcp
        setup_terraform
        deploy_infrastructure
        ;;
    "app")
        check_prerequisites
        authenticate_gcp
        build_and_push_image
        deploy_to_cloud_run
        show_deployment_info
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  (no command)  - Full deployment (infrastructure + application)"
        echo "  infrastructure - Deploy only infrastructure with Terraform"
        echo "  app          - Deploy only application to Cloud Run"
        echo "  help         - Show this help message"
        echo
        echo "Prerequisites:"
        echo "  - gcloud CLI installed and authenticated"
        echo "  - Terraform >= 1.0 installed"
        echo "  - Docker installed"
        echo "  - terraform.tfvars configured"
        echo "  - backend.tf configured"
        ;;
    *)
        main
        ;;
esac
