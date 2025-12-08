# CrossChainVaultV25 Deployment Record

**Status**: Deployed but not production (cross-chain messaging issues)

**Date**: 2025-11-20

**Decision**: Deferred in favor of V23 (Custom MessageBridge)

---

## Deployment Details

### Sepolia Testnet
- **Address**: `0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312`
- **Transaction**: [0x...](https://sepolia.etherscan.io/address/0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312)
- **Gas Cost**: 0.0048 ETH

### Amoy Testnet
- **Address**: `0xbafd9d789f96d18cedd057899a4ba3273c9f6d0e`
- **Transaction**: [0x15f86b...](https://amoy.polygonscan.com/tx/0x15f86b05ef796c3693e0f0fea5be7ae09ae55d0a2f5e9d417c2680b8429ace56)
- **Gas Cost**: 0.119 POL

---

## V25 Features

- Axelar Gateway integration
- CCIP Router integration
- Chainlink price oracles
- BridgeManager for cross-chain messaging

---

## Known Issues

**Cross-Chain Messaging Fails**
- `supply()` and `depositCollateral()` revert with "execution reverted"
- Issue occurs during `_broadcastLiquidityUpdate()` / `_broadcastCollateralUpdate()`
- Likely causes:
  - BridgeManager authorization
  - Insufficient gas for Axelar/CCIP fees
  - Bridge route configuration

**View Functions Work**
- `getSupplyAPY()` returns correct values
- `chainLiquidity()` readable
- Contract is deployed and functional (except messaging)

---

## Decision: Use V23 Instead

**Rationale**:
- V23 (Custom MessageBridge) works reliably
- No external dependencies (Axelar/CCIP)
- Focus on core features first
- Revisit production bridges when features stabilize

**V23 Production Addresses**:
- Sepolia: `0x397c9aFDBB18803931154bbB6F9854fcbdaEeCff`
- Amoy: `0xf0dba0090aaAEAe37dBe9Ce1c3a117b766b8A31d`

---

## For Deployment Workflows

See [Cross-Chain README](./README.md) for:
- Deployment procedures
- Withdrawal workflows
- Testing guides
- Troubleshooting

---

**This document is kept for historical reference. V25 contracts remain deployed but are not used in production.** Summary

## Deployment Status

### Sepolia Testnet ✅
- **Status**: Deployed Successfully
- **Vault Address**: `0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312`
- **Bridge Manager**: `0xA8d853C5b945924d217Ec4119E9f0e2eFf714B8a`
- **Axelar Gateway**: `0xe432150cce91c13a887f7D836923d5597adD8E31`
- **CCIP Router**: `0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59`
- **ETH/USD Oracle**: `0x184e08394672B9Bf7aE670A3867C3c97A67A4e5C`
- **MATIC/USD Oracle (reference)**: `0x895c8848429745221d540366BC7aFCD0A7AFE3bF`
- **Transaction**: [View on Etherscan](https://sepolia.etherscan.io/address/0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312)

### Amoy Testnet ✅
- **Status**: Deployed Successfully
- **Vault Address**: `0xbafd9d789f96d18cedd057899a4ba3273c9f6d0e`
- **Bridge Manager**: `0xEEcd2114162D577c4668B8e92a6FB34d0eA6A149`
- **Axelar Gateway**: `0x2A723E9BBD44C27A0F0FC13f46C41Ab59EDdd6E8`
- **CCIP Router**: `0x9C32fCB86BF0f4a1A8921a9Fe46de3198bb884B2`
- **MATIC/USD Oracle**: `0x895c8848429745221d540366BC7aFCD0A7AFE3bF`
- **ETH/USD Oracle (reference)**: `0x184e08394672B9Bf7aE670A3867C3c97A67A4e5C`
- **Transaction**: [View on PolygonScan](https://amoy.polygonscan.com/address/0xbafd9d789f96d18cedd057899a4ba3273c9f6d0e)

## V25 Features

### New Functionality
1. **Supply/Lend Mechanism** - Users can supply liquidity to earn interest
2. **Utilization-Based Interest Rates** - Dynamic APY based on pool utilization
3. **Interest Accrual** - Automatic interest calculation for suppliers
4. **Cross-Chain Liquidity Tracking** - Liquidity state syncs across chains

### Interest Rate Model
```
Base APY: 2%
Slope: 10%
Borrow Multiplier: 1.2x

Utilization Rate → Supply APY → Borrow APY
    0%          →      2%     →     2.4%
   25%          →    4.5%     →     5.4%
   50%          →      7%     →     8.4%
   75%          →    9.5%     →    11.4%
  100%          →     12%     →    14.4%
```

## Configuration Steps

### 1. Complete Amoy Deployment
```bash
# Get MATIC from faucet
# https://faucet.polygon.technology/

# Deploy to Amoy
PRIVATE_KEY=<key> forge script script/DeployVaultV25.s.sol:DeployVaultV25 \
  --rpc-url https://polygon-amoy.infura.io/v3/<api-key> \
  --broadcast --legacy
```

### 2. Configure Trusted Vaults
```bash
# On Sepolia - Set Amoy vault as trusted
PRIVATE_KEY=<key> cast send 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312 \
  "setTrustedVault(string,address)" "polygon" <amoy-vault-address> \
  --rpc-url https://sepolia.infura.io/v3/<api-key>

# On Amoy - Set Sepolia vault as trusted
PRIVATE_KEY=<key> cast send <amoy-vault-address> \
  "setTrustedVault(string,address)" "ethereum" 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312 \
  --rpc-url https://polygon-amoy.infura.io/v3/<api-key> --legacy
```

## Testing Guide

### 1. Supply Liquidity
```bash
# Supply 0.1 ETH with 0.01 ETH for gas
PRIVATE_KEY=<key> cast send 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312 \
  "supply(uint256)" 10000000000000000 \
  --value 110000000000000000 \
  --rpc-url https://sepolia.infura.io/v3/<api-key>

# Check total liquidity
cast call 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312 \
  "chainLiquidity(string)(uint256)" "ethereum" \
  --rpc-url https://sepolia.infura.io/v3/<api-key>
```

### 2. Check APY
```bash
# Check supply APY (starts at 2% with 0 utilization)
cast call 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312 \
  "getSupplyAPY(string)(uint256)" "ethereum" \
  --rpc-url https://sepolia.infura.io/v3/<api-key>

# Check borrow APY
cast call 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312 \
  "getBorrowAPY(string)(uint256)" "ethereum" \
  --rpc-url https://sepolia.infura.io/v3/<api-key>
```

### 3. Test Borrowing from Liquidity Pool
```bash
# 1. Deposit collateral (0.2 ETH collateral + 0.01 ETH gas)
PRIVATE_KEY=<key> cast send 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312 \
  "depositCollateral(address,uint256)" \
  0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA 10000000000000000 \
  --value 110000000000000000 \
  --rpc-url https://sepolia.infura.io/v3/<api-key>

# 2. Borrow from pool (0.05 ETH borrow + 0.01 ETH gas)
PRIVATE_KEY=<key> cast send 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312 \
  "borrow(uint256,uint256)" \
  5000000000000000 10000000000000000 \
  --value 10000000000000000 \
  --rpc-url https://sepolia.infura.io/v3/<api-key>

# 3. Check utilization rate
cast call 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312 \
  "getUtilizationRate(string)(uint256)" "ethereum" \
  --rpc-url https://sepolia.infura.io/v3/<api-key>
```

### 4. Test Interest Accrual
```bash
# Wait 1 day or advance block.timestamp in tests

# Check balance with accrued interest
cast call 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312 \
  "getSuppliedBalanceWithInterest(address,string)(uint256)" \
  0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA "ethereum" \
  --rpc-url https://sepolia.infura.io/v3/<api-key>
```

### 5. Withdraw Liquidity
```bash
# Withdraw supplied amount with interest
PRIVATE_KEY=<key> cast send 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312 \
  "withdrawSupplied(uint256,uint256)" \
  5000000000000000 10000000000000000 \
  --value 10000000000000000 \
  --rpc-url https://sepolia.infura.io/v3/<api-key>
```

## Cross-Chain Testing Scenario

### Scenario: Supply on Sepolia, Borrow on Amoy
This demonstrates the power of cross-chain unified liquidity:

1. **Supply liquidity on Sepolia**
   - User supplies 1 ETH on Sepolia
   - Earns interest based on Sepolia pool utilization

2. **Deposit collateral on Amoy**
   - User deposits 1000 MATIC collateral on Amoy
   - Worth ~$890 USD at current prices

3. **Borrow from Amoy pool using Sepolia credit line**
   - User's collateral: 1000 MATIC ($890 USD) on Amoy
   - Credit line: $890 × 70% = $623 USD
   - Available to borrow: $623 worth of MATIC on Amoy
   - Borrow uses liquidity from Amoy pool (supplied by other users)

4. **Cross-chain sync**
   - Borrow event broadcasts to Sepolia
   - Sepolia vault updates global credit line
   - Both chains aware of user's total position

## New Functions

### Supply Functions
- `supply(uint256 gasAmount)` - Supply liquidity to earn interest
- `withdrawSupplied(uint256 amount, uint256 gasAmount)` - Withdraw with accrued interest

### View Functions
- `getSupplyAPY(string chain)` - Get current supply APY
- `getBorrowAPY(string chain)` - Get current borrow APY
- `getSuppliedBalanceWithInterest(address user, string chain)` - Get balance with pending interest
- `getAvailableLiquidity(string chain)` - Get borrowable liquidity
- `getUtilizationRate(string chain)` - Get pool utilization rate

### State Variables
- `chainLiquidity` - Total supplied per chain
- `chainUtilized` - Total borrowed from pool per chain
- `suppliedBalances` - User's supplied balance per chain
- `lastInterestUpdate` - Last interest update timestamp

## Events
- `Supplied(address indexed user, string chain, uint256 amount)`
- `LiquidityWithdrawn(address indexed user, string chain, uint256 amount)`
- `InterestAccrued(address indexed user, string chain, uint256 interest)`
- `LiquidityUpdated(string chain, uint256 totalLiquidity, uint256 utilized)`

## Security Considerations

1. **Interest Accrual Safety**
   - Interest only accrues when state-changing functions are called
   - No automatic compound interest (prevents attack vectors)
   - Uses time-based calculation with overflow protection

2. **Liquidity Availability**
   - Borrow checks available liquidity (total - utilized)
   - Withdraw checks available liquidity before transfer
   - Prevents bank run scenarios

3. **Cross-Chain Sync**
   - Liquidity state broadcasts to all chains
   - Ensures global view of pool utilization
   - Prevents double-spending of liquidity

4. **Utilization Caps**
   - No hard cap on utilization
   - APY increases with utilization to incentivize deposits
   - Market-driven balance between supply and demand

## Next Steps

1. ✅ Deploy to Sepolia
2. ⏳ Deploy to Amoy (needs funds)
3. ⏳ Configure trusted vaults
4. ⏳ Create frontend hooks for supply/withdraw
5. ⏳ Build UI for liquidity pool management
6. ⏳ Test complete flow on testnets
7. ⏳ Document Sprint 10 completion

## Comparison with V24

| Feature | V24 | V25 |
|---------|-----|-----|
| Collateral Deposit | ✅ | ✅ |
| Cross-Chain Borrowing | ✅ | ✅ |
| USD Valuations | ✅ | ✅ |
| Health Factor | ✅ | ✅ |
| **Supply/Lend** | ❌ | ✅ |
| **Interest Rates** | ❌ | ✅ |
| **Liquidity Pool** | ❌ | ✅ |
| **Interest Accrual** | ❌ | ✅ |

## Deployed Addresses Summary

| Network | Vault V25 | Bridge Manager | Oracle |
|---------|-----------|----------------|--------|
| Sepolia | `0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312` | `0xA8d853C5b945924d217Ec4119E9f0e2eFf714B8a` | `0x184e08394672B9Bf7aE670A3867C3c97A67A4e5C` |
| Amoy | *Pending* | `0xEEcd2114162D577c4668B8e92a6FB34d0eA6A149` | `0x895c8848429745221d540366BC7aFCD0A7AFE3bF` |
