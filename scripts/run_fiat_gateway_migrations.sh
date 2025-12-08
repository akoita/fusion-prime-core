#!/bin/bash
# Run Alembic migrations for Fiat Gateway Service
# Usage: ./scripts/run_fiat_gateway_migrations.sh [PROJECT_ID]

set -e

PROJECT_ID=${1:-${GCP_PROJECT:-"fusion-prime"}}
INSTANCE_NAME="fp-fiat-gateway-db"
REGION="us-central1"

echo "🗄️  Running Alembic migrations for Fiat Gateway"
echo "   Project: $PROJECT_ID"
echo "   Instance: $INSTANCE_NAME"
echo ""

# Set project
gcloud config set project "$PROJECT_ID"

# Check if instance exists
if ! gcloud sql instances describe "$INSTANCE_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo "❌ Error: Database instance $INSTANCE_NAME does not exist"
    echo "   Run ./scripts/setup_sprint04_databases.sh first"
    exit 1
fi

# Start Cloud SQL Proxy in background
echo "🔌 Starting Cloud SQL Proxy..."
CONN_NAME=$(gcloud sql instances describe "$INSTANCE_NAME" \
    --format="value(connectionName)" \
    --project="$PROJECT_ID")

# Check if cloud-sql-proxy is installed
if ! command -v cloud-sql-proxy &> /dev/null; then
    echo "⚠️  cloud-sql-proxy not found. Installing..."
    # Download cloud-sql-proxy
    wget https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64 -O /tmp/cloud-sql-proxy
    chmod +x /tmp/cloud-sql-proxy
    PROXY_BIN="/tmp/cloud-sql-proxy"
else
    PROXY_BIN="cloud-sql-proxy"
fi

# Start proxy in background
$PROXY_BIN "$CONN_NAME" --port=5432 > /tmp/cloud-sql-proxy.log 2>&1 &
PROXY_PID=$!

# Wait for proxy to be ready
echo "   Waiting for Cloud SQL Proxy to be ready..."
sleep 3

# Check if proxy is running
if ! kill -0 $PROXY_PID 2>/dev/null; then
    echo "❌ Error: Cloud SQL Proxy failed to start"
    cat /tmp/cloud-sql-proxy.log
    exit 1
fi

echo "   ✅ Cloud SQL Proxy running (PID: $PROXY_PID)"

# Set up database connection
export DATABASE_URL="postgresql+psycopg2://postgres:${DB_PASSWORD}@localhost:5432/fiat_gateway"

# Run migrations
echo ""
echo "📦 Running migrations..."
cd services/fiat-gateway

if [ -z "$DB_PASSWORD" ]; then
    read -sp "Enter database password: " DB_PASSWORD
    echo ""
    export DATABASE_URL="postgresql+psycopg2://postgres:${DB_PASSWORD}@localhost:5432/fiat_gateway"
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📥 Creating virtual environment and installing dependencies..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run migrations
echo "🚀 Running Alembic migrations..."
alembic upgrade head

echo ""
echo "✅ Migrations complete!"

# Stop Cloud SQL Proxy
echo "🛑 Stopping Cloud SQL Proxy..."
kill $PROXY_PID
wait $PROXY_PID 2>/dev/null

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Fiat Gateway Database Migrations Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
