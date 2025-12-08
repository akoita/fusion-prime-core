import axios, { AxiosInstance } from 'axios'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  'https://risk-engine-961424092563.us-central1.run.app'

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for automatic token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // Handle 401 Unauthorized - try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // Dynamically import authManager to avoid circular dependency
        const { authManager } = await import('./auth')

        // Attempt to refresh token
        const newToken = await authManager.refreshToken()

        // Update the failed request with new token
        originalRequest.headers.Authorization = `Bearer ${newToken}`

        // Retry the original request
        return apiClient(originalRequest)
      } catch (refreshError) {
        // Refresh failed, redirect to login
        console.error('Token refresh failed:', refreshError)
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)
