#!/bin/bash
#
# Backfill Wrapper Script for Escrow Indexer
# Makes it easier to run the backfill with common configurations
#

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}📦 Escrow Indexer Backfill Script${NC}"
echo ""

# Configuration
PROJECT_ID="${GCP_PROJECT:-fusion-prime}"
RPC_URL="${RPC_URL:-https://sepolia.infura.io/v3/YOUR_KEY}"
FACTORY_ADDRESS="${ESCROW_FACTORY_ADDRESS:-0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914}"

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${YELLOW}⚠️  DATABASE_URL not set${NC}"
    echo ""
    echo "Options:"
    echo "  1. Set DATABASE_URL manually:"
    echo "     export DATABASE_URL=postgresql://user:pass@host:5432/escrow_indexer"
    echo ""
    echo "  2. Get from Secret Manager:"
    read -p "Get DATABASE_URL from Secret Manager? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Fetching DATABASE_URL from Secret Manager..."
        export DATABASE_URL=$(gcloud secrets versions access latest \
            --secret=escrow-indexer-connection-string \
            --project=$PROJECT_ID 2>/dev/null || \
            gcloud secrets versions access latest \
            --secret=escrow-indexer-db-url \
            --project=$PROJECT_ID)

        if [ -z "$DATABASE_URL" ]; then
            echo -e "${RED}❌ Failed to fetch DATABASE_URL from Secret Manager${NC}"
            exit 1
        fi

        echo -e "${GREEN}✅ DATABASE_URL loaded from Secret Manager${NC}"
    else
        echo "Please set DATABASE_URL and run again"
        exit 1
    fi
fi

# Check if RPC_URL is default
if [[ "$RPC_URL" == *"YOUR_KEY"* ]]; then
    echo -e "${YELLOW}⚠️  RPC_URL contains placeholder${NC}"
    echo "Please set a valid RPC URL:"
    echo "  export RPC_URL=https://sepolia.infura.io/v3/YOUR_ACTUAL_KEY"
    echo "  Or: export RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY"
    exit 1
fi

# Show configuration
echo "Configuration:"
echo "  RPC URL: $RPC_URL"
echo "  Factory: $FACTORY_ADDRESS"
echo ""

# Parse arguments or prompt
FROM_BLOCK="${1:-}"
TO_BLOCK="${2:-latest}"
DRY_RUN="${3:-}"

if [ -z "$FROM_BLOCK" ]; then
    echo "Enter starting block number (or press Enter for 0):"
    read FROM_BLOCK
    FROM_BLOCK="${FROM_BLOCK:-0}"
fi

echo ""
echo "Backfill Parameters:"
echo "  From block: $FROM_BLOCK"
echo "  To block: $TO_BLOCK"
echo ""

# Ask for confirmation
if [ "$DRY_RUN" != "--dry-run" ]; then
    echo -e "${YELLOW}⚠️  This will index historical escrows into the database${NC}"
    read -p "Continue? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled"
        exit 0
    fi
fi

# Run backfill
echo ""
echo -e "${GREEN}🚀 Starting backfill...${NC}"
echo ""

cd "$(dirname "$0")/.."

python3 scripts/backfill.py \
    --rpc-url "$RPC_URL" \
    --factory-address "$FACTORY_ADDRESS" \
    --from-block "$FROM_BLOCK" \
    --to-block "$TO_BLOCK" \
    --batch-size 1000 \
    $DRY_RUN

echo ""
echo -e "${GREEN}✅ Backfill complete!${NC}"
echo ""
echo "Verify by querying the API:"
echo "  curl http://localhost:8080/api/v1/escrows/stats"
echo ""
