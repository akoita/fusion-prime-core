#!/bin/bash
# Quick Environment Setup Script
# Creates .env.production with deployed contract addresses

set -e

echo "========================================="
echo "Fusion Prime Environment Setup"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if .env.production already exists
if [ -f .env.production ]; then
    echo -e "${YELLOW}⚠${NC} .env.production already exists!"
    read -p "Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted. Existing .env.production kept."
        exit 0
    fi
fi

# Create .env.production from template
echo "Creating .env.production from template..."
cp env.production.example .env.production

# Update with actual deployed addresses
echo "Updating with deployed contract addresses..."
sed -i 's|SEPOLIA_ESCROW_FACTORY=.*|SEPOLIA_ESCROW_FACTORY=0x0F146104422a920E90627f130891bc948298d6F8|' .env.production
sed -i 's|GCP_PROJECT_ID=.*|GCP_PROJECT_ID=fusion-prime|' .env.production
sed -i 's|GCP_REGION=.*|GCP_REGION=us-central1|' .env.production

echo -e "${GREEN}✓${NC} Created .env.production with deployed addresses"
echo ""

# Prompt for RPC URL
echo "========================================="
echo "Configure RPC URL (Required)"
echo "========================================="
echo ""
echo "You need an Ethereum RPC provider to interact with Sepolia."
echo "Options:"
echo "  1. Infura (https://infura.io)"
echo "  2. Alchemy (https://alchemy.com)"
echo "  3. Your own node"
echo ""
read -p "Enter Sepolia RPC URL (or press Enter to skip): " RPC_URL

if [ -n "$RPC_URL" ]; then
    sed -i "s|SEPOLIA_RPC_URL=.*|SEPOLIA_RPC_URL=$RPC_URL|" .env.production
    echo -e "${GREEN}✓${NC} RPC URL configured"
else
    echo -e "${YELLOW}⚠${NC} RPC URL not set - you'll need to add it manually later"
fi

echo ""

# Prompt for private key
echo "========================================="
echo "Configure Deployer Private Key (Optional)"
echo "========================================="
echo ""
echo -e "${YELLOW}WARNING:${NC} Never commit your private key to git!"
echo ""
read -p "Enter deployer private key (or press Enter to skip): " -s PRIVATE_KEY
echo ""

if [ -n "$PRIVATE_KEY" ]; then
    sed -i "s|DEPLOYER_PRIVATE_KEY=|DEPLOYER_PRIVATE_KEY=$PRIVATE_KEY|" .env.production
    echo -e "${GREEN}✓${NC} Private key configured"
else
    echo -e "${YELLOW}⚠${NC} Private key not set - add it manually if needed"
fi

echo ""

# Prompt for Etherscan API key
echo "========================================="
echo "Configure Etherscan API Key (Optional)"
echo "========================================="
echo ""
echo "Needed for contract verification on Etherscan"
echo "Get one at: https://etherscan.io/myapikey"
echo ""
read -p "Enter Etherscan API key (or press Enter to skip): " ETHERSCAN_KEY

if [ -n "$ETHERSCAN_KEY" ]; then
    sed -i "s|ETHERSCAN_API_KEY=|ETHERSCAN_API_KEY=$ETHERSCAN_KEY|" .env.production
    echo -e "${GREEN}✓${NC} Etherscan API key configured"
else
    echo -e "${YELLOW}⚠${NC} Etherscan API key not set"
fi

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Your .env.production file has been created with:"
echo "  ✓ Deployed contract addresses"
echo "  ✓ GCP project configuration"
if [ -n "$RPC_URL" ]; then
    echo "  ✓ Sepolia RPC URL"
fi
if [ -n "$PRIVATE_KEY" ]; then
    echo "  ✓ Deployer private key"
fi
if [ -n "$ETHERSCAN_KEY" ]; then
    echo "  ✓ Etherscan API key"
fi
echo ""
echo "To use these variables in your shell:"
echo "  export \$(cat .env.production | grep -v '^#' | xargs)"
echo ""
echo "To verify your deployment:"
echo "  source .env.production"
echo "  ./scripts/verify-deployment.sh"
echo ""
echo "To start local development:"
echo "  docker compose up -d"
echo ""

