#!/bin/bash
# Complete startup script for local testing environment

set -e

echo "════════════════════════════════════════════════════════════"
echo "  FUSION PRIME - LOCAL TESTING ENVIRONMENT SETUP"
echo "════════════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Detect Docker Compose command (V1 vs V2)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo -e "${RED}❌ Error: Docker Compose not found${NC}"
    echo ""
    echo "Please install Docker Compose:"
    echo "  - Docker Desktop: https://docs.docker.com/desktop/"
    echo "  - Docker Engine + Compose plugin: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Using: $DOCKER_COMPOSE${NC}"
echo ""

# Step 1: Start infrastructure services
echo -e "${BLUE}Step 1: Starting Infrastructure Services${NC}"
echo "──────────────────────────────────────────────────────────"
$DOCKER_COMPOSE up -d postgres pubsub-emulator anvil redis
echo ""

# Step 2: Wait for services to be healthy
echo -e "${BLUE}Step 2: Waiting for Infrastructure to be Ready${NC}"
echo "──────────────────────────────────────────────────────────"
echo "⏳ Waiting for PostgreSQL..."
until $DOCKER_COMPOSE exec -T postgres pg_isready -U fusion_prime > /dev/null 2>&1; do
    sleep 1
done
echo -e "${GREEN}✅ PostgreSQL ready${NC}"

echo "⏳ Waiting for Pub/Sub emulator..."
until curl -s http://localhost:8085 > /dev/null 2>&1; do
    sleep 1
done
echo -e "${GREEN}✅ Pub/Sub emulator ready${NC}"

echo "⏳ Waiting for Anvil..."
until cast client --rpc-url http://localhost:8545 > /dev/null 2>&1; do
    sleep 1
done
echo -e "${GREEN}✅ Anvil ready${NC}"
echo ""

# Step 3: Initialize Pub/Sub topics and subscriptions
echo -e "${BLUE}Step 3: Initializing Pub/Sub${NC}"
echo "──────────────────────────────────────────────────────────"
export PUBSUB_EMULATOR_HOST=localhost:8085
export GCP_PROJECT=fusion-prime-local

if command -v python3 &> /dev/null; then
    python3 scripts/setup/init_local_pubsub.py
else
    bash scripts/setup/init_local_pubsub.sh
fi
echo ""

# Step 4: Database Migration Status
echo -e "${BLUE}Step 4: Database Migration Status${NC}"
echo "──────────────────────────────────────────────────────────"

