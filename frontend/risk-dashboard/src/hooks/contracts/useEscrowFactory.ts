import { useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { parseEther, type Address } from 'viem';
import { sepolia } from 'wagmi/chains';
import { CONTRACTS } from '@/config/chains';
import EscrowFactoryABI from '@/abis/EscrowFactory.json';

/**
 * Hook to read user's escrows from the EscrowFactory contract
 *
 * @param userAddress - The address of the user to query escrows for
 * @returns Object containing escrows array, loading state, and error
 *
 * @example
 * const { data: escrows, isLoading } = useUserEscrows(userAddress);
 */
export function useUserEscrows(userAddress?: Address) {
  return useReadContract({
    address: CONTRACTS[sepolia.id].EscrowFactory as Address,
    abi: EscrowFactoryABI,
    functionName: 'getUserEscrows',
    args: userAddress ? [userAddress] : undefined,
    query: {
      enabled: !!userAddress, // Only run query if address is provided
    },
  });
}

/**
 * Hook to get the total number of escrows created
 *
 * @returns Object containing escrow count, loading state, and error
 *
 * @example
 * const { data: count } = useEscrowCount();
 */
export function useEscrowCount() {
  return useReadContract({
    address: CONTRACTS[sepolia.id].EscrowFactory as Address,
    abi: EscrowFactoryABI,
    functionName: 'getEscrowCount',
  });
}

/**
 * Hook to create a new escrow
 *
 * @returns Object with write function and transaction state
 *
 * @example
 * const { createEscrow, isLoading, isSuccess, txHash } = useCreateEscrow();
 *
 * // Create escrow with 1 ETH
 * createEscrow({
 *   payee: '0x...',
 *   arbiter: '0x...',
 *   timelock: 3600, // 1 hour in seconds
 *   amount: '1.0', // ETH amount as string
 * });
 */
export function useCreateEscrow() {
  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  /**
   * Create a new escrow
   *
   * @param payee - Address that will receive funds
   * @param arbiter - Address that can resolve disputes
   * @param timelock - Time in seconds before payee can claim without approval
   * @param amount - Amount of ETH to escrow (as string, e.g., "1.0")
   * @param approvalsRequired - Number of approvals required (default: 1)
   */
  const createEscrow = ({
    payee,
    arbiter,
    timelock,
    amount,
    approvalsRequired = 1,
  }: {
    payee: Address;
    arbiter: Address;
    timelock: number;
    amount: string;
    approvalsRequired?: number;
  }) => {
    writeContract({
      address: CONTRACTS[sepolia.id].EscrowFactory as Address,
      abi: EscrowFactoryABI,
      functionName: 'createEscrow',
      args: [payee, BigInt(timelock), approvalsRequired, arbiter],
      value: parseEther(amount),
    });
  };

  return {
    createEscrow,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError,
    error,
    txHash: hash,
  };
}

/**
 * Hook to create a deterministic escrow (using CREATE2)
 *
 * @returns Object with write function and transaction state
 *
 * @example
 * const { createDeterministicEscrow } = useCreateDeterministicEscrow();
 *
 * createDeterministicEscrow({
 *   payee: '0x...',
 *   arbiter: '0x...',
 *   timelock: 3600,
 *   amount: '1.0',
 *   salt: '0x1234...', // 32-byte salt for CREATE2
 * });
 */
export function useCreateDeterministicEscrow() {
  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const createDeterministicEscrow = ({
    payee,
    arbiter,
    timelock,
    amount,
    salt,
  }: {
    payee: Address;
    arbiter: Address;
    timelock: number;
    amount: string;
    salt: `0x${string}`;
  }) => {
    writeContract({
      address: CONTRACTS[sepolia.id].EscrowFactory as Address,
      abi: EscrowFactoryABI,
      functionName: 'createEscrowDeterministic',
      args: [payee, arbiter, BigInt(timelock), salt],
      value: parseEther(amount),
    });
  };

  return {
    createDeterministicEscrow,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError,
    error,
    txHash: hash,
  };
}

/**
 * Hook to compute the deterministic address for an escrow
 *
 * @param payer - Address of the payer
 * @param payee - Address of the payee
 * @param arbiter - Address of the arbiter
 * @param timelock - Timelock duration in seconds
 * @param salt - 32-byte salt for CREATE2
 *
 * @returns Object containing the computed escrow address
 *
 * @example
 * const { data: escrowAddress } = useComputeEscrowAddress(
 *   payerAddress,
 *   payeeAddress,
 *   arbiterAddress,
 *   3600,
 *   '0x1234...'
 * );
 */
export function useComputeEscrowAddress(
  payer?: Address,
  payee?: Address,
  arbiter?: Address,
  timelock?: number,
  salt?: `0x${string}`
) {
  return useReadContract({
    address: CONTRACTS[sepolia.id].EscrowFactory as Address,
    abi: EscrowFactoryABI,
    functionName: 'computeEscrowAddress',
    args:
      payer && payee && arbiter && timelock !== undefined && salt
        ? [payer, payee, arbiter, BigInt(timelock), salt]
        : undefined,
    query: {
      enabled: !!(payer && payee && arbiter && timelock !== undefined && salt),
    },
  });
}
