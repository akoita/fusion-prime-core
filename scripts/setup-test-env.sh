#!/bin/bash

# Setup environment variables for testnet tests
set -e

echo "🔧 Setting up environment variables for testnet tests..."

# Load existing variables from .env.test
source .env.test

# Map TESTNET_ variables to expected variable names
export PUBSUB_PROJECT_ID=$TESTNET_PUBSUB_PROJECT_ID
export GCP_PROJECT=$TESTNET_PUBSUB_PROJECT_ID
export RELAYER_SERVICE_URL=$TESTNET_RELAYER_SERVICE_URL

# Also ensure other essential variables are exported
export SETTLEMENT_SERVICE_URL=$SETTLEMENT_SERVICE_URL
export ESCROW_FACTORY_ADDRESS=$ESCROW_FACTORY_ADDRESS
export ETH_RPC_URL=$ETH_RPC_URL
export CHAIN_ID=11155111
export DATABASE_URL=$DATABASE_URL

echo "✅ Environment variables set:"
echo "  PUBSUB_PROJECT_ID: $PUBSUB_PROJECT_ID"
echo "  GCP_PROJECT: $GCP_PROJECT"
echo "  RELAYER_SERVICE_URL: $RELAYER_SERVICE_URL"
echo "  SETTLEMENT_SERVICE_URL: $SETTLEMENT_SERVICE_URL"
echo "  ESCROW_FACTORY_ADDRESS: $ESCROW_FACTORY_ADDRESS"
echo "  ETH_RPC_URL: $ETH_RPC_URL"
echo "  CHAIN_ID: $CHAIN_ID"
echo "  DATABASE_URL: $DATABASE_URL"