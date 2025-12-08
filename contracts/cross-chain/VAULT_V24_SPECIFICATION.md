# CrossChainVaultV24 Specification

**Version**: V24 with Chainlink Oracle Integration
**Status**: Ready to Implement
**Date**: 2025-11-08

---

## Key Changes from V23

### 1. **Oracle Integration** 🆕

```solidity
// Add price oracle mapping
mapping(string => IPriceOracle) public chainOracles;

// Oracle addresses
// Sepolia: 0x184e08394672B9Bf7aE670A3867C3c97A67A4e5C (ETH/USD)
// Amoy: 0x895c8848429745221d540366BC7aFCD0A7AFE3bF (MATIC/USD)
```

### 2. **USD-Based Valuations** 🆕

```solidity
/**
 * @notice Get total collateral value in USD for a user across ALL chains
 * @param user User address
 * @return totalValueUSD Total collateral value in USD (18 decimals)
 */
function getTotalCollateralValueUSD(address user) public view returns (uint256) {
    uint256 totalUSD = 0;

    for (uint256 i = 0; i < allSupportedChains.length; i++) {
        string memory chainName = allSupportedChains[i];
        uint256 nativeAmount = collateralBalances[user][chainName];

        if (nativeAmount > 0) {
            IPriceOracle oracle = chainOracles[chainName];
            require(address(oracle) != address(0), "Oracle not set");

            uint256 usdValue = oracle.convertToUSD(nativeAmount);
            totalUSD += usdValue;
        }
    }

    return totalUSD;
}

/**
 * @notice Get total borrowed value in USD for a user across ALL chains
 */
function getTotalBorrowedValueUSD(address user) public view returns (uint256) {
    uint256 totalUSD = 0;

    for (uint256 i = 0; i < allSupportedChains.length; i++) {
        string memory chainName = allSupportedChains[i];
        uint256 borrowedAmount = borrowBalances[user][chainName];

        if (borrowedAmount > 0) {
            IPriceOracle oracle = chainOracles[chainName];
            uint256 usdValue = oracle.convertToUSD(borrowedAmount);
            totalUSD += usdValue;
        }
    }

    return totalUSD;
}
```

### 3. **USD-Based Credit Line** 🆕

```solidity
/**
 * @notice Calculate credit line in USD (70% of collateral value)
 * @param user User address
 * @return creditLineUSD Maximum borrowing capacity in USD
 */
function getCreditLineUSD(address user) public view returns (uint256) {
    uint256 collateralValueUSD = getTotalCollateralValueUSD(user);
    return (collateralValueUSD * COLLATERAL_RATIO) / 100;
}

// Constants
uint256 public constant COLLATERAL_RATIO = 70; // 70% LTV
```

### 4. **Health Factor Calculation** 🆕

```solidity
/**
 * @notice Calculate health factor (Aave-style)
 * @param user User address
 * @return healthFactor Health factor with 18 decimals (1e18 = 100%)
 *
 * healthFactor = (collateral * liquidationThreshold) / totalBorrowed
 *
 * Examples:
 * - 2.0 = Very healthy (200% collateralized)
 * - 1.5 = Healthy (150% collateralized)
 * - 1.1 = Warning (110% collateralized)
 * - 1.0 = At liquidation threshold
 * - <1.0 = Undercollateralized (can be liquidated)
 */
function getHealthFactor(address user) public view returns (uint256) {
    uint256 totalBorrowedUSD = getTotalBorrowedValueUSD(user);

    if (totalBorrowedUSD == 0) {
        return type(uint256).max; // No debt = infinite health
    }

    uint256 collateralValueUSD = getTotalCollateralValueUSD(user);
    uint256 liquidationThresholdValue = (collateralValueUSD * LIQUIDATION_THRESHOLD) / 100;

    return (liquidationThresholdValue * 1e18) / totalBorrowedUSD;
}

// Constants
uint256 public constant LIQUIDATION_THRESHOLD = 80; // Can be liquidated at 80%
```

### 5. **Updated Borrow Function** 🔄

