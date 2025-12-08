# Cross-Chain Gas Requirements for V20

## Issue Summary

**Date**: 2025-11-08
**Version**: V20
**Problem**: Insufficient gas causing failed cross-chain synchronization

## Root Cause

V20 was deployed with `MIN_GAS_AMOUNT = 0.01 ether`, which is **insufficient** for Axelar testnet relayers to process cross-chain messages.

## Evidence

### Failed Transaction
- **TX Hash**: `0xef28f8108134808f59f75e27d6c27830943b5c79ef92afde808c864ca4d4a031`
- **Source**: Polygon Amoy
- **Destination**: Ethereum Sepolia
- **Gas Paid**: 0.01 ETH
- **Status**: "Insufficient Fee" (Axelarscan)
- **Message ID**: `0x2d66a73bc4b0922952692a86c856e51b20c41dbed2287aa8fd4738cd9fc783ea`

### Recovery Attempt #1: addNativeGas()
- **Rescue TX**: `0xfb6a79b4ac0b1bdf50479da96d3a5c3f761f2c686f1a8b501446070d5f2a8384`
- **Method**: `addNativeGas()` on AxelarGasService
- **Additional Gas**: 0.05 ETH
- **Total Gas**: 0.06 ETH (0.01 + 0.05)
- **Result**: Still insufficient - message not processed after 10+ minutes

### Recovery Attempt #2: manualSync()
- **Manual Sync TX**: `0x1191b6a87495d9468c6567827a41f13be71032b243d8aae67cd832b3265d8307`
- **Method**: `manualSync()` function (V20 recovery feature)
- **Gas Paid**: 0.1 ETH (10x original amount)
- **New Message ID**: `0x395162e0158218a80f9ef9730ac99a34fe64fbed47f12ec48228dfc73ae2a362`
- **Status**: Monitoring - waiting for Axelar processing

## Recommended Fix for V21

```solidity
/// @notice Minimum gas amount required for cross-chain messages
/// @dev Testnets require 0.1 ETH minimum based on empirical testing
/// @dev 0.01 ETH failed, 0.06 ETH failed, testing 0.1 ETH
/// @dev Mainnet will be much lower as native tokens have actual value
/// @dev Any overpayment is automatically refunded by Axelar
uint256 public constant MIN_GAS_AMOUNT = 0.1 ether; // Increased from 0.01
```

## Testnet vs Mainnet Considerations

### Testnets (Sepolia, Amoy)
- Native tokens have no value
- Relayers set VERY high minimum thresholds
- **Tested**: 0.01 ETH ❌ Failed
- **Tested**: 0.06 ETH ❌ Failed (still insufficient after 10+ min)
- **Testing**: 0.1 ETH ⏳ In progress
- **Recommended**: 0.1 ETH minimum (may need even higher)

### Mainnet (Ethereum, Polygon)
- Native tokens have real value
- Relayers accept lower fees
- **Recommended**: Start at 0.01 ETH, adjust based on monitoring

## Gas Estimation Best Practices

1. **Always overpay**: Axelar refunds excess gas automatically
2. **Use estimateGasFee()**: Check AxelarGasService before sending
3. **Monitor failures**: Track insufficient fee errors in production
4. **Add gas recovery**: Use `addNativeGas()` to rescue failed messages

## Recovery Mechanism

V20 includes `manualSync()` function for recovering from failed cross-chain messages:

```solidity
function manualSync(
    address user,
    string memory destinationChain,
    uint256 gasAmount
) external payable
```

**Usage**: If a cross-chain message fails due to insufficient gas:
1. Use `addNativeGas()` to add more gas to original message, OR
2. Use `manualSync()` to send a new sync message with higher gas

## Action Items

- [ ] Test if 0.06 ETH is sufficient for Amoy → Sepolia messages
- [ ] Deploy V21 with increased `MIN_GAS_AMOUNT = 0.05 ether`
- [ ] Update frontend hooks to use 0.05 ETH default
- [ ] Add gas estimation calls to frontend before transactions
- [ ] Monitor Axelarscan for any future insufficient fee errors

## References

- Axelar Docs: https://docs.axelar.dev/dev/gas-service/pay-gas/
- Increase Gas: https://docs.axelar.dev/dev/gas-service/increase-gas/
- Axelarscan Testnet: https://testnet.axelarscan.io/
