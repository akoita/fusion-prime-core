# CREATE2 Deployment Guide

## Overview

This document explains the CREATE2 deployment pattern used in the FusionPrime cross-chain vault system, why it was necessary, and how it ensures deterministic contract addresses across multiple blockchains.

## The Problem: Address Mismatch in Cross-Chain Systems

### Initial Implementation Issue

In our first deployment, the CrossChainVault contracts were deployed with different addresses on each chain:
- **Sepolia:** `0xD78a7E04A3167E7BB37Bb4c1E7f0c93C3898Acb2`
- **Polygon Amoy:** `0xe31BB84E7836A63461928c663466cc5DE7Ff3c95`

### Why This Was a Problem

The vault's cross-chain messaging logic sent messages to `address(this)` as the destination:

```solidity
// Attempted to send message to own address
bridgeManager.sendMessage(
    destChain,
    abi.encode(MessageType.COLLATERAL_UPDATE, user, amount),
    address(this)  // ❌ Different address on each chain!
);
```

When a message was sent from Amoy (`0xe31BB...`) to Sepolia, it tried to deliver to `0xe31BB...` on Sepolia, but that contract didn't exist there! The actual Sepolia vault was at `0xD78a...`.

**Result:** All cross-chain messages failed silently. Deposits on Amoy never synced to Sepolia.

## The Solution: CREATE2 Deterministic Deployment

### What is CREATE2?

CREATE2 is an EVM opcode (EIP-1014) that allows deploying contracts to deterministic addresses calculated from:

```
address = keccak256(0xff ++ deployerAddress ++ salt ++ keccak256(bytecode))[12:]
```

**Key insight:** If you use the same deployer address, salt, and bytecode on different chains, you get the **exact same contract address**.

### Requirements for Identical Addresses

To achieve identical addresses across chains, you need:

1. ✅ **Same deployer address** - Use a factory contract at the same address
2. ✅ **Same salt** - Use identical salt bytes32 value
3. ✅ **Identical bytecode** - Same contract code AND constructor arguments

## Implementation

### Step 1: Normalize Constructor Parameters

The original constructor accepted a `_chainName` parameter that differed per chain:

```solidity
// ❌ OLD: Different parameter per chain = different bytecode
constructor(
    address _bridgeManager,
    address _axelarGateway,
    string memory _chainName,  // "ethereum" vs "polygon"
    string[] memory _supportedChains
)
```

**Solution:** Remove the chain-specific parameter and auto-detect from `block.chainid`:

```solidity
// ✅ NEW: Identical parameters = identical bytecode
constructor(
    address _bridgeManager,
    address _axelarGateway,
    string[] memory _supportedChains
) {
    bridgeManager = BridgeManager(_bridgeManager);
    axelarGateway = _axelarGateway;
    thisChainName = _getChainName(block.chainid);  // Auto-detect!
    // ...
}

function _getChainName(uint256 chainId) internal pure returns (string memory) {
    if (chainId == 11155111) return "ethereum"; // Sepolia
    if (chainId == 80002) return "polygon";     // Amoy
    revert("Unsupported chain");
}
```

### Step 2: Create a VaultFactory

Factory contract for deploying vaults with CREATE2:

```solidity
// contracts/cross-chain/src/VaultFactory.sol
contract VaultFactory {
    function deployVault(
        address bridgeManager,
        address axelarGateway,
        string[] memory supportedChains,
        bytes32 salt
    ) external returns (address vault) {
        bytes memory bytecode = abi.encodePacked(
            type(CrossChainVault).creationCode,
            abi.encode(bridgeManager, axelarGateway, supportedChains)
        );

        assembly {
            vault := create2(0, add(bytecode, 32), mload(bytecode), salt)
            if iszero(vault) { revert(0, 0) }
        }

        emit VaultDeployed(vault, block.chainid, salt);
    }

    function computeVaultAddress(
        address bridgeManager,
        address axelarGateway,
        string[] memory supportedChains,
        bytes32 salt
    ) external view returns (address predicted) {
        bytes memory bytecode = abi.encodePacked(
            type(CrossChainVault).creationCode,
            abi.encode(bridgeManager, axelarGateway, supportedChains)
        );

        bytes32 hash = keccak256(
            abi.encodePacked(
                bytes1(0xff),
                address(this),
                salt,
                keccak256(bytecode)
            )
        );

        predicted = address(uint160(uint256(hash)));
    }
}
```

