# CrossChainVault V20: Safety Features Deployment

## Overview

V20 introduces critical safety features to prevent permanent out-of-sync states between cross-chain vaults. These features were implemented in response to the issue discovered in V19 where insufficient gas payment caused failed cross-chain messages and permanent balance inconsistencies.

## Problem Statement

### Issue in V19
When a user deposited on Polygon Amoy with insufficient gas (0.001 ETH instead of required 0.01 ETH):
- Transaction: https://testnet.axelarscan.io/gmp/0xc5bff02619039addf839d5801f4e896a2271343ad4746371deb4b995759c37ef-6
- Error: "Insufficient Fee"
- Result: Message stuck at "Waiting for Finality"

### Impact
- Local deposit succeeded immediately on Amoy (0.01 ETH deposited)
- Cross-chain message to Sepolia FAILED due to insufficient gas
- Sepolia vault never received balance update
- **Permanent out-of-sync state**: Amoy showed 0.021 ETH, Sepolia showed 0.011 ETH
- No automatic recovery mechanism existed

## V20 Safety Features

### 1. MIN_GAS_AMOUNT Enforcement

**Location**: `src/CrossChainVault.sol:60`

```solidity
/// @notice Minimum gas amount required for cross-chain messages
/// @dev Set to 0.01 ETH to ensure sufficient gas for Axelar/CCIP messages
/// @dev Any overpayment is automatically refunded by Axelar
uint256 public constant MIN_GAS_AMOUNT = 0.01 ether;
```

**Enforcement Points**:
- `depositCollateral()` (line 171-173)
- `withdrawCollateral()` (line 191-193)
- `borrow()` (line 213-215)

**Error**:
```solidity
error InsufficientGasAmount(uint256 provided, uint256 required);
```

**Behavior**:
- Transactions revert BEFORE any state changes if gas < 0.01 ETH
- Prevents users from creating out-of-sync state
- Clear error message shows required vs provided gas

### 2. Manual Sync Function

**Location**: `src/CrossChainVault.sol:249-288`

```solidity
function manualSync(address user, string memory destinationChain, uint256 gasAmount) external payable
```

**Purpose**: Re-broadcast current balance to a specific chain for recovery

**Use Case**: When a cross-chain message fails (e.g., insufficient gas, network issue)

**Example Recovery**:
```bash
# User had 0.021 ETH on Amoy but Sepolia only shows 0.011 ETH
# Call manualSync from Amoy to sync Sepolia

cast send 0xb0e352b60264C926f7B19F0fC5A1eeE499163c19 \
  "manualSync(address,string,uint256)" \
  0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA \
  "ethereum" \
  10000000000000000 \
  --value 10000000000000000 \
  --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY
```

**Validation**:
- Enforces MIN_GAS_AMOUNT (0.01 ETH)
- Requires destination chain to be supported
- Cannot sync to same chain
- Requires non-zero collateral

**Event**:
```solidity
event ManualSyncInitiated(address indexed user, string destinationChain, uint256 gasAmount);
```

### 3. Reconcile Balance Function

**Location**: `src/CrossChainVault.sol:290-308`

```solidity
function reconcileBalance(address user, uint256 gasAmount) external payable
```

**Purpose**: Emergency function to re-sync ALL chains with current state

**Use Case**: Fix out-of-sync state across multiple chains simultaneously

**Example**:
```bash
# Re-broadcast current Amoy balance to all other chains
cast send 0xb0e352b60264C926f7B19F0fC5A1eeE499163c19 \
  "reconcileBalance(address,uint256)" \
  0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA \
  10000000000000000 \
  --value 10000000000000000 \
  --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY
```

**Behavior**:
- Re-uses `_broadcastCollateralUpdate()` to send current state to all chains
- Gas divided equally among destination chains
- Enforces MIN_GAS_AMOUNT validation

## Frontend Updates

### Gas Fee Display

**Location**: `frontend/risk-dashboard/src/pages/cross-chain/VaultManagement.tsx`

**Changes**:
1. Added `MIN_GAS_AMOUNT` constant (line 15)
2. Blue info banners showing gas fee requirements
3. Total cost calculation displayed to users
4. Gas amount added to withdraw function (was missing in V19)

**Deposit Card**:
```typescript
// Gas Fee Info Banner
<div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
  <p className="text-xs text-blue-800">
    <strong>Cross-Chain Gas Fee:</strong> {MIN_GAS_AMOUNT} {chainId === sepolia.id ? 'ETH' : 'MATIC'}
    will be added automatically for message delivery. Any excess will be refunded.
  </p>
</div>

// Total cost display
{depositAmount && parseFloat(depositAmount) > 0 && (
  <p className="mt-1 text-xs text-gray-500">
    Total cost: {(parseFloat(depositAmount) + parseFloat(MIN_GAS_AMOUNT)).toFixed(4)}
    {chainId === sepolia.id ? 'ETH' : 'MATIC'} (includes {MIN_GAS_AMOUNT} gas)
  </p>
)}
```

### Updated ABI

**Location**: `frontend/risk-dashboard/src/abis/CrossChainVault.json`

Includes new functions:
- `MIN_GAS_AMOUNT()` view
- `manualSync(address,string,uint256)` payable
- `reconcileBalance(address,uint256)` payable

## Deployment Details

### V20 Addresses

