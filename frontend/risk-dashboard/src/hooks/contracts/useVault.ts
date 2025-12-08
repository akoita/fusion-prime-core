import { useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { type Address, parseEther } from 'viem';
import { sepolia } from 'wagmi/chains';
import { CONTRACTS } from '@/config/chains';
import { polygonAmoy } from '@/config/chains';
import { GAS_LIMITS } from '@/config/gasLimits';

// CrossChainVault ABI - just the functions we need
const VAULT_ABI = [
  {
    inputs: [{ name: 'user', type: 'address' }, { name: 'chain', type: 'string' }],
    name: 'collateralBalances',
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [{ name: 'user', type: 'address' }],
    name: 'totalCollateral',
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [{ name: 'user', type: 'address' }],
    name: 'totalBorrowed',
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [{ name: 'user', type: 'address' }],
    name: 'totalCreditLine',
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [{ name: 'user', type: 'address' }, { name: 'chain', type: 'string' }],
    name: 'borrowBalances',
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [{ name: 'user', type: 'address' }, { name: 'gasAmount', type: 'uint256' }],
    name: 'depositCollateral',
    outputs: [],
    stateMutability: 'payable',
    type: 'function',
  },
  {
    inputs: [{ name: 'amount', type: 'uint256' }, { name: 'gasAmount', type: 'uint256' }],
    name: 'withdrawCollateral',
    outputs: [],
    stateMutability: 'payable',
    type: 'function',
  },
  {
    inputs: [{ name: 'amount', type: 'uint256' }, { name: 'gasAmount', type: 'uint256' }],
    name: 'borrow',
    outputs: [],
    stateMutability: 'payable',
    type: 'function',
  },
  {
    inputs: [{ name: 'amount', type: 'uint256' }],
    name: 'repay',
    outputs: [],
    stateMutability: 'payable',
    type: 'function',
  },
] as const;

/**
 * Hook to get user's collateral balance for a specific chain in the vault
 */
export function useVaultCollateralBalance(
  userAddress?: Address,
  chainName?: string,
  vaultChainId: number = sepolia.id
) {
  const vaultAddress = CONTRACTS[vaultChainId]?.CrossChainVault as Address;

  return useReadContract({
    address: vaultAddress,
    abi: VAULT_ABI,
    functionName: 'collateralBalances',
    args: userAddress && chainName ? [userAddress, chainName] : undefined,
    chainId: vaultChainId,
    query: {
      enabled: !!vaultAddress && !!userAddress && !!chainName,
    },
  });
}

/**
 * Hook to get user's borrowed balance for a specific chain in the vault
 */
export function useVaultBorrowBalance(
  userAddress?: Address,
  chainName?: string,
  vaultChainId: number = sepolia.id
) {
  const vaultAddress = CONTRACTS[vaultChainId]?.CrossChainVault as Address;

  return useReadContract({
    address: vaultAddress,
    abi: VAULT_ABI,
    functionName: 'borrowBalances',
    args: userAddress && chainName ? [userAddress, chainName] : undefined,
    chainId: vaultChainId,
    query: {
      enabled: !!vaultAddress && !!userAddress && !!chainName,
    },
  });
}

/**
 * Hook to get user's total collateral across all chains
 */
export function useVaultTotalCollateral(userAddress?: Address, chainId: number = sepolia.id) {
  const vaultAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  return useReadContract({
    address: vaultAddress,
    abi: VAULT_ABI,
    functionName: 'totalCollateral',
    args: userAddress ? [userAddress] : undefined,
    chainId,
    query: {
      enabled: !!vaultAddress && !!userAddress,
    },
  });
}

/**
 * Hook to get user's total borrowed amount
 */
export function useVaultTotalBorrowed(userAddress?: Address, chainId: number = sepolia.id) {
  const vaultAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  return useReadContract({
    address: vaultAddress,
    abi: VAULT_ABI,
    functionName: 'totalBorrowed',
    args: userAddress ? [userAddress] : undefined,
    chainId,
    query: {
      enabled: !!vaultAddress && !!userAddress,
    },
  });
}

/**
 * Hook to get user's total credit line
 */
export function useVaultCreditLine(userAddress?: Address, chainId: number = sepolia.id) {
  const vaultAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  return useReadContract({
    address: vaultAddress,
    abi: VAULT_ABI,
    functionName: 'totalCreditLine',
    args: userAddress ? [userAddress] : undefined,
    chainId,
    query: {
      enabled: !!vaultAddress && !!userAddress,
    },
  });
}

/**
 * Hook to deposit collateral into the vault
 */
export function useDepositToVault(chainId: number = sepolia.id) {
  const vaultAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess: txMined, data: receipt } = useWaitForTransactionReceipt({
    hash,
  });

  const isSuccess = txMined && receipt?.status === 'success';
  const isReverted = txMined && receipt?.status === 'reverted';

  const deposit = (userAddress: Address, amount: string, gasAmount: string = '0.01') => {
    const depositAmountWei = parseEther(amount);
    const gasAmountWei = parseEther(gasAmount);
    const totalValue = depositAmountWei + gasAmountWei;

    writeContract({
      address: vaultAddress,
      abi: VAULT_ABI,
      functionName: 'depositCollateral',
      args: [userAddress, gasAmountWei],
      value: totalValue,
      gas: GAS_LIMITS.DEPOSIT, // 600k with 20% buffer for cross-chain broadcasting
      chainId,
    });
  };

  return {
    deposit,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError: isError || isReverted,
    error,
    txHash: hash,
  };
}

