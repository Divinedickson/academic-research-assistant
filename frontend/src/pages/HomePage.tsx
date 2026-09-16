import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { API_BASE_URL } from '../api/client'
import { useAuth } from '../auth/useAuth'

type HealthState = 'checking' | 'online' | 'offline'

const features = [
  {
    title: 'Organize your literature',
    description: 'Keep papers together in focused research collections.',
  },
  {
    title: 'Search beyond keywords',
    description: 'Find relevant passages even when your question uses different wording.',
  },
  {
    title: 'Check the evidence',
    description: 'Expand citations to inspect the passage behind each answer.',
  },
]

const workflowSteps = [
  'Create a collection and upload a text-based PDF.',
  'Process and embed the paper.',
  'Search your collection or ask a research question.',
  'Review the answer and its supporting sources.',
]

const limitations = [
  'Scanned PDFs currently require OCR and are not supported.',
  'Generated answers can be incorrect; verify the cited passages.',
  'Questions and selected excerpts are sent to an external AI provider when generating answers.',
  'Upload only papers you have permission to process.',
]

export function HomePage() {
  const { isAuthenticated } = useAuth()
  const [healthState, setHealthState] = useState<HealthState>('checking')
  const [message, setMessage] = useState('Checking backend health')

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
            ? 'Backend API available'
            : 'Backend responded with an unexpected status',
        )
      } catch {
        if (!controller.signal.aborted) {
          setHealthState('offline')
          setMessage('Backend API not reachable')
        }
      }
    }

    checkBackendHealth()

    return () => controller.abort()
  }, [])

  return (
    <div className="landing-page">
      <section className="landing-hero">
        <div className="hero-copy">
          <p className="eyebrow">Academic Research Assistant</p>
          <h1>Explore research papers. Find answers backed by evidence.</h1>
          <p className="hero-description">
            Upload academic PDFs, search across your collection by meaning, and ask questions with
            answers linked to supporting passages and PDF page numbers.
          </p>
          <div className="actions">
            {isAuthenticated ? (
              <Link className="button primary" to="/dashboard">
                Open dashboard
              </Link>
            ) : (
              <Link className="button primary" to="/register">
                Get started
              </Link>
            )}
            <a className="button" href="#workflow">
              See how it works
            </a>
          </div>
        </div>
        <aside className="hero-panel" aria-label="System status">
          <div className={`status-indicator ${healthState}`} aria-live="polite">
            <span aria-hidden="true" />
            <strong>{healthState}</strong>
          </div>
          <p>{message}</p>
          <code>{API_BASE_URL}/api/health/</code>
        </aside>
      </section>

      <section className="landing-section" aria-labelledby="features-heading">
        <div className="section-heading">
          <p className="eyebrow">Features</p>
          <h2 id="features-heading">Built for evidence-first reading</h2>
        </div>
        <div className="feature-grid">
          {features.map((feature) => (
            <article className="feature-card" key={feature.title}>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section
        className="landing-section workflow-section"
        id="workflow"
        aria-labelledby="workflow-heading"
      >
        <div className="section-heading">
          <p className="eyebrow">How it works</p>
          <h2 id="workflow-heading">From PDF to cited answer</h2>
        </div>
        <ol className="workflow-list">
          {workflowSteps.map((step, index) => (
            <li key={step}>
              <span>{index + 1}</span>
              <p>{step}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="landing-section limits-section" aria-labelledby="limits-heading">
        <div className="section-heading">
          <p className="eyebrow">Limitations and privacy</p>
          <h2 id="limits-heading">Use with care</h2>
        </div>
        <ul className="limits-list">
          {limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}
