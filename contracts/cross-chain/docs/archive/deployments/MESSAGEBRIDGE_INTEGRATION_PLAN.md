# MessageBridge Integration with CrossChainVault

## Overview

Switching from Axelar (unreliable testnet) to our own MessageBridge for full control and reliability.

## Why MessageBridge?

**Problems with Axelar**:
- ❌ Testnet relayers unreliable/offline
- ❌ 0.01 ETH insufficient
- ❌ 0.06 ETH insufficient
- ❌ 0.1 ETH still not processed after 10+ minutes
- ❌ No user experience acceptable

**Benefits of MessageBridge**:
- ✅ Full control over relayer
- ✅ No external gas fees (just transaction gas)
- ✅ Instant execution (1-2 block confirmation)
- ✅ Predictable costs
- ✅ Easy debugging and monitoring
- ✅ Can customize retry logic

## Architecture

### Current (V20 with Axelar)
```
CrossChainVault → AxelarAdapter → Axelar Gateway → ❌ FAILS
```

### New (V21 with MessageBridge)
```
CrossChainVault → MessageBridge → Our Relayer → ✅ WORKS
```

## Implementation Steps

### Phase 1: Deploy MessageBridge Infrastructure

1. **Deploy BridgeRegistry on Sepolia**
   ```bash
   cd contracts/bridge
   forge script script/DeployBridge.s.sol:DeployBridge \
     --rpc-url $SEPOLIA_RPC_URL \
     --broadcast --verify -vvvv
   ```

2. **Deploy BridgeRegistry on Amoy**
   ```bash
   forge script script/DeployBridge.s.sol:DeployBridge \
     --rpc-url $AMOY_RPC_URL \
     --broadcast --verify -vvvv
   ```

3. **Configure Network Pairs**
   - Register Sepolia (11155111) ↔ Amoy (80002) pair
   - Enable bidirectional messaging
   - Set min/max amounts (no limits for messages)

### Phase 2: Create MessageBridgeAdapter for Vault

Create `/home/koita/dev/web3/fusion-prime/contracts/cross-chain/src/adapters/MessageBridgeAdapter.sol`:

```solidity
// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {IBridgeAdapter} from "../interfaces/IBridgeAdapter.sol";

interface IMessageBridge {
    function sendMessage(
        uint64 destChainId,
        address recipient,
        bytes calldata payload
    ) external returns (bytes32 messageId);
}

contract MessageBridgeAdapter is IBridgeAdapter {
    IMessageBridge public immutable messageBridge;
    mapping(string => uint64) public chainNameToId;

    constructor(address _messageBridge, string[] memory _chainNames, uint64[] memory _chainIds) {
        messageBridge = IMessageBridge(_messageBridge);
        for (uint256 i = 0; i < _chainNames.length; i++) {
            chainNameToId[_chainNames[i]] = _chainIds[i];
        }
    }

    function sendMessage(
        string memory destinationChain,
        string memory destinationAddress,
        bytes memory payload,
        address /* gasToken - not used */
    ) external payable returns (bytes32 messageId) {
        uint64 destChainId = chainNameToId[destinationChain];
        require(destChainId != 0, "Unsupported chain");

        address dest = _parseAddress(destinationAddress);
        return messageBridge.sendMessage(destChainId, dest, payload);
    }

    function estimateGas(
        string memory /* destinationChain */,
        bytes memory /* payload */
    ) external pure returns (uint256) {
        // No gas fees for our own bridge - only transaction gas
        return 0;
    }

    function isChainSupported(string memory chainName) external view returns (bool) {
        return chainNameToId[chainName] != 0;
    }

    function _parseAddress(string memory addr) internal pure returns (address) {
        bytes memory tmp = bytes(addr);
        require(tmp.length == 42, "Invalid address");

        uint160 result = 0;
        for (uint256 i = 2; i < 42; i++) {
            result *= 16;
            uint8 b = uint8(tmp[i]);
            if (b >= 48 && b <= 57) result += b - 48;
            else if (b >= 65 && b <= 70) result += b - 55;
            else if (b >= 97 && b <= 102) result += b - 87;
        }
        return address(result);
    }
}
```