/**
 * Hook to withdraw collateral from the vault
 */
export function useWithdrawFromVault(chainId: number = sepolia.id) {
  const vaultAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess: txMined, data: receipt } = useWaitForTransactionReceipt({
    hash,
  });

  const isSuccess = txMined && receipt?.status === 'success';
  const isReverted = txMined && receipt?.status === 'reverted';

  const withdraw = (amount: string, gasAmount: string = '0.01') => {
    const withdrawAmountWei = parseEther(amount);
    const gasAmountWei = parseEther(gasAmount);

    writeContract({
      address: vaultAddress,
      abi: VAULT_ABI,
      functionName: 'withdrawCollateral',
      args: [withdrawAmountWei, gasAmountWei],
      value: gasAmountWei,
      gas: GAS_LIMITS.WITHDRAW, // 600k with 20% buffer for cross-chain broadcasting
      chainId,
    });
  };

  return {
    withdraw,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError: isError || isReverted,
    error,
    txHash: hash,
  };
}

/**
 * Hook to borrow from the vault
 */
export function useBorrowFromVault(chainId: number = sepolia.id) {
  const vaultAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess: txMined, data: receipt } = useWaitForTransactionReceipt({
    hash,
  });

  const isSuccess = txMined && receipt?.status === 'success';
  const isReverted = txMined && receipt?.status === 'reverted';

  const borrow = (amount: string, gasAmount: string = '0.01') => {
    const borrowAmountWei = parseEther(amount);
    const gasAmountWei = parseEther(gasAmount);
    const totalValue = borrowAmountWei + gasAmountWei;

    writeContract({
      address: vaultAddress,
      abi: VAULT_ABI,
      functionName: 'borrow',
      args: [borrowAmountWei, gasAmountWei],
      value: gasAmountWei,
      gas: GAS_LIMITS.BORROW, // 600k with 20% buffer for cross-chain broadcasting
      chainId,
    });
  };

  return {
    borrow,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError: isError || isReverted,
    error,
    txHash: hash,
  };
}

/**
 * Hook to repay borrowed amount to the vault
 */
export function useRepayToVault(chainId: number = sepolia.id) {
  const vaultAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess: txMined, data: receipt } = useWaitForTransactionReceipt({
    hash,
  });

  const isSuccess = txMined && receipt?.status === 'success';
  const isReverted = txMined && receipt?.status === 'reverted';

  const repay = (amount: string, gasAmount: string = '0.01') => {
    const repayAmountWei = parseEther(amount);
    const gasAmountWei = parseEther(gasAmount);
    const totalValue = repayAmountWei + gasAmountWei;

    writeContract({
      address: vaultAddress,
      abi: VAULT_ABI,
      functionName: 'repay',
      args: [repayAmountWei],
      value: totalValue, // Send repayment + gas
      gas: GAS_LIMITS.REPAY, // 300k - lower as no cross-chain broadcast needed
      chainId,
    });
  };

  return {
    repay,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError: isError || isReverted,
    error,
    txHash: hash,
  };
}

/**
 * Hook to get all vault data for a user (queries only connected chain)
 */
export function useVaultData(userAddress?: Address, chainId: number = sepolia.id) {
  const sepoliaBalance = useVaultCollateralBalance(userAddress, 'ethereum-sepolia', chainId);
  const amoyBalance = useVaultCollateralBalance(userAddress, 'polygon-amoy', chainId);
  const sepoliaBorrowed = useVaultBorrowBalance(userAddress, 'ethereum-sepolia', chainId);
  const amoyBorrowed = useVaultBorrowBalance(userAddress, 'polygon-amoy', chainId);
  const totalCollateral = useVaultTotalCollateral(userAddress, chainId);
  const totalBorrowed = useVaultTotalBorrowed(userAddress, chainId);
  const creditLine = useVaultCreditLine(userAddress, chainId);

  return {
    sepoliaBalance: sepoliaBalance.data,
    amoyBalance: amoyBalance.data,
    sepoliaBorrowed: sepoliaBorrowed.data,
    amoyBorrowed: amoyBorrowed.data,
    totalCollateral: totalCollateral.data,
    totalBorrowed: totalBorrowed.data,
    creditLine: creditLine.data,
    isLoading:
      sepoliaBalance.isLoading ||
      amoyBalance.isLoading ||
      sepoliaBorrowed.isLoading ||
      amoyBorrowed.isLoading ||
      totalCollateral.isLoading ||
      totalBorrowed.isLoading ||
      creditLine.isLoading,
    isError:
      sepoliaBalance.isError ||
      amoyBalance.isError ||
      sepoliaBorrowed.isError ||
      amoyBorrowed.isError ||
      totalCollateral.isError ||
      totalBorrowed.isError ||
      creditLine.isError,
  };
}

