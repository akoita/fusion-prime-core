# CCIP Chain Selector Fix

## Problem
The CCIPAdapter was deployed with incorrect chain selectors:
- **Polygon Amoy**: Deployed with `12532609583862916517`
- **Correct value**: `16281711391670634445`
- **Arbitrum Sepolia**: Deployed with `5800955286103778722`
- **Correct value**: `3478487238524512106`

Source: https://docs.chain.link/ccip/directory/testnet

This caused the CCIP Router's `getFee()` function to revert because it didn't recognize the invalid chain selectors.

## Root Cause
The chain selectors in `contracts/script/DeployCrossChain.s.sol` were incorrect when the contracts were initially deployed to Sepolia.

## Workaround Applied
Since the BridgeManager contract doesn't allow updating adapters (no access control, and `registerAdapter` checks for existing registration), we switched to using Axelar instead:

```bash
# Transaction: 0x660269bd4baabc3022743854aba097d68f4462b0ea9ed32f4be4d166b82d373a
cast send 0xC96DA7e94E8407e0988bb60A1b23B9358Cd63A56 \
  "setPreferredProtocol(string,string)" \
  "polygon" "axelar" \
  --private-key $DEPLOYER_PRIVATE_KEY \
  --rpc-url https://ethereum-sepolia-rpc.publicnode.com
```

**Status**: ✅ Working
- Preferred protocol for "polygon" is now "axelar"
- Gas estimation working: Returns ~55200 wei
- Cross-chain transfers should now work via Axelar bridge

## Permanent Fix (For Future Deployments)
The deployment script has been updated with correct chain selectors in commit [TBD]:
- `CCIP_SELECTOR_AMOY = 16281711391670634445`
- `CCIP_SELECTOR_ARBITRUM = 3478487238524512106`

A fix script has also been created at `contracts/script/FixCCIPSelector.s.sol` to deploy a new CCIPAdapter with correct selectors, but it cannot be used until either:
1. The BridgeManager is upgraded with adapter update functionality
2. A new BridgeManager is deployed
3. The old CCIP adapter is somehow removed from the mapping

## Testing
After applying the workaround:
```bash
# Verify preferred protocol
cast call 0xC96DA7e94E8407e0988bb60A1b23B9358Cd63A56 \
  "preferredProtocol(string)(string)" \
  "polygon" \
  --rpc-url https://ethereum-sepolia-rpc.publicnode.com
# Returns: "axelar" ✅

# Test gas estimation
cast call 0xC96DA7e94E8407e0988bb60A1b23B9358Cd63A56 \
  "estimateGas(string,bytes)(uint256,string)" \
  "polygon" \
  "0x6efc2ecb7a021c2249ae2cf253a7f9fa37ad71ba00000000000000000000000000000000000000000000000000038d7ea4c68000" \
  --rpc-url https://ethereum-sepolia-rpc.publicnode.com
# Returns: 55200 [5.52e4] "axelar" ✅
```

## Contracts Affected
- **BridgeManager (Sepolia)**: `0xC96DA7e94E8407e0988bb60A1b23B9358Cd63A56`
- **CCIPAdapter (Sepolia)**: `0x9204E095e6d50Ff8f828e71F4C0849C5aEfe992c` (has wrong selectors, no longer used)
- **AxelarAdapter (Sepolia)**: `0x3C8e965aFF06DFcaE9f6cc778b38d72D54D1381d` (now preferred for polygon)

## Next Steps
For production deployment:
1. Use the corrected chain selectors in DeployCrossChain.s.sol
2. Consider adding access control to BridgeManager with adapter update functionality
3. Test both CCIP and Axelar bridges on testnet before mainnet deployment
