#!/bin/bash

###############################################################################
# Automated Test Suite Runner with Relayer Sync
#
# This script automates the complete test workflow:
# 1. Syncs the relayer to a recent block using the admin endpoint
# 2. Waits for the relayer to catch up
# 3. Runs the complete test suite
#
# Usage:
#   bash tests/run_complete_tests_with_sync.sh [blocks_behind]
#
# Arguments:
#   blocks_behind (optional): Number of blocks behind current to start from
#                            Default: 5
#
# Example:
#   bash tests/run_complete_tests_with_sync.sh 10
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RELAYER_URL="https://escrow-event-relayer-service-ggats6pubq-uc.a.run.app"
BLOCKS_BEHIND=${1:-5}  # Default to 5 blocks behind
SYNC_WAIT_TIME=20      # Seconds to wait for relayer to sync

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Automated Test Suite with Relayer Sync               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Get current blockchain height
echo -e "${YELLOW}[1/4] Fetching current blockchain height...${NC}"
CURRENT_BLOCK=$(curl -s "${RELAYER_URL}/health" | python3 -c "import sys, json; print(json.load(sys.stdin)['current_block'])" 2>/dev/null)

if [ -z "$CURRENT_BLOCK" ]; then
    echo -e "${RED}❌ Failed to fetch current block from relayer${NC}"
    echo -e "${YELLOW}⚠️  Attempting to continue with tests anyway...${NC}"
    exec bash tests/run_dev_tests.sh complete
    exit $?
fi

echo -e "${GREEN}✅ Current blockchain height: $CURRENT_BLOCK${NC}"

# Step 2: Calculate and set start block
START_BLOCK=$((CURRENT_BLOCK - BLOCKS_BEHIND))
echo ""
echo -e "${YELLOW}[2/4] Setting relayer start block to $START_BLOCK ($BLOCKS_BEHIND blocks behind)...${NC}"

RESPONSE=$(curl -s -X POST "${RELAYER_URL}/admin/set-start-block" \
  -H "Content-Type: application/json" \
  -d "{\"start_block\": $START_BLOCK}" 2>/dev/null)

if [ -z "$RESPONSE" ]; then
    echo -e "${RED}❌ Failed to update relayer start block${NC}"
    echo -e "${YELLOW}⚠️  Attempting to continue with tests anyway...${NC}"
    exec bash tests/run_dev_tests.sh complete
    exit $?
fi

# Parse response
NEW_BLOCK=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['last_processed_block'])" 2>/dev/null)
BLOCKS_TO_SYNC=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['blocks_behind'])" 2>/dev/null)

echo -e "${GREEN}✅ Relayer updated successfully${NC}"
echo -e "   Last processed block: ${BLUE}$NEW_BLOCK${NC}"
echo -e "   Blocks to sync: ${BLUE}$BLOCKS_TO_SYNC${NC}"

# Step 3: Wait for relayer to sync
echo ""
echo -e "${YELLOW}[3/4] Waiting ${SYNC_WAIT_TIME}s for relayer to sync...${NC}"

for i in $(seq 1 $SYNC_WAIT_TIME); do
    echo -n "."
    sleep 1

    # Check sync status every 5 seconds
    if [ $((i % 5)) -eq 0 ]; then
        BEHIND=$(curl -s "${RELAYER_URL}/health" | python3 -c "import sys, json; print(json.load(sys.stdin)['blocks_behind'])" 2>/dev/null || echo "?")
        if [ "$BEHIND" = "0" ]; then
            echo ""
            echo -e "${GREEN}✅ Relayer fully synced! (0 blocks behind)${NC}"
            break
        fi
        echo -n " ($BEHIND blocks behind) "
    fi
done

echo ""

# Final sync check
FINAL_STATUS=$(curl -s "${RELAYER_URL}/health" | python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"{data['blocks_behind']} blocks behind, {data['events_processed']} events processed\")" 2>/dev/null)
echo -e "   Final status: ${BLUE}$FINAL_STATUS${NC}"

# Step 4: Run tests
echo ""
echo -e "${YELLOW}[4/4] Running complete test suite...${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# Execute the test suite
exec bash tests/run_dev_tests.sh complete
