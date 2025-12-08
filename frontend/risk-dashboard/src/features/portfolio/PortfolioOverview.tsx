import { usePortfolioData } from '@/hooks/usePortfolioData'
import { useRealTimeUpdates } from '@/hooks/useRealTimeUpdates'
import CollateralBreakdown from '@/components/charts/CollateralBreakdown'
import AssetAllocation from '@/components/charts/AssetAllocation'
import { StatCardSkeleton, ChartSkeleton, TableSkeleton } from '@/components/common/SkeletonLoader'
import { PageTransition, StaggerChildren, StaggerItem, FadeIn } from '@/components/common/PageTransition'
import { AlertCircle, TrendingUp, Wallet, BarChart3 } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

export default function PortfolioOverview() {
  const { user } = useAuth()
  const userId = user?.id
  const { data, isLoading, error } = usePortfolioData(userId)
  const { isConnected } = useRealTimeUpdates(userId)

  if (isLoading) {
    return (
      <PageTransition>
        <div className="space-y-6">
          <FadeIn>
            <div className="mb-6">
              <div className="h-8 w-64 bg-gray-200 rounded mb-2 animate-pulse" />
              <div className="h-4 w-96 bg-gray-200 rounded animate-pulse" />
            </div>
          </FadeIn>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ChartSkeleton />
            <ChartSkeleton />
          </div>

          <TableSkeleton rows={5} />
        </div>
      </PageTransition>
    )
  }

  if (error) {
    return (
      <PageTransition>
        <div className="flex items-center justify-center min-h-96">
          <div className="bg-red-50 border-2 border-red-200 rounded-lg p-8 max-w-md text-center">
            <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
              <AlertCircle className="h-8 w-8 text-red-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Failed to Load Portfolio</h3>
            <p className="text-red-700 mb-4">
              {error instanceof Error ? error.message : 'Unknown error occurred'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </PageTransition>
    )
  }

  // Transform positions for charts
  const collateralPositions =
    data?.positions?.map((pos) => ({
      asset: pos.asset,
      value: pos.collateralValueUsd || 0,
    })) || []

  const assetAllocationData =
    data?.positions?.map((pos) => ({
      asset: pos.asset,
      collateral: pos.collateralValueUsd || 0,
      borrowed: pos.borrowedValueUsd || 0,
    })) || []

  return (
    <PageTransition>
      <div className="space-y-6">
        <FadeIn delay={0.1}>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-3xl font-bold text-white tracking-tight">
              Portfolio <span className="text-gradient">Overview</span>
            </h2>
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-gray-400'
                  }`}
                title={isConnected ? 'Real-time updates active' : 'Real-time updates disconnected'}
              />
              <span className="text-sm text-gray-500">
                {isConnected ? 'Live' : 'Offline'}
              </span>
            </div>
          </div>
          <p className="text-gray-600">
            Real-time view of your portfolio exposure and risk metrics
          </p>
        </FadeIn>

        <StaggerChildren className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StaggerItem>
            <div className="glass-panel rounded-xl p-6 transition-all duration-300 hover:scale-[1.02]">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-gray-400">Total Collateral</h3>
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <Wallet className="h-5 w-5 text-blue-400" />
                </div>
              </div>
              <p className="text-3xl font-bold text-white">
                {data?.totalCollateralUsd
                  ? `$${data.totalCollateralUsd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                  : '$0.00'}
              </p>
            </div>
          </StaggerItem>

          <StaggerItem>
            <div className="glass-panel rounded-xl p-6 transition-all duration-300 hover:scale-[1.02]">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-gray-400">Total Borrowed</h3>
                <div className="p-2 bg-orange-500/10 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-orange-400" />
                </div>
              </div>
              <p className="text-3xl font-bold text-white">
                {data?.totalBorrowedUsd
                  ? `$${data.totalBorrowedUsd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                  : '$0.00'}
              </p>
            </div>
          </StaggerItem>

          <StaggerItem>
            <div className="glass-panel rounded-xl p-6 transition-all duration-300 hover:scale-[1.02]">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-gray-400">Margin Health</h3>
                <div className="p-2 bg-green-500/10 rounded-lg">
                  <BarChart3 className="h-5 w-5 text-green-400" />
                </div>
              </div>
              <p className="text-3xl font-bold text-white">
                {data?.marginHealthScore !== undefined
                  ? `${data.marginHealthScore.toFixed(1)}%`
                  : '—'}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {data?.marginHealthScore !== undefined && (
                  <>
                    {data.marginHealthScore < 15
                      ? '🔴 Liquidation Risk'
                      : data.marginHealthScore < 30
                        ? '🟠 Margin Call'
                        : data.marginHealthScore < 45
                          ? '🟡 Warning'
                          : '🟢 Healthy'}
                  </>
                )}
              </p>
            </div>
          </StaggerItem>
        </StaggerChildren>

        {/* Charts */}
        <FadeIn delay={0.3}>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="glass-panel rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">
                Collateral Breakdown
              </h3>
              {collateralPositions.length > 0 ? (
                <CollateralBreakdown positions={collateralPositions} />
              ) : (
                <div className="flex items-center justify-center h-64 text-gray-400">
                  No collateral positions available
                </div>
              )}
            </div>

            <div className="glass-panel rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">
                Asset Allocation
              </h3>
              {assetAllocationData.length > 0 ? (
                <AssetAllocation data={assetAllocationData} />
              ) : (
                <div className="flex items-center justify-center h-64 text-gray-400">
                  No asset data available
                </div>
              )}
            </div>
          </div>
        </FadeIn>

        {/* Positions Table */}
        {data?.positions && data.positions.length > 0 && (
          <FadeIn delay={0.4}>
            <div className="glass-panel rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-white/10">
                <h3 className="text-lg font-semibold text-white">
                  Position Details
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-white/10">
                  <thead className="bg-white/5">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Asset
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Chain
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Collateral (USD)
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Borrowed (USD)
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/10">
                    {data.positions.map((position, index) => (
                      <tr key={index} className="hover:bg-white/5 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">
                          {position.asset}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                          {position.chain}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-200">
                          ${(position.collateralValueUsd || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-200">
                          ${(position.borrowedValueUsd || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </FadeIn>
        )}
      </div>
    </PageTransition>
  )
}
