import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { ProductLogo } from '../components/ProductLogo'

export function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      await login({ username, password })
      navigate('/dashboard')
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.status === 401) {
        setError('Invalid username or password.')
      } else {
        setError('Unable to log in right now.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <section className="panel auth-panel">
        <Link className="auth-brand" to="/">
          <ProductLogo className="auth-logo" />
          <span>Academic Research Assistant</span>
        </Link>
        <p className="eyebrow">Welcome back</p>
        <h1>Log in</h1>
        <form className="auth-form" onSubmit={handleSubmit}>
        <label>
          Username
          <input
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            autoComplete="current-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error ? <p className="form-error">{error}</p> : null}
        <button className="button primary" disabled={isSubmitting} type="submit">
          {isSubmitting ? 'Logging in...' : 'Log in'}
        </button>
        </form>
        <p>
          New here? <Link to="/register">Create an account</Link>.
        </p>
      </section>
    </div>
  )
}
