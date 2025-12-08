import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import type { MarginHealth } from '@/types/risk'

interface MarginHealthResponse {
  user_id: string
  margin_health_score: number
  collateral_value_usd: number
  borrowed_value_usd: number
  status: 'healthy' | 'warning' | 'critical' | 'liquidation'
  timestamp: string
}

export function useMarginHealth(userId?: string) {
  return useQuery<MarginHealth>({
    queryKey: ['marginHealth', userId],
    queryFn: async () => {
      if (!userId) {
        throw new Error('User ID is required')
      }

      const response = await apiClient.post<MarginHealthResponse>(
        '/api/v1/margin/health',
        {
          user_id: userId,
          collateral_positions: [], // Will be populated from portfolio
          borrow_positions: [],
        }
      )

      return {
        score: response.data.margin_health_score,
        status: response.data.status,
        threshold: 30, // Margin call threshold
        timestamp: response.data.timestamp,
      }
    },
    enabled: !!userId,
    refetchInterval: 15000, // Refetch every 15 seconds for real-time feel
  })
}