# Check if database is accessible
if docker compose exec -T postgres pg_isready -U fusion_prime > /dev/null 2>&1; then
    echo "✅ PostgreSQL is ready"

    # Check if tables exist
    TABLE_COUNT=$(docker compose exec -T postgres psql -U fusion_prime -d fusion_prime -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' \n' || echo "0")

    if [ "$TABLE_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✅ Database tables already exist ($TABLE_COUNT tables)${NC}"
        echo "   Migrations will be handled by the settlement service on startup"
    else
        echo -e "${YELLOW}⚠️  No tables found. Migrations will run on service startup.${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  PostgreSQL not ready. Migrations will run on service startup.${NC}"
fi

echo ""

# Step 5: Deploy smart contracts to Anvil
echo -e "${BLUE}Step 5: Deploying Smart Contracts to Anvil${NC}"
echo "──────────────────────────────────────────────────────────"

# Set up environment for deployment
export PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
export CHAIN_NAME=local
export CHAIN_ID=31337

# Try using the new configuration-based deployment
if [ -f "contracts/scripts/deploy_with_config.py" ]; then
    echo "Using configuration-based deployment..."
    python3 contracts/scripts/deploy_with_config.py local http://localhost:8545
    DEPLOY_SUCCESS=$?
else
    echo "Falling back to direct Foundry deployment..."
    cd contracts

    if [ -f "script/DeployMultichain.s.sol" ]; then
        echo "Deploying EscrowFactory..."

        # Deploy using Foundry
        DEPLOY_OUTPUT=$(forge script script/DeployMultichain.s.sol:DeployMultichain \
            --rpc-url http://localhost:8545 \
            --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
            --broadcast \
            --legacy \
            2>&1)

        echo "$DEPLOY_OUTPUT"

        # Extract contract address from Foundry output
        FACTORY_ADDRESS=$(echo "$DEPLOY_OUTPUT" | grep -oP 'Factory deployed:\s*\K0x[a-fA-F0-9]{40}' | head -1)

        if [ -z "$FACTORY_ADDRESS" ]; then
            # Try alternative extraction from JSON artifact
            if [ -f "deployments/31337-local.json" ]; then
                FACTORY_ADDRESS=$(cat deployments/31337-local.json | grep -oP '"escrowFactory":"?\K0x[a-fA-F0-9]{40}' | head -1)
            elif [ -f "deployments/31337-unknown.json" ]; then
                FACTORY_ADDRESS=$(cat deployments/31337-unknown.json | grep -oP '"escrowFactory":"?\K0x[a-fA-F0-9]{40}' | head -1)
            fi
        fi

        if [ -n "$FACTORY_ADDRESS" ]; then
            echo -e "${GREEN}✅ EscrowFactory deployed at: $FACTORY_ADDRESS${NC}"
            DEPLOY_SUCCESS=0
        else
            echo -e "${YELLOW}⚠️  Could not extract factory address. You may need to set it manually.${NC}"
            DEPLOY_SUCCESS=1
        fi
    else
        echo -e "${YELLOW}⚠️  Deploy script not found. Skipping contract deployment.${NC}"
        DEPLOY_SUCCESS=1
    fi

    cd "$PROJECT_ROOT"
fi

# Update .env.local with factory address if deployment succeeded
if [ $DEPLOY_SUCCESS -eq 0 ] && [ -n "$FACTORY_ADDRESS" ]; then
    echo -e "${GREEN}✅ EscrowFactory deployed at: $FACTORY_ADDRESS${NC}"

    # Update .env.local
    if grep -q "ESCROW_FACTORY_ADDRESS=" .env.local; then
        sed -i "s/ESCROW_FACTORY_ADDRESS=.*/ESCROW_FACTORY_ADDRESS=$FACTORY_ADDRESS/" .env.local
    else
        echo "ESCROW_FACTORY_ADDRESS=$FACTORY_ADDRESS" >> .env.local
    fi

    # Export for docker-compose
    export ESCROW_FACTORY_ADDRESS="$FACTORY_ADDRESS"
    echo "$FACTORY_ADDRESS" > .factory_address

    # Also export ABI path
    if [ -f "contracts/abi/EscrowFactory.json" ]; then
        echo "ESCROW_FACTORY_ABI_PATH=contracts/abi/EscrowFactory.json" >> .env.local
    fi
fi

echo ""

# Step 6: Start application services
echo -e "${BLUE}Step 6: Starting Application Services${NC}"
echo "──────────────────────────────────────────────────────────"
$DOCKER_COMPOSE up -d settlement-service risk-engine-service compliance-service event-relayer
echo ""

# Step 7: Wait for services to be healthy
echo -e "${BLUE}Step 7: Waiting for Services to be Ready${NC}"
echo "──────────────────────────────────────────────────────────"
echo "⏳ Waiting for Settlement service..."
until curl -s http://localhost:8000/health > /dev/null 2>&1; do
    sleep 1
done
echo -e "${GREEN}✅ Settlement service ready${NC}"

echo "⏳ Waiting for Risk Engine..."
until curl -s http://localhost:8001/health/ > /dev/null 2>&1; do
    sleep 1
done
echo -e "${GREEN}✅ Risk Engine ready${NC}"

echo "⏳ Waiting for Compliance service..."
until curl -s http://localhost:8002/health/ > /dev/null 2>&1; do
    sleep 1
done
echo -e "${GREEN}✅ Compliance service ready${NC}"

echo "⏳ Waiting for Relayer (5s grace period)..."
sleep 5
echo -e "${GREEN}✅ Relayer started${NC}"
echo ""

# Final summary
echo "════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ LOCAL TESTING ENVIRONMENT READY!${NC}"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "🌐 Services:"
echo "   - Anvil (Blockchain):      http://localhost:8545"
echo "   - PostgreSQL:              localhost:5432"
echo "   - Pub/Sub Emulator:        localhost:8085"
echo "   - Settlement Service:      http://localhost:8000"
echo "   - Risk Engine:             http://localhost:8001"
echo "   - Compliance Service:      http://localhost:8002"
echo ""
echo "📋 Next Steps:"
echo "   1. Source environment variables:"
echo "      source .env.local"
echo ""
echo "   2. Run integration tests:"
echo "      export TEST_ENVIRONMENT=local"
echo "      pytest tests/test_escrow_creation_workflow.py -v"
echo ""
echo "   3. View logs:"
echo "      $DOCKER_COMPOSE logs -f event-relayer"
echo "      $DOCKER_COMPOSE logs -f settlement-service"
echo ""
echo "   4. Stop environment:"
echo "      $DOCKER_COMPOSE down"
echo ""

if [ -n "$FACTORY_ADDRESS" ]; then
    echo "🔑 Contract Addresses:"
    echo "   EscrowFactory: $FACTORY_ADDRESS"
    echo ""
fi

echo "📚 Documentation:"
echo "   - tests/TESTING_GAPS.md"
echo "   - tests/TRUE_E2E_IMPLEMENTATION.md"
echo "   - tests/MISSING_FEATURES_IMPLEMENTED.md"
echo ""
echo "Happy Testing! 🚀"
