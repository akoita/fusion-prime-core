import {
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface PerformanceData {
  date: string
  return: number
  cumulative_return: number
  benchmark_return?: number
}

interface PerformanceChartProps {
  data: PerformanceData[]
}

export default function PerformanceChart({ data }: PerformanceChartProps) {
  const chartData = data.map((item) => ({
    date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    Return: (item.return * 100).toFixed(2),
    'Cumulative Return': (item.cumulative_return * 100).toFixed(2),
    Benchmark: item.benchmark_return ? (item.benchmark_return * 100).toFixed(2) : null,
  }))

  return (
    <ResponsiveContainer width="100%" height={400}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="colorReturn" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="colorBenchmark" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#6b7280" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#6b7280" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis tickFormatter={(value) => `${value}%`} />
        <Tooltip
          formatter={(value: string) => `${value}%`}
        />
        <Legend />
        <Area
          type="monotone"
          dataKey="Cumulative Return"
          stroke="#3b82f6"
          fillOpacity={1}
          fill="url(#colorReturn)"
        />
        <Line
          type="monotone"
          dataKey="Benchmark"
          stroke="#6b7280"
          strokeWidth={2}
          strokeDasharray="5 5"
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
