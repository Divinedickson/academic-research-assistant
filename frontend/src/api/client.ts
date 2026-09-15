const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

type RequestOptions = RequestInit & {
  auth?: boolean
}

export class ApiError extends Error {
  status: number
  data: unknown

  constructor(status: number, data: unknown) {
    super(`API request failed with status ${status}`)
    this.status = status
    this.data = data
  }
}

class ApiClient {
  private accessToken: string | null = null

  setAccessToken(token: string | null) {
    this.accessToken = token
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const headers = new Headers(options.headers)

    if (options.body && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json')
    }

    if (options.auth !== false && this.accessToken) {
      headers.set('Authorization', `Bearer ${this.accessToken}`)
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    })
    const text = await response.text()
    const data = text ? JSON.parse(text) : null

    if (!response.ok) {
      throw new ApiError(response.status, data)
    }

    return data as T
  }
}

export const apiClient = new ApiClient()
export { API_BASE_URL }
