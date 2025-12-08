#!/bin/bash
# Deploy Sprint 04 databases using Terraform
# Usage: ./scripts/deploy_databases_terraform.sh [ENVIRONMENT] [PROJECT_ID]

set -e

ENVIRONMENT=${1:-"dev"}
PROJECT_ID=${2:-${GCP_PROJECT:-"fusion-prime"}}
TF_DIR="infra/terraform/project"
TFVARS_FILE="terraform.${ENVIRONMENT}.tfvars"

echo "🏗️  Deploying Sprint 04 Databases via Terraform"
echo "   Environment: $ENVIRONMENT"
echo "   Project: $PROJECT_ID"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT/$TF_DIR"

# Check if tfvars file exists
if [ ! -f "$TFVARS_FILE" ]; then
    echo "⚠️  Warning: $TFVARS_FILE not found"
    echo "   Will use default values from variables.tf"
    TFVARS_ARGS=""
else
    echo "✅ Using $TFVARS_FILE"
    TFVARS_ARGS="-var-file=$TFVARS_FILE"
fi

# Initialize Terraform (if needed)
if [ ! -d ".terraform" ]; then
    echo ""
    echo "📦 Initializing Terraform..."
    terraform init
    echo "✅ Terraform initialized"
else
    echo "✅ Terraform already initialized"
fi

# Set GCP project
echo ""
echo "🔧 Setting GCP project..."
gcloud config set project "$PROJECT_ID"

# Plan changes
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Planning Terraform Changes"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
terraform plan $TFVARS_ARGS -out=tfplan

# Ask for confirmation
echo ""
read -p "Do you want to apply these changes? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

# Apply changes
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Applying Terraform Changes"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
terraform apply tfplan

# Show outputs
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Database Information"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Fiat Gateway Database:"
echo "  Connection Name: $(terraform output -raw fiat_gateway_db_connection_name 2>/dev/null || echo 'N/A')"
echo "  Connection String Secret: $(terraform output -raw fiat_gateway_db_connection_string_secret 2>/dev/null || echo 'N/A')"
echo ""
echo "Cross-Chain Integration Database:"
echo "  Connection Name: $(terraform output -raw cross_chain_db_connection_name 2>/dev/null || echo 'N/A')"
echo "  Connection String Secret: $(terraform output -raw cross_chain_db_connection_string_secret 2>/dev/null || echo 'N/A')"
echo ""

# Verify secrets
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 Verifying Secrets in Secret Manager"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SECRETS=(
    "fp-fiat-gateway-db-connection-string"
    "fp-cross-chain-db-connection-string"
)

for SECRET in "${SECRETS[@]}"; do
    if gcloud secrets describe "$SECRET" --project="$PROJECT_ID" &>/dev/null; then
        echo "  ✅ $SECRET exists"
    else
        echo "  ⚠️  $SECRET not found (may need time to propagate)"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Database Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Next Steps:"
echo "  1. Run Alembic migrations for Fiat Gateway:"
echo "     ./scripts/run_fiat_gateway_migrations.sh"
echo ""
echo "  2. Update Cloud Build configs with connection names"
echo ""
echo "  3. Deploy services:"
echo "     ./scripts/deploy_sprint04_services.sh"
echo ""
