/**
 * Gas limit configuration for V23 CrossChainVault operations
 *
 * V23 vaults broadcast cross-chain messages for every operation,
 * which requires more gas than simple single-chain operations.
 *
 * These limits include a 20% safety buffer above the typical gas usage:
 * - Typical usage: ~500k gas
 * - With buffer: 600k gas
 */

export const GAS_LIMITS = {
  /**
   * Gas limit for deposit operations
   * Includes: local storage update + cross-chain message broadcasting
   */
  DEPOSIT: 600000n,

  /**
   * Gas limit for withdrawal operations
   * Includes: local storage update + cross-chain message broadcasting
   */
  WITHDRAW: 600000n,

  /**
   * Gas limit for borrow operations
   * Includes: local storage update + cross-chain message broadcasting
   */
  BORROW: 600000n,

  /**
   * Gas limit for repay operations
   * Typically lower since it doesn't broadcast cross-chain messages
   */
  REPAY: 300000n,

  /**
   * Gas limit for reconcileBalance operations
   * Used for manual state synchronization
   */
  RECONCILE: 600000n,
} as const;

/**
 * Default cross-chain gas payment amount
 * This is sent to MessageBridge for relayer incentivization (currently unused)
 */
export const DEFAULT_CROSS_CHAIN_GAS = '0.01' as const;

/**
 * Helper function to get user-friendly error messages for common issues
 */
export function getTransactionErrorMessage(error: Error | null): string {
  if (!error) return 'Transaction failed';

  const errorMessage = error.message.toLowerCase();

  // Out of gas errors
  if (errorMessage.includes('out of gas') || errorMessage.includes('gas required exceeds')) {
    return 'Transaction ran out of gas. This is a temporary issue - please try again. The gas limit has been increased automatically.';
  }

  // User rejected
  if (errorMessage.includes('user rejected') || errorMessage.includes('user denied')) {
    return 'Transaction was cancelled';
  }

  // Insufficient funds
  if (errorMessage.includes('insufficient funds')) {
    return 'Insufficient balance to cover transaction cost and gas fees';
  }

  // Network issues
  if (errorMessage.includes('network') || errorMessage.includes('connection')) {
    return 'Network connection issue. Please check your internet connection and try again.';
  }

  // Contract-specific errors
  if (errorMessage.includes('insufficient collateral')) {
    return 'Insufficient collateral for this operation';
  }

  if (errorMessage.includes('unsupported chain')) {
    return 'This chain is not supported for cross-chain operations';
  }

  if (errorMessage.includes('message already')) {
    return 'This message has already been processed';
  }

  // Generic fallback
  return `Transaction failed: ${error.message.slice(0, 100)}`;
}
