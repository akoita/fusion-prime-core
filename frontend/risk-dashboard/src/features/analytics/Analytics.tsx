import { useState } from 'react'
import { useAnalytics } from '@/hooks/useAnalytics'
import VaRTrends from '@/components/charts/VaRTrends'
import PerformanceChart from '@/components/charts/PerformanceChart'

export default function Analytics() {
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d')
  const { data, isLoading, error } = useAnalytics(undefined, timeRange)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600">Loading analytics data...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-600">
          Error loading analytics: {error instanceof Error ? error.message : 'Unknown error'}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-3xl font-bold text-gray-900">
            Analytics & Reports
          </h2>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as '7d' | '30d' | '90d')}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>
        </div>
        <p className="text-gray-600">
          Risk metrics, VaR trends, and portfolio performance analytics
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">
            Volatility
          </h3>
          <p className="text-2xl font-bold text-gray-900">
            {data?.volatility ? `${(data.volatility * 100).toFixed(2)}%` : '—'}
          </p>
          <p className="text-xs text-gray-500 mt-1">Annualized volatility</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">
            Sharpe Ratio
          </h3>
          <p className="text-2xl font-bold text-gray-900">
            {data?.sharpe_ratio ? data.sharpe_ratio.toFixed(2) : '—'}
          </p>
          <p className="text-xs text-gray-500 mt-1">Risk-adjusted return</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">
            Max Drawdown
          </h3>
          <p className="text-2xl font-bold text-gray-900">
            {data?.max_drawdown ? `${(data.max_drawdown * 100).toFixed(2)}%` : '—'}
          </p>
          <p className="text-xs text-gray-500 mt-1">Peak to trough decline</p>
        </div>
      </div>

      {/* VaR Trends Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Value at Risk (VaR) Trends
        </h3>
        {data?.var_trends && data.var_trends.length > 0 ? (
          <VaRTrends data={data.var_trends} />
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500">
            No VaR data available
          </div>
        )}
        <div className="mt-4 text-sm text-gray-600">
          <p className="mb-2">
            <strong>VaR (Value at Risk):</strong> Maximum potential loss at a given confidence level
          </p>
          <p className="mb-2">
            <strong>CVaR (Conditional VaR):</strong> Expected loss given that loss exceeds VaR threshold
          </p>
          <p>
            <strong>Time Horizons:</strong> 1 day, 7 days, and 30 days VaR calculations
          </p>
        </div>
      </div>

      {/* Performance Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Portfolio Performance
        </h3>
        {data?.performance && data.performance.length > 0 ? (
          <PerformanceChart data={data.performance} />
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500">
            No performance data available
          </div>
        )}
        <div className="mt-4 text-sm text-gray-600">
          <p>
            Cumulative return shows portfolio performance over time compared to benchmark
          </p>
        </div>
      </div>

      {/* Export Options */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Export Reports
        </h3>
        <div className="flex gap-4">
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Export CSV
          </button>
          <button className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors">
            Export PDF
          </button>
        </div>
        <p className="text-sm text-gray-500 mt-2">
          Download analytics reports for regulatory compliance and reporting
        </p>
      </div>
    </div>
  )
}
