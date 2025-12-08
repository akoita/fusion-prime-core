# Cross-Chain Bridge Architecture

## Overview

This document explains how the bridge abstraction layer enables seamless interoperability between Axelar GMP and Chainlink CCIP.

---

## 🏗️ Architecture Layers

### 1. **Unified Interface Layer** (`IBridgeAdapter`)

**Purpose**: Single interface that all bridge protocols implement

```solidity
interface IBridgeAdapter {
    function sendMessage(...) external payable returns (bytes32);
    function estimateGas(...) external view returns (uint256);
    function isChainSupported(...) external view returns (bool);
    // ...
}
```

**Why it works**: Both Axelar and CCIP implement the same methods, even though their internals differ.

---

### 2. **Protocol Adapters** (AxelarAdapter, CCIPAdapter)

**Purpose**: Convert protocol-specific details to unified format

#### **AxelarAdapter** Implementation:

```solidity
contract AxelarAdapter is IBridgeAdapter {
    IAxelarGateway public gateway;      // Axelar-specific
    IAxelarGasService public gasService; // Axelar-specific

    function sendMessage(...) external payable {
        // 1. Use Axelar's Gateway.callContract()
        gateway.callContract(destinationChain, destinationAddress, payload);

        // 2. Pay gas via GasService
        gasService.payNativeGasForContractCall{value: msg.value}(...);
    }
}
```

**Key Points**:
- Uses `IAxelarGateway` and `IAxelarGasService` (Axelar-specific)
- Accepts string addresses (Axelar format)
- Uses string chain names ("ethereum", "polygon")

---

#### **CCIPAdapter** Implementation:

```solidity
contract CCIPAdapter is IBridgeAdapter {
    IRouterClient public router; // CCIP-specific

    function sendMessage(...) external payable {
        // 1. Convert string address to address type
        address destination = toAddress(destinationAddress);

        // 2. Convert string chain name to uint64 selector
        uint64 selector = chainNameToSelector[destinationChain];

        // 3. Encode receiver + calldata (CCIP format)
        bytes memory receiverAndCalldata = abi.encodePacked(destination, payload);

        // 4. Send via CCIP Router
        router.send(selector, receiverAndCalldata);
    }
}
```

**Key Points**:
- Uses `IRouterClient` (CCIP-specific)
- Converts string address → address type
- Converts string chain name → uint64 chain selector
- Encodes message as `receiver + calldata` (CCIP requirement)

---

### 3. **Bridge Manager** (Orchestration Layer)

**Purpose**: Routes messages to the right adapter based on chain preferences

```solidity
contract BridgeManager {
    mapping(string => IBridgeAdapter) public adapters; // protocol => adapter
    mapping(string => string) public preferredProtocol; // chain => protocol

    function sendMessage(...) external payable returns (bytes32) {
        // 1. Get preferred protocol for this chain
        string memory protocol = preferredProtocol[destinationChain];

        // 2. If no preference, find any adapter that supports the chain
        if (bytes(protocol).length == 0) {
            protocol = _findSupportedAdapter(destinationChain);
        }

        // 3. Route to the adapter
        IBridgeAdapter adapter = adapters[protocol];
        return adapter.sendMessage(...);
    }
}
```

