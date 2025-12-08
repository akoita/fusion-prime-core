#!/bin/bash
# Run Alembic migrations for Fiat Gateway using Cloud Run exec
# This connects to the deployed service and runs migrations

set -e

PROJECT_ID=${1:-${GCP_PROJECT:-"fusion-prime"}}
SERVICE_NAME="fiat-gateway-service"
REGION="us-central1"

echo "🗄️  Running Fiat Gateway Database Migrations"
echo "   Service: $SERVICE_NAME"
echo "   Project: $PROJECT_ID"
echo ""

# Check if service exists
if ! gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo "⚠️  Service $SERVICE_NAME not found. Deploy it first."
    exit 1
fi

echo "📋 Running migrations via Cloud Run exec..."
echo "   This will connect to the service and run: alembic upgrade head"
echo ""

# Run migrations via Cloud Run exec
gcloud run jobs execute migration-job \
    --region=$REGION \
    --project=$PROJECT_ID \
    --wait 2>/dev/null || {

    echo "⚠️  Migration job not found. Creating one..."

    # Create a Cloud Run Job for migrations
    gcloud run jobs create migration-job \
        --image=us-central1-docker.pkg.dev/$PROJECT_ID/fusion-prime-services/$SERVICE_NAME:latest \
        --region=$REGION \
        --project=$PROJECT_ID \
        --set-secrets=DATABASE_URL=fp-fiat-gateway-db-connection-string:latest \
        --add-cloudsql-instances=fusion-prime:us-central1:fp-fiat-gateway-db-a0cd6952 \
        --vpc-connector=fusion-prime-connector \
        --vpc-egress=private-ranges-only \
        --command="alembic" \
        --args="upgrade,head" || {

        echo "💡 Alternative: Run migrations manually via Cloud SQL Proxy"
        echo "   See: scripts/run_fiat_gateway_migrations.sh"
    }
}

echo ""
echo "✅ Migrations complete!"
