#!/bin/bash
# Setup Cloud SQL databases for Sprint 04 services
# Usage: ./scripts/setup_sprint04_databases.sh [PROJECT_ID]

set -e

PROJECT_ID=${1:-${GCP_PROJECT:-"fusion-prime"}}
REGION="us-central1"

echo "🚀 Setting up Cloud SQL databases for Sprint 04 services"
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"
echo ""

# Set project
gcloud config set project "$PROJECT_ID"

# Function to create database if it doesn't exist
create_database() {
    local INSTANCE_NAME=$1
    local DB_NAME=$2

    echo "📊 Checking database: $DB_NAME on instance $INSTANCE_NAME"

    # Check if database exists
    if gcloud sql databases describe "$DB_NAME" --instance="$INSTANCE_NAME" --project="$PROJECT_ID" &>/dev/null; then
        echo "   ✅ Database $DB_NAME already exists"
    else
        echo "   📝 Creating database $DB_NAME..."
        gcloud sql databases create "$DB_NAME" \
            --instance="$INSTANCE_NAME" \
            --project="$PROJECT_ID"
        echo "   ✅ Database $DB_NAME created"
    fi
}

# Function to create instance if it doesn't exist
create_instance() {
    local INSTANCE_NAME=$1

    echo "🔍 Checking Cloud SQL instance: $INSTANCE_NAME"

    if gcloud sql instances describe "$INSTANCE_NAME" --project="$PROJECT_ID" &>/dev/null; then
        echo "   ✅ Instance $INSTANCE_NAME already exists"
    else
        echo "   📝 Creating instance $INSTANCE_NAME..."
        gcloud sql instances create "$INSTANCE_NAME" \
            --database-version=POSTGRES_15 \
            --tier=db-f1-micro \
            --region="$REGION" \
            --project="$PROJECT_ID" \
            --backup-start-time=03:00 \
            --enable-bin-log \
            --maintenance-window-day=SUN \
            --maintenance-window-hour=04

        echo "   ✅ Instance $INSTANCE_NAME created"
    fi
}

# 1. Fiat Gateway Database
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  Fiat Gateway Database"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
FIAT_INSTANCE="fp-fiat-gateway-db"
create_instance "$FIAT_INSTANCE"
create_database "$FIAT_INSTANCE" "fiat_gateway"

# Get connection name
FIAT_CONN_NAME=$(gcloud sql instances describe "$FIAT_INSTANCE" \
    --format="value(connectionName)" \
    --project="$PROJECT_ID")
echo "   📍 Connection name: $FIAT_CONN_NAME"

# 2. Cross-Chain Integration Database
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  Cross-Chain Integration Database"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
CC_INSTANCE="fp-cross-chain-db"
create_instance "$CC_INSTANCE"
create_database "$CC_INSTANCE" "cross_chain"

# Get connection name
CC_CONN_NAME=$(gcloud sql instances describe "$CC_INSTANCE" \
    --format="value(connectionName)" \
    --project="$PROJECT_ID")
echo "   📍 Connection name: $CC_CONN_NAME"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Database Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Next Steps:"
echo "   1. Store connection strings in Secret Manager (see setup_secrets.sh)"
echo "   2. Run Alembic migrations for Fiat Gateway"
echo "   3. Update cloudbuild.yaml with connection names:"
echo "      - Fiat Gateway: $FIAT_CONN_NAME"
echo "      - Cross-Chain: $CC_CONN_NAME"
echo ""
