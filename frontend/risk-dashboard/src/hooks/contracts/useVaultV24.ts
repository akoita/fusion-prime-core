import { useReadContract } from 'wagmi';
import { Address, formatEther } from 'viem';
import { sepolia, polygonAmoy } from '@/config/chains';
import { CONTRACT_ADDRESSES } from '@/config/contracts';
import CrossChainVaultV24ABI from '@/abis/CrossChainVaultV24.json';

/**
 * Get the vault address for the current chain
 */
export function getVaultAddress(chainId: number): Address {
  if (chainId === sepolia.id) {
    return CONTRACT_ADDRESSES.SEPOLIA_VAULT_V24;
  } else if (chainId === polygonAmoy.id) {
    return CONTRACT_ADDRESSES.AMOY_VAULT_V24;
  }
  return CONTRACT_ADDRESSES.SEPOLIA_VAULT_V24; // Default to Sepolia
}

/**
 * Hook to get user's complete financial summary in USD
 * Returns all values in USD (18 decimals)
 */
export function useVaultSummaryUSD(userAddress?: Address, chainId: number = sepolia.id) {
  const vaultAddress = getVaultAddress(chainId);

  const { data, isLoading, isError, refetch } = useReadContract({
    address: vaultAddress,
    abi: CrossChainVaultV24ABI,
    functionName: 'getUserSummaryUSD',
    args: userAddress ? [userAddress] : undefined,
    query: {
      enabled: !!userAddress,
      refetchInterval: 10000, // Refetch every 10 seconds
    },
  });

  if (!data || !Array.isArray(data)) {
    return {
      collateralUSD: 0n,
      borrowedUSD: 0n,
      creditLineUSD: 0n,
      healthFactor: 0n,
      availableUSD: 0n,
      isLoading,
      isError,
      refetch,
    };
  }

  return {
    collateralUSD: data[0] as bigint,
    borrowedUSD: data[1] as bigint,
    creditLineUSD: data[2] as bigint,
    healthFactor: data[3] as bigint,
    availableUSD: data[4] as bigint,
    isLoading,
    isError,
    refetch,
  };
}

/**
 * Hook to get health factor
 * Returns health factor with 18 decimals (1e18 = 100%)
 *
 * Examples:
 * - 2.0e18 = Very healthy (200%)
 * - 1.5e18 = Healthy (150%)
 * - 1.1e18 = Warning (110%)
 * - 1.0e18 = At liquidation threshold
 * - <1.0e18 = Can be liquidated
 */
export function useHealthFactor(userAddress?: Address, chainId: number = sepolia.id) {
  const vaultAddress = getVaultAddress(chainId);

  const { data, isLoading, isError, refetch } = useReadContract({
    address: vaultAddress,
    abi: CrossChainVaultV24ABI,
    functionName: 'getHealthFactor',
    args: userAddress ? [userAddress] : undefined,
    query: {
      enabled: !!userAddress,
      refetchInterval: 10000,
    },
  });

  return {
    healthFactor: (data as bigint) || 0n,
    isLoading,
    isError,
    refetch,
  };
}

/**
 * Hook to get total collateral value in USD across ALL chains
 */
export function useTotalCollateralUSD(userAddress?: Address, chainId: number = sepolia.id) {
  const vaultAddress = getVaultAddress(chainId);

  const { data, isLoading, isError, refetch } = useReadContract({
    address: vaultAddress,
    abi: CrossChainVaultV24ABI,
    functionName: 'getTotalCollateralValueUSD',
    args: userAddress ? [userAddress] : undefined,
    query: {
      enabled: !!userAddress,
      refetchInterval: 10000,
    },
  });

  return {
    totalCollateralUSD: (data as bigint) || 0n,
    isLoading,
    isError,
    refetch,
  };
}

/**
 * Hook to get total borrowed value in USD across ALL chains
 */
export function useTotalBorrowedUSD(userAddress?: Address, chainId: number = sepolia.id) {
  const vaultAddress = getVaultAddress(chainId);

  const { data, isLoading, isError, refetch } = useReadContract({
    address: vaultAddress,
    abi: CrossChainVaultV24ABI,
    functionName: 'getTotalBorrowedValueUSD',
    args: userAddress ? [userAddress] : undefined,
    query: {
      enabled: !!userAddress,
      refetchInterval: 10000,
    },
  });

  return {
    totalBorrowedUSD: (data as bigint) || 0n,
    isLoading,
    isError,
    refetch,
  };
}

