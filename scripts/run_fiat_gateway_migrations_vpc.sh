#!/bin/bash
# Run Alembic migrations for Fiat Gateway via Cloud Run Job (with VPC access)
# This uses Cloud Run Job which has automatic VPC connector access

set -e

PROJECT_ID=${1:-${GCP_PROJECT:-"fusion-prime"}}
SERVICE_NAME="fiat-gateway-service"
REGION="us-central1"
JOB_NAME="fiat-gateway-migrations"

echo "🗄️  Running Fiat Gateway Database Migrations (VPC Mode)"
echo "   Project: $PROJECT_ID"
echo "   Service: $SERVICE_NAME"
echo "   Region: $REGION"
echo ""

# Check if Cloud Run service exists (to get the image)
if ! gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "⚠️  Service $SERVICE_NAME not found. Building image first..."

    # Build and push image
    cd "$(dirname "$0")/../services/fiat-gateway"
    gcloud builds submit --config=cloudbuild.yaml --project="$PROJECT_ID" || {
        echo "❌ Failed to build service. Please deploy it first."
        exit 1
    }
fi

# Get the latest image
IMAGE=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(spec.template.spec.containers[0].image)" 2>/dev/null || echo "")

if [ -z "$IMAGE" ]; then
    IMAGE="us-central1-docker.pkg.dev/$PROJECT_ID/fusion-prime-services/$SERVICE_NAME:latest"
    echo "📦 Using default image: $IMAGE"
else
    echo "📦 Using service image: $IMAGE"
fi

echo ""
echo "🔧 Creating/Updating Cloud Run Job for migrations..."
echo "   Job will have VPC connector access for private IP connection"
echo ""

# Check if job exists
if gcloud run jobs describe "$JOB_NAME" --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "📋 Updating existing job..."
    gcloud run jobs update "$JOB_NAME" \
        --image="$IMAGE" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --set-secrets="DATABASE_URL=fp-fiat-gateway-db-connection-string:latest" \
        --set-cloudsql-instances="fusion-prime:us-central1:fp-fiat-gateway-db-a0cd6952" \
        --vpc-connector="fusion-prime-connector" \
        --vpc-egress="private-ranges-only" \
        --command="sh" \
        --args="-c,cd /app/services/fiat-gateway && export DATABASE_URL=\"\${DATABASE_URL}\" && alembic upgrade head" \
        --max-retries=1 \
        --task-timeout=600 \
        --memory=512Mi \
        --cpu=1 || {
        echo "⚠️  Failed to update job. Creating new one..."
        # Delete and recreate
        gcloud run jobs delete "$JOB_NAME" --region="$REGION" --project="$PROJECT_ID" --quiet 2>/dev/null || true
    }
fi

# Create job if it doesn't exist
if ! gcloud run jobs describe "$JOB_NAME" --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "📋 Creating new migration job..."
    gcloud run jobs create "$JOB_NAME" \
        --image="$IMAGE" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --set-secrets="DATABASE_URL=fp-fiat-gateway-db-connection-string:latest" \
        --set-cloudsql-instances="fusion-prime:us-central1:fp-fiat-gateway-db-a0cd6952" \
        --vpc-connector="fusion-prime-connector" \
        --vpc-egress="private-ranges-only" \
        --command="sh" \
        --args="-c,cd /app/services/fiat-gateway && export DATABASE_URL=\"\${DATABASE_URL}\" && alembic upgrade head" \
        --max-retries=1 \
        --task-timeout=600 \
        --memory=512Mi \
        --cpu=1
fi

echo ""
echo "🚀 Executing migrations..."
echo ""

# Execute the job
EXECUTION_NAME=$(gcloud run jobs execute "$JOB_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(metadata.name)" \
    --wait 2>&1)

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migrations completed successfully!"
    echo ""
    echo "📊 Execution: $EXECUTION_NAME"

    # Show logs
    echo ""
    echo "📋 Migration logs:"
    gcloud run jobs executions logs read "$EXECUTION_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --limit=50 2>&1 | tail -30

else
    echo ""
    echo "❌ Migration failed!"
    echo ""
    echo "📋 Error logs:"
    gcloud run jobs executions logs read "$EXECUTION_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --limit=50 2>&1 | tail -30

    exit 1
fi

echo ""
echo "✅ Migration job complete!"
echo ""
echo "📋 Next Steps:"
echo "  1. Verify tables created: Check database schema"
echo "  2. Test service endpoints"
echo "  3. Run migrations for Cross-Chain Integration if needed"
