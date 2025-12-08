# Sprint 10: Oracle Integration for Cross-Chain Asset Pricing

**Duration**: 1 week (December 11-17, 2025)
**Status**: 📋 **PLANNED**
**Goal**: Integrate Chainlink price feeds to properly value different assets across chains

**Last Updated**: 2025-11-06

---

## Context

**Current Problem**: System assumes 1 ETH = 1 MATIC in value

**Example**:
- User deposits 1 ETH on Sepolia (~$2,000)
- User borrows 0.9 MATIC on Amoy (~$0.90)
- System treats these as equal value!

**Risk**: Users can exploit price differences between chains

**Sprint Objective**: Use Chainlink oracles to get real-time prices and value all assets in USD

---

## Strategic Value

Accurate pricing is critical for:
- **Fair Lending**: Prevent users from borrowing more value than they deposit
- **Risk Management**: Calculate true collateralization ratios
- **Multi-Asset Support**: Enable different assets on different chains
- **Protocol Safety**: Protect against price manipulation

---

## Objectives

### 1. Integrate Chainlink Price Feeds ✅
**Goal**: Get real-time ETH/USD and MATIC/USD prices

**Chainlink Addresses** (Testnet):
```solidity
// Sepolia testnet
address constant ETH_USD_FEED = 0x694AA1769357215DE4FAC081bf1f309aDC325306;

// Amoy testnet
address constant MATIC_USD_FEED = 0xd0D5e3DB44DE05E9F294BB0a3bEEaF030DE24Ada;
```

**Contract Integration** (contracts/cross-chain/src/CrossChainVault.sol):
```solidity
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

contract CrossChainVault {
    AggregatorV3Interface public priceFeed;

    constructor(
        address _bridgeManager,
        address _axelarGateway,
        address _priceFeed, // NEW: Chainlink price feed address
        string memory _chainName,
        string[] memory _supportedChains
    ) {
        bridgeManager = BridgeManager(_bridgeManager);
        axelarGateway = _axelarGateway;
        priceFeed = AggregatorV3Interface(_priceFeed); // NEW
        thisChainName = _chainName;
        // ... rest
    }

    /// @notice Get latest price from Chainlink oracle
    /// @return price in USD with 8 decimals (e.g., 2000_00000000 = $2000)
    function getLatestPrice() public view returns (int256) {
        (
            /* uint80 roundID */,
            int256 price,
            /* uint256 startedAt */,
            /* uint256 timeStamp */,
            /* uint80 answeredInRound */
        ) = priceFeed.latestRoundData();

        require(price > 0, "Invalid price from oracle");
        return price;
    }

    /// @notice Convert native token amount to USD value
    /// @param amount Amount of native tokens (ETH/MATIC)
    /// @return USD value with 18 decimals
    function convertToUSD(uint256 amount) public view returns (uint256) {
        int256 price = getLatestPrice(); // 8 decimals
        // amount has 18 decimals, price has 8 decimals
        // result should have 18 decimals
        return (amount * uint256(price)) / 1e8;
    }
}
```

**Estimated Time**: 4 hours

---

### 2. Update Credit Line Calculation with USD Values
**Goal**: Calculate collateral and borrowed in common currency (USD)

**Current Calculation**:
```solidity
// WRONG: Assumes 1 ETH = 1 MATIC
totalCreditLine = totalCollateral - totalBorrowed;
```

