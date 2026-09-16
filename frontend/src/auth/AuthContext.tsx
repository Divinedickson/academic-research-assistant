import {
  type ReactNode,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { apiClient } from '../api/client'
import {
  AuthContext,
  type LoginInput,
  type RegisterInput,
  type User,
} from './auth-context'

const REFRESH_TOKEN_STORAGE_KEY = 'ara_refresh_token'

type AuthResponse = {
  user: User
  access: string
  refresh: string
}

type RefreshResponse = {
  access: string
}

function storeSession(authResponse: AuthResponse) {
  apiClient.setAccessToken(authResponse.access)
  localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, authResponse.refresh)
}

function clearSession() {
  apiClient.setAccessToken(null)
  localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  async function loadCurrentUser() {
    const currentUser = await apiClient.request<User>('/api/auth/me/')
    setUser(currentUser)
  }

  async function refreshAccessToken() {
    const refresh = localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)

    if (!refresh) {
      return null
    }

    try {
      const refreshResponse = await apiClient.request<RefreshResponse>(
        '/api/auth/token/refresh/',
        {
          method: 'POST',
          auth: false,
          body: JSON.stringify({ refresh }),
        },
      )
      apiClient.setAccessToken(refreshResponse.access)
      return refreshResponse.access
    } catch {
      clearSession()
      setUser(null)
      return null
    }
  }

  async function register(input: RegisterInput) {
    const authResponse = await apiClient.request<AuthResponse>('/api/auth/register/', {
      method: 'POST',
      auth: false,
      body: JSON.stringify(input),
    })
    storeSession(authResponse)
    setUser(authResponse.user)
  }

  async function login(input: LoginInput) {
    const authResponse = await apiClient.request<AuthResponse>('/api/auth/login/', {
      method: 'POST',
      auth: false,
      body: JSON.stringify(input),
    })
    storeSession(authResponse)
    setUser(authResponse.user)
  }

  function logout() {
    clearSession()
    setUser(null)
  }

  useEffect(() => {
    apiClient.setUnauthorizedHandler(refreshAccessToken)

    return () => {
      apiClient.setUnauthorizedHandler(null)
    }
  })

  useEffect(() => {
    async function restoreSession() {
      const access = await refreshAccessToken()

      if (!access) {
        setIsLoading(false)
        return
      }

      try {
        await loadCurrentUser()
      } catch {
        clearSession()
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    }

    restoreSession()
  }, [])

  const value = useMemo(
    () => ({
      user,
      isLoading,
      isAuthenticated: Boolean(user),
      register,
      login,
      logout,
      loadCurrentUser,
    }),
    [user, isLoading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
