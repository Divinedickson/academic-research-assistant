import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { API_BASE_URL } from '../api/client'
import { useAuth } from '../auth/useAuth'

type HealthState = 'checking' | 'online' | 'offline'

export function HomePage() {
  const { isAuthenticated, user } = useAuth()
  const [healthState, setHealthState] = useState<HealthState>('checking')
  const [message, setMessage] = useState('Checking backend health...')

  useEffect(() => {
    const controller = new AbortController()

    async function checkBackendHealth() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/health/`, {
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}`)
        }

        const data = await response.json()
        setHealthState(data.status === 'ok' ? 'online' : 'offline')
        setMessage(
          data.status === 'ok'
            ? 'Backend API is available.'
            : 'Backend responded, but the health status was unexpected.',
        )
      } catch {
        if (!controller.signal.aborted) {
          setHealthState('offline')
          setMessage('Backend API is not reachable.')
        }
      }
    }

    checkBackendHealth()

    return () => controller.abort()
  }, [])

  return (
    <section className="panel" aria-live="polite">
      <p className="eyebrow">Academic Research Assistant</p>
      <h1>Project foundation</h1>
      <div className={`status-indicator ${healthState}`}>
        <span aria-hidden="true" />
        <strong>{healthState}</strong>
      </div>
      <p>{message}</p>
      <code>{API_BASE_URL}/api/health/</code>
      <div className="actions">
        {isAuthenticated ? (
          <Link className="button primary" to="/dashboard">
            Open dashboard for {user?.username}
          </Link>
        ) : (
          <>
            <Link className="button primary" to="/login">
              Log in
            </Link>
            <Link className="button" to="/register">
              Register
            </Link>
          </>
        )}
      </div>
    </section>
  )
}
