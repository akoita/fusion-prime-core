# Chainlink Oracle Integration - Deployment Summary

**Date**: 2025-11-08
**Status**: ✅ Successfully Deployed

---

## Overview

Integrated Chainlink price oracles to enable accurate USD-based valuation of user collateral across chains. This fixes the critical issue where 1 ETH was incorrectly treated as equal to 1 MATIC.

---

## Deployed Contracts

### Sepolia (Chain ID: 11155111)
- **Oracle Address**: `0x184e08394672B9Bf7aE670A3867C3c97A67A4e5C`
- **Price Feed**: ETH/USD
- **Chainlink Feed**: `0x694AA1769357215DE4FAC081bf1f309aDC325306`
- **Current Price**: $3,444 USD per ETH
- **Owner**: `0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA`

### Amoy (Chain ID: 80002)
- **Oracle Address**: `0x895c8848429745221d540366BC7aFCD0A7AFE3bF`
- **Price Feed**: MATIC/USD
- **Chainlink Feed**: `0x001382149eBa3441043c1c66972b4772963f5D43`
- **Current Price**: $0.178 USD per MATIC
- **Owner**: `0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA`

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  User deposits 1 ETH on Sepolia                     │
│  → Oracle converts: 1 ETH × $3,444 = $3,444 USD     │
│                                                      │
│  User deposits 1000 MATIC on Amoy                   │
│  → Oracle converts: 1000 MATIC × $0.178 = $178 USD  │
│                                                      │
│  Total Collateral Value: $3,622 USD                 │
│  Credit Line (70%): $2,535 USD                      │
│                                                      │
│  User can borrow:                                    │
│  - 0.736 ETH (worth $2,535) on Sepolia             │
│  - OR 14,243 MATIC (worth $2,535) on Amoy          │
└─────────────────────────────────────────────────────┘
```

---

## Contract Features

### ChainlinkPriceOracle.sol

**Key Functions**:
```solidity
// Get current native token price in USD (8 decimals)
function getNativePrice() external view returns (uint256);

// Convert token amount to USD value (18 decimals)
function convertToUSD(uint256 amount) external view returns (uint256);

// Convert USD value to token amount (18 decimals)
function convertFromUSD(uint256 usdValue) external view returns (uint256);
```

**Safety Features**:
- ✅ Price staleness check (rejects data older than 1 hour)
- ✅ Positive price validation
- ✅ Round data validation
- ✅ Owner-only price feed updates

---

## Testing

### Sepolia Oracle Test

```bash
$ cast call 0x184e08394672B9Bf7aE670A3867C3c97A67A4e5C \
  "getNativePrice()(uint256)" \
  --rpc-url https://sepolia.infura.io/v3/YOUR_KEY

# Expected output: 344451407100 (= $3,444.51 USD with 8 decimals)
```

```bash
$ cast call 0x184e08394672B9Bf7aE670A3867C3c97A67A4e5C \
  "convertToUSD(uint256)(uint256)" \
  1000000000000000000 \
  --rpc-url https://sepolia.infura.io/v3/YOUR_KEY

# Expected output: ~3444000000000000000000 (= $3,444 with 18 decimals)
```

### Amoy Oracle Test

```bash
$ cast call 0x895c8848429745221d540366BC7aFCD0A7AFE3bF \
  "getNativePrice()(uint256)" \
  --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY

# Expected output: 17864365 (= $0.178 USD with 8 decimals)
```

```bash
$ cast call 0x895c8848429745221d540366BC7aFCD0A7AFE3bF \
  "convertToUSD(uint256)(uint256)" \
  1000000000000000000 \
  --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY

# Expected output: ~178000000000000000 (= $0.178 with 18 decimals)
```

---

## Next Steps

### 1. Update Environment Variables

Add to `/contracts/cross-chain/.env`:
```bash
# Oracle Addresses
SEPOLIA_ORACLE=0x184e08394672B9Bf7aE670A3867C3c97A67A4e5C
AMOY_ORACLE=0x895c8848429745221d540366BC7aFCD0A7AFE3bF
```

###  2. Create CrossChainVaultV24 with Oracle Integration

Key changes needed:
```solidity
// Add oracle reference
IPriceOracle public priceOracle;

