#!/bin/bash
#
# Deployment script for Escrow Indexer Service
# Sets up Pub/Sub subscription, database secrets, and deploys to Cloud Run
#

set -e  # Exit on error

# Configuration
PROJECT_ID="${GCP_PROJECT:-fusion-prime}"
REGION="us-central1"
SERVICE_NAME="escrow-indexer"
PUBSUB_TOPIC="settlement.events.v1"
PUBSUB_SUBSCRIPTION="escrow-indexer-sub"
DATABASE_SECRET_NAME="escrow-indexer-db-url"

echo "🚀 Deploying Escrow Indexer Service"
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

# Set project
echo "📋 Setting GCP project..."
gcloud config set project $PROJECT_ID

# Create Pub/Sub subscription if it doesn't exist
echo "📡 Setting up Pub/Sub subscription..."
if gcloud pubsub subscriptions describe $PUBSUB_SUBSCRIPTION --project=$PROJECT_ID &> /dev/null; then
    echo "   Subscription $PUBSUB_SUBSCRIPTION already exists"
else
    echo "   Creating subscription $PUBSUB_SUBSCRIPTION..."
    gcloud pubsub subscriptions create $PUBSUB_SUBSCRIPTION \
        --topic=$PUBSUB_TOPIC \
        --ack-deadline=60 \
        --message-retention-duration=7d \
        --project=$PROJECT_ID
    echo "   ✅ Subscription created"
fi

# Check if database secret exists
echo "🔐 Checking database secret..."
if ! gcloud secrets describe $DATABASE_SECRET_NAME --project=$PROJECT_ID &> /dev/null; then
    echo "   ❌ Database secret $DATABASE_SECRET_NAME not found"
    echo "   Please create the secret with your database URL:"
    echo ""
    echo "   echo -n 'postgresql://user:pass@host:5432/escrow_indexer' | \\"
    echo "     gcloud secrets create $DATABASE_SECRET_NAME --data-file=-"
    echo ""
    exit 1
else
    echo "   ✅ Database secret exists"
fi

# Deploy using Cloud Build
echo "🏗️  Building and deploying service..."
gcloud builds submit --config cloudbuild.yaml --project=$PROJECT_ID

# Get service URL
echo ""
echo "🌐 Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Service URL: $SERVICE_URL"
echo "Health check: $SERVICE_URL/health"
echo ""
echo "API Endpoints:"
echo "  - GET $SERVICE_URL/api/v1/escrows/by-payer/{address}"
echo "  - GET $SERVICE_URL/api/v1/escrows/by-payee/{address}"
echo "  - GET $SERVICE_URL/api/v1/escrows/by-arbiter/{address}"
echo "  - GET $SERVICE_URL/api/v1/escrows/by-role/{address}"
echo "  - GET $SERVICE_URL/api/v1/escrows/{escrowAddress}"
echo "  - GET $SERVICE_URL/api/v1/escrows/stats"
echo ""
echo "📊 Check logs:"
echo "  gcloud run logs read $SERVICE_NAME --region=$REGION --limit=100"
echo ""
echo "💡 Test the API:"
echo "  curl $SERVICE_URL/health"
echo "  curl $SERVICE_URL/api/v1/escrows/stats"
echo ""
