import { useEffect, useRef, useState } from 'react'
import { websocketManager } from '@/lib/websocket'
import { useQueryClient } from '@tanstack/react-query'

interface MarginHealthUpdate {
  user_id: string
  margin_health_score: number
  collateral_value_usd: number
  borrowed_value_usd: number
  status: 'healthy' | 'warning' | 'critical' | 'liquidation'
  timestamp: string
}

interface PortfolioUpdate {
  total_collateral_usd: number
  total_borrow_usd: number
  margin_health_score: number
  positions: Array<{
    asset: string
    chain: string
    collateral_value_usd: number
    borrowed_value_usd: number
  }>
}

export function useRealTimeUpdates(userId?: string) {
  const queryClient = useQueryClient()
  const [isConnected, setIsConnected] = useState(false)
  const socketRef = useRef<ReturnType<typeof websocketManager.connect> | null>(null)

  useEffect(() => {
    // Connect to WebSocket
    socketRef.current = websocketManager.connect(userId)
    setIsConnected(websocketManager.isConnected())

    // Listen for connection status
    const handleConnect = () => setIsConnected(true)
    const handleDisconnect = () => setIsConnected(false)

    socketRef.current.on('connect', handleConnect)
    socketRef.current.on('disconnect', handleDisconnect)

    // Listen for margin health updates
    const handleMarginUpdate = (data: MarginHealthUpdate) => {
      // Invalidate and refetch margin health query
      queryClient.setQueryData(['marginHealth', userId], {
        score: data.margin_health_score,
        status: data.status,
        threshold: 30,
        timestamp: data.timestamp,
      })

      // Trigger a background refetch
      queryClient.invalidateQueries({ queryKey: ['marginHealth', userId] })
    }

    // Listen for portfolio updates
    const handlePortfolioUpdate = (data: PortfolioUpdate) => {
      // Update portfolio data cache
      queryClient.setQueryData(['portfolio', userId], {
        totalCollateralUsd: data.total_collateral_usd,
        totalBorrowedUsd: data.total_borrow_usd,
        marginHealthScore: data.margin_health_score,
        positions: data.positions.map((pos) => ({
          asset: pos.asset,
          chain: pos.chain,
          collateralAmount: 0, // Not provided in update
          collateralValueUsd: pos.collateral_value_usd,
          borrowedAmount: 0, // Not provided in update
          borrowedValueUsd: pos.borrowed_value_usd,
        })),
      })

      // Trigger a background refetch for full data
      queryClient.invalidateQueries({ queryKey: ['portfolio', userId] })
    }

    // Listen for alert updates
    const handleAlertUpdate = () => {
      queryClient.invalidateQueries({ queryKey: ['alerts', userId] })
    }

    // Subscribe to events
    socketRef.current.on('margin_health_update', handleMarginUpdate)
    socketRef.current.on('portfolio_update', handlePortfolioUpdate)
    socketRef.current.on('alert_update', handleAlertUpdate)

    // Cleanup on unmount
    return () => {
      socketRef.current?.off('connect', handleConnect)
      socketRef.current?.off('disconnect', handleDisconnect)
      socketRef.current?.off('margin_health_update', handleMarginUpdate)
      socketRef.current?.off('portfolio_update', handlePortfolioUpdate)
      socketRef.current?.off('alert_update', handleAlertUpdate)
    }
  }, [userId, queryClient])

  return { isConnected }
}
