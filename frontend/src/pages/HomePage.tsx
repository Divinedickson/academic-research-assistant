import { Link } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

const features = [
  {
    title: 'Organize your literature',
    description: 'Keep papers together in focused research collections.',
  },
  {
    title: 'Ask in your own words',
    description: 'Ask natural questions and find useful passages across your papers.',
  },
  {
    title: 'Check the evidence',
    description: 'Expand citations to inspect the passage behind each answer.',
  },
]

const workflowSteps = [
  'Create a collection.',
  'Upload your PDF papers.',
  'Prepare each paper for questions.',
  'Ask a question and review the supporting sources.',
]

const limitations = [
  'Scanned PDFs currently require OCR and are not supported.',
  'Generated answers can be incorrect; verify the cited passages.',
  'Questions and selected excerpts are sent to an external AI service when generating answers.',
  'Upload only papers you have permission to process.',
]

export function HomePage() {
  const { isAuthenticated } = useAuth()

  return (
    <div className="landing-page">
      <section className="landing-hero">
        <div className="hero-copy">
          <p className="eyebrow">Academic Research Assistant</p>
          <h1>Research papers, clearer answers.</h1>
          <p className="hero-description">
            Organize academic PDFs and ask questions with answers linked to the original evidence.
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
      </section>

      <section className="landing-section" aria-labelledby="features-heading">
        <div className="section-heading">
          <p className="eyebrow">Features</p>
          <h2 id="features-heading">Built for evidence-first reading</h2>
        </div>
        <div className="feature-grid">
          {features.map((feature) => (
            <article className="feature-card" key={feature.title}>
              <span className="feature-mark" aria-hidden="true" />
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