/**
 * Hook to get aggregated vault data from BOTH chains (for sync status detection)
 */
export function useAggregatedVaultData(userAddress?: Address, connectedChainId: number = sepolia.id) {
  // Query Sepolia vault
  const sepoliaBalanceFromSepolia = useVaultCollateralBalance(userAddress, 'ethereum', sepolia.id);
  const amoyBalanceFromSepolia = useVaultCollateralBalance(userAddress, 'polygon', sepolia.id);
  const sepoliaBorrowedFromSepolia = useVaultBorrowBalance(userAddress, 'ethereum', sepolia.id);
  const amoyBorrowedFromSepolia = useVaultBorrowBalance(userAddress, 'polygon', sepolia.id);
  const totalFromSepolia = useVaultTotalCollateral(userAddress, sepolia.id);
  const borrowedFromSepolia = useVaultTotalBorrowed(userAddress, sepolia.id);
  const creditFromSepolia = useVaultCreditLine(userAddress, sepolia.id);

  // Query Amoy vault
  const sepoliaBalanceFromAmoy = useVaultCollateralBalance(userAddress, 'ethereum', polygonAmoy.id);
  const amoyBalanceFromAmoy = useVaultCollateralBalance(userAddress, 'polygon', polygonAmoy.id);
  const sepoliaBorrowedFromAmoy = useVaultBorrowBalance(userAddress, 'ethereum', polygonAmoy.id);
  const amoyBorrowedFromAmoy = useVaultBorrowBalance(userAddress, 'polygon', polygonAmoy.id);
  const totalFromAmoy = useVaultTotalCollateral(userAddress, polygonAmoy.id);
  const borrowedFromAmoy = useVaultTotalBorrowed(userAddress, polygonAmoy.id);
  const creditFromAmoy = useVaultCreditLine(userAddress, polygonAmoy.id);

  // Detect sync status
  const sepoliaSynced = sepoliaBalanceFromSepolia.data === sepoliaBalanceFromAmoy.data;
  const amoySynced = amoyBalanceFromSepolia.data === amoyBalanceFromAmoy.data;
  const totalSynced = totalFromSepolia.data === totalFromAmoy.data;
  const allSynced = sepoliaSynced && amoySynced && totalSynced;

  // Aggregate real balances (from source chains)
  const realSepoliaBalance = sepoliaBalanceFromSepolia.data || 0n;
  const realAmoyBalance = amoyBalanceFromAmoy.data || 0n;
  const aggregatedTotal = realSepoliaBalance + realAmoyBalance;

  return {
    // Per-chain balances from authoritative source
    sepoliaBalance: realSepoliaBalance,
    amoyBalance: realAmoyBalance,
    sepoliaBorrowed: sepoliaBorrowedFromSepolia.data,
    amoyBorrowed: amoyBorrowedFromAmoy.data,

    // Aggregated totals
    aggregatedTotal,

    // What the connected chain sees
    localTotal: connectedChainId === sepolia.id ? totalFromSepolia.data : totalFromAmoy.data,
    localCreditLine: connectedChainId === sepolia.id ? creditFromSepolia.data : creditFromAmoy.data,
    localBorrowed: connectedChainId === sepolia.id ? borrowedFromSepolia.data : borrowedFromAmoy.data,

    // Sync status
    syncStatus: {
      allSynced,
      sepoliaSynced,
      amoySynced,
      totalSynced,
      sepoliaVaultView: {
        sepoliaBalance: sepoliaBalanceFromSepolia.data || 0n,
        amoyBalance: amoyBalanceFromSepolia.data || 0n,
        total: totalFromSepolia.data || 0n,
      },
      amoyVaultView: {
        sepoliaBalance: sepoliaBalanceFromAmoy.data || 0n,
        amoyBalance: amoyBalanceFromAmoy.data || 0n,
        total: totalFromAmoy.data || 0n,
      },
    },

    isLoading:
      sepoliaBalanceFromSepolia.isLoading ||
      amoyBalanceFromAmoy.isLoading ||
      totalFromSepolia.isLoading ||
      totalFromAmoy.isLoading,
  };
}