**New Calculation**:
```solidity
mapping(address => mapping(string => uint256)) public collateralUSD;
mapping(address => mapping(string => uint256)) public borrowedUSD;

function _updateCreditLine(address user) internal {
    // Get USD value of all collateral
    uint256 totalCollateralUSD = 0;
    for (uint256 i = 0; i < allSupportedChains.length; i++) {
        string memory chain = allSupportedChains[i];
        uint256 nativeAmount = collateralBalances[user][chain];
        uint256 usdValue = _getCollateralValueUSD(chain, nativeAmount);
        totalCollateralUSD += usdValue;
    }

    // Get USD value of all borrowed
    uint256 totalBorrowedUSD = 0;
    for (uint256 i = 0; i < allSupportedChains.length; i++) {
        string memory chain = allSupportedChains[i];
        uint256 nativeAmount = borrowBalances[user][chain];
        uint256 usdValue = _getBorrowValueUSD(chain, nativeAmount);
        totalBorrowedUSD += usdValue;
    }

    // Calculate credit line in USD
    if (totalCollateralUSD >= totalBorrowedUSD) {
        totalCreditLine[user] = totalCollateralUSD - totalBorrowedUSD;
    } else {
        totalCreditLine[user] = 0;
    }
}

// Helper to get USD value based on chain
function _getCollateralValueUSD(string memory chain, uint256 amount)
    internal view returns (uint256)
{
    // For now, use local price feed
    // In production, might query oracle on specific chain
    return convertToUSD(amount);
}
```

**Challenge**: Each vault only has price feed for its own chain
- Sepolia vault has ETH/USD feed
- Amoy vault has MATIC/USD feed
- But Sepolia vault needs to value MATIC collateral!

**Solution**: Store prices in cross-chain messages
```solidity
// When sending cross-chain update, include current price
struct CollateralUpdate {
    bytes32 messageId;
    address user;
    uint8 action;
    uint256 amount;
    string chainName;
    uint256 priceUSD; // NEW: Current price on source chain
}
```

**Estimated Time**: 8 hours

---

### 3. Display USD Values in Frontend
**Goal**: Show all balances in USD alongside native tokens

**Hook Update** (useVault.ts):
```typescript
export function useVaultDataWithPrices(userAddress?: Address, chainId: number) {
  const vaultData = useVaultData(userAddress, chainId);

  // Get ETH/USD price
  const ethPrice = useReadContract({
    address: CONTRACTS[sepolia.id]?.CrossChainVault as Address,
    abi: VAULT_ABI,
    functionName: 'getLatestPrice',
    chainId: sepolia.id,
  });

  // Get MATIC/USD price
  const maticPrice = useReadContract({
    address: CONTRACTS[polygonAmoy.id]?.CrossChainVault as Address,
    abi: VAULT_ABI,
    functionName: 'getLatestPrice',
    chainId: polygonAmoy.id,
  });

  // Calculate USD values
  const sepoliaBalanceUSD = vaultData.sepoliaBalance && ethPrice.data
    ? (Number(formatEther(vaultData.sepoliaBalance)) * Number(ethPrice.data)) / 1e8
    : 0;

  const amoyBalanceUSD = vaultData.amoyBalance && maticPrice.data
    ? (Number(formatEther(vaultData.amoyBalance)) * Number(maticPrice.data)) / 1e8
    : 0;

  return {
    ...vaultData,
    ethPrice: ethPrice.data ? Number(ethPrice.data) / 1e8 : 0,
    maticPrice: maticPrice.data ? Number(maticPrice.data) / 1e8 : 0,
    sepoliaBalanceUSD,
    amoyBalanceUSD,
    totalCollateralUSD: sepoliaBalanceUSD + amoyBalanceUSD,
  };
}
```

**UI Update** (VaultDashboard.tsx):
```typescript
const vaultDataWithPrices = useVaultDataWithPrices(address, vaultChainId);

// Update stat cards to show USD
<div className="bg-white border-2 border-gray-200 rounded-lg p-6">
  <div className="flex items-center justify-between mb-2">
    <span className="text-sm font-medium text-gray-600">Total Collateral</span>
    <Wallet className="h-5 w-5 text-green-600" />
  </div>
  <div className="text-2xl font-bold text-gray-900">
    ${vaultDataWithPrices.totalCollateralUSD.toFixed(2)}
  </div>
  <div className="text-sm text-gray-500 mt-1">
    {formatEther(vaultData.totalCollateral)} ETH
  </div>
</div>

// Add price display
<div className="mt-4 text-sm text-gray-600">
  Current Prices:
  <div className="flex gap-4 mt-2">
    <span>ETH: ${vaultDataWithPrices.ethPrice.toFixed(2)}</span>
    <span>MATIC: ${vaultDataWithPrices.maticPrice.toFixed(4)}</span>
  </div>
</div>
```

