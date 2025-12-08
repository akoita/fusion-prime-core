export interface PortfolioExposure {
  totalCollateralUsd: number
  totalBorrowedUsd: number
  marginHealthScore: number
  positions: Position[]
}

export interface Position {
  asset: string
  chain: string
  collateralAmount: number
  collateralValueUsd: number
  borrowedAmount: number
  borrowedValueUsd: number
}

export interface MarginHealth {
  score: number
  status: 'healthy' | 'warning' | 'critical' | 'liquidation'
  threshold: number
  timestamp: string
}

export interface Alert {
  id: string
  type: 'margin_call' | 'liquidation' | 'warning'
  severity: 'low' | 'medium' | 'high' | 'critical'
  message: string
  timestamp: string
  acknowledged: boolean
}
