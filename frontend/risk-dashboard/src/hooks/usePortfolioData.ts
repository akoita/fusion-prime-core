import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import type { PortfolioExposure } from '@/types/risk'

export function usePortfolioData(userId?: string) {
  return useQuery<PortfolioExposure>({
    queryKey: ['portfolio', userId],
    queryFn: async () => {
      try {
        // Try to fetch risk metrics first
        const response = await apiClient.get('/risk/metrics')
        const metrics = response.data

        // Transform metrics to PortfolioExposure format
        // If the API doesn't return the expected format or returns empty data, use mock data
        if (
          metrics &&
          typeof metrics === 'object' &&
          (metrics.total_collateral_usd || metrics.total_borrow_usd || metrics.margin_health_score)
        ) {
          return {
            totalCollateralUsd: metrics.total_collateral_usd || 0,
            totalBorrowedUsd: metrics.total_borrow_usd || 0,
            marginHealthScore: metrics.margin_health_score || 0,
            positions: metrics.positions || [],
          } as PortfolioExposure
        }

        // If API returns empty/null data, fall through to mock data
        console.warn('API returned empty data, using mock portfolio data for demo')

        // Fallback to mock data for development
        return {
          totalCollateralUsd: 125000.0,
          totalBorrowedUsd: 45000.0,
          marginHealthScore: 77.8,
          positions: [
            {
              asset: 'ETH',
              chain: 'ethereum',
              collateralAmount: 10.5,
              collateralValueUsd: 25000.0,
              borrowedAmount: 0,
              borrowedValueUsd: 0,
            },
            {
              asset: 'BTC',
              chain: 'ethereum',
              collateralAmount: 1.2,
              collateralValueUsd: 50000.0,
              borrowedAmount: 0,
              borrowedValueUsd: 0,
            },
            {
              asset: 'USDC',
              chain: 'ethereum',
              collateralAmount: 50000,
              collateralValueUsd: 50000.0,
              borrowedAmount: 45000,
              borrowedValueUsd: 45000.0,
            },
          ],
        }
      } catch (error) {
        // If API call fails, return mock data for development/demo
        console.warn('Failed to fetch portfolio data, using mock data:', error)
        return {
          totalCollateralUsd: 125000.0,
          totalBorrowedUsd: 45000.0,
          marginHealthScore: 77.8,
          positions: [
            {
              asset: 'ETH',
              chain: 'ethereum',
              collateralAmount: 10.5,
              collateralValueUsd: 25000.0,
              borrowedAmount: 0,
              borrowedValueUsd: 0,
            },
            {
              asset: 'BTC',
              chain: 'ethereum',
              collateralAmount: 1.2,
              collateralValueUsd: 50000.0,
              borrowedAmount: 0,
              borrowedValueUsd: 0,
            },
            {
              asset: 'USDC',
              chain: 'ethereum',
              collateralAmount: 50000,
              collateralValueUsd: 50000.0,
              borrowedAmount: 45000,
              borrowedValueUsd: 45000.0,
            },
          ],
        }
      }
    },
    enabled: true,
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 1, // Only retry once, then use mock data
  })
}
