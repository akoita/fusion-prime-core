import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authManager, User } from '@/lib/auth'

interface AuthContextType {
  user: User | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  isLoading: boolean
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Check if user is already authenticated
    const savedUser = authManager.getUser()
    if (savedUser && authManager.isAuthenticated()) {
      setUser(savedUser)
    }
    setIsLoading(false)
  }, [])

  const login = async (email: string, password: string) => {
    try {
      const authenticatedUser = await authManager.login(email, password)
      setUser(authenticatedUser)
    } catch (error) {
      throw error
    }
  }

  const logout = () => {
    authManager.logout()
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        logout,
        isLoading,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
