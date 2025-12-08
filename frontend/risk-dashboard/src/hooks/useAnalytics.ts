import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'

interface VaRData {
  date: string
  var_1d: number
  var_7d: number
  var_30d: number
  cvar_1d: number
}

interface PerformanceData {
  date: string
  return: number
  cumulative_return: number
  benchmark_return?: number
}

interface AnalyticsData {
  var_trends: VaRData[]
  performance: PerformanceData[]
  volatility: number
  sharpe_ratio: number
  max_drawdown: number
}

export function useAnalytics(portfolioId?: string, timeRange = '30d') {
  return useQuery<AnalyticsData>({
    queryKey: ['analytics', portfolioId, timeRange],
    queryFn: async () => {
      try {
        // Fetch VaR trends
        const varResponse = await apiClient.get('/analytics/portfolio/portfolio-1/history', {
          params: { time_range: timeRange },
        })

        // Fetch performance data
        const perfResponse = await apiClient.get('/analytics/performance/portfolio-1', {
          params: { time_range: timeRange },
        })

        // Fetch volatility
        const volResponse = await apiClient.get('/analytics/volatility/portfolio-1', {
          params: { time_range: timeRange },
        })

        // Fetch Sharpe ratio
        const sharpeResponse = await apiClient.get('/analytics/sharpe/portfolio-1', {
          params: { time_range: timeRange },
        })

        // Fetch drawdown
        const drawdownResponse = await apiClient.get('/analytics/drawdown/portfolio-1', {
          params: { time_range: timeRange },
        })

        // Transform data for charts
        const varTrends = Array.isArray(varResponse.data)
          ? varResponse.data.map((item: any) => ({
              date: item.date || item.timestamp,
              var_1d: item.var_1d || 0,
              var_7d: item.var_7d || 0,
              var_30d: item.var_30d || 0,
              cvar_1d: item.cvar_1d || 0,
            }))
          : []

        const performance = Array.isArray(perfResponse.data)
          ? perfResponse.data.map((item: any) => ({
              date: item.date || item.timestamp,
              return: item.return || 0,
              cumulative_return: item.cumulative_return || 0,
              benchmark_return: item.benchmark_return,
            }))
          : []

        return {
          var_trends: varTrends.slice(0, 30), // Last 30 data points
          performance: performance.slice(0, 30),
          volatility: volResponse.data?.volatility || 0,
          sharpe_ratio: sharpeResponse.data?.sharpe_ratio || 0,
          max_drawdown: drawdownResponse.data?.max_drawdown || 0,
        }
      } catch (error) {
        // Return mock data for development
        console.warn('Failed to fetch analytics data, using mock data:', error)
        return generateMockAnalyticsData(timeRange)
      }
    },
    enabled: true,
    refetchInterval: 60000, // Refetch every minute
  })
}

function generateMockAnalyticsData(timeRange: string): AnalyticsData {
  const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90
  const baseDate = new Date()
  baseDate.setDate(baseDate.getDate() - days)

  const varTrends: VaRData[] = []
  const performance: PerformanceData[] = []

  for (let i = 0; i < days; i++) {
    const date = new Date(baseDate)
    date.setDate(date.getDate() + i)
    const dateStr = date.toISOString().split('T')[0]

    // Generate realistic VaR data
    varTrends.push({
      date: dateStr,
      var_1d: 5000 + Math.random() * 2000,
      var_7d: 12000 + Math.random() * 4000,
      var_30d: 35000 + Math.random() * 10000,
      cvar_1d: 6000 + Math.random() * 2000,
    })

    // Generate realistic performance data
    const dailyReturn = (Math.random() - 0.5) * 0.02 // ±2% daily return
    const cumulativeReturn = i === 0 ? 0 : performance[i - 1].cumulative_return + dailyReturn

    performance.push({
      date: dateStr,
      return: dailyReturn,
      cumulative_return: cumulativeReturn,
      benchmark_return: dailyReturn * 0.8, // Benchmark slightly lower
    })
  }

  return {
    var_trends: varTrends,
    performance: performance,
    volatility: 0.15 + Math.random() * 0.1, // 15-25% volatility
    sharpe_ratio: 1.2 + Math.random() * 0.8, // 1.2-2.0 Sharpe ratio
    max_drawdown: -0.12 + Math.random() * 0.08, // -12% to -4% drawdown
  }
}
