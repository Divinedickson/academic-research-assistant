import { useEffect, useState } from 'react'
import './App.css'

type HealthState = 'checking' | 'online' | 'offline'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

function App() {
  const [healthState, setHealthState] = useState<HealthState>('checking')
  const [message, setMessage] = useState('Checking backend health...')

  useEffect(() => {
    const controller = new AbortController()

    async function checkBackendHealth() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/health/`, {
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
    <main className="app-shell">
      <section className="status-panel" aria-live="polite">
        <p className="eyebrow">Academic Research Assistant</p>
        <h1>Project foundation</h1>
        <div className={`status-indicator ${healthState}`}>
          <span aria-hidden="true" />
          <strong>{healthState}</strong>
        </div>
        <p>{message}</p>
        <code>{apiBaseUrl}/api/health/</code>
      </section>
    </main>
  )
}

export default App