**Estimated Time**: 6 hours

---

### 4. Update Borrow Validation with Oracle Prices
**Goal**: Prevent borrowing more USD value than deposited

**Contract Logic**:
```solidity
function borrow(uint256 amount, uint256 gasAmount) external payable {
    require(msg.value >= gasAmount, "Insufficient gas payment");

    // Accrue interest (if implemented in Sprint 09)
    if (ANNUAL_INTEREST_RATE > 0) {
        _accrueInterest(msg.sender);
    }

    // NEW: Calculate USD values
    uint256 borrowAmountUSD = convertToUSD(amount);
    uint256 totalBorrowedUSD = _getTotalBorrowedUSD(msg.sender) + borrowAmountUSD;
    uint256 totalCollateralUSD = _getTotalCollateralUSD(msg.sender);

    // Check collateralization ratio in USD terms
    uint256 requiredCollateral = (totalBorrowedUSD * MIN_COLLATERALIZATION_RATIO) / 100;
    require(totalCollateralUSD >= requiredCollateral,
            "Insufficient collateral (USD value)");

    // Rest of borrow logic...
    borrowBalances[msg.sender][thisChainName] += amount;
    totalBorrowed[msg.sender] += amount;

    _updateCreditLine(msg.sender);
    _broadcastBorrowUpdate(msg.sender, thisChainName, amount, true, gasAmount);

    payable(msg.sender).transfer(amount);
    emit Borrowed(msg.sender, thisChainName, amount);
}
```

**Estimated Time**: 4 hours

---

### 5. Testing & Edge Cases
**Goal**: Ensure oracle integration works correctly

**Test Scenarios**:

**Test 1: Price Feed Connectivity**
- [ ] Call `getLatestPrice()` on Sepolia
- [ ] Verify returns reasonable ETH price (~$2000)
- [ ] Call `getLatestPrice()` on Amoy
- [ ] Verify returns reasonable MATIC price (~$1)

**Test 2: USD Conversion Accuracy**
- [ ] Convert 1 ETH to USD
- [ ] Verify matches current market price
- [ ] Convert 1000 MATIC to USD
- [ ] Verify calculation correct

**Test 3: Cross-Asset Borrowing**
- [ ] Deposit 1 ETH on Sepolia ($2000)
- [ ] Try to borrow 1000 MATIC on Amoy ($1000)
- [ ] Should succeed (50% utilization)
- [ ] Try to borrow 2500 MATIC ($2500)
- [ ] Should fail (exceeds 120% ratio)

**Test 4: Price Feed Failure Handling**
- [ ] Simulate oracle returning 0
- [ ] Verify contract reverts with "Invalid price"
- [ ] Test with negative price
- [ ] Verify handled gracefully

**Test 5: USD Display in UI**
- [ ] Check all stat cards show USD values
- [ ] Verify USD and native amounts both visible
- [ ] Check current prices displayed
- [ ] Verify formatting (2 decimals for USD)

**Test 6: Multi-Chain Price Aggregation**
- [ ] Have collateral on both chains
- [ ] Verify total USD value aggregated correctly
- [ ] Change network, verify prices update
- [ ] Check borrowing capacity in USD

**Estimated Time**: 6 hours

---

## Week Plan

### Days 1-2 (Dec 11-12): Contract Integration
- [ ] Add Chainlink dependency to contracts
- [ ] Update CrossChainVault constructor with price feed
- [ ] Implement `getLatestPrice()` function
- [ ] Implement `convertToUSD()` function
- [ ] Write unit tests for oracle calls
- [ ] Deploy to Sepolia with ETH/USD feed
- [ ] Deploy to Amoy with MATIC/USD feed

