# Sprint 11: Liquidations & Multi-Currency - Implementation Plan

**Goal**: Implement liquidation mechanism and ERC20 token support to make Fusion Prime competitive with Aave/Compound

**Status**: 📋 **PLANNED**

**Duration**: 2-3 weeks

**Last Updated**: 2025-11-20

---

## Executive Summary

Sprint 11 adds two critical features identified in Sprint 10 completion:
1. **Liquidation Mechanism** - Protect lenders by liquidating undercollateralized positions
2. **Multi-Currency Support** - Support ERC20 tokens (USDC, DAI, WETH, WBTC) beyond native ETH/MATIC

This brings Fusion Prime to feature parity with established lending protocols while maintaining our unique cross-chain advantage.

---

## User Review Required

> [!IMPORTANT]
> **Scope Clarification**
> 
> There are two different Sprint 11 documents:
> - `/docs/sprints/sprint-11.md` - "Polish & Optimization" (2 weeks, Dec 18-31)
> - Sprint 10 completion summary - "Liquidations & Multi-Currency" (this plan)
> 
> **Question**: Which Sprint 11 should we implement?
> - Option A: Liquidations & Multi-Currency (this plan, ~60-70 hours)
> - Option B: Polish & Optimization (UI/UX improvements, ~50 hours)
> - Option C: Hybrid approach (prioritize liquidations, defer multi-currency)

> [!WARNING]
> **Technical Complexity**
> 
> Liquidations require:
> - Smart contract changes (V29 deployment)
> - Backend service (liquidation bot)
> - Cross-chain coordination
> - Thorough testing to avoid loss of funds
> 
> This is higher risk than UI polish work.

---

## Proposed Changes

### Smart Contracts

#### [NEW] [CrossChainVaultV29.sol](file:///home/koita/dev/web3/fusion-prime/contracts/cross-chain/src/CrossChainVaultV29.sol)

**Purpose**: Add liquidation mechanism and ERC20 token support to V23/V24 architecture

**New Features**:

**1. Liquidation Function**
```solidity
function liquidate(
    address user,
    uint256 repayAmount
) external payable returns (uint256 collateralSeized)
```

**Logic**:
- Check health factor < 100% (LIQUIDATION_THRESHOLD = 80%)
- Calculate collateral to seize with bonus (5-10%)
- Transfer collateral to liquidator
- Reduce user's debt
- Emit `Liquidated` event
- Broadcast liquidation to other chains

**2. ERC20 Support**
```solidity
function depositCollateralERC20(address token, uint256 amount, uint256 gasAmount)
function withdrawCollateralERC20(address token, uint256 amount, uint256 gasAmount)
function borrowERC20(address token, uint256 amount, uint256 gasAmount)
function repayERC20(address token, uint256 amount)
```

**Token Tracking**:
- `mapping(address => mapping(address => mapping(string => uint256))) tokenCollateralBalances`
- `mapping(address => bool) supportedTokens`
- `mapping(address => uint256) collateralFactors` (e.g., USDC = 90%, WBTC = 75%)

**3. Health Factor Calculation**
```solidity
function getHealthFactor(address user) public view returns (uint256) {
    uint256 totalCollateralUSD = getTotalCollateralValueUSD(user);
    uint256 totalBorrowedUSD = getTotalBorrowedValueUSD(user);
    
    if (totalBorrowedUSD == 0) return type(uint256).max;
    
    // Health factor = (collateral * liquidation threshold) / borrowed
    return (totalCollateralUSD * LIQUIDATION_THRESHOLD) / (totalBorrowedUSD * 100);
}
```

**Events**:
```solidity
event Liquidated(
    address indexed liquidator,
    address indexed user,
    uint256 repayAmount,
    uint256 collateralSeized,
    uint256 bonus
);
event TokenAdded(address indexed token, uint256 collateralFactor);
```

---

#### [MODIFY] [PriceOracle.sol](file:///home/koita/dev/web3/fusion-prime/contracts/cross-chain/src/PriceOracle.sol)

**Changes**:
- Add price feeds for USDC, DAI, WETH, WBTC
- Support `getTokenPrice(address token)` function
- Add price staleness checks (revert if > 1 hour old)

