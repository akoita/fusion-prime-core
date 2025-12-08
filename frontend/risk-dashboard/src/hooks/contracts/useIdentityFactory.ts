/**
 * Hooks for IdentityFactory contract
 * Handles identity creation and lookup
 */

import { useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { sepolia } from 'viem/chains';
import IdentityFactoryABI from '../../abis/IdentityFactory.json';

// Contract address (update after deployment)
const IDENTITY_FACTORY_ADDRESS = import.meta.env.VITE_IDENTITY_FACTORY_ADDRESS as `0x${string}` || '0x0000000000000000000000000000000000000000';

/**
 * Hook to get identity address for a wallet
 */
export function useGetIdentity(ownerAddress?: `0x${string}`, chainId: number = sepolia.id) {
  const { data, isError, isLoading, refetch } = useReadContract({
    address: IDENTITY_FACTORY_ADDRESS,
    abi: IdentityFactoryABI,
    functionName: 'getIdentity',
    args: ownerAddress ? [ownerAddress] : undefined,
    chainId,
  });

  return {
    identityAddress: data as `0x${string}` | undefined,
    isLoading,
    isError,
    refetch,
  };
}

/**
 * Hook to check if wallet has an identity
 */
export function useHasIdentity(ownerAddress?: `0x${string}`, chainId: number = sepolia.id) {
  const { data, isError, isLoading, refetch } = useReadContract({
    address: IDENTITY_FACTORY_ADDRESS,
    abi: IdentityFactoryABI,
    functionName: 'hasIdentity',
    args: ownerAddress ? [ownerAddress] : undefined,
    chainId,
  });

  return {
    hasIdentity: data as boolean | undefined,
    isLoading,
    isError,
    refetch,
  };
}

/**
 * Hook to create identity for current user
 */
export function useCreateIdentity(chainId: number = sepolia.id) {
  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const createIdentity = () => {
    writeContract({
      address: IDENTITY_FACTORY_ADDRESS,
      abi: IdentityFactoryABI,
      functionName: 'createIdentity',
      chainId,
    });
  };

  return {
    createIdentity,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError,
    error,
    txHash: hash,
  };
}

/**
 * Hook to get total identity count
 */
export function useGetIdentityCount(chainId: number = sepolia.id) {
  const { data, isError, isLoading } = useReadContract({
    address: IDENTITY_FACTORY_ADDRESS,
    abi: IdentityFactoryABI,
    functionName: 'getIdentityCount',
    chainId,
  });

  return {
    count: data ? Number(data) : 0,
    isLoading,
    isError,
  };
}

/**
 * Combined hook for identity status
 */
export function useIdentityStatus(walletAddress?: `0x${string}`, chainId: number = sepolia.id) {
  const { hasIdentity, isLoading: hasIdentityLoading, refetch: refetchHas } = useHasIdentity(walletAddress, chainId);
  const { identityAddress, isLoading: identityLoading, refetch: refetchAddress } = useGetIdentity(walletAddress, chainId);

  const refetch = () => {
    refetchHas();
    refetchAddress();
  };

  return {
    hasIdentity: hasIdentity || false,
    identityAddress: identityAddress || undefined,
    isLoading: hasIdentityLoading || identityLoading,
    refetch,
  };
}