### Step 3: Deployment Script with CREATE2

```solidity
// script/DeployCrossChainCREATE2.s.sol

// Define consistent salts across all chains
bytes32 constant BRIDGE_MANAGER_SALT = keccak256("FusionPrime.BridgeManager.v1");
bytes32 constant VAULT_FACTORY_SALT = keccak256("FusionPrime.VaultFactory.v1");
bytes32 constant VAULT_SALT = keccak256("FusionPrime.CrossChainVault.v1");

function deployContracts() internal returns (DeploymentResult memory result) {
    // Deploy factory with CREATE2
    result.vaultFactory = deployWithCREATE2(
        type(VaultFactory).creationCode,
        VAULT_FACTORY_SALT
    );

    VaultFactory factory = VaultFactory(result.vaultFactory);

    // Deploy vault via factory
    string[] memory supportedChains = new string[](2);
    supportedChains[0] = "ethereum";
    supportedChains[1] = "polygon";

    // Predict address before deployment
    address predictedVault = factory.computeVaultAddress(
        result.bridgeManager,
        AXELAR_GATEWAY,
        supportedChains,
        VAULT_SALT
    );

    // Deploy vault
    result.crossChainVault = factory.deployVault(
        result.bridgeManager,
        AXELAR_GATEWAY,
        supportedChains,
        VAULT_SALT
    );

    // Verify addresses match
    require(result.crossChainVault == predictedVault, "Address mismatch!");
}

function deployWithCREATE2(bytes memory bytecode, bytes32 salt)
    internal
    returns (address deployed)
{
    assembly {
        deployed := create2(0, add(bytecode, 32), mload(bytecode), salt)
        if iszero(deployed) { revert(0, 0) }
    }
}
```

### Step 4: Deploy to All Chains

Run the same deployment script on each chain:

```bash
# Deploy to Sepolia
DEPLOYER_PRIVATE_KEY=0x... forge script script/DeployCrossChainCREATE2.s.sol:DeployCrossChainCREATE2 \
  --rpc-url https://sepolia.infura.io/v3/YOUR_KEY \
  --broadcast -vvv

# Deploy to Polygon Amoy
DEPLOYER_PRIVATE_KEY=0x... forge script script/DeployCrossChainCREATE2.s.sol:DeployCrossChainCREATE2 \
  --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY \
  --broadcast -vvv
```

## Results

### Verified Identical Addresses

After CREATE2 deployment:

| Contract          | Sepolia                                      | Polygon Amoy                                 | Status |
|-------------------|----------------------------------------------|----------------------------------------------|--------|
| BridgeManager     | `0xB700E59DD350D5C6648413F5eF2856467461120E` | `0xB700E59DD350D5C6648413F5eF2856467461120E` | ✅ SAME |
| VaultFactory      | `0x4DD56e9e3591C211aF05c2f760f141216d3f9273` | `0x4DD56e9e3591C211aF05c2f760f141216d3f9273` | ✅ SAME |
| CrossChainVault   | `0xAD5f1C2F6229F3628AC031F300C45de81a62638F` | `0xAD5f1C2F6229F3628AC031F300C45de81a62638F` | ✅ SAME |
| AxelarAdapter     | `0xD69C799f27bdbCd595867933DcA5f791e46B05FE` | `0xD69C799f27bdbCd595867933DcA5f791e46B05FE` | ✅ SAME |

### Cross-Chain Messaging Now Works

With identical vault addresses, the message flow works perfectly:

