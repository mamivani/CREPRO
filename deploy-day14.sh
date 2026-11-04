#!/bin/bash

# Day 14 Deployment Script - Automated setup for Azure deployment

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SUBSCRIPTION_ID="${1:-YOUR-SUBSCRIPTION-ID}"
RESOURCE_GROUP_NAME="${2:-crepro-dev-rg}"
LOCATION="${3:-eastus}"
REGISTRY_NAME="creprobuilddev"
ENVIRONMENT_NAME="crepro-dev-env"
POSTGRES_SERVER="crepro-db-dev"

echo -e "${YELLOW}=== CREPRO Day 14 Deployment Script ===${NC}"
echo ""

# Function to print section headers
print_section() {
    echo -e "${YELLOW}>>> $1${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error and exit
print_error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

# Check prerequisites
print_section "Checking prerequisites"

# Check Azure CLI
if ! command -v az &> /dev/null; then
    print_error "Azure CLI not found. Install from https://aka.ms/azure-cli"
fi
print_success "Azure CLI installed"

# Check Terraform
if ! command -v terraform &> /dev/null; then
    print_error "Terraform not found. Install from https://www.terraform.io"
fi
print_success "Terraform installed"

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Install from https://www.docker.com"
fi
print_success "Docker installed"

# Check PostgreSQL CLI
if ! command -v psql &> /dev/null; then
    print_error "psql not found. Install PostgreSQL client from https://www.postgresql.org"
fi
print_success "PostgreSQL client installed"

echo ""

# Azure Login
print_section "Azure authentication"

if ! az account show &>/dev/null; then
    print_error "Not logged into Azure. Run: az login"
fi

CURRENT_SUBSCRIPTION=$(az account show --query id -o tsv)
if [ "$SUBSCRIPTION_ID" == "YOUR-SUBSCRIPTION-ID" ]; then
    print_error "Please set SUBSCRIPTION_ID: $0 <subscription-id>"
fi

az account set --subscription "$SUBSCRIPTION_ID"
print_success "Authenticated to Azure subscription: $SUBSCRIPTION_ID"

echo ""

# Terraform deployment
print_section "Deploying Azure infrastructure"

cd infrastructure/terraform

# Initialize Terraform
print_section "Initializing Terraform"
terraform init
print_success "Terraform initialized"

# Plan deployment
print_section "Planning deployment"
terraform plan -var-file="dev.tfvars" \
    -var="subscription_id=$SUBSCRIPTION_ID" \
    -var="location=$LOCATION" \
    -out=tfplan

read -p "Review plan above. Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_error "Deployment cancelled"
fi

# Apply deployment
print_section "Deploying infrastructure"
terraform apply tfplan
print_success "Azure infrastructure deployed"

# Get outputs
REGISTRY_URL=$(terraform output -raw container_registry_url)
DATABASE_HOST=$(terraform output -raw database_host)
APP_ENVIRONMENT_ID=$(terraform output -raw app_environment_id)

print_success "Container Registry: $REGISTRY_URL"
print_success "Database Host: $DATABASE_HOST"
print_success "App Environment ID: $APP_ENVIRONMENT_ID"

cd ../..

echo ""

# Database initialization
print_section "Initializing PostgreSQL database"

# Get database credentials (should be stored in Key Vault)
read -sp "Enter PostgreSQL admin password: " POSTGRES_PASSWORD
echo

# Wait for database to be ready
print_section "Waiting for PostgreSQL to be ready"
sleep 30

# Apply database schema
psql -h "$DATABASE_HOST" \
    -U pgadmin \
    -d crepro \
    -f infrastructure/database/01-adapter-ledger-schema.sql \
    -w <<< "$POSTGRES_PASSWORD" || print_error "Failed to apply database schema"

print_success "Database schema applied"

echo ""

# Build and push container images
print_section "Building and pushing container images"

# Login to registry
az acr login --name "$REGISTRY_NAME"
print_success "Logged into container registry"

# Build ERP Adapter
print_section "Building erp-adapter image"
cd services/erp_adapter
docker build -t "$REGISTRY_URL/crepro-erp-adapter:latest" .
docker push "$REGISTRY_URL/crepro-erp-adapter:latest"
print_success "erp-adapter image pushed"
cd ../..

# Build Reconciliation
print_section "Building erp-reconciliation image"
cd services/erp_reconciliation
docker build -t "$REGISTRY_URL/crepro-erp-reconciliation:latest" .
docker push "$REGISTRY_URL/crepro-erp-reconciliation:latest"
print_success "erp-reconciliation image pushed"
cd ../..

echo ""

# Verify deployment
print_section "Verifying deployment"

print_success "Deployment complete!"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Deploy Container Apps (requires manual configuration in Azure Portal or additional Terraform)"
echo "2. Set environment variables in Container Apps:"
echo "   - ERP_BASE_URL=https://erp.example.com"
echo "   - ERP_USERNAME=Administrator"
echo "   - ERP_PASSWORD=(from Key Vault)"
echo "   - DATABASE_URL=(from Key Vault)"
echo "   - ADAPTER_SERVICE_URL=http://erp-adapter.svc.cluster.local"
echo "3. Run smoke tests"
echo "4. Monitor via Application Insights"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "  View logs:         az containerapp logs show -n erp-adapter -g $RESOURCE_GROUP_NAME"
echo "  Scale app:         az containerapp update -n erp-adapter -g $RESOURCE_GROUP_NAME --set properties.template.scale.maxReplicas=5"
echo "  Restart app:       az containerapp restart -n erp-adapter -g $RESOURCE_GROUP_NAME"
echo "  Destroy resources: cd infrastructure/terraform && terraform destroy -var-file=dev.tfvars"
echo ""

print_success "Deployment script completed!"