**Price Feed Addresses** (Sepolia):
```solidity
USDC/USD: 0xA2F78ab2355fe2f984D808B5CeE7FD0A93D5270E
DAI/USD: 0x14866185B1962B63C3Ea9E03Bc1da838bab34C19
WETH/USD: 0x694AA1769357215DE4FAC081bf1f309aDC325306
WBTC/USD: 0x1b44F3514812d835EB1BDB0acB33d3fA3351Ee43
```

---

### Backend Services

#### [NEW] [services/liquidation-bot/](file:///home/koita/dev/web3/fusion-prime/services/liquidation-bot/)

**Purpose**: Monitor positions and execute profitable liquidations

**Architecture**:
```
liquidation-bot/
├── src/
│   ├── monitor.ts          # Query positions, calculate health factors
│   ├── executor.ts         # Execute liquidation transactions
│   ├── profitability.ts    # Calculate if liquidation is profitable
│   └── index.ts            # Main service loop
├── config/
│   └── chains.ts           # Chain configs, RPC endpoints
├── package.json
└── README.md
```

**Monitor Logic**:
1. Query all users with borrowed positions
2. Calculate health factor for each
3. Filter health factor < 100%
4. Calculate profitability (bonus - gas costs)
5. Execute if profitable

**Configuration**:
```typescript
{
  minProfitUSD: 10,           // Minimum profit to execute
  maxGasPriceGwei: 50,        // Max gas price
  checkIntervalMs: 30000,     // Check every 30 seconds
  chains: ['sepolia', 'amoy']
}
```

---

### Frontend

#### [NEW] [LiquidationDashboard.tsx](file:///home/koita/dev/web3/fusion-prime/frontend/risk-dashboard/src/pages/cross-chain/LiquidationDashboard.tsx)

**Purpose**: Show liquidatable positions and manual liquidation interface

**Features**:
- Table of liquidatable positions (health factor < 100%)
- Manual liquidation button
- Profitability calculator
- Liquidation history

---

#### [NEW] [TokenSelector.tsx](file:///home/koita/dev/web3/fusion-prime/frontend/risk-dashboard/src/components/vault/TokenSelector.tsx)

**Purpose**: Allow users to select which token to deposit/borrow

**Features**:
- Dropdown with supported tokens
- Token balances display
- Token icons
- Approve/allowance flow

---

#### [MODIFY] [VaultDashboard.tsx](file:///home/koita/dev/web3/fusion-prime/frontend/risk-dashboard/src/pages/cross-chain/VaultDashboard.tsx)

**Changes**:
- Add health factor warning banner (< 120%)
- Add token selector to deposit/borrow forms
- Show multi-token positions
- Add liquidation risk indicator

---

#### [NEW] [useVaultV29.ts](file:///home/koita/dev/web3/fusion-prime/frontend/risk-dashboard/src/hooks/contracts/useVaultV29.ts)

**Purpose**: React hooks for V29 vault interactions

**Hooks**:
- `useHealthFactor(userAddress)`
- `useLiquidate()`
- `useDepositERC20(token)`
- `useWithdrawERC20(token)`
- `useBorrowERC20(token)`
- `useRepayERC20(token)`
- `useTokenBalance(token, user)`
- `useTokenAllowance(token, user, spender)`

---

## Verification Plan

### Automated Tests

**Smart Contract Tests**:
```bash
cd contracts/cross-chain
forge test -vvv --match-contract VaultV29Test
```

**Test Cases**:
- ✅ Liquidation at 99% health factor succeeds
- ✅ Liquidation at 101% health factor fails
- ✅ Liquidation bonus calculated correctly
- ✅ ERC20 deposit/withdraw works
- ✅ Cross-chain ERC20 sync works
- ✅ Price feed integration works
- ✅ Token allowance checks work

**Bot Tests**:
```bash
cd services/liquidation-bot
npm test
```

### Manual Verification

**1. Liquidation Flow**:
- [ ] Create undercollateralized position (health < 100%)
- [ ] Verify bot detects position
- [ ] Execute liquidation manually
- [ ] Verify collateral transferred with bonus
- [ ] Verify debt reduced
- [ ] Check cross-chain sync

**2. ERC20 Flow**:
- [ ] Approve USDC spending
- [ ] Deposit USDC as collateral
- [ ] Borrow DAI
- [ ] Repay DAI
- [ ] Withdraw USDC
- [ ] Verify cross-chain token balances

**3. Multi-Token Position**:
- [ ] Deposit ETH + USDC + WBTC
- [ ] Borrow DAI
- [ ] Check health factor calculation
- [ ] Verify position display in UI

