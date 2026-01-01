#!/bin/bash
# Mutation Testing Script for CrossChainVaultBase
# Tests your test suite quality by injecting bugs (mutations) and checking if tests catch them

set -e

echo "================================"
echo "Smart Contract Mutation Testing"
echo "================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

cd "$(dirname "$0")/.."

echo -e "\n${YELLOW}Option 1: Foundry Mutation (if available)${NC}"
echo "Run: forge mutate --match-contract CrossChainVaultBaseTest"
echo ""

echo -e "${YELLOW}Option 2: Manual Mutation Examples${NC}"
echo "The following mutations should be caught by your test suite:"
echo ""

# Define mutations
declare -a MUTATIONS=(
    "src/CrossChainVaultBase.sol|require(msg.value > 0|require(msg.value >= 0|Zero deposit check"
    "src/CrossChainVaultBase.sol|healthFactor < 100|healthFactor <= 100|Liquidation threshold"
    "src/CrossChainVaultBase.sol|amount > tc.borrowed ? tc.borrowed : amount|amount|Repay cap"
    "src/CrossChainVaultBase.sol|tc.borrowed += amount|tc.borrowed = amount|Borrow accumulation"
    "src/CrossChainVaultBase.sol|pos.collateral -= amount|pos.collateral += amount|Withdraw direction"
)

echo "Test these mutations manually by temporarily editing the source:"
echo ""

for mutation in "${MUTATIONS[@]}"; do
    IFS='|' read -r file find replace desc <<< "$mutation"
    echo -e "  ${GREEN}[$desc]${NC}"
    echo "    File: $file"
    echo "    Change: '$find' -> '$replace'"
    echo "    Expected: Tests should FAIL after this mutation"
    echo ""
done

echo -e "${YELLOW}Option 3: vertigo-rs (External Tool)${NC}"
echo "Install: cargo install vertigo"
echo "Run: vertigo run --campaign mutation ./src/CrossChainVaultBase.sol"
echo ""

echo -e "${YELLOW}Option 4: Gambit (Certora Mutation Tool)${NC}"
echo "pip install gambit"
echo "gambit mutate src/CrossChainVaultBase.sol"
echo ""

echo "================================"
echo "Mutation Score Interpretation:"
echo "================================"
echo "- Killed mutants: Test suite caught the bug ✓"
echo "- Survived mutants: Test suite missed the bug ✗"
echo "- Score = Killed / Total × 100%"
echo ""
echo "Target: > 80% mutation score"
