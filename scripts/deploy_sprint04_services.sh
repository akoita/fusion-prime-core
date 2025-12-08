#!/bin/bash
# Deploy all Sprint 04 services to Cloud Run
# Usage: ./scripts/deploy_sprint04_services.sh [PROJECT_ID]

set -e

PROJECT_ID=${1:-${GCP_PROJECT:-"fusion-prime"}}

echo "🚀 Deploying Sprint 04 Services to Cloud Run"
echo "   Project: $PROJECT_ID"
echo ""

# Set project
gcloud config set project "$PROJECT_ID"

# Function to deploy a service
deploy_service() {
    local SERVICE_NAME=$1
    local BUILD_DIR=$2

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 Deploying: $SERVICE_NAME"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    cd "$BUILD_DIR"

    if [ ! -f "cloudbuild.yaml" ]; then
        echo "❌ Error: cloudbuild.yaml not found in $BUILD_DIR"
        return 1
    fi

    echo "   🔨 Building and deploying..."
    gcloud builds submit --config=cloudbuild.yaml --project="$PROJECT_ID"

    if [ $? -eq 0 ]; then
        echo "   ✅ $SERVICE_NAME deployed successfully"

        # Get service URL
        SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
            --region=us-central1 \
            --format="value(status.url)" \
            --project="$PROJECT_ID" 2>/dev/null || echo "N/A")

        echo "   🔗 Service URL: $SERVICE_URL"
    else
        echo "   ❌ Failed to deploy $SERVICE_NAME"
        return 1
    fi

    echo ""
    cd - > /dev/null
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# 1. Fiat Gateway Service
deploy_service "fiat-gateway-service" "services/fiat-gateway"

# 2. Cross-Chain Integration Service
deploy_service "cross-chain-integration-service" "services/cross-chain-integration"

# 3. API Key Service
deploy_service "api-key-service" "infra/api-gateway/api-key-service"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All Services Deployed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Service URLs:"
echo ""
gcloud run services list --platform=managed --region=us-central1 --project="$PROJECT_ID" \
    --filter="metadata.name:fiat-gateway-service OR metadata.name:cross-chain-integration-service OR metadata.name:api-key-service" \
    --format="table(metadata.name, status.url)"
echo ""
echo "🧪 Next Steps:"
echo "   1. Test health endpoints"
echo "   2. Run integration tests"
echo "   3. Verify service logs"
echo ""