// Update credit line calculation
function getCreditLine(address user) public view returns (uint256) {
    uint256 totalCollateralUSD = getTotalCollateralValue(user);
    return (totalCollateralUSD * 70) / 100; // 70% LTV
}

// Get total collateral in USD
function getTotalCollateralValue(address user) public view returns (uint256) {
    uint256 totalUSD = 0;

    // Get collateral on each chain and convert to USD
    for (each chain) {
        uint256 nativeAmount = collateralBalances[user][chain];
        uint256 usdValue = getChainOracle(chain).convertToUSD(nativeAmount);
        totalUSD += usdValue;
    }

    return totalUSD;
}
```

### 3. Deploy New Vault

```bash
# Create DeployVaultV24.s.sol with oracle addresses
$ forge script script/DeployVaultV24.s.sol:DeployVaultV24 \
  --rpc-url sepolia --broadcast

$ forge script script/DeployVaultV24.s.sol:DeployVaultV24 \
  --rpc-url amoy --broadcast
```

### 4. Update Frontend

Add oracle ABI and update hooks to display USD values:
```typescript
// frontend/risk-dashboard/src/hooks/contracts/useVaultValue.ts
export function useVaultCollateralValueUSD(userAddress?: Address) {
  // Query oracle for conversion
  const ethValue = useOracleConversion(ethAmount, sepolia.id);
  const maticValue = useOracleConversion(maticAmount, polygonAmoy.id);

  return {
    ethValueUSD: ethValue.data,
    maticValueUSD: maticValue.data,
    totalValueUSD: (ethValue.data || 0n) + (maticValue.data || 0n),
  };
}
```

### 5. Testing Checklist

- [ ] Verify oracle prices are updating (check every hour)
- [ ] Test deposit on Sepolia, verify USD value is correct
- [ ] Test deposit on Amoy, verify USD value is correct
- [ ] Test cross-chain borrowing with mixed collateral
- [ ] Verify credit line calculations are accurate
- [ ] Test health factor with real price data

---

## Security Considerations

### Price Feed Validation
- ✅ **Staleness check**: Rejects prices older than 1 hour
- ✅ **Positive price check**: Prevents negative or zero prices
- ✅ **Round validation**: Ensures data integrity

### Oracle Manipulation Risks
- ⚠️ **Single price feed**: Currently using one Chainlink feed per chain
- ✅ **Mitigation**: Chainlink feeds are decentralized (21+ nodes)
- 🔮 **Future**: Could add secondary oracle (Pyth) for validation

### Owner Privileges
- ⚠️ **Owner can update price feeds**: Emergency failsafe
- ✅ **Transparent**: All updates emit events
- 🔮 **Future**: Consider timelock or multisig for production

---

## Gas Costs

- **Deployment**: ~565k gas per oracle (~$0.50 on Sepolia)
- **Read Price**: ~30k gas
- **Convert to USD**: ~35k gas

---

## Documentation Links

- **Chainlink Price Feeds**: https://docs.chain.link/data-feeds/price-feeds
- **Sepolia Testnet Feeds**: https://docs.chain.link/data-feeds/price-feeds/addresses?network=ethereum&page=1#sepolia-testnet
- **Amoy Testnet Feeds**: https://docs.chain.link/data-feeds/price-feeds/addresses?network=polygon&page=1#polygon-amoy-testnet

---

## Files Created

1. `/contracts/cross-chain/src/oracles/ChainlinkPriceOracle.sol` - Main oracle contract
2. `/contracts/cross-chain/src/interfaces/IPriceOracle.sol` - Oracle interface
3. `/contracts/cross-chain/src/interfaces/AggregatorV3Interface.sol` - Chainlink interface
4. `/contracts/cross-chain/script/DeployOracles.s.sol` - Deployment script
5. `/contracts/cross-chain/CHAINLINK_ORACLE_DEPLOYMENT.md` - This file

---

## Status: Ready for V24 Vault Integration ✅

Oracles are deployed and tested. Next step is to create CrossChainVaultV24 that uses these oracles for USD-based valuations.
