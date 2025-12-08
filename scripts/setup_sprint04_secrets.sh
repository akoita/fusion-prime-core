#!/bin/bash
# Setup secrets in Secret Manager for Sprint 04 services
# Usage: ./scripts/setup_sprint04_secrets.sh [PROJECT_ID]

set -e

PROJECT_ID=${1:-${GCP_PROJECT:-"fusion-prime"}}

echo "🔐 Setting up secrets in Secret Manager"
echo "   Project: $PROJECT_ID"
echo ""

# Set project
gcloud config set project "$PROJECT_ID"

# Function to create or update secret
create_secret() {
    local SECRET_NAME=$1
    local SECRET_VALUE=$2
    local DESCRIPTION=$3

    echo "📝 Secret: $SECRET_NAME"

    if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
        echo "   ⚠️  Secret already exists. Updating..."
        echo -n "$SECRET_VALUE" | gcloud secrets versions add "$SECRET_NAME" \
            --data-file=- \
            --project="$PROJECT_ID"
        echo "   ✅ Secret updated"
    else
        echo "   📝 Creating secret..."
        echo -n "$SECRET_VALUE" | gcloud secrets create "$SECRET_NAME" \
            --data-file=- \
            --replication-policy="automatic" \
            --project="$PROJECT_ID"
        echo "   ✅ Secret created"
    fi
}

# Function to prompt for secret value
prompt_secret() {
    local SECRET_NAME=$1
    local DESCRIPTION=$2
    local DEFAULT_VALUE=${3:-""}

    if [ -n "$DEFAULT_VALUE" ]; then
        read -p "   Enter $DESCRIPTION [$DEFAULT_VALUE]: " VALUE
        VALUE=${VALUE:-$DEFAULT_VALUE}
    else
        read -p "   Enter $DESCRIPTION: " VALUE
    fi

    echo "$VALUE"
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔑 Database Connection Strings"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get database connection strings
FIAT_CONN_NAME=$(gcloud sql instances describe fp-fiat-gateway-db \
    --format="value(connectionName)" \
    --project="$PROJECT_ID" 2>/dev/null || echo "")

CC_CONN_NAME=$(gcloud sql instances describe fp-cross-chain-db \
    --format="value(connectionName)" \
    --project="$PROJECT_ID" 2>/dev/null || echo "")

if [ -n "$FIAT_CONN_NAME" ]; then
    echo "📊 Fiat Gateway Database"
    read -p "   Enter PostgreSQL username [postgres]: " DB_USER
    DB_USER=${DB_USER:-postgres}
    read -sp "   Enter PostgreSQL password: " DB_PASS
    echo ""

    FIAT_CONN_STR="postgresql+asyncpg://${DB_USER}:${DB_PASS}@/${FIAT_CONN_NAME}/fiat_gateway?host=/cloudsql/${FIAT_CONN_NAME}"
    create_secret "fp-fiat-gateway-db-connection-string" "$FIAT_CONN_STR" "Fiat Gateway database connection string"
fi

if [ -n "$CC_CONN_NAME" ]; then
    echo "📊 Cross-Chain Integration Database"
    read -p "   Enter PostgreSQL username [postgres]: " DB_USER
    DB_USER=${DB_USER:-postgres}
    read -sp "   Enter PostgreSQL password (same as above?): " DB_PASS
    echo ""

    CC_CONN_STR="postgresql+asyncpg://${DB_USER}:${DB_PASS}@/${CC_CONN_NAME}/cross_chain?host=/cloudsql/${CC_CONN_NAME}"
    create_secret "fp-cross-chain-db-connection-string" "$CC_CONN_STR" "Cross-Chain Integration database connection string"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💳 Fiat Gateway Secrets (Circle & Stripe)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CIRCLE_API_KEY=$(prompt_secret "fp-circle-api-key" "Circle API Key" "")
create_secret "fp-circle-api-key" "$CIRCLE_API_KEY" "Circle API key for USDC operations"

CIRCLE_WALLET_ID=$(prompt_secret "fp-circle-wallet-id" "Circle Wallet ID" "")
create_secret "fp-circle-wallet-id" "$CIRCLE_WALLET_ID" "Circle wallet ID"

STRIPE_SECRET_KEY=$(prompt_secret "fp-stripe-secret-key" "Stripe Secret Key" "")
create_secret "fp-stripe-secret-key" "$STRIPE_SECRET_KEY" "Stripe secret key"

STRIPE_WEBHOOK_SECRET=$(prompt_secret "fp-stripe-webhook-secret" "Stripe Webhook Secret" "")
create_secret "fp-stripe-webhook-secret" "$STRIPE_WEBHOOK_SECRET" "Stripe webhook secret"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌉 Cross-Chain Integration Secrets"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Axelar API key (optional)
read -p "   Enter Axelar API Key (optional, press Enter to skip): " AXELAR_KEY
if [ -n "$AXELAR_KEY" ]; then
    create_secret "fp-axelar-api-key" "$AXELAR_KEY" "Axelar API key for enhanced rate limits"
fi

# CCIP RPC URL
CCIP_URL=$(prompt_secret "fp-ccip-rpc-url" "CCIP RPC URL" "https://ccip.chain.link")
create_secret "fp-ccip-rpc-url" "$CCIP_URL" "Chainlink CCIP RPC URL"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Secrets Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Next Steps:"
echo "   1. Run Alembic migrations for Fiat Gateway"
echo "   2. Deploy services via Cloud Build"
echo ""
