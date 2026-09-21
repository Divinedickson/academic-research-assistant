const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000' : '')
).replace(/\/$/, '')

type RequestOptions = RequestInit & {
  auth?: boolean
}

type UnauthorizedHandler = () => Promise<string | null>

export class ApiError extends Error {
  status: number
  data: unknown

  constructor(status: number, data: unknown) {
    super(`API request failed with status ${status}`)
    this.status = status
    this.data = data
  }
}

export function getApiErrorMessage(
  error: unknown,
  fallback = 'We could not complete that request. Please try again.',
) {
  if (!(error instanceof ApiError) || typeof error.data !== 'object' || !error.data) {
    return fallback
  }

  return Object.values(error.data).flat().join(' ') || fallback
}

class ApiClient {
  private accessToken: string | null = null
  private unauthorizedHandler: UnauthorizedHandler | null = null

  setAccessToken(token: string | null) {
    this.accessToken = token
  }

  setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
    this.unauthorizedHandler = handler
  }

  async request<T>(path: string, options: RequestOptions = {}, hasRetried = false): Promise<T> {
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

    if (
      response.status === 401 &&
      options.auth !== false &&
      !hasRetried &&
      this.unauthorizedHandler
    ) {
      const refreshedAccessToken = await this.unauthorizedHandler()

      if (refreshedAccessToken) {
        this.setAccessToken(refreshedAccessToken)
        return this.request<T>(path, options, true)
      }
    }

    if (!response.ok) {
      throw new ApiError(response.status, data)
    }

    return data as T
  }
}

export const apiClient = new ApiClient()
export { API_BASE_URL }