### Phase 3: Modify CrossChainVault to Receive Messages

Add to CrossChainVault.sol:

```solidity
/// @notice MessageBridge callback - called by our bridge relayer
/// @dev This is called by MessageBridge when a cross-chain message arrives
function handleBridgeMessage(
    uint64 sourceChainId,
    address sender,
    bytes calldata payload
) external {
    // Only MessageBridge can call this
    require(msg.sender == address(messageBridge), "Unauthorized");

    // Verify sender is trusted vault
    string memory sourceChain = _chainIdToName(sourceChainId);
    require(sender == trustedVaults[sourceChain], "Untrusted sender");

    // Process the message (same logic as _execute)
    _processMessage(sourceChain, _addressToString(sender), payload);
}
```

### Phase 4: Deploy V21 Vault with MessageBridge

1. **Deploy MessageBridgeAdapter on both chains**
2. **Deploy V21 CrossChainVault on Sepolia**
   - Constructor: Use MessageBridgeAdapter instead of AxelarAdapter
   - Remove MIN_GAS_AMOUNT requirement (no gas fees!)
3. **Deploy V21 CrossChainVault on Amoy**
4. **Configure trustedVaults bidirectionally**

### Phase 5: Set Up and Run Bridge Relayer

1. **Install relayer dependencies**:
   ```bash
   cd services/bridge-relayer
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure .env**:
   ```bash
   RELAYER_PRIVATE_KEY=<your_relayer_key>
   SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/...
   AMOY_RPC_URL=https://polygon-amoy.infura.io/v3/...
   SEPOLIA_MESSAGE_BRIDGE_ADDRESS=<deployed_address>
   AMOY_MESSAGE_BRIDGE_ADDRESS=<deployed_address>
   SEPOLIA_VAULT_ADDRESS=<v21_vault_address>
   AMOY_VAULT_ADDRESS=<v21_vault_address>
   ```

3. **Modify relayer to call vault's handleBridgeMessage()**:
   - When MessageSent event detected
   - Extract payload
   - Call `vault.handleBridgeMessage(sourceChainId, sender, payload)` on destination

4. **Start relayer**:
   ```bash
   uvicorn app.main:app --reload
   ```

## Cost Comparison

| Solution | Gas Fee | Transaction Gas | Total | Reliability |
|----------|---------|-----------------|-------|-------------|
| Axelar V20 | 0.01 ETH | ~0.002 ETH | ~0.012 ETH | ❌ FAILED |
| Axelar (attempt 2) | 0.06 ETH | ~0.002 ETH | ~0.062 ETH | ❌ FAILED |
| Axelar (attempt 3) | 0.1 ETH | ~0.002 ETH | ~0.102 ETH | ❌ FAILED |
| **MessageBridge** | **0 ETH** | **~0.002 ETH** | **~0.002 ETH** | **✅ WORKS** |

## Timeline

- **Phase 1** (Deploy Bridge): ~30 minutes
- **Phase 2** (Create Adapter): ~15 minutes
- **Phase 3** (Modify Vault): ~15 minutes
- **Phase 4** (Deploy V21): ~30 minutes
- **Phase 5** (Set up Relayer): ~20 minutes

**Total: ~2 hours**

## Next Steps

1. Deploy MessageBridge infrastructure
2. Create and test MessageBridgeAdapter
3. Update vault to receive bridge messages
4. Deploy V21
5. Run relayer locally
6. Test deposit → sync flow
7. Update frontend to use V21 addresses

## Risks & Mitigation

**Risk**: Relayer downtime = no cross-chain sync
**Mitigation**:
- Run relayer on GCP Cloud Run (auto-restart)
- Add monitoring and alerts
- Implement retry logic
- Have backup relayer ready

**Risk**: Relayer private key security
**Mitigation**:
- Use GCP Secret Manager
- Separate relayer wallet (not deployer)
- Monitor relayer balance

**Risk**: Message replay attacks
**Mitigation**:
- MessageBridge has nonce-based message IDs
- Vault tracks processedMessages
- Double-spend protection built-in