**Benefits**:
- ✅ Single entry point for all cross-chain messages
- ✅ Protocol-agnostic (vault doesn't know which protocol is used)
- ✅ Chain-specific preferences (e.g., "Use CCIP for Polygon, Axelar for Ethereum")
- ✅ Automatic fallback if preferred protocol unavailable

---

## 🔄 Complete Message Flow

```
┌─────────────────────────────────────┐
│   CrossChainVault                   │
│   Need to send collateral update     │
└────────────┬────────────────────────┘
             │
             │ bridgeManager.sendMessage(
             │   "polygon",              ← Chain name (same for both)
             │   "0x...",                ← Address (string format)
             │   payload                 ← Message data
             │ )
             ▼
┌─────────────────────────────────────┐
│   BridgeManager                     │
│   Checks: preferredProtocol["polygon"]│
│   Result: "ccip"                     │
└────────────┬────────────────────────┘
             │
             │ adapters["ccip"].sendMessage(...)
             ▼
┌─────────────────────────────────────┐
│   CCIPAdapter                       │
│   1. Convert: "polygon" → selector  │
│   2. Convert: "0x..." → address     │
│   3. Encode: receiver + calldata    │
│   4. Call: router.send(...)          │
└────────────┬────────────────────────┘
             │
             ▼
      Chainlink CCIP Router
             │
             ▼
      Polygon Chain
```

---

## 🔧 How Differences Are Handled

### **Address Format**

| Protocol | Format | Solution |
|----------|--------|----------|
| **Axelar** | `string "0x123..."` | Used directly |
| **CCIP** | `address(0x123...)` | CCIPAdapter converts string → address |

**Implementation**:
```solidity
// CCIPAdapter handles conversion
function sendMessage(..., string memory destinationAddress, ...) {
    address destination = toAddress(destinationAddress); // Convert
    // Use address type with CCIP Router
}
```

---

### **Chain Identifiers**

| Protocol | Format | Solution |
|----------|--------|----------|
| **Axelar** | `string "polygon"` | Used directly |
| **CCIP** | `uint64 4014682061` | CCIPAdapter maintains mapping |

**Implementation**:
```solidity
// CCIPAdapter constructor
constructor(..., uint64[] memory selectors, string[] memory names) {
    for (uint i = 0; i < selectors.length; i++) {
        chainNameToSelector[names[i]] = selectors[i]; // Map name → selector
        chainSelectorToName[selectors[i]] = names[i];  // Map selector → name
    }
}
```

---

### **Gas Payment**

| Protocol | Method | Solution |
|----------|--------|----------|
| **Axelar** | Separate call to `GasService.payNativeGasForContractCall()` | AxelarAdapter calls it before gateway |
| **CCIP** | Included in `router.send()` value | CCIPAdapter forwards msg.value |

**Implementation**:
```solidity
// AxelarAdapter
gasService.payNativeGasForContractCall{value: msg.value}(...);
gateway.callContract(...);

// CCIPAdapter
router.send{value: msg.value}(...); // Gas included
```

---

### **Message Encoding**

| Protocol | Format | Solution |
|----------|--------|----------|
| **Axelar** | Raw payload bytes | Used directly |
| **CCIP** | `receiver + calldata` | CCIPAdapter encodes |

**Implementation**:
```solidity
// CCIPAdapter
bytes memory receiverAndCalldata = abi.encodePacked(destination, payload);
router.send(selector, receiverAndCalldata);
```

---

## 💡 Key Design Principles

### 1. **Abstraction Through Interface**

- CrossChainVault doesn't know about Axelar or CCIP specifics
- Only knows about `IBridgeAdapter` interface
- Easy to add new protocols (Wormhole, LayerZero, etc.)

### 2. **Adapter Pattern**

- Each adapter encapsulates protocol-specific logic
- Handles conversions and format differences
- Isolates complexity from vault contract

### 3. **Manager Orchestration**

- Single point of control
- Flexible routing (preferences + fallback)
- Protocol selection transparent to users

### 4. **Unified Interface Benefits**

- **For Developers**: Same API regardless of protocol
- **For Users**: Protocol choice is transparent
- **For Operations**: Easy to switch protocols or use multiple

---

## 🚀 Adding a New Bridge Protocol

1. **Implement IBridgeAdapter**:
   ```solidity
   contract WormholeAdapter is IBridgeAdapter {
       // Implement all interface methods
   }
   ```

2. **Register with BridgeManager**:
   ```solidity
   bridgeManager.registerAdapter(wormholeAdapter);
   ```

3. **Set Preferences (Optional)**:
   ```solidity
   bridgeManager.setPreferredProtocol("arbitrum", "wormhole");
   ```

4. **Done!** CrossChainVault automatically supports it.

---

## 📊 Current Status

✅ **Implemented**:
- IBridgeAdapter interface
- AxelarAdapter
- CCIPAdapter
- BridgeManager

⏳ **In Progress**:
- Update CrossChainVault to use BridgeManager
- Deployment scripts with adapter initialization

---

## 🔗 Integration Example

```solidity
// Deployment script
BridgeManager manager = new BridgeManager();

// Deploy adapters
AxelarAdapter axelar = new AxelarAdapter(gateway, gasService, chains);
CCIPAdapter ccip = new CCIPAdapter(router, selectors, chainNames);

// Register adapters
manager.registerAdapter(axelar);
manager.registerAdapter(ccip);

// Set preferences
manager.setPreferredProtocol("polygon", "ccip");
manager.setPreferredProtocol("ethereum", "axelar");

// Deploy vault with manager
CrossChainVault vault = new CrossChainVault(manager, chainName, chains);
```
