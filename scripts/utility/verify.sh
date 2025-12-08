#!/bin/bash
# Deployment Verification Script
# Checks that all deployed resources are accessible and configured correctly

set -e

echo "========================================="
echo "Fusion Prime Deployment Verification"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if required tools are installed
echo "Checking required tools..."
command -v cast >/dev/null 2>&1 || { echo -e "${RED}✗${NC} cast (Foundry) is not installed"; exit 1; }
command -v gcloud >/dev/null 2>&1 || { echo -e "${RED}✗${NC} gcloud is not installed"; exit 1; }
command -v terraform >/dev/null 2>&1 || { echo -e "${RED}✗${NC} terraform is not installed"; exit 1; }
echo -e "${GREEN}✓${NC} All required tools installed"
echo ""

# Load environment variables if .env exists
if [ -f .env.production ]; then
    echo "Loading environment variables from .env.production..."
    export $(cat .env.production | grep -v '^#' | xargs)
    echo -e "${GREEN}✓${NC} Environment variables loaded"
else
    echo -e "${YELLOW}⚠${NC} .env.production not found, using system environment"
fi
echo ""

# ========================================
# Smart Contract Verification (Sepolia)
# ========================================
echo "========================================="
echo "Smart Contract Verification (Sepolia)"
echo "========================================="

if [ -z "$SEPOLIA_RPC_URL" ]; then
    echo -e "${YELLOW}⚠${NC} SEPOLIA_RPC_URL not set - skipping smart contract verification"
    echo "  To enable: export SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY"
    SKIP_CONTRACT_VERIFICATION=true
else
    SKIP_CONTRACT_VERIFICATION=false
fi

if [ "$SKIP_CONTRACT_VERIFICATION" = false ]; then
    if [ -z "$SEPOLIA_ESCROW_FACTORY" ]; then
        echo -e "${YELLOW}⚠${NC} SEPOLIA_ESCROW_FACTORY not set"
        echo "  Set: export SEPOLIA_ESCROW_FACTORY=0x0F146104422a920E90627f130891bc948298d6F8"
    else
        echo "Checking Escrow Factory at $SEPOLIA_ESCROW_FACTORY..."

        CODE=$(cast code $SEPOLIA_ESCROW_FACTORY --rpc-url $SEPOLIA_RPC_URL 2>/dev/null || echo "")
        if [ -n "$CODE" ] && [ "$CODE" != "0x" ]; then
            echo -e "${GREEN}✓${NC} Escrow Factory deployed and has code"
        else
            echo -e "${RED}✗${NC} Escrow Factory not deployed or has no code"
        fi
    fi
else
    echo "Skipping contract verification (no RPC URL)"
    echo ""
    echo "Deployed contracts (view on Etherscan):"
    echo "  Proxy: https://sepolia.etherscan.io/address/0xDaff9610aDBA338f6F1F7b06344EA86EeA8Ca2f9"
    echo "  Factory: https://sepolia.etherscan.io/address/0x0F146104422a920E90627f130891bc948298d6F8"
    echo "  Implementation: https://sepolia.etherscan.io/address/0x4B41533B38F7AB154707Db176915352C60EA4017"
fi

echo ""

# ========================================
# GCP Infrastructure Verification
# ========================================
echo "========================================="
echo "GCP Infrastructure Verification"
echo "========================================="

# Check GCP authentication
echo "Checking GCP authentication..."
CURRENT_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || echo "")
if [ -n "$CURRENT_ACCOUNT" ]; then
    echo -e "${GREEN}✓${NC} Authenticated as: $CURRENT_ACCOUNT"
else
    echo -e "${RED}✗${NC} Not authenticated to GCP"
    echo "  Run: gcloud auth login"
    exit 1
fi

# Check current project
echo "Checking GCP project..."
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
if [ -n "$CURRENT_PROJECT" ]; then
    echo -e "${GREEN}✓${NC} Current project: $CURRENT_PROJECT"

    # Verify project exists
    PROJECT_EXISTS=$(gcloud projects describe $CURRENT_PROJECT --format="value(projectId)" 2>/dev/null || echo "")
    if [ -n "$PROJECT_EXISTS" ]; then
        echo -e "${GREEN}✓${NC} Project exists and is accessible"
    else
        echo -e "${RED}✗${NC} Project not found or not accessible"
    fi
else
    echo -e "${RED}✗${NC} No GCP project configured"
    echo "  Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo ""

# Check Pub/Sub topics
echo "Checking Pub/Sub topics..."
TOPICS=$(gcloud pubsub topics list --format="value(name)" 2>/dev/null || echo "")
if [ -n "$TOPICS" ]; then
    echo -e "${GREEN}✓${NC} Pub/Sub topics found:"
    echo "$TOPICS" | while read topic; do
        echo "  - $topic"
    done
else
    echo -e "${YELLOW}⚠${NC} No Pub/Sub topics found (may not be deployed yet)"
fi

echo ""