---

## Implementation Order

### Phase 1: Liquidation Mechanism (Week 1)

**Days 1-2**: Smart Contract
- Create V29 based on V23
- Implement `liquidate()` function
- Add health factor calculation
- Write unit tests

**Days 3-4**: Liquidation Bot
- Create bot service structure
- Implement monitoring logic
- Implement execution logic
- Test on testnet

**Day 5**: Frontend
- Create LiquidationDashboard
- Add health factor warnings
- Test manual liquidation

### Phase 2: Multi-Currency (Week 2)

**Days 6-8**: ERC20 Smart Contract
- Add ERC20 deposit/withdraw
- Add ERC20 borrow/repay
- Add token tracking
- Write unit tests

**Day 9**: Price Feeds
- Add Chainlink feeds for all tokens
- Update oracle interface
- Test price integration

**Day 10**: Frontend
- Create TokenSelector
- Update VaultDashboard
- Add multi-token position view
- Test token flows

### Phase 3: Testing & Deployment (Week 3)

**Days 11-12**: Integration Testing
- End-to-end liquidation tests
- Multi-token position tests
- Cross-chain sync tests
- Bot execution tests

**Day 13**: Deployment
- Deploy V29 to Sepolia
- Deploy V29 to Amoy
- Configure price feeds
- Deploy liquidation bot
- Update frontend config

---

## Success Criteria

| Criteria | Target |
|----------|--------|
| Liquidation function works | ✅ Tested on testnet |
| Health factor < 100% triggers liquidation | ✅ Verified |
| Liquidation bonus | 5-10% to liquidator |
| Bot monitors positions | Every 30 seconds |
| Bot executes liquidations | When profitable |
| ERC20 tokens supported | USDC, DAI, WETH, WBTC |
| Price feeds integrated | All 4 tokens |
| Cross-chain token sync | Works for all tokens |
| Frontend token selection | Intuitive UI |
| All tests pass | 100% |

---

## Dependencies

**Smart Contracts**:
- OpenZeppelin ERC20 (already installed)
- Chainlink price feeds (already integrated)

**Liquidation Bot**:
```bash
npm install ethers @chainlink/contracts dotenv
```

**Frontend**:
- Token metadata/icons
- Updated ABI for V29

---

## Risks & Mitigations

**Risk 1**: Liquidation bot not profitable on testnet
- **Mitigation**: Test with mainnet fork, adjust bonus to 10% if needed

**Risk 2**: ERC20 cross-chain sync complexity
- **Mitigation**: Reuse existing message bridge, add token parameter

**Risk 3**: Price feed failures
- **Mitigation**: Add staleness checks, revert if price > 1 hour old

**Risk 4**: Liquidation cascades (market crash)
- **Mitigation**: Add liquidation delay, circuit breakers (future)

**Risk 5**: Gas costs too high for small liquidations
- **Mitigation**: Set minimum liquidation amount, batch liquidations

---

## Post-Sprint Actions

1. **Security Audit**: Engage auditor for liquidation logic
2. **Mainnet Preparation**: Test on mainnet fork with real prices
3. **Bot Monitoring**: Set up alerts for bot failures
4. **Documentation**: Update user guide with liquidation warnings
5. **Sprint 12**: Consider governance, flash loans, or mainnet deployment

---

## Comparison with Competitors

### vs. Aave

| Feature | Aave | Fusion Prime V29 | Status |
|---------|------|------------------|--------|
| Liquidations | ✅ | ✅ | **Achieved** |
| Multi-Currency | ✅ | ✅ | **Achieved** |
| Cross-Chain Unified | ❌ | ✅ | **Advantage** |
| Flash Loans | ✅ | ❌ | Aave ahead |
| Governance | ✅ | ❌ | Aave ahead |

### vs. Compound

| Feature | Compound | Fusion Prime V29 | Status |
|---------|----------|------------------|--------|
| Liquidations | ✅ | ✅ | **Achieved** |
| Multi-Currency | ✅ | ✅ | **Achieved** |
| Cross-Chain | ❌ | ✅ | **Advantage** |
| cToken Model | ✅ | Different | Different approach |

---

**Document Version**: 1.0  
**Status**: 📋 Planned  
**Predecessor**: Sprint 10 (Cross-Chain Liquidity)  
**Successor**: Sprint 12 (TBD - Governance or Mainnet)
