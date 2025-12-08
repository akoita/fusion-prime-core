import { useEffect, useRef } from 'react'

interface MarginHealthGaugeProps {
  score: number
  threshold?: number
  size?: number
}

export default function MarginHealthGauge({
  score,
  threshold = 30,
  size = 200,
}: MarginHealthGaugeProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const centerX = size / 2
    const centerY = size / 2
    const radius = size * 0.35
    const lineWidth = size * 0.08

    // Clear canvas
    ctx.clearRect(0, 0, size, size)

    // Draw background arc
    ctx.beginPath()
    ctx.arc(centerX, centerY, radius, Math.PI, 0, false)
    ctx.lineWidth = lineWidth
    ctx.strokeStyle = '#e5e7eb'
    ctx.stroke()

    // Determine color based on score
    let color = '#10b981' // green
    if (score < threshold * 0.5) {
      color = '#ef4444' // red (liquidation)
    } else if (score < threshold) {
      color = '#f59e0b' // orange (margin call)
    } else if (score < threshold * 1.5) {
      color = '#fbbf24' // yellow (warning)
    }

    // Calculate angle (0 = -180°, 100 = 0°)
    const normalizedScore = Math.min(Math.max(score, 0), 100)
    const angle = Math.PI - (normalizedScore / 100) * Math.PI

    // Draw score arc
    ctx.beginPath()
    ctx.arc(centerX, centerY, radius, Math.PI, angle, true)
    ctx.lineWidth = lineWidth
    ctx.strokeStyle = color
    ctx.lineCap = 'round'
    ctx.stroke()

    // Draw threshold markers
    const warningThreshold = threshold * 1.5
    if (warningThreshold <= 100) {
      const warningAngle = Math.PI - (warningThreshold / 100) * Math.PI
      ctx.beginPath()
      ctx.moveTo(
        centerX + radius * Math.cos(warningAngle),
        centerY - radius * Math.sin(warningAngle)
      )
      ctx.lineTo(
        centerX + (radius + lineWidth * 0.5) * Math.cos(warningAngle),
        centerY - (radius + lineWidth * 0.5) * Math.sin(warningAngle)
      )
      ctx.lineWidth = 2
      ctx.strokeStyle = '#fbbf24'
      ctx.stroke()
    }

    const callThreshold = threshold
    const callAngle = Math.PI - (callThreshold / 100) * Math.PI
    ctx.beginPath()
    ctx.moveTo(
      centerX + radius * Math.cos(callAngle),
      centerY - radius * Math.sin(callAngle)
    )
    ctx.lineTo(
      centerX + (radius + lineWidth * 0.5) * Math.cos(callAngle),
      centerY - (radius + lineWidth * 0.5) * Math.sin(callAngle)
    )
    ctx.lineWidth = 2
    ctx.strokeStyle = '#f59e0b'
    ctx.stroke()

    // Draw text
    ctx.fillStyle = '#1f2937'
    ctx.font = `bold ${size * 0.15}px sans-serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(`${score.toFixed(1)}%`, centerX, centerY - size * 0.1)

    ctx.fillStyle = '#6b7280'
    ctx.font = `${size * 0.08}px sans-serif`
    ctx.fillText('Margin Health', centerX, centerY + size * 0.1)

    // Status indicator
    let statusText = 'Healthy'
    if (score < threshold * 0.5) {
      statusText = 'Liquidation'
    } else if (score < threshold) {
      statusText = 'Margin Call'
    } else if (score < threshold * 1.5) {
      statusText = 'Warning'
    }

    ctx.fillStyle = color
    ctx.font = `${size * 0.07}px sans-serif`
    ctx.fillText(statusText, centerX, centerY + size * 0.2)
  }, [score, threshold, size])

  return (
    <div className="flex flex-col items-center">
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        className="drop-shadow-sm"
      />
      <div className="mt-4 text-sm text-gray-600 text-center">
        <div className="flex items-center justify-center gap-4 mt-2">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span>Healthy (&gt;{threshold * 1.5}%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <span>Warning ({threshold}-{threshold * 1.5}%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-orange-500"></div>
            <span>Margin Call (&lt;{threshold}%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <span>Liquidation (&lt;{threshold * 0.5}%)</span>
          </div>
        </div>
      </div>
    </div>
  )
}