### Days 3-4 (Dec 13-14): Credit Line Updates
- [ ] Update `_updateCreditLine()` to use USD values
- [ ] Modify borrow validation with USD checks
- [ ] Update cross-chain messages to include prices
- [ ] Test USD-based collateralization
- [ ] Fix any bugs in calculation logic

### Days 5-6 (Dec 15-16): Frontend Integration
- [ ] Add oracle ABI functions to VAULT_ABI
- [ ] Create `useVaultDataWithPrices()` hook
- [ ] Update VaultDashboard to show USD values
- [ ] Add current price display
- [ ] Test UI with real oracle data

### Day 7 (Dec 17): Testing & Documentation
- [ ] Run all 6 test scenarios
- [ ] Fix any edge cases
- [ ] Update documentation
- [ ] Record demo video
- [ ] Prepare for Sprint 11

---

## Success Criteria

| Criteria | Target |
|----------|--------|
| Oracle connectivity | 100% uptime |
| Price accuracy | ±1% of market price |
| USD calculations | Correct to 2 decimals |
| Cross-asset borrowing | Works correctly |
| UI shows USD values | All balances displayed |
| Price feed failure | Graceful error handling |

---

## Non-Goals (Deferred)

- ❌ Multiple oracle providers (Chainlink only)
- ❌ TWAP (Time-Weighted Average Price) for manipulation resistance
- ❌ Backup oracles (Pyth, API3, etc.)
- ❌ Historical price data
- ❌ Price impact calculations
- ❌ Custom oracle for exotic assets

**Rationale**: Focus on basic oracle integration. Advanced features for production later.

---

## Risk Management

### Risk: Oracle Goes Offline
**Mitigation**: Revert transactions, don't use stale prices

### Risk: Price Manipulation
**Mitigation**: Use Chainlink (decentralized oracles), check staleness

### Risk: Conversion Errors
**Mitigation**: Extensive testing, use SafeMath-like checks

### Risk: Gas Costs Too High
**Mitigation**: Cache prices, only update periodically

---

## Dependencies

**Required**:
- ✅ Sprint 07 complete (borrowing/lending)
- ✅ Sprint 08 complete (auto-sync)
- ✅ Sprint 09 complete (risk management)

**External**:
- Chainlink testnet oracles operational
- RPC endpoints have archive data

**Blockers**: None (Chainlink is reliable)

---

## Documentation Updates

- [ ] Document oracle integration in contracts README
- [ ] Add price feed addresses to deployment docs
- [ ] Update CROSSCHAIN_VAULT_SPEC.md (Oracle Integration section)
- [ ] Create user guide: "Understanding USD Values"
- [ ] Update IMPLEMENTATION_ROADMAP.md (Phase 4 complete)

---

## Metrics

- **Sprint Velocity**: 28 hours estimated work
- **Features**: 4 (oracle integration, USD calculation, UI updates, testing)
- **Contract Changes**: 3 new functions, 1 new dependency
- **Frontend Changes**: 1 new hook, UI updates across dashboard

---

## Chainlink Resources

**Documentation**:
- Price Feeds: https://docs.chain.link/data-feeds/price-feeds
- Testnet Addresses: https://docs.chain.link/data-feeds/price-feeds/addresses?network=ethereum&page=1

**Testnet Faucets**:
- Sepolia ETH: https://sepoliafaucet.com/
- Amoy MATIC: https://faucet.polygon.technology/

**Monitoring**:
- Sepolia ETH/USD Feed: https://sepolia.etherscan.io/address/0x694AA1769357215DE4FAC081bf1f309aDC325306
- Amoy MATIC/USD Feed: https://amoy.polygonscan.com/address/0xd0D5e3DB44DE05E9F294BB0a3bEEaF030DE24Ada

---

**Document Version**: 1.0
**Status**: 📋 Planned (starts after Sprint 09)
**Predecessor**: Sprint 09 (Risk Management)
**Successor**: Sprint 11 (Polish & Optimization)
