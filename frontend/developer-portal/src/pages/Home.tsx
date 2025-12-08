export default function Home() {
  return (
    <div className="px-4 py-8">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Fusion Prime API
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Unified API for cross-chain settlement, risk analytics, and fiat operations
        </p>
        <div className="flex justify-center gap-4">
          <a
            href="/reference"
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            View API Reference
          </a>
          <a
            href="/playground"
            className="px-6 py-3 bg-gray-200 text-gray-900 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Try in Playground
          </a>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6 mt-12">
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-2">Cross-Chain Settlement</h2>
          <p className="text-gray-600">
            Execute settlements across Ethereum, Polygon, Arbitrum, and Base using
            Axelar or Chainlink CCIP
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-2">Risk Analytics</h2>
          <p className="text-gray-600">
            Real-time margin health monitoring, VaR calculations, and portfolio
            analytics
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-2">Fiat Gateway</h2>
          <p className="text-gray-600">
            On-ramp and off-ramp fiat to stablecoins via Circle or Stripe integration
          </p>
        </div>
      </div>

      <div className="mt-12 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">
          Getting Started
        </h3>
        <ol className="list-decimal list-inside space-y-2 text-blue-800">
          <li>Create an API key in the <a href="/keys" className="underline">API Keys</a> section</li>
          <li>Review the <a href="/reference" className="underline">API Reference</a> documentation</li>
          <li>Test endpoints in the <a href="/playground" className="underline">Playground</a></li>
          <li>Integrate into your application</li>
        </ol>
      </div>
    </div>
  )
}