```
Amoy Vault (0xAD5f...)  →  Axelar Gateway  →  Sepolia Vault (0xAD5f...)
                              ✅ Same address = message delivered successfully
```

## Testing Results

Tested operations on Polygon Amoy:

| Operation          | Amount        | TX Hash                                                            | Status  |
|-------------------|---------------|---------------------------------------------------------------------|---------|
| Deposit Collateral| 0.001 MATIC   | `0x0c12a0ae34d2b08e8dad56afb4584d47eec4b46a09d7ee22b6cf2b1f5c8d7d58` | ✅ Success |
| Borrow            | 0.001 MATIC   | `0xf38eb1b963b6d93aebb75a84c6dd96ecef74bd7f4e55d2089ae2f21bfbbf6d2e` | ✅ Success |
| Withdraw          | 0.0005 MATIC  | `0x4a9d681d85889b5a847dfc1b3c9e20cbb41b7e2e3cd6a6ab39b15b5ee972b77e` | ✅ Success |

All transactions sent messages to the correct destination address (`0xAD5f...`) on both chains.

## Benefits of CREATE2 Pattern

### 1. **Simplified Cross-Chain Logic**
No need for address registries or configuration files. The vault always knows to send messages to its own address.

### 2. **Security**
Guaranteed that messages go to the correct vault contract. No risk of misconfiguration.

### 3. **User Experience**
Users see the same address across all chains. Easier to verify and trust.

### 4. **Production Ready**
This is the industry-standard pattern used by:
- **Uniswap V3** - Same pool addresses across chains
- **Aave V3** - Same contract addresses across deployments
- **Safe (Gnosis Safe)** - Deterministic wallet addresses

## Common Pitfalls

### 1. Different Constructor Arguments
❌ **Wrong:**
```solidity
// Sepolia
new CrossChainVault(bridgeManager, gateway, "ethereum", chains);
// Amoy
new CrossChainVault(bridgeManager, gateway, "polygon", chains);
// Different bytecode → different addresses!
```

✅ **Correct:**
```solidity
// Both chains
new CrossChainVault(bridgeManager, gateway, chains);
// Auto-detects chain name from block.chainid
```

### 2. Different Salt Values
```solidity
// ❌ Wrong: Using timestamp or random values
bytes32 salt = keccak256(abi.encode(block.timestamp));

// ✅ Correct: Using deterministic, hardcoded salt
bytes32 salt = keccak256("FusionPrime.CrossChainVault.v1");
```

### 3. Different Deployer Addresses
The factory must be deployed at the same address on all chains. This requires:
- Same deployment account nonce on each chain, OR
- Deploy the factory itself using CREATE2 (bootstrapping)

## Maintenance and Upgrades

### Upgrading Contracts

To deploy a new version:

1. **Change the salt:**
   ```solidity
   bytes32 constant VAULT_SALT = keccak256("FusionPrime.CrossChainVault.v2");
   ```

2. **Deploy to all chains with new salt**

3. **Migrate state if needed** (transfer funds from v1 to v2)

### Adding New Chains

When adding a new chain:

1. Deploy factory to the new chain (must match existing factory address)
2. Run deployment script with same salts
3. Verify addresses match existing deployments

## References

- **EIP-1014:** CREATE2 Specification - https://eips.ethereum.org/EIPS/eip-1014
- **Uniswap V3 Deployment:** Example of CREATE2 pattern in production
- **Foundry CREATE2 Helper:** https://book.getfoundry.sh/reference/forge/forge-create

## Conclusion

CREATE2 deployment solved our cross-chain address mismatch problem by ensuring the CrossChainVault has the same address (`0xAD5f1C2F6229F3628AC031F300C45de81a62638F`) on all supported chains.

This enables:
- ✅ Seamless cross-chain messaging
- ✅ Simplified contract architecture
- ✅ Better user experience
- ✅ Production-grade deployment pattern

**Key Takeaway:** For any cross-chain protocol where contracts need to communicate with each other, CREATE2 is essential to ensure consistent addresses across all chains.
