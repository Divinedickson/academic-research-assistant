import { createContext } from 'react'

export type User = {
  id: number
  username: string
  email: string
}

export type RegisterInput = {
  username: string
  email: string
  password: string
  password_confirmation: string
}

export type LoginInput = {
  username: string
  password: string
}

export type AuthContextValue = {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  register: (input: RegisterInput) => Promise<void>
  login: (input: LoginInput) => Promise<void>
  logout: () => void
  loadCurrentUser: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)