**Ethereum Sepolia (Chain ID: 11155111)**:
- CrossChainVault: `0x5820443E51ED666cDFe3d19f293f72CD61829C5d`
- BridgeManager: `0x169a745617FbeD172C2eDcB5172CFE6c84515d1b`
- AxelarAdapter: `0x62A1Aa8b31C3ab1f25D9637D2ef66C3d37e416eA`
- CCIPAdapter: `0x5Ac2Ccb1D08A2046881F13e7D0639AfD212e4086`

**Polygon Amoy (Chain ID: 80002)**:
- CrossChainVault: `0xb0e352b60264C926f7B19F0fC5A1eeE499163c19`
- BridgeManager: `0x169a745617FbeD172C2eDcB5172CFE6c84515d1b` (same as Sepolia via CREATE2)
- AxelarAdapter: `0x62A1Aa8b31C3ab1f25D9637D2ef66C3d37e416eA` (same as Sepolia via CREATE2)
- CCIPAdapter: `0xd3875fcE61215E2EBFFD21fB82Dd57a6A017B223`

### Configuration

TrustedVaults configured bidirectionally:
- Sepolia vault trusts Amoy vault (`0xb0e352b60264C926f7B19F0fC5A1eeE499163c19`)
- Amoy vault trusts Sepolia vault (`0x5820443E51ED666cDFe3d19f293f72CD61829C5d`)

Preferred protocol: Axelar (for both chains)

### Deployment Salt

```solidity
bytes32 salt = keccak256("CrossChainVault-V20-SafetyFeatures");
```

This enables CREATE2 deterministic deployment:
- BridgeManager and AxelarAdapter have SAME addresses on both chains
- Simplifies multi-chain setup and verification

## Testing Recovery Scenarios

### Scenario 1: Failed Cross-Chain Message

**Setup**:
1. User deposits on Sepolia with 0.01 ETH + 0.01 ETH gas
2. Cross-chain message succeeds
3. Balances in sync

**Recovery Test** (simulating old V19 issue):
Cannot occur in V20 due to MIN_GAS_AMOUNT enforcement

### Scenario 2: Manual Sync After Out-of-Sync

**If** you have an out-of-sync state from V19:

```bash
# Step 1: Check current balances on both chains
cast call 0x5820443E51ED666cDFe3d19f293f72CD61829C5d \
  "getTotalCollateral(address)(uint256)" \
  0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA \
  --rpc-url https://sepolia.infura.io/v3/YOUR_KEY

cast call 0xb0e352b60264C926f7B19F0fC5A1eeE499163c19 \
  "getTotalCollateral(address)(uint256)" \
  0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA \
  --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY

# Step 2: If balances differ, use manualSync from the chain with higher balance
# (Amoy has 0.021, Sepolia has 0.011 - sync from Amoy)
cast send 0xb0e352b60264C926f7B19F0fC5A1eeE499163c19 \
  "manualSync(address,string,uint256)" \
  0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA \
  "ethereum" \
  10000000000000000 \
  --value 10000000000000000 \
  --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY \
  --private-key YOUR_KEY

# Step 3: Wait for Axelar relayer to execute (check Axelarscan)
# Step 4: Verify balances are now in sync
```

## Comparison: V19 vs V20

| Feature | V19 | V20 |
|---------|-----|-----|
| **Gas Validation** | None - accepted any amount | MIN_GAS_AMOUNT (0.01 ETH) enforced |
| **Failed Message Handling** | Permanent out-of-sync | Manual recovery functions |
| **User Experience** | Silent failures possible | Clear error messages, gas fee display |
| **Recovery Mechanism** | None | `manualSync()` and `reconcileBalance()` |
| **Frontend Gas Display** | None | Blue info banners with total cost |
| **Withdraw Gas** | Missing | Fixed - now includes gas payment |

## Migration from V19 to V20

### For Users with Existing Balances

**Option 1**: Withdraw from V19 and re-deposit in V20
```bash
# 1. Withdraw from V19 on both chains
# 2. Deposit into V20 with correct gas (0.01 ETH)
```

**Option 2**: Continue using V19 but be cautious
- Always use 0.01 ETH gas manually
- Monitor Axelarscan for message status
- Use manualSync if needed (not available in V19)

### For New Users

Start directly with V20:
- Frontend already updated to V20 addresses
- Minimum gas automatically enforced
- Recovery functions available if needed

## Production Readiness

V20 addresses the critical production issue of permanent out-of-sync state:

✅ **Prevention**: MIN_GAS_AMOUNT enforcement stops issues before they start
✅ **Detection**: Clear error messages when gas is insufficient
✅ **Recovery**: Manual sync and reconciliation functions
✅ **User Experience**: Gas fee transparency in UI
✅ **Testing**: Can safely test recovery scenarios

## Next Steps

1. ✅ Deploy V20 on Sepolia
2. ✅ Deploy V20 on Polygon Amoy
3. ✅ Configure trustedVaults bidirectionally
4. ✅ Update frontend with V20 addresses
5. ⏳ Test deposit with correct gas (0.01 ETH)
6. ⏳ Verify automatic cross-chain sync
7. ⏳ Test manualSync recovery function
8. ⏳ Monitor for any edge cases

## Support

For issues or questions:
- Check Axelarscan for message status
- Review contract events for detailed error info
- Use manualSync for recovery from failed messages
- Contact development team for critical issues
