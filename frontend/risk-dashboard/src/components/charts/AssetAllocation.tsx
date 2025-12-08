import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface AssetData {
  asset: string
  collateral: number
  borrowed: number
}

interface AssetAllocationProps {
  data: AssetData[]
}

export default function AssetAllocation({ data }: AssetAllocationProps) {
  const chartData = data.map((item) => ({
    name: item.asset,
    Collateral: item.collateral,
    Borrowed: item.borrowed,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis
          tickFormatter={(value) => `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
        />
        <Tooltip
          formatter={(value: number) => `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
        />
        <Legend />
        <Bar dataKey="Collateral" fill="#10b981" />
        <Bar dataKey="Borrowed" fill="#ef4444" />
      </BarChart>
    </ResponsiveContainer>
  )
}
