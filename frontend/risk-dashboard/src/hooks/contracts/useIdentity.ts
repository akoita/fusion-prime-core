/**
 * Hooks for Identity contract
 * Handles claim verification and identity information
 */

import { useReadContract } from 'wagmi';
import { sepolia } from 'viem/chains';
import IdentityABI from '../../abis/Identity.json';

// Claim topic constants
export const CLAIM_TOPICS = {
  KYC_VERIFIED: 1,
  AML_CLEARED: 2,
  ACCREDITED_INVESTOR: 3,
  SANCTIONS_CLEARED: 4,
  COUNTRY_ALLOWED: 5,
} as const;

export const CLAIM_TOPIC_NAMES: Record<number, string> = {
  1: 'KYC Verified',
  2: 'AML Cleared',
  3: 'Accredited Investor',
  4: 'Sanctions Cleared',
  5: 'Country Allowed',
};

/**
 * Hook to check if identity has a specific claim
 */
export function useHasClaim(
  identityAddress?: `0x${string}`,
  topic?: number,
  chainId: number = sepolia.id
) {
  const { data, isError, isLoading, refetch } = useReadContract({
    address: identityAddress,
    abi: IdentityABI,
    functionName: 'hasClaim',
    args: topic !== undefined ? [BigInt(topic)] : undefined,
    chainId,
  });

  return {
    hasClaim: data as boolean | undefined,
    isLoading,
    isError,
    refetch,
  };
}

/**
 * Hook to check KYC verification status
 */
export function useIsKYCVerified(identityAddress?: `0x${string}`, chainId: number = sepolia.id) {
  return useHasClaim(identityAddress, CLAIM_TOPICS.KYC_VERIFIED, chainId);
}

/**
 * Hook to check AML clearance status
 */
export function useIsAMLCleared(identityAddress?: `0x${string}`, chainId: number = sepolia.id) {
  return useHasClaim(identityAddress, CLAIM_TOPICS.AML_CLEARED, chainId);
}

/**
 * Hook to get claim IDs for a topic
 */
export function useGetClaimIdsByTopic(
  identityAddress?: `0x${string}`,
  topic?: number,
  chainId: number = sepolia.id
) {
  const { data, isError, isLoading, refetch } = useReadContract({
    address: identityAddress,
    abi: IdentityABI,
    functionName: 'getClaimIdsByTopic',
    args: topic !== undefined ? [BigInt(topic)] : undefined,
    chainId,
  });

  return {
    claimIds: data as `0x${string}`[] | undefined,
    isLoading,
    isError,
    refetch,
  };
}

/**
 * Hook to get claim details
 */
export function useGetClaim(
  identityAddress?: `0x${string}`,
  claimId?: `0x${string}`,
  chainId: number = sepolia.id
) {
  const { data, isError, isLoading, refetch } = useReadContract({
    address: identityAddress,
    abi: IdentityABI,
    functionName: 'getClaim',
    args: claimId ? [claimId] : undefined,
    chainId,
  });

  // Parse claim data
  const claim = data
    ? {
        topic: Number((data as any)[0]),
        scheme: Number((data as any)[1]),
        issuer: (data as any)[2] as `0x${string}`,
        signature: (data as any)[3] as `0x${string}`,
        data: (data as any)[4] as `0x${string}`,
        uri: (data as any)[5] as string,
      }
    : undefined;

  return {
    claim,
    isLoading,
    isError,
    refetch,
  };
}

/**
 * Hook to check multiple claims at once
 */
export function useVerificationStatus(
  identityAddress?: `0x${string}`,
  chainId: number = sepolia.id
) {
  const { hasClaim: hasKYC, isLoading: kycLoading, refetch: refetchKYC } = useIsKYCVerified(identityAddress, chainId);
  const { hasClaim: hasAML, isLoading: amlLoading, refetch: refetchAML } = useIsAMLCleared(identityAddress, chainId);

  const refetchAll = () => {
    refetchKYC();
    refetchAML();
  };

  return {
    isKYCVerified: hasKYC || false,
    isAMLCleared: hasAML || false,
    isFullyVerified: (hasKYC && hasAML) || false,
    isLoading: kycLoading || amlLoading,
    refetch: refetchAll,
  };
}

/**
 * Hook to get all verification data for display
 */
export function useIdentityVerificationData(
  identityAddress?: `0x${string}`,
  chainId: number = sepolia.id
) {
  const kyc = useIsKYCVerified(identityAddress, chainId);
  const aml = useIsAMLCleared(identityAddress, chainId);
  const accredited = useHasClaim(identityAddress, CLAIM_TOPICS.ACCREDITED_INVESTOR, chainId);
  const sanctions = useHasClaim(identityAddress, CLAIM_TOPICS.SANCTIONS_CLEARED, chainId);

  const claims = [
    {
      topic: CLAIM_TOPICS.KYC_VERIFIED,
      name: 'KYC Verified',
      verified: kyc.hasClaim || false,
      loading: kyc.isLoading,
      required: true,
    },
    {
      topic: CLAIM_TOPICS.AML_CLEARED,
      name: 'AML Cleared',
      verified: aml.hasClaim || false,
      loading: aml.isLoading,
      required: true,
    },
    {
      topic: CLAIM_TOPICS.ACCREDITED_INVESTOR,
      name: 'Accredited Investor',
      verified: accredited.hasClaim || false,
      loading: accredited.isLoading,
      required: false,
    },
    {
      topic: CLAIM_TOPICS.SANCTIONS_CLEARED,
      name: 'Sanctions Cleared',
      verified: sanctions.hasClaim || false,
      loading: sanctions.isLoading,
      required: false,
    },
  ];

  const allLoading = claims.some((c) => c.loading);
  const requiredVerified = claims.filter((c) => c.required).every((c) => c.verified);
  const allVerified = claims.every((c) => c.verified);

  return {
    claims,
    allLoading,
    requiredVerified,
    allVerified,
  };
}
