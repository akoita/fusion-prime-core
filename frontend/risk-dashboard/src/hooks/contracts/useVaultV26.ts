import { useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { Address, formatEther, parseEther } from 'viem';
import { sepolia } from 'wagmi/chains';
import { polygonAmoy } from '@/config/chains';
import { CONTRACT_ADDRESSES } from '@/config/contracts';
import CrossChainVaultV26ABI from '@/abis/CrossChainVaultV26.json';

/**
 * Get the V26 vault address for the current chain
 */
export function getVaultV26Address(chainId: number): Address {
  if (chainId === sepolia.id) {
    return '0xae5D920fd1bCfEdF7c574B9bA5f40D0043A24C9d' as Address;
  } else if (chainId === polygonAmoy.id) {
    return '0x4f884aaa05F721036Ee643c6B24f2023b44D8e43' as Address;
  }
  return '0xae5D920fd1bCfEdF7c574B9bA5f40D0043A24C9d' as Address;
}

/**
 * Get chain name from chain ID
 */
function getChainName(chainId: number): string {
  if (chainId === sepolia.id) return 'ethereum';
  if (chainId === polygonAmoy.id) return 'polygon';
  return 'ethereum';
}

// ============================================
// SUPPLY/LEND HOOKS
// ============================================

/**
 * Hook to supply liquidity to the pool
 */
export function useSupplyLiquidity(chainId: number = sepolia.id) {
  const { writeContract, data: hash, isPending, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const supply = (amount: bigint, gasAmount: bigint = parseEther('0.01')) => {
    const vaultAddress = getVaultV26Address(chainId);

    writeContract({
      address: vaultAddress,
      abi: CrossChainVaultV26ABI,
      functionName: 'supply',
      args: [gasAmount],
      value: amount + gasAmount,
    });
  };

  return {
    supply,
    hash,
    isPending,
    isConfirming,
    isSuccess,
    error,
  };
}

/**
 * Hook to withdraw supplied liquidity
 */
export function useWithdrawSupplied(chainId: number = sepolia.id) {
  const { writeContract, data: hash, isPending, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const withdraw = (amount: bigint, gasAmount: bigint = parseEther('0.01')) => {
    const vaultAddress = getVaultV26Address(chainId);

    writeContract({
      address: vaultAddress,
      abi: CrossChainVaultV26ABI,
      functionName: 'withdrawSupplied',
      args: [amount, gasAmount],
      value: gasAmount,
    });
  };

  return {
    withdraw,
    hash,
    isPending,
    isConfirming,
    isSuccess,
    error,
  };
}

/**
 * Hook to get user's supplied balance with pending interest
 */
export function useSuppliedBalance(
  userAddress?: Address,
  chainId: number = sepolia.id
) {
  const vaultAddress = getVaultV26Address(chainId);
  const chainName = getChainName(chainId);

  const { data, isLoading, isError, refetch } = useReadContract({
    address: vaultAddress,
    abi: CrossChainVaultV26ABI,
    functionName: 'getSuppliedBalanceWithInterest',
    args: userAddress ? [userAddress, chainName] : undefined,
    query: {
      enabled: !!userAddress,
      refetchInterval: 10000,
    },
  });

  return {
    suppliedBalance: (data as bigint) || 0n,
    isLoading,
    isError,
    refetch,
  };
}

// ============================================
// APY & INTEREST RATE HOOKS
// ============================================

/**
 * Hook to get current supply APY for a chain
 */
export function useSupplyAPY(chainId: number = sepolia.id) {
  const vaultAddress = getVaultV26Address(chainId);
  const chainName = getChainName(chainId);

  const { data, isLoading, isError, refetch } = useReadContract({
    address: vaultAddress,
    abi: CrossChainVaultV26ABI,
    functionName: 'getSupplyAPY',
    args: [chainName],
    query: {
      refetchInterval: 30000, // Refetch every 30 seconds
    },
  });

  // Convert from 18 decimals to percentage
  const apyPercentage = data
    ? Number(data as bigint) / 1e16 // Divide by 1e16 to get percentage (1e18 / 100)
    : 0;

  return {
    supplyAPY: data as bigint || 0n,
    apyPercentage,
    isLoading,
    isError,
    refetch,
  };
}

/**
 * Hook to get current borrow APY for a chain
 */
export function useBorrowAPY(chainId: number = sepolia.id) {
  const vaultAddress = getVaultV26Address(chainId);
  const chainName = getChainName(chainId);

  const { data, isLoading, isError, refetch } = useReadContract({
    address: vaultAddress,
    abi: CrossChainVaultV26ABI,
    functionName: 'getBorrowAPY',
    args: [chainName],
    query: {
      refetchInterval: 30000,
    },
  });

  const apyPercentage = data
    ? Number(data as bigint) / 1e16
    : 0;

  return {
    borrowAPY: data as bigint || 0n,
    apyPercentage,
    isLoading,
    isError,
    refetch,
  };
}

// ============================================
// LIQUIDITY POOL HOOKS
// ============================================

/**
 * Hook to get available liquidity in the pool
 */
export function useAvailableLiquidity(chainId: number = sepolia.id) {
  const vaultAddress = getVaultV26Address(chainId);
  const chainName = getChainName(chainId);

  const { data, isLoading, isError, refetch } = useReadContract({
    address: vaultAddress,
    abi: CrossChainVaultV26ABI,
    functionName: 'getAvailableLiquidity',
    args: [chainName],
    query: {
      refetchInterval: 10000,
    },
  });

  return {
    availableLiquidity: (data as bigint) || 0n,
    isLoading,
    isError,
    refetch,
  };
}

/**
 * Hook to get pool utilization rate
 */
export function useUtilizationRate(chainId: number = sepolia.id) {
  const vaultAddress = getVaultV26Address(chainId);
  const chainName = getChainName(chainId);

  const { data, isLoading, isError, refetch } = useReadContract({
    address: vaultAddress,
    abi: CrossChainVaultV26ABI,
    functionName: 'getUtilizationRate',
    args: [chainName],
    query: {
      refetchInterval: 30000,
    },
  });

  // Convert from 18 decimals to percentage
  const utilizationPercentage = data
    ? Number(data as bigint) / 1e16
    : 0;

  return {
    utilizationRate: data as bigint || 0n,
    utilizationPercentage,
    isLoading,
    isError,
    refetch,
  };
}

/**
 * Hook to get total liquidity and utilization for a chain
 */
export function usePoolStats(chainId: number = sepolia.id) {
  const vaultAddress = getVaultV26Address(chainId);
  const chainName = getChainName(chainId);

  // Get total liquidity
  const { data: totalLiquidity, isLoading: loadingLiquidity } = useReadContract({
    address: vaultAddress,
    abi: CrossChainVaultV26ABI,
    functionName: 'chainLiquidity',
    args: [chainName],
    query: {
      refetchInterval: 10000,
    },
  });

  // Get utilized liquidity
  const { data: utilized, isLoading: loadingUtilized } = useReadContract({
    address: vaultAddress,
    abi: CrossChainVaultV26ABI,
    functionName: 'chainUtilized',
    args: [chainName],
    query: {
      refetchInterval: 10000,
    },
  });

  const totalLiquidityBigInt = (totalLiquidity as bigint) || 0n;
  const utilizedBigInt = (utilized as bigint) || 0n;
  const available = totalLiquidityBigInt - utilizedBigInt;

  return {
    totalLiquidity: totalLiquidityBigInt,
    utilized: utilizedBigInt,
    available,
    isLoading: loadingLiquidity || loadingUtilized,
  };
}

// ============================================
// COMBINED DASHBOARD HOOK
// ============================================

/**
 * Hook to get complete pool and user stats for dashboard
 */
export function useSupplyDashboard(
  userAddress?: Address,
  chainId: number = sepolia.id
) {
  const { suppliedBalance, isLoading: loadingBalance, refetch: refetchBalance } =
    useSuppliedBalance(userAddress, chainId);

  const { apyPercentage: supplyAPY, isLoading: loadingSupplyAPY } =
    useSupplyAPY(chainId);

  const { apyPercentage: borrowAPY, isLoading: loadingBorrowAPY } =
    useBorrowAPY(chainId);

  const { utilizationPercentage, isLoading: loadingUtilization } =
    useUtilizationRate(chainId);

  const { totalLiquidity, utilized, available, isLoading: loadingPool } =
    usePoolStats(chainId);

  // Calculate estimated earnings per day
  const dailyEarnings = suppliedBalance > 0n
    ? (suppliedBalance * BigInt(Math.floor(supplyAPY * 100))) / (365n * 10000n)
    : 0n;

  return {
    // User stats
    suppliedBalance,
    dailyEarnings,

    // Pool stats
    totalLiquidity,
    utilized,
    available,
    utilizationPercentage,
    supplyAPY,
    borrowAPY,

    // Loading states
    isLoading: loadingBalance || loadingSupplyAPY || loadingBorrowAPY ||
               loadingUtilization || loadingPool,

    // Actions
    refetch: refetchBalance,
  };
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Format APY for display
 */
export function formatAPY(apy: bigint): string {
  const percentage = Number(apy) / 1e16;
  return `${percentage.toFixed(2)}%`;
}

/**
 * Format utilization rate for display
 */
export function formatUtilization(rate: bigint): string {
  const percentage = Number(rate) / 1e16;
  return `${percentage.toFixed(2)}%`;
}

/**
 * Calculate estimated earnings
 * @param principal Amount supplied
 * @param apyPercent APY as percentage (e.g., 7 for 7%)
 * @param days Number of days
 */
export function calculateEarnings(
  principal: bigint,
  apyPercent: number,
  days: number
): bigint {
  if (principal === 0n || apyPercent === 0) return 0n;

  const apyBigInt = BigInt(Math.floor(apyPercent * 100)); // Convert to basis points
  const daysBigInt = BigInt(days);

  return (principal * apyBigInt * daysBigInt) / (365n * 10000n);
}

/**
 * Get utilization status color
 */
export function getUtilizationStatus(utilizationPercent: number): {
  status: 'low' | 'medium' | 'high' | 'critical';
  color: string;
  label: string;
} {
  if (utilizationPercent < 25) {
    return { status: 'low', color: 'green', label: 'Low Utilization' };
  } else if (utilizationPercent < 50) {
    return { status: 'medium', color: 'blue', label: 'Medium Utilization' };
  } else if (utilizationPercent < 75) {
    return { status: 'high', color: 'yellow', label: 'High Utilization' };
  } else {
    return { status: 'critical', color: 'orange', label: 'Critical Utilization' };
  }
}
