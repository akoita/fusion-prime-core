#!/bin/bash

# TEMPORARY DEV TOOL - Withdraw from all known vault deployments
# This script scans broadcast history and withdraws from all vaults
#
# WARNING: For TESTNET DEVELOPMENT ONLY
# Remove before mainnet deployment
#
# Usage:
#   ./script/WithdrawFromAllVaults.sh sepolia
#   ./script/WithdrawFromAllVaults.sh amoy

set -e

CHAIN=$1

if [ -z "$CHAIN" ]; then
    echo "Usage: $0 <chain>"
    echo "  chain: sepolia or amoy"
    exit 1
fi

# Set RPC URL and chain ID based on chain
if [ "$CHAIN" = "sepolia" ]; then
    RPC_URL="https://sepolia.infura.io/v3/6c474ab8fd5f48b294e1a082adc2c826"
    CHAIN_ID="11155111"
    LEGACY_FLAG=""
elif [ "$CHAIN" = "amoy" ]; then
    RPC_URL="https://polygon-amoy.infura.io/v3/6c474ab8fd5f48b294e1a082adc2c826"
    CHAIN_ID="80002"
    LEGACY_FLAG="--legacy"
else
    echo "Unknown chain: $CHAIN"
    echo "Supported chains: sepolia, amoy"
    exit 1
fi

echo "==================================="
echo "Emergency Withdrawal from All Vaults"
echo "==================================="
echo "Chain: $CHAIN"
echo "Chain ID: $CHAIN_ID"
echo ""

# Known vault addresses (add more as you deploy)
VAULTS=(
    # V23 Vaults
    "0x397c9aFDBB18803931154bbB6F9854fcbdaEeCff" # Sepolia V23
    "0xf0dba0090aaAEAe37dBe9Ce1c3a117b766b8A31d" # Amoy V23

    # V24 Vaults
    "0x3d0be24dDa36816769819f899d45f01a45979e8B" # Sepolia V24
    "0x4B5e551288713992945c6E96b0C9A106d0DD1115" # Amoy V24

    # V25 Vaults
    "0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312" # Sepolia V25
    "0xbafd9d789f96d18cedd057899a4ba3273c9f6d0e" # Amoy V25
)

# Filter vaults by chain (simple heuristic: Sepolia has more 0x4, 0x3, Amoy has more 0xb, 0xf)
# In practice, you'd maintain separate lists or check on-chain
echo "Attempting withdrawal from known vaults..."
echo ""

for VAULT in "${VAULTS[@]}"; do
    echo "-----------------------------------"
    echo "Vault: $VAULT"

    # Try to withdraw (will fail gracefully if no funds or wrong chain)
    forge script script/EmergencyWithdrawAll.s.sol:EmergencyWithdrawAll \
        --rpc-url "$RPC_URL" \
        --broadcast $LEGACY_FLAG \
        --sig "run(address)" "$VAULT" || echo "Skipped (no funds or error)"

    echo ""
done

echo "==================================="
echo "Withdrawal sweep complete!"
echo "==================================="
echo ""
echo "Note: Some vaults may have been skipped if:"
echo "  - They are on a different chain"
echo "  - You have no deposits in them"
echo "  - The vault version is incompatible"
