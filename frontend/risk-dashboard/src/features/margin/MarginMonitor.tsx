import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import MarginHealthGauge from '@/components/charts/MarginHealthGauge'
import { useMarginHealth } from '@/hooks/useMarginHealth'
import { useAlerts } from '@/hooks/useAlerts'
import { useRealTimeUpdates } from '@/hooks/useRealTimeUpdates'

export default function MarginMonitor() {
  const { user } = useAuth()
  const userId = user?.id
  const [selectedThreshold, setSelectedThreshold] = useState(30)
  const { isConnected } = useRealTimeUpdates(userId)

  const { data: marginHealth, isLoading: healthLoading } = useMarginHealth(userId)
  const { data: alerts, isLoading: alertsLoading } = useAlerts(userId)

  // Mock data for demo when userId is not available
  const displayHealth = marginHealth || {
    score: 75.5,
    status: 'healthy' as const,
    threshold: selectedThreshold,
    timestamp: new Date().toISOString(),
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-3xl font-bold text-white tracking-tight">
            Margin <span className="text-gradient">Monitor</span>
          </h2>
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-gray-400'
                }`}
              title={isConnected ? 'Real-time updates active' : 'Real-time updates disconnected'}
            />
            <span className="text-sm text-gray-400">
              {isConnected ? 'Live' : 'Offline'}
            </span>
          </div>
        </div>
        <p className="text-gray-400">
          Real-time margin health monitoring and alerts
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Margin Health Gauge */}
        <div className="glass-panel rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">
            Margin Health Score
          </h3>
          {healthLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-400">Loading margin health...</div>
            </div>
          ) : (
            <div className="flex justify-center">
              <MarginHealthGauge
                score={displayHealth.score}
                threshold={selectedThreshold}
                size={250}
              />
            </div>
          )}
          <div className="mt-4 flex items-center justify-center gap-4">
            <label className="text-sm text-gray-400">
              Threshold:
              <select
                value={selectedThreshold}
                onChange={(e) => setSelectedThreshold(Number(e.target.value))}
                className="ml-2 px-2 py-1 bg-white/5 border border-white/10 rounded text-white"
              >
                <option value={15}>15% (Liquidation)</option>
                <option value={30}>30% (Margin Call)</option>
                <option value={45}>45% (Warning)</option>
              </select>
            </label>
          </div>
        </div>

        {/* Alerts Panel */}
        <div className="glass-panel rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">
            Recent Alerts
          </h3>
          {alertsLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-600">Loading alerts...</div>
            </div>
          ) : alerts && alerts.length > 0 ? (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-4 rounded-lg border ${alert.severity === 'critical'
                      ? 'bg-red-500/10 border-red-500/20'
                      : alert.severity === 'high'
                        ? 'bg-orange-500/10 border-orange-500/20'
                        : alert.severity === 'medium'
                          ? 'bg-yellow-500/10 border-yellow-500/20'
                          : 'bg-blue-500/10 border-blue-500/20'
                    }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-white">
                          {alert.type === 'margin_call'
                            ? '⚡ Margin Call'
                            : alert.type === 'liquidation'
                              ? '🔴 Liquidation'
                              : '⚠️ Warning'}
                        </span>
                        <span
                          className={`text-xs px-2 py-1 rounded ${alert.severity === 'critical'
                              ? 'bg-red-500/20 text-red-300'
                              : alert.severity === 'high'
                                ? 'bg-orange-500/20 text-orange-300'
                                : alert.severity === 'medium'
                                  ? 'bg-yellow-500/20 text-yellow-300'
                                  : 'bg-blue-500/20 text-blue-300'
                            }`}
                        >
                          {alert.severity.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-sm text-gray-300">{alert.message}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(alert.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">
              No alerts at this time
            </div>
          )}
        </div>
      </div>

      {/* Status Summary */}
      <div className="glass-panel rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">
          Status Summary
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-white">
              {displayHealth.score.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-400">Current Score</div>
          </div>
          <div className="text-center">
            <div
              className={`text-2xl font-bold ${displayHealth.status === 'healthy'
                  ? 'text-green-400'
                  : displayHealth.status === 'warning'
                    ? 'text-yellow-400'
                    : displayHealth.status === 'critical'
                      ? 'text-orange-400'
                      : 'text-red-400'
                }`}
            >
              {displayHealth.status.toUpperCase()}
            </div>
            <div className="text-sm text-gray-400">Status</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-white">
              {selectedThreshold}%
            </div>
            <div className="text-sm text-gray-400">Margin Call Threshold</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-white">
              {alerts?.filter((a) => !a.acknowledged).length || 0}
            </div>
            <div className="text-sm text-gray-400">Unacknowledged Alerts</div>
          </div>
        </div>
      </div>
    </div>
  )
}