# Check service accounts
echo "Checking service accounts..."
SERVICE_ACCOUNTS=$(gcloud iam service-accounts list --format="value(email)" 2>/dev/null || echo "")
if [ -n "$SERVICE_ACCOUNTS" ]; then
    echo -e "${GREEN}✓${NC} Service accounts found:"
    echo "$SERVICE_ACCOUNTS" | head -5 | while read sa; do
        echo "  - $sa"
    done
    SA_COUNT=$(echo "$SERVICE_ACCOUNTS" | wc -l)
    if [ "$SA_COUNT" -gt 5 ]; then
        echo "  ... and $((SA_COUNT - 5)) more"
    fi
else
    echo -e "${YELLOW}⚠${NC} No service accounts found"
fi

echo ""

# Check Cloud SQL instances
echo "Checking Cloud SQL instances..."
SQL_INSTANCES=$(gcloud sql instances list --format="value(name)" 2>/dev/null || echo "")
if [ -n "$SQL_INSTANCES" ]; then
    echo -e "${GREEN}✓${NC} Cloud SQL instances found:"
    echo "$SQL_INSTANCES" | while read instance; do
        STATUS=$(gcloud sql instances describe $instance --format="value(state)" 2>/dev/null || echo "UNKNOWN")
        echo "  - $instance (Status: $STATUS)"
    done
else
    echo -e "${YELLOW}⚠${NC} No Cloud SQL instances found (may not be deployed yet)"
fi

echo ""

# Check BigQuery datasets
echo "Checking BigQuery datasets..."
BQ_DATASETS=$(bq ls --format=prettyjson 2>/dev/null | jq -r '.[].datasetReference.datasetId' 2>/dev/null || echo "")
if [ -n "$BQ_DATASETS" ]; then
    echo -e "${GREEN}✓${NC} BigQuery datasets found:"
    echo "$BQ_DATASETS" | while read dataset; do
        echo "  - $dataset"
    done
else
    echo -e "${YELLOW}⚠${NC} No BigQuery datasets found (may not be deployed yet)"
fi

echo ""

# Check Cloud Run services
echo "Checking Cloud Run services..."
CLOUD_RUN_SERVICES=$(gcloud run services list --format="value(metadata.name)" 2>/dev/null || echo "")
if [ -n "$CLOUD_RUN_SERVICES" ]; then
    echo -e "${GREEN}✓${NC} Cloud Run services found:"
    echo "$CLOUD_RUN_SERVICES" | while read service; do
        URL=$(gcloud run services describe $service --format="value(status.url)" 2>/dev/null || echo "")
        echo "  - $service"
        echo "    URL: $URL"
    done
else
    echo -e "${YELLOW}⚠${NC} No Cloud Run services found (may not be deployed yet)"
fi

echo ""

# ========================================
# Terraform State Verification
# ========================================
echo "========================================="
echo "Terraform State Verification"
echo "========================================="

# Check bootstrap state
if [ -d "infra/terraform/bootstrap" ]; then
    echo "Checking bootstrap Terraform state..."
    cd infra/terraform/bootstrap
    if [ -f ".terraform/terraform.tfstate" ] || [ -f "terraform.tfstate" ]; then
        BOOTSTRAP_RESOURCES=$(terraform state list 2>/dev/null | wc -l || echo "0")
        if [ "$BOOTSTRAP_RESOURCES" -gt 0 ]; then
            echo -e "${GREEN}✓${NC} Bootstrap Terraform has $BOOTSTRAP_RESOURCES resources"
        else
            echo -e "${YELLOW}⚠${NC} Bootstrap Terraform state is empty or not initialized"
        fi
    else
        echo -e "${YELLOW}⚠${NC} Bootstrap Terraform not initialized"
    fi
    cd ../../..
fi

# Check project state
if [ -d "infra/terraform/project" ]; then
    echo "Checking project Terraform state..."
    cd infra/terraform/project
    if [ -f ".terraform/terraform.tfstate" ] || [ -f "terraform.tfstate" ]; then
        PROJECT_RESOURCES=$(terraform state list 2>/dev/null | wc -l || echo "0")
        if [ "$PROJECT_RESOURCES" -gt 0 ]; then
            echo -e "${GREEN}✓${NC} Project Terraform has $PROJECT_RESOURCES resources"
        else
            echo -e "${YELLOW}⚠${NC} Project Terraform state is empty or not initialized"
        fi
    else
        echo -e "${YELLOW}⚠${NC} Project Terraform not initialized"
    fi
    cd ../../..
fi

echo ""

# ========================================
# Summary
# ========================================
echo "========================================="
echo "Verification Summary"
echo "========================================="
echo ""
echo "Please review the results above and update DEPLOYMENT_STATUS.md with:"
echo "  1. Smart contract addresses (if not already set)"
echo "  2. GCP project ID"
echo "  3. Any missing environment variables"
echo ""
echo "Next steps:"
echo "  1. Update DEPLOYMENT_STATUS.md with deployment details"
echo "  2. Configure remaining infrastructure (Cloud SQL, BigQuery, etc.)"
echo "  3. Deploy settlement service to Cloud Run"
echo "  4. Start event relayer"
echo "  5. Test end-to-end flow"
echo ""
echo "For detailed instructions, see:"
echo "  - DEPLOYMENT_STATUS.md"
echo "  - contracts/DEPLOYMENT.md"
echo "  - docs/LOCAL_DEVELOPMENT.md"
echo ""
