#!/bin/bash
# Setup script for local Event Relayer development

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================="
echo "Fusion Prime Local Relayer Setup"
echo "========================================="
echo ""

# Check if Docker Compose is running
if ! docker compose ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠${NC} Docker Compose services not running. Starting them..."
    docker compose up -d
    echo "Waiting for services to be ready..."
    sleep 30
fi

# Check if Anvil is running
echo "Checking Anvil status..."
if ! docker compose ps anvil | grep -q "Up"; then
    echo -e "${RED}✗${NC} Anvil is not running. Please start Docker Compose first."
    exit 1
fi

# Deploy contracts to Anvil
echo -e "${BLUE}📋${NC} Deploying contracts to Anvil..."
cd contracts

# Check if contracts are already deployed
if [ -f "broadcast/DeployMultichain.s.sol/31337/run-latest.json" ]; then
    echo -e "${YELLOW}⚠${NC} Contracts already deployed. Using existing addresses."
    ESCROW_FACTORY=$(jq -r '.transactions[0].contractAddress' broadcast/DeployMultichain.s.sol/31337/run-latest.json)
else
    echo "Deploying contracts..."
    forge script script/DeployMultichain.s.sol:DeployMultichain \
        --rpc-url http://localhost:8545 \
        --broadcast \
        --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
    ESCROW_FACTORY=$(jq -r '.transactions[0].contractAddress' broadcast/DeployMultichain.s.sol/31337/run-latest.json)
fi

echo -e "${GREEN}✓${NC} Escrow Factory deployed at: $ESCROW_FACTORY"

cd ..

# Update Docker Compose with contract address
echo -e "${BLUE}📋${NC} Updating Docker Compose with contract address..."
sed -i "s/CONTRACT_ADDRESS: \"0x_UPDATE_AFTER_DEPLOY\"/CONTRACT_ADDRESS: \"$ESCROW_FACTORY\"/" docker-compose.yml

# Initialize Pub/Sub emulator
echo -e "${BLUE}📋${NC} Initializing Pub/Sub emulator..."
if [ -f "scripts/init-pubsub-emulator.sh" ]; then
    ./scripts/init-pubsub-emulator.sh
else
    echo "Creating Pub/Sub topic and subscription..."
    docker compose exec pubsub-emulator gcloud pubsub topics create settlement.events.v1 --project=fusion-prime-local
    docker compose exec pubsub-emulator gcloud pubsub subscriptions create settlement-events-consumer --topic=settlement.events.v1 --project=fusion-prime-local
fi

# Start the relayer
echo -e "${BLUE}📋${NC} Starting Event Relayer..."
docker compose up -d event-relayer

# Wait for relayer to start
echo "Waiting for relayer to start..."
sleep 10

# Check relayer status
echo -e "${BLUE}📋${NC} Checking relayer status..."
if docker compose ps event-relayer | grep -q "Up"; then
    echo -e "${GREEN}✓${NC} Event Relayer is running!"
else
    echo -e "${RED}✗${NC} Event Relayer failed to start. Check logs:"
    docker compose logs event-relayer
    exit 1
fi

# Show logs
echo ""
echo "========================================="
echo "Event Relayer Logs (last 20 lines)"
echo "========================================="
docker compose logs --tail=20 event-relayer

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo -e "${GREEN}✓${NC} All services are running:"
echo "  - Anvil (Ethereum): http://localhost:8545"
echo "  - Settlement Service: http://localhost:8000"
echo "  - Event Relayer: Running in background"
echo "  - Pub/Sub Emulator: localhost:8085"
echo "  - PostgreSQL: localhost:5432"
echo ""
echo -e "${BLUE}📋${NC} Useful commands:"
echo "  View relayer logs: docker compose logs -f event-relayer"
echo "  Stop relayer: docker compose stop event-relayer"
echo "  Restart relayer: docker compose restart event-relayer"
echo "  Test settlement service: curl http://localhost:8000/health"
echo ""
echo -e "${YELLOW}⚠${NC} Note: The relayer will start monitoring from block 0."
echo "    If you want to test with existing events, create some escrows first!"
echo ""
echo "To create a test escrow:"
echo "  cast send $ESCROW_FACTORY \\"
echo "    \"createEscrow(address,uint256,uint256,uint256)\" \\"
echo "    0x70997970C51812dc3A010C7d01b50e0d17dc79C8 \\"
echo "    \$(cast --to-wei 0.01) \\"
echo "    3600 \\"
echo "    2 \\"
echo "    --rpc-url http://localhost:8545 \\"
echo "    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \\"
echo "    --value \$(cast --to-wei 0.01)"
