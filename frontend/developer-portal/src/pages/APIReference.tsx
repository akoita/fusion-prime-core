import { useEffect, useRef } from 'react'

export default function APIReference() {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Load Stoplight Elements for API documentation
    if (containerRef.current) {
      import('@stoplight/elements').then(({ API }) => {
        // This would load the OpenAPI spec and render it
        // For now, showing placeholder
      })
    }
  }, [])

  return (
    <div className="px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">API Reference</h1>

      <div ref={containerRef} className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-600 mb-4">
          Interactive API documentation will be loaded here using Stoplight Elements.
        </p>
        <p className="text-sm text-gray-500">
          The OpenAPI specification is available at:{' '}
          <code className="bg-gray-100 px-2 py-1 rounded">/openapi.yaml</code>
        </p>

        {/* Placeholder for Stoplight Elements */}
        <div className="mt-8 border border-gray-200 rounded p-8 text-center text-gray-400">
          <p>API Documentation will be rendered here</p>
          <p className="text-sm mt-2">
            Install @stoplight/elements and configure to load openapi.yaml
          </p>
        </div>
      </div>
    </div>
  )
}
