import { useState } from 'react'
import axios from 'axios'

export default function Playground() {
  const [apiKey, setApiKey] = useState('')
  const [endpoint, setEndpoint] = useState('/v1/health')
  const [method, setMethod] = useState('GET')
  const [requestBody, setRequestBody] = useState('')
  const [response, setResponse] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'https://api-dev.fusionprime.dev'

  const handleRequest = async () => {
    setLoading(true)
    setResponse(null)

    try {
      const config: any = {
        method: method.toLowerCase(),
        url: `${apiBaseUrl}${endpoint}`,
        headers: {
          'Content-Type': 'application/json',
        },
      }

      if (apiKey) {
        config.headers['X-API-Key'] = apiKey
      }

      if (method !== 'GET' && requestBody) {
        config.data = JSON.parse(requestBody)
      }

      const res = await axios(config)
      setResponse({
        status: res.status,
        data: res.data,
        headers: res.headers,
      })
    } catch (error: any) {
      setResponse({
        status: error.response?.status || 'Error',
        error: error.response?.data || error.message,
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">API Playground</h1>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Request Configuration */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Request Configuration</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                API Key (optional)
              </label>
              <input
                type="text"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="fp_..."
                className="w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                HTTP Method
              </label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2"
              >
                <option>GET</option>
                <option>POST</option>
                <option>PUT</option>
                <option>DELETE</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Endpoint
              </label>
              <input
                type="text"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder="/v1/health"
                className="w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>

            {method !== 'GET' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Request Body (JSON)
                </label>
                <textarea
                  value={requestBody}
                  onChange={(e) => setRequestBody(e.target.value)}
                  placeholder='{"key": "value"}'
                  rows={6}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 font-mono text-sm"
                />
              </div>
            )}

            <button
              onClick={handleRequest}
              disabled={loading}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Sending...' : 'Send Request'}
            </button>
          </div>
        </div>

        {/* Response */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Response</h2>

          {response ? (
            <div>
              <div className="mb-2">
                <span
                  className={`px-2 py-1 rounded text-sm font-semibold ${
                    response.status >= 200 && response.status < 300
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  {response.status}
                </span>
              </div>
              <pre className="bg-gray-50 p-4 rounded overflow-auto text-sm">
                {JSON.stringify(response.data || response.error, null, 2)}
              </pre>
            </div>
          ) : (
            <p className="text-gray-400 text-center py-8">
              {loading ? 'Loading...' : 'Response will appear here'}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
