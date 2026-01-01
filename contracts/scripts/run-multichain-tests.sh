#!/bin/bash
# Multi-Chain Local Testing Script
# Starts 3 Anvil instances and deploys contracts to each

set -e

PRIVATE_KEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

echo "🔗 Starting Multi-Chain Local Test Environment"
echo "================================================"

# Kill any existing Anvil instances
pkill -f "anvil" 2>/dev/null || true
sleep 2

# Start 3 Anvil instances in background
echo "🚀 Starting Anvil instances..."

anvil --port 31337 --chain-id 31337 --silent &
PID_A=$!
echo "   Chain A (31337): PID $PID_A"

anvil --port 31338 --chain-id 31338 --silent &
PID_B=$!
echo "   Chain B (31338): PID $PID_B"

anvil --port 31339 --chain-id 31339 --silent &
PID_C=$!
echo "   Chain C (31339): PID $PID_C"

# Wait for chains to start
sleep 3
echo "✅ All chains started"

# Deploy to each chain
echo ""
echo "📦 Deploying contracts..."

echo "   Deploying to Chain A..."
PRIVATE_KEY=$PRIVATE_KEY forge script script/DeployMultiChainLocal.s.sol:DeployMultiChainLocal \
  --rpc-url http://127.0.0.1:31337 \
  --broadcast --quiet

echo "   Deploying to Chain B..."
PRIVATE_KEY=$PRIVATE_KEY forge script script/DeployMultiChainLocal.s.sol:DeployMultiChainLocal \
  --rpc-url http://127.0.0.1:31338 \
  --broadcast --quiet

echo "   Deploying to Chain C..."
PRIVATE_KEY=$PRIVATE_KEY forge script script/DeployMultiChainLocal.s.sol:DeployMultiChainLocal \
  --rpc-url http://127.0.0.1:31339 \
  --broadcast --quiet

echo "✅ Contracts deployed to all chains"

# Run cross-chain tests
echo ""
echo "🧪 Running cross-chain tests..."
forge test --match-contract "AxelarAdapter|CCIPAdapter|BridgeManager|CrossChainVault" -vvv

echo ""
echo "✅ Multi-chain tests complete!"

# Cleanup
echo ""
echo "🧹 Cleaning up Anvil instances..."
kill $PID_A $PID_B $PID_C 2>/dev/null || true

echo "Done!"
