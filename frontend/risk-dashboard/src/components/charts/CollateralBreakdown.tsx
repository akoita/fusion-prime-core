import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

interface Position {
  asset: string
  value: number
}

interface CollateralBreakdownProps {
  positions: Position[]
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

export default function CollateralBreakdown({ positions }: CollateralBreakdownProps) {
  const data = positions.map((pos) => ({
    name: pos.asset,
    value: pos.value,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={(props: any) => {
            const { name, percent } = props
            return `${name} ${(percent * 100).toFixed(0)}%`
          }}
          outerRadius={100}
          fill="#8884d8"
          dataKey="value"
        >
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number) => `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}
