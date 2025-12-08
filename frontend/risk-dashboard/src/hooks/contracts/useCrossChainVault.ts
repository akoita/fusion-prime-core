import { useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { parseEther, type Address } from 'viem';
import { sepolia } from 'wagmi/chains';
import { CONTRACTS } from '@/config/chains';
import { polygonAmoy } from '@/config/chains';
import CrossChainVaultABI from '@/abis/CrossChainVault.json';
import { GAS_LIMITS, DEFAULT_CROSS_CHAIN_GAS, getTransactionErrorMessage } from '@/config/gasLimits';

/**
 * Hook to read user's total collateral across all chains
 *
 * @param userAddress - The address to query collateral for
 * @param chainId - The chain ID to query (optional, defaults to Sepolia)
 * @returns Object containing total collateral, loading state, and error
 *
 * @example
 * const { data: totalCollateral } = useTotalCollateral(userAddress);
 */
export function useTotalCollateral(userAddress?: Address, chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  return useReadContract({
    address: contractAddress,
    abi: CrossChainVaultABI,
    functionName: 'getTotalCollateral',
    args: userAddress ? [userAddress] : undefined,
    chainId,
    query: {
      enabled: !!userAddress && !!contractAddress,
    },
  });
}

/**
 * Hook to read user's total borrowed amount across all chains
 *
 * @param userAddress - The address to query borrowed amount for
 * @param chainId - The chain ID to query
 * @returns Object containing total borrowed, loading state, and error
 *
 * @example
 * const { data: totalBorrowed } = useTotalBorrowed(userAddress);
 */
export function useTotalBorrowed(userAddress?: Address, chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  return useReadContract({
    address: contractAddress,
    abi: CrossChainVaultABI,
    functionName: 'getTotalBorrowed',
    args: userAddress ? [userAddress] : undefined,
    chainId,
    query: {
      enabled: !!userAddress && !!contractAddress,
    },
  });
}

/**
 * Hook to read user's available credit line
 *
 * @param userAddress - The address to query credit line for
 * @param chainId - The chain ID to query
 * @returns Object containing credit line, loading state, and error
 *
 * @example
 * const { data: creditLine } = useCreditLine(userAddress);
 */
export function useCreditLine(userAddress?: Address, chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  return useReadContract({
    address: contractAddress,
    abi: CrossChainVaultABI,
    functionName: 'getCreditLine',
    args: userAddress ? [userAddress] : undefined,
    chainId,
    query: {
      enabled: !!userAddress && !!contractAddress,
    },
  });
}

/**
 * Hook to read user's collateral on a specific chain
 *
 * @param userAddress - The address to query collateral for
 * @param chainName - The name of the chain (e.g., "ethereum-sepolia", "polygon-amoy")
 * @param chainId - The chain ID to query from
 * @returns Object containing collateral on chain, loading state, and error
 *
 * @example
 * const { data: collateral } = useCollateralOnChain(userAddress, 'ethereum-sepolia');
 */
export function useCollateralOnChain(
  userAddress?: Address,
  chainName?: string,
  chainId: number = sepolia.id
) {
  const contractAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  return useReadContract({
    address: contractAddress,
    abi: CrossChainVaultABI,
    functionName: 'getCollateralOnChain',
    args: userAddress && chainName ? [userAddress, chainName] : undefined,
    chainId,
    query: {
      enabled: !!userAddress && !!chainName && !!contractAddress,
    },
  });
}

/**
 * Hook to get the current chain name from the vault
 *
 * @param chainId - The chain ID to query
 * @returns Object containing chain name, loading state, and error
 *
 * @example
 * const { data: chainName } = useVaultChainName();
 */
export function useVaultChainName(chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  return useReadContract({
    address: contractAddress,
    abi: CrossChainVaultABI,
    functionName: 'thisChainName',
    chainId,
    query: {
      enabled: !!contractAddress,
    },
  });
}

/**
 * Hook to check if a chain is supported
 *
 * @param chainName - The name of the chain to check
 * @param chainId - The chain ID to query from
 * @returns Object containing boolean indicating if chain is supported
 *
 * @example
 * const { data: isSupported } = useIsChainSupported('polygon-amoy');
 */
export function useIsChainSupported(chainName?: string, chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  return useReadContract({
    address: contractAddress,
    abi: CrossChainVaultABI,
    functionName: 'supportedChains',
    args: chainName ? [chainName] : undefined,
    chainId,
    query: {
      enabled: !!chainName && !!contractAddress,
    },
  });
}

/**
 * Hook to deposit collateral to the vault
 *
 * @param chainId - The chain ID to deposit on
 * @returns Object with depositCollateral function and transaction state
 *
 * @example
 * const { depositCollateral, isLoading, isSuccess } = useDepositCollateral();
 * depositCollateral({
 *   user: '0x...',  // User address to credit
 *   amount: '1.0',  // Amount in ETH/MATIC
 * });
 */
export function useDepositCollateral(chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  /**
   * Deposit collateral
   *
   * @param user - Address to credit the collateral to
   * @param amount - Amount to deposit (as string, e.g., "1.0")
   * @param gasAmount - Amount for cross-chain gas (optional, defaults to "0.01")
   */
  const depositCollateral = ({
    user,
    amount,
    gasAmount = DEFAULT_CROSS_CHAIN_GAS,
  }: {
    user: Address;
    amount: string;
    gasAmount?: string;
  }) => {
    const depositAmountWei = parseEther(amount);
    const gasAmountWei = parseEther(gasAmount);
    const totalValue = depositAmountWei + gasAmountWei;

    console.log('[useCrossChainVault] Deposit params:', {
      user,
      amount,
      gasAmount,
      gasAmountWei: gasAmountWei.toString(),
      depositAmountWei: depositAmountWei.toString(),
      totalValue: totalValue.toString(),
    });

    writeContract({
      address: contractAddress,
      abi: CrossChainVaultABI,
      functionName: 'depositCollateral',
      args: [user, gasAmountWei],
      value: totalValue,
      gas: 600000n, // Increased for cross-chain message broadcasting (V23)
      chainId,
    });
  };

  return {
    depositCollateral,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError,
    error,
    errorMessage: error ? getTransactionErrorMessage(error) : undefined,
    txHash: hash,
  };
}

/**
 * Hook to withdraw collateral from the vault
 *
 * @param chainId - The chain ID to withdraw from
 * @returns Object with withdrawCollateral function and transaction state
 *
 * @example
 * const { withdrawCollateral, isLoading } = useWithdrawCollateral();
 * withdrawCollateral({ amount: '0.5' }); // Withdraw 0.5 ETH/MATIC
 */
export function useWithdrawCollateral(chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const withdrawCollateral = ({
    amount,
    gasAmount = DEFAULT_CROSS_CHAIN_GAS,
  }: {
    amount: string;
    gasAmount?: string;
  }) => {
    const withdrawAmountWei = parseEther(amount);
    const gasAmountWei = parseEther(gasAmount);

    writeContract({
      address: contractAddress,
      abi: CrossChainVaultABI,
      functionName: 'withdrawCollateral',
      args: [withdrawAmountWei, gasAmountWei],
      value: gasAmountWei,
      gas: GAS_LIMITS.WITHDRAW,
      chainId,
    });
  };

  return {
    withdrawCollateral,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError,
    error,
    errorMessage: error ? getTransactionErrorMessage(error) : undefined,
    txHash: hash,
  };
}

/**
 * Hook to borrow against collateral
 *
 * @param chainId - The chain ID to borrow on
 * @returns Object with borrow function and transaction state
 *
 * @example
 * const { borrow, isLoading, isSuccess } = useBorrow();
 * borrow({ amount: '0.5' }); // Borrow 0.5 ETH/MATIC
 */
export function useBorrow(chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const borrow = ({
    amount,
    gasAmount = DEFAULT_CROSS_CHAIN_GAS,
  }: {
    amount: string;
    gasAmount?: string;
  }) => {
    const borrowAmountWei = parseEther(amount);
    const gasAmountWei = parseEther(gasAmount);

    writeContract({
      address: contractAddress,
      abi: CrossChainVaultABI,
      functionName: 'borrow',
      args: [borrowAmountWei, gasAmountWei],
      value: gasAmountWei,
      gas: GAS_LIMITS.BORROW,
      chainId,
    });
  };

  return {
    borrow,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError,
    error,
    errorMessage: error ? getTransactionErrorMessage(error) : undefined,
    txHash: hash,
  };
}

/**
 * Hook to repay borrowed amount
 *
 * @param chainId - The chain ID to repay on
 * @returns Object with repay function and transaction state
 *
 * @example
 * const { repay, isLoading, isSuccess } = useRepay();
 * repay({ amount: '0.5' }); // Repay 0.5 ETH/MATIC
 */
export function useRepay(chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const repay = ({ amount }: { amount: string }) => {
    writeContract({
      address: contractAddress,
      abi: CrossChainVaultABI,
      functionName: 'repay',
      args: [parseEther(amount)],
      value: parseEther(amount),
      gas: GAS_LIMITS.REPAY,
      chainId,
    });
  };

  return {
    repay,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError,
    error,
    errorMessage: error ? getTransactionErrorMessage(error) : undefined,
    txHash: hash,
  };
}

/**
 * Hook to get all vault data for a user across both chains
 * This is a convenience hook that aggregates data from multiple chains
 *
 * @param userAddress - The address to query vault data for
 * @returns Object containing vault data from both chains
 *
 * @example
 * const { sepolia, polygonAmoy, isLoading } = useMultiChainVaultData(userAddress);
 */
export function useMultiChainVaultData(userAddress?: Address) {
  // Sepolia data
  const sepoliaCollateral = useTotalCollateral(userAddress, sepolia.id);
  const sepoliaBorrowed = useTotalBorrowed(userAddress, sepolia.id);
  const sepoliaCreditLine = useCreditLine(userAddress, sepolia.id);

  // Polygon Amoy data
  const amoyCollateral = useTotalCollateral(userAddress, polygonAmoy.id);
  const amoyBorrowed = useTotalBorrowed(userAddress, polygonAmoy.id);
  const amoyCreditLine = useCreditLine(userAddress, polygonAmoy.id);

  return {
    sepolia: {
      totalCollateral: sepoliaCollateral.data,
      totalBorrowed: sepoliaBorrowed.data,
      creditLine: sepoliaCreditLine.data,
      isLoading:
        sepoliaCollateral.isLoading ||
        sepoliaBorrowed.isLoading ||
        sepoliaCreditLine.isLoading,
      isError:
        sepoliaCollateral.isError ||
        sepoliaBorrowed.isError ||
        sepoliaCreditLine.isError,
    },
    polygonAmoy: {
      totalCollateral: amoyCollateral.data,
      totalBorrowed: amoyBorrowed.data,
      creditLine: amoyCreditLine.data,
      isLoading:
        amoyCollateral.isLoading || amoyBorrowed.isLoading || amoyCreditLine.isLoading,
      isError:
        amoyCollateral.isError || amoyBorrowed.isError || amoyCreditLine.isError,
    },
    isLoading:
      sepoliaCollateral.isLoading ||
      sepoliaBorrowed.isLoading ||
      sepoliaCreditLine.isLoading ||
      amoyCollateral.isLoading ||
      amoyBorrowed.isLoading ||
      amoyCreditLine.isLoading,
    isError:
      sepoliaCollateral.isError ||
      sepoliaBorrowed.isError ||
      sepoliaCreditLine.isError ||
      amoyCollateral.isError ||
      amoyBorrowed.isError ||
      amoyCreditLine.isError,
  };
}