```solidity
/**
 * @notice Borrow native token (uses USD valuations)
 * @param amount Amount to borrow in native token
 * @param gasAmount Gas for cross-chain message
 */
function borrow(uint256 amount, uint256 gasAmount) external payable {
    require(msg.value >= gasAmount, "Insufficient gas");
    require(gasAmount >= MIN_GAS_AMOUNT, "Gas too low");

    // Calculate values in USD
    IPriceOracle oracle = chainOracles[thisChainName];
    require(address(oracle) != address(0), "Oracle not set");

    uint256 borrowValueUSD = oracle.convertToUSD(amount);
    uint256 totalBorrowedUSD = getTotalBorrowedValueUSD(msg.sender);
    uint256 creditLineUSD = getCreditLineUSD(msg.sender);

    // Check credit line in USD
    require(
        totalBorrowedUSD + borrowValueUSD <= creditLineUSD,
        "Exceeds credit line"
    );

    // Check health factor after borrow
    uint256 newTotalBorrowedUSD = totalBorrowedUSD + borrowValueUSD;
    uint256 collateralValueUSD = getTotalCollateralValueUSD(msg.sender);
    uint256 liquidationValue = (collateralValueUSD * LIQUIDATION_THRESHOLD) / 100;

    require(
        newTotalBorrowedUSD <= liquidationValue,
        "Would trigger liquidation"
    );

    // Transfer tokens
    payable(msg.sender).transfer(amount);

    // Update state
    borrowBalances[msg.sender][thisChainName] += amount;
    totalBorrowed[msg.sender] += amount; // In native token

    // Broadcast to other chains
    _broadcastUpdate(msg.sender, ACTION_BORROW, amount, gasAmount);

    emit Borrowed(msg.sender, thisChainName, amount);
}
```

### 6. **View Functions for Frontend** 🆕

```solidity
/**
 * @notice Get user's complete financial summary in USD
 * @return collateralUSD Total collateral in USD
 * @return borrowedUSD Total borrowed in USD
 * @return creditLineUSD Available credit in USD
 * @return healthFactor Health factor (1e18 = 100%)
 * @return availableUSD Remaining borrowing capacity in USD
 */
function getUserSummaryUSD(address user)
    external
    view
    returns (
        uint256 collateralUSD,
        uint256 borrowedUSD,
        uint256 creditLineUSD,
        uint256 healthFactor,
        uint256 availableUSD
    )
{
    collateralUSD = getTotalCollateralValueUSD(user);
    borrowedUSD = getTotalBorrowedValueUSD(user);
    creditLineUSD = getCreditLineUSD(user);
    healthFactor = getHealthFactor(user);

    availableUSD = creditLineUSD > borrowedUSD
        ? creditLineUSD - borrowedUSD
        : 0;
}

/**
 * @notice Get per-chain breakdown in USD
 */
function getChainBreakdownUSD(address user, string memory chainName)
    external
    view
    returns (
        uint256 collateralNative,
        uint256 collateralUSD,
        uint256 borrowedNative,
        uint256 borrowedUSD
    )
{
    collateralNative = collateralBalances[user][chainName];
    borrowedNative = borrowBalances[user][chainName];

    IPriceOracle oracle = chainOracles[chainName];
    if (address(oracle) != address(0)) {
        collateralUSD = oracle.convertToUSD(collateralNative);
        borrowedUSD = oracle.convertToUSD(borrowedNative);
    }
}
```

---

## Constructor Changes

```solidity
constructor(
    address _messageBridge,
    string[] memory _supportedChains,
    uint64[] memory _chainIds,
    address[] memory _oracleAddresses  // NEW: Oracle addresses per chain
) {
    // ... existing setup ...

    // Set up oracles
    require(_oracleAddresses.length == _supportedChains.length, "Mismatched oracle array");

    for (uint256 i = 0; i < _supportedChains.length; i++) {
        if (_oracleAddresses[i] != address(0)) {
            chainOracles[_supportedChains[i]] = IPriceOracle(_oracleAddresses[i]);
        }
    }
}
```

---

## Deployment Parameters

### Sepolia Deployment

