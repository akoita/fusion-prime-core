import { useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import type { Address } from 'viem';
import EscrowABI from '@/abis/Escrow.json';

/**
 * Escrow status enum
 */
export enum EscrowStatus {
  Created = 0,
  Approved = 1,
  Released = 2,
  Refunded = 3,
  Disputed = 4,
}

/**
 * Escrow details interface
 */
export interface EscrowDetails {
  payer: Address | undefined;
  payee: Address | undefined;
  arbiter: Address | undefined;
  amount: bigint | undefined;
  timelock: bigint | undefined;
  isApproved: boolean;
  approvalsCount: bigint | undefined;
  approvalsRequired: bigint | undefined;
  status: number;
  released: bigint | undefined;
  refunded: bigint | undefined;
  isLoading: boolean;
  isError: boolean;
}

/**
 * Hook to read escrow status
 *
 * @param escrowAddress - Address of the escrow contract
 * @returns Object containing escrow status, loading state, and error
 *
 * @example
 * const { data: status } = useEscrowStatus('0x...');
 * if (status === EscrowStatus.Created) { ... }
 */
export function useEscrowStatus(escrowAddress?: Address) {
  return useReadContract({
    address: escrowAddress,
    abi: EscrowABI.abi,
    functionName: 'getStatus',
    query: {
      enabled: !!escrowAddress,
    },
  });
}

/**
 * Hook to read escrow details
 *
 * @param escrowAddress - Address of the escrow contract
 * @returns Object containing all escrow details
 *
 * @example
 * const { data: details } = useEscrowDetails('0x...');
 * console.log(details?.payer, details?.payee, details?.amount);
 */
export function useEscrowDetails(escrowAddress?: Address): EscrowDetails {
  const payer = useReadContract({
    address: escrowAddress,
    abi: EscrowABI.abi,
    functionName: 'payer',
    query: {
      enabled: !!escrowAddress,
    },
  });

  const payee = useReadContract({
    address: escrowAddress,
    abi: EscrowABI.abi,
    functionName: 'payee',
    query: {
      enabled: !!escrowAddress,
    },
  });

  const arbiter = useReadContract({
    address: escrowAddress,
    abi: EscrowABI.abi,
    functionName: 'arbiter',
    query: {
      enabled: !!escrowAddress,
    },
  });

  const amount = useReadContract({
    address: escrowAddress,
    abi: EscrowABI.abi,
    functionName: 'amount',
    query: {
      enabled: !!escrowAddress,
    },
  });

  const timelock = useReadContract({
    address: escrowAddress,
    abi: EscrowABI.abi,
    functionName: 'releaseTime',
    query: {
      enabled: !!escrowAddress,
    },
  });

  // Log errors for debugging
  if (payer.error) console.error(`Escrow ${escrowAddress} - payer() error:`, payer.error);
  if (payee.error) console.error(`Escrow ${escrowAddress} - payee() error:`, payee.error);
  if (arbiter.error) console.error(`Escrow ${escrowAddress} - arbiter() error:`, arbiter.error);
  if (amount.error) console.error(`Escrow ${escrowAddress} - amount() error:`, amount.error);
  if (timelock.error) console.error(`Escrow ${escrowAddress} - releaseTime() error:`, timelock.error);

  const approvalsCount = useReadContract({
    address: escrowAddress,
    abi: EscrowABI.abi,
    functionName: 'approvalsCount',
    query: {
      enabled: !!escrowAddress,
    },
  });

  const approvalsRequired = useReadContract({
    address: escrowAddress,
    abi: EscrowABI.abi,
    functionName: 'approvalsRequired',
    query: {
      enabled: !!escrowAddress,
    },
  });

  const released = useReadContract({
    address: escrowAddress,
    abi: EscrowABI.abi,
    functionName: 'released',
    query: {
      enabled: !!escrowAddress,
    },
  });

  const refunded = useReadContract({
    address: escrowAddress,
    abi: EscrowABI.abi,
    functionName: 'refunded',
    query: {
      enabled: !!escrowAddress,
    },
  });

  // Calculate if escrow is approved (all required approvals received)
  const isApproved = approvalsCount.data !== undefined &&
                     approvalsRequired.data !== undefined &&
                     approvalsCount.data !== null &&
                     approvalsRequired.data !== null &&
                     approvalsCount.data >= approvalsRequired.data;

  // Calculate status: 0=Created, 1=Approved, 2=Released, 3=Refunded
  let status = 0; // Created
  if (refunded.data) status = 3; // Refunded
  else if (released.data) status = 2; // Released
  else if (isApproved) status = 1; // Approved

  return {
    payer: payer.data as Address | undefined,
    payee: payee.data as Address | undefined,
    arbiter: arbiter.data as Address | undefined,
    amount: amount.data as bigint | undefined,
    timelock: timelock.data as bigint | undefined,
    isApproved,
    approvalsCount: approvalsCount.data as bigint | undefined,
    approvalsRequired: approvalsRequired.data as bigint | undefined,
    status,
    released: released.data as bigint | undefined,
    refunded: refunded.data as bigint | undefined,
    isLoading:
      payer.isLoading ||
      payee.isLoading ||
      arbiter.isLoading ||
      amount.isLoading ||
      timelock.isLoading ||
      approvalsCount.isLoading ||
      approvalsRequired.isLoading ||
      released.isLoading ||
      refunded.isLoading,
    isError:
      payer.isError ||
      payee.isError ||
      arbiter.isError ||
      amount.isError ||
      timelock.isError ||
      approvalsCount.isError ||
      approvalsRequired.isError ||
      released.isError ||
      refunded.isError,
  };
}

/**
 * Hook to approve an escrow (called by payee)
 *
 * @param escrowAddress - Address of the escrow contract
 * @returns Object with approve function and transaction state
 *
 * @example
 * const { approve, isLoading } = useApproveEscrow('0x...');
 * approve(); // Payee approves the escrow
 */
export function useApproveEscrow(escrowAddress?: Address) {
  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const approve = () => {
    if (!escrowAddress) return;
    writeContract({
      address: escrowAddress,
      abi: EscrowABI.abi,
      functionName: 'approve',
    });
  };

  return {
    approve,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError,
    error,
    txHash: hash,
  };
}

/**
 * Hook to release funds to payee (called by arbiter)
 *
 * @param escrowAddress - Address of the escrow contract
 * @returns Object with release function and transaction state
 *
 * @example
 * const { release, isLoading } = useReleaseEscrow('0x...');
 * release(); // Arbiter releases funds to payee
 */
export function useReleaseEscrow(escrowAddress?: Address) {
  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const release = () => {
    if (!escrowAddress) return;
    writeContract({
      address: escrowAddress,
      abi: EscrowABI.abi,
      functionName: 'release',
    });
  };

  return {
    release,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError,
    error,
    txHash: hash,
  };
}

/**
 * Hook to refund to payer (called by arbiter or payer after dispute/timeout)
 *
 * @param escrowAddress - Address of the escrow contract
 * @returns Object with refund function and transaction state
 *
 * @example
 * const { refund, isLoading } = useRefundEscrow('0x...');
 * refund(); // Refund to payer
 */
export function useRefundEscrow(escrowAddress?: Address) {
  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const refund = () => {
    if (!escrowAddress) return;
    writeContract({
      address: escrowAddress,
      abi: EscrowABI.abi,
      functionName: 'refund',
    });
  };

  return {
    refund,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError,
    error,
    txHash: hash,
  };
}

/**
 * Hook to check if timelock has expired
 * Note: This is calculated client-side, not a contract call
 *
 * @param escrowAddress - Address of the escrow contract
 * @returns Object containing boolean indicating if timelock expired
 *
 * @example
 * const { data: isExpired } = useIsTimelockExpired('0x...');
 */
export function useIsTimelockExpired(escrowAddress?: Address) {
  const details = useEscrowDetails(escrowAddress);

  // Calculate timelock expiration client-side
  const isExpired = details.timelock
    ? Date.now() / 1000 > Number(details.timelock)
    : false;

  return {
    data: isExpired,
    isLoading: details.isLoading,
    isError: details.isError,
  };
}

/**
 * Helper function to get human-readable status
 */
export function getStatusText(status?: number): string {
  if (status === undefined) return 'Unknown';

  switch (status) {
    case EscrowStatus.Created:
      return 'Created';
    case EscrowStatus.Approved:
      return 'Approved';
    case EscrowStatus.Released:
      return 'Released';
    case EscrowStatus.Refunded:
      return 'Refunded';
    case EscrowStatus.Disputed:
      return 'Disputed';
    default:
      return 'Unknown';
  }
}

/**
 * Helper function to get status color for UI
 */
export function getStatusColor(status?: number): string {
  if (status === undefined) return 'gray';

  switch (status) {
    case EscrowStatus.Created:
      return 'blue'; // In progress
    case EscrowStatus.Approved:
      return 'green'; // Approved, waiting for release
    case EscrowStatus.Released:
      return 'green'; // Completed successfully
    case EscrowStatus.Refunded:
      return 'yellow'; // Refunded
    case EscrowStatus.Disputed:
      return 'red'; // Disputed
    default:
      return 'gray';
  }
}
