import { useState, useEffect } from 'react'
import axios from 'axios'

interface APIKey {
  key_id: string
  key_name: string
  tier: string
  created_at: string
  requests_today: number
  requests_limit: number
}

export default function APIKeys() {
  const [keys, setKeys] = useState<APIKey[]>([])
  const [loading, setLoading] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyTier, setNewKeyTier] = useState('free')

  const apiKeyServiceUrl =
    import.meta.env.VITE_API_KEY_SERVICE_URL || 'https://api-key-service.run.app'

  useEffect(() => {
    loadKeys()
  }, [])

  const loadKeys = async () => {
    setLoading(true)
    try {
      const res = await axios.get(`${apiKeyServiceUrl}/api/v1/keys`)
      setKeys(res.data.keys || [])
    } catch (error) {
      console.error('Failed to load API keys:', error)
    } finally {
      setLoading(false)
    }
  }

  const createKey = async () => {
    if (!newKeyName) return

    setLoading(true)
    try {
      await axios.post(`${apiKeyServiceUrl}/api/v1/keys`, {
        key_name: newKeyName,
        tier: newKeyTier,
      })
      setNewKeyName('')
      setShowCreateForm(false)
      loadKeys()
    } catch (error) {
      console.error('Failed to create API key:', error)
    } finally {
      setLoading(false)
    }
  }

  const revokeKey = async (keyId: string) => {
    if (!confirm('Are you sure you want to revoke this API key?')) return

    setLoading(true)
    try {
      await axios.delete(`${apiKeyServiceUrl}/api/v1/keys/${keyId}`)
      loadKeys()
    } catch (error) {
      console.error('Failed to revoke API key:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">API Keys</h1>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          {showCreateForm ? 'Cancel' : 'Create API Key'}
        </button>
      </div>

      {showCreateForm && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Create New API Key</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Key Name
              </label>
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="My Application"
                className="w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tier
              </label>
              <select
                value={newKeyTier}
                onChange={(e) => setNewKeyTier(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2"
              >
                <option value="free">Free (100 req/min)</option>
                <option value="pro">Pro (1000 req/min)</option>
                <option value="enterprise">Enterprise (10000 req/min)</option>
              </select>
            </div>
            <button
              onClick={createKey}
              disabled={loading}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Create
            </button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Tier
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Usage
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading && keys.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                  Loading...
                </td>
              </tr>
            ) : keys.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                  No API keys. Create one to get started.
                </td>
              </tr>
            ) : (
              keys.map((key) => (
                <tr key={key.key_id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {key.key_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <span
                      className={`px-2 py-1 rounded text-xs font-semibold ${
                        key.tier === 'enterprise'
                          ? 'bg-purple-100 text-purple-800'
                          : key.tier === 'pro'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {key.tier}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(key.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {key.requests_today} / {key.requests_limit}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      onClick={() => revokeKey(key.key_id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