```bash
PRIVATE_KEY=<key> forge script script/DeployVaultV24.s.sol:DeployVaultV24 \
  --rpc-url https://sepolia.infura.io/v3/YOUR_KEY \
  --broadcast

# Parameters:
MESSAGE_BRIDGE=0xA8d853C5b945924d217Ec4119E9f0e2eFf714B8a
SUPPORTED_CHAINS=["ethereum-sepolia", "polygon-amoy"]
CHAIN_IDS=[11155111, 80002]
ORACLES=[
  0x184e08394672B9Bf7aE670A3867C3c97A67A4e5C,  # Sepolia ETH/USD
  0x895c8848429745221d540366BC7aFCD0A7AFE3bF   # Amoy MATIC/USD (cross-chain reference)
]
```

### Amoy Deployment

```bash
PRIVATE_KEY=<key> forge script script/DeployVaultV24.s.sol:DeployVaultV24 \
  --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY \
  --broadcast

# Parameters:
MESSAGE_BRIDGE=0xEEcd2114162D577c4668B8e92a6FB34d0eA6A149
SUPPORTED_CHAINS=["ethereum-sepolia", "polygon-amoy"]
CHAIN_IDS=[11155111, 80002]
ORACLES=[
  0x184e08394672B9Bf7aE670A3867C3c97A67A4e5C,  # Sepolia ETH/USD (cross-chain reference)
  0x895c8848429745221d540366BC7aFCD0A7AFE3bF   # Amoy MATIC/USD
]
```

---

## Testing Scenarios

### Test 1: Mixed Collateral Borrowing

```solidity
// User deposits on both chains
depositCollateral(1 ETH) on Sepolia   // = $3,444 USD
depositCollateral(1000 MATIC) on Amoy // = $178 USD

// Total Collateral: $3,622 USD
// Credit Line (70%): $2,535 USD

// Can borrow:
borrow(0.73 ETH) on Sepolia   // = $2,514 USD ✅
// OR
borrow(14,150 MATIC) on Amoy  // = $2,518 USD ✅

// Health Factor: 2.535 / 2.514 = 1.42 (142%) ✅ Healthy
```

### Test 2: Health Factor Warning

```solidity
// User has $10,000 collateral
// Borrows $7,000

// Health Factor: (10000 * 0.80) / 7000 = 1.14 (114%)
// Status: ⚠️ Warning (close to liquidation at 110%)
```

### Test 3: Oracle Price Changes

```solidity
// Initial: 1 ETH = $3,000, deposited 1 ETH
// Borrowed: $2,100 (70% of $3,000)
// Health Factor: 1.14 (80% / 70% = 114%)

// ETH drops to $2,500
// Collateral Value: $2,500
// Borrowed Value: $2,100
// Health Factor: (2500 * 0.80) / 2100 = 0.95 (95%)
// Status: ❌ Can be liquidated!
```

---

## Events

```solidity
// New events
event OracleUpdated(string indexed chainName, address indexed oracle);
event HealthFactorUpdated(address indexed user, uint256 healthFactor);
event CreditLineExceeded(address indexed user, uint256 attempted, uint256 available);
```

---

## Security Considerations

1. **Oracle Failure Handling**: Revert if oracle returns stale/invalid data
2. **Rounding**: Always round down for credit calculations
3. **Health Factor**: Check BEFORE and AFTER operations
4. **Cross-Chain Oracle References**: Vaults need oracles for ALL chains, not just local

---

## Frontend Integration

```typescript
// New hook for USD values
export function useVaultValuesUSD(userAddress?: Address, chainId: number) {
  const { data } = useReadContract({
    address: vaultAddress,
    abi: VAULT_ABI,
    functionName: 'getUserSummaryUSD',
    args: [userAddress],
  });

  return {
    collateralUSD: data?.[0],
    borrowedUSD: data?.[1],
    creditLineUSD: data?.[2],
    healthFactor: data?.[3],
    availableUSD: data?.[4],
  };
}
```

---

## Next Steps

1. ✅ Oracles deployed (Sepolia: 0x184e08..., Amoy: 0x895c88...)
2. ⏳ Create CrossChainVaultV24.sol with above spec
3. ⏳ Create deployment script DeployVaultV24.s.sol
4. ⏳ Deploy to Sepolia and Amoy
5. ⏳ Update frontend to display USD values
6. ⏳ Add health factor visualization
7. ⏳ Test cross-chain borrowing with real prices

---

**Status**: Specification complete, ready to implement! 🚀