/**
 * Hook to get credit line in USD (70% of collateral value)
 */
export function useCreditLineUSD(userAddress?: Address, chainId: number = sepolia.id) {
  const vaultAddress = getVaultAddress(chainId);

  const { data, isLoading, isError, refetch } = useReadContract({
    address: vaultAddress,
    abi: CrossChainVaultV24ABI,
    functionName: 'getCreditLineUSD',
    args: userAddress ? [userAddress] : undefined,
    query: {
      enabled: !!userAddress,
      refetchInterval: 10000,
    },
  });

  return {
    creditLineUSD: (data as bigint) || 0n,
    isLoading,
    isError,
    refetch,
  };
}

/**
 * Hook to get per-chain breakdown in USD
 */
export function useChainBreakdownUSD(
  userAddress?: Address,
  chainName?: string,
  chainId: number = sepolia.id
) {
  const vaultAddress = getVaultAddress(chainId);

  const { data, isLoading, isError, refetch } = useReadContract({
    address: vaultAddress,
    abi: CrossChainVaultV24ABI,
    functionName: 'getChainBreakdownUSD',
    args: userAddress && chainName ? [userAddress, chainName] : undefined,
    query: {
      enabled: !!userAddress && !!chainName,
      refetchInterval: 10000,
    },
  });

  if (!data || !Array.isArray(data)) {
    return {
      collateralNative: 0n,
      collateralUSD: 0n,
      borrowedNative: 0n,
      borrowedUSD: 0n,
      isLoading,
      isError,
      refetch,
    };
  }

  return {
    collateralNative: data[0] as bigint,
    collateralUSD: data[1] as bigint,
    borrowedNative: data[2] as bigint,
    borrowedUSD: data[3] as bigint,
    isLoading,
    isError,
    refetch,
  };
}

/**
 * Utility to format health factor as a percentage
 * @param healthFactor Health factor with 18 decimals
 * @returns Percentage string (e.g., "150%")
 */
export function formatHealthFactor(healthFactor: bigint): string {
  if (healthFactor === 0n) return '0%';

  // Check if infinite (max uint256)
  const maxUint256 = BigInt('115792089237316195423570985008687907853269984665640564039457584007913129639935');
  if (healthFactor === maxUint256) return '∞';

  // Convert to percentage: (healthFactor / 1e18) * 100
  const percentage = Number(healthFactor * 100n / BigInt(1e18));
  return `${percentage.toFixed(2)}%`;
}

/**
 * Utility to get health factor status
 */
export function getHealthFactorStatus(healthFactor: bigint): {
  status: 'excellent' | 'healthy' | 'warning' | 'danger' | 'liquidatable';
  color: string;
  label: string;
} {
  if (healthFactor === 0n) {
    return { status: 'liquidatable', color: 'red', label: 'Liquidatable' };
  }

  // Check if infinite
  const maxUint256 = BigInt('115792089237316195423570985008687907853269984665640564039457584007913129639935');
  if (healthFactor === maxUint256) {
    return { status: 'excellent', color: 'green', label: 'No Debt' };
  }

  // Convert to decimal for comparison
  const hfDecimal = Number(healthFactor) / Number(1e18);

  if (hfDecimal >= 2.0) {
    return { status: 'excellent', color: 'green', label: 'Excellent' };
  } else if (hfDecimal >= 1.5) {
    return { status: 'healthy', color: 'blue', label: 'Healthy' };
  } else if (hfDecimal >= 1.1) {
    return { status: 'warning', color: 'yellow', label: 'Warning' };
  } else if (hfDecimal >= 1.0) {
    return { status: 'danger', color: 'orange', label: 'Danger' };
  } else {
    return { status: 'liquidatable', color: 'red', label: 'Liquidatable' };
  }
}

/**
 * Utility to format USD value
 * @param usdValue USD value with 18 decimals
 * @param decimals Number of decimal places to show
 * @returns Formatted USD string (e.g., "$1,234.56")
 */
export function formatUSD(usdValue: bigint, decimals: number = 2): string {
  const value = Number(formatEther(usdValue));
  return `$${value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}
