import { useQuery } from '@tanstack/react-query';
import type { Address } from 'viem';
import { getEscrowsByRole, type IndexedEscrow } from '@/lib/escrow-indexer';

/**
 * Hook to get escrows where user is involved in any role (payer, payee, or arbiter)
 *
 * ⚡ PERFORMANCE: Uses the escrow-indexer API for instant queries (<100ms)
 * instead of slow blockchain scanning (10-30 seconds).
 *
 * The indexer maintains a real-time PostgreSQL database of all escrows,
 * updated automatically via Pub/Sub events from the blockchain relayer.
 *
 * @param userAddress - The address to query escrows for
 * @returns Object containing escrows grouped by role, loading state, and error
 *
 * @example
 * const { data, isLoading, error } = useEscrowsByRole(userAddress);
 * // data.asPayer - Array of escrows where user is payer
 * // data.asPayee - Array of escrows where user is payee
 * // data.asArbiter - Array of escrows where user is arbiter
 */
export function useEscrowsByRole(userAddress?: Address) {
  const query = useQuery({
    queryKey: ['escrows-by-role', userAddress],
    queryFn: async () => {
      if (!userAddress) {
        return {
          asPayer: [],
          asPayee: [],
          asArbiter: [],
        };
      }

      console.log('🚀 Fetching escrows from indexer for:', userAddress);
      const startTime = performance.now();

      const response = await getEscrowsByRole(userAddress);

      const duration = performance.now() - startTime;
      console.log('✅ Indexer query completed in', duration.toFixed(0), 'ms');
      console.log('📊 Results:', {
        asPayer: response.escrows.asPayer.length,
        asPayee: response.escrows.asPayee.length,
        asArbiter: response.escrows.asArbiter.length,
      });

      // Convert indexed escrows to Address arrays for backward compatibility
      return {
        asPayer: response.escrows.asPayer.map((e) => e.escrow_address as Address),
        asPayee: response.escrows.asPayee.map((e) => e.escrow_address as Address),
        asArbiter: response.escrows.asArbiter.map((e) => e.escrow_address as Address),
      };
    },
    enabled: !!userAddress,
    staleTime: 30000, // Consider data fresh for 30 seconds
    gcTime: 300000, // Keep in cache for 5 minutes
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000),
  });

  return {
    asPayer: query.data?.asPayer || [],
    asPayee: query.data?.asPayee || [],
    asArbiter: query.data?.asArbiter || [],
    isLoading: query.isLoading,
    error: query.error as Error | null,
  };
}

/**
 * Hook to get detailed escrow data (not just addresses)
 * Returns the full IndexedEscrow objects with all metadata
 */
export function useEscrowsByRoleDetailed(userAddress?: Address) {
  return useQuery({
    queryKey: ['escrows-by-role-detailed', userAddress],
    queryFn: async () => {
      if (!userAddress) {
        return {
          asPayer: [] as IndexedEscrow[],
          asPayee: [] as IndexedEscrow[],
          asArbiter: [] as IndexedEscrow[],
        };
      }

      const response = await getEscrowsByRole(userAddress);
      return response.escrows;
    },
    enabled: !!userAddress,
    staleTime: 30000,
    gcTime: 300000,
  });
}
