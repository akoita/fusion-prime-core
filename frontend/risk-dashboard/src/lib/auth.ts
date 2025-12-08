import axios from 'axios'

const IDENTITY_SERVICE_URL =
  import.meta.env.VITE_IDENTITY_SERVICE_URL || 'http://localhost:8002'

interface User {
  id: string
  email: string
  name: string
  role: string
  wallet_address?: string
  identity_address?: string
  is_verified: boolean
}

interface AuthTokens {
  accessToken: string
  refreshToken?: string
}

interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

interface UserResponse {
  id: number
  email: string
  name: string
  role: string
  wallet_address?: string
  identity_address?: string
  is_verified: boolean
  created_at: string
}

class AuthManager {
  private readonly ACCESS_TOKEN_KEY = 'auth_token'
  private readonly REFRESH_TOKEN_KEY = 'refresh_token'
  private readonly USER_KEY = 'auth_user'
  private refreshPromise: Promise<string> | null = null

  async login(email: string, password: string): Promise<User> {
    try {
      // Call Identity Service login endpoint
      const response = await axios.post<LoginResponse>(
        `${IDENTITY_SERVICE_URL}/auth/login`,
        { email, password }
      )

      const { access_token, refresh_token } = response.data

      // Store tokens
      this.setTokens({ accessToken: access_token, refreshToken: refresh_token })

      // Fetch user profile
      const user = await this.fetchUserProfile(access_token)
      this.setUser(user)

      return user
    } catch (error: any) {
      if (error.response?.status === 401) {
        throw new Error('Invalid email or password')
      }
      throw new Error(error.response?.data?.detail || 'Login failed')
    }
  }

  async register(
    email: string,
    password: string,
    name: string,
    walletAddress?: string
  ): Promise<User> {
    try {
      // Call Identity Service register endpoint
      const response = await axios.post<UserResponse>(
        `${IDENTITY_SERVICE_URL}/auth/register`,
        {
          email,
          password,
          name,
          wallet_address: walletAddress,
        }
      )

      // After registration, log in automatically
      return await this.login(email, password)
    } catch (error: any) {
      if (error.response?.status === 400) {
        throw new Error(error.response.data.detail || 'Email already registered')
      }
      throw new Error(error.response?.data?.detail || 'Registration failed')
    }
  }

  private async fetchUserProfile(accessToken: string): Promise<User> {
    try {
      // For now, we'll decode the JWT to get user info (basic implementation)
      // In production, you'd call a /auth/me endpoint
      const tokenParts = accessToken.split('.')
      if (tokenParts.length !== 3) {
        throw new Error('Invalid token format')
      }

      const payload = JSON.parse(atob(tokenParts[1]))

      // Return user data from token
      // Note: This is a simplified version. In production, call /auth/me endpoint
      return {
        id: payload.sub,
        email: payload.email,
        name: payload.name || 'User',
        role: payload.role || 'user',
        is_verified: false,
      }
    } catch (error) {
      // Fallback: return minimal user data
      return {
        id: '1',
        email: 'user@example.com',
        name: 'User',
        role: 'user',
        is_verified: false,
      }
    }
  }

  async logout(): Promise<void> {
    try {
      const refreshToken = this.getRefreshToken()
      if (refreshToken) {
        // Call logout endpoint to revoke refresh token
        await axios.post(`${IDENTITY_SERVICE_URL}/auth/logout`, {
          refresh_token: refreshToken,
        })
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      // Clear local storage
      localStorage.removeItem(this.ACCESS_TOKEN_KEY)
      localStorage.removeItem(this.REFRESH_TOKEN_KEY)
      localStorage.removeItem(this.USER_KEY)
      window.location.href = '/login'
    }
  }

  getToken(): string | null {
    return localStorage.getItem(this.ACCESS_TOKEN_KEY)
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY)
  }

  getUser(): User | null {
    const userStr = localStorage.getItem(this.USER_KEY)
    if (!userStr) return null
    try {
      return JSON.parse(userStr)
    } catch {
      return null
    }
  }

  isAuthenticated(): boolean {
    return !!this.getToken()
  }

  setTokens(tokens: AuthTokens): void {
    if (tokens.accessToken) {
      localStorage.setItem(this.ACCESS_TOKEN_KEY, tokens.accessToken)
    }
    if (tokens.refreshToken) {
      localStorage.setItem(this.REFRESH_TOKEN_KEY, tokens.refreshToken)
    }
  }

  setUser(user: User): void {
    localStorage.setItem(this.USER_KEY, JSON.stringify(user))
  }

  async refreshToken(): Promise<string> {
    // Prevent multiple simultaneous refresh requests
    if (this.refreshPromise) {
      return this.refreshPromise
    }

    this.refreshPromise = this._performRefresh()

    try {
      const newToken = await this.refreshPromise
      return newToken
    } finally {
      this.refreshPromise = null
    }
  }

  private async _performRefresh(): Promise<string> {
    const refreshToken = this.getRefreshToken()
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }

    try {
      const response = await axios.post<LoginResponse>(
        `${IDENTITY_SERVICE_URL}/auth/refresh`,
        { refresh_token: refreshToken }
      )

      const { access_token, refresh_token: new_refresh_token } = response.data

      // Update tokens
      this.setTokens({
        accessToken: access_token,
        refreshToken: new_refresh_token,
      })

      return access_token
    } catch (error: any) {
      // If refresh fails, logout user
      this.logout()
      throw new Error('Session expired. Please login again.')
    }
  }
}

export const authManager = new AuthManager()
export type { User }
