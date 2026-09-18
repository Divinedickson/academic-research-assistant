import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { ProductLogo } from '../components/ProductLogo'

export function RegisterPage() {
  const navigate = useNavigate()
  const { register } = useAuth()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      await register({
        username,
        email,
        password,
        password_confirmation: passwordConfirmation,
      })
      navigate('/dashboard')
    } catch (caughtError) {
      setError(getApiErrorMessage(caughtError, 'Unable to register right now.'))
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
        <p className="eyebrow">Create account</p>
        <h1>Register</h1>
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
          Email
          <input
            autoComplete="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            autoComplete="new-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        <label>
          Confirm password
          <input
            autoComplete="new-password"
            type="password"
            value={passwordConfirmation}
            onChange={(event) => setPasswordConfirmation(event.target.value)}
            required
          />
        </label>
        {error ? <p className="form-error">{error}</p> : null}
        <button className="button primary" disabled={isSubmitting} type="submit">
          {isSubmitting ? 'Creating account...' : 'Register'}
        </button>
        </form>
        <p>
          Already have an account? <Link to="/login">Log in</Link>.
        </p>
      </section>
    </div>
  )
}
