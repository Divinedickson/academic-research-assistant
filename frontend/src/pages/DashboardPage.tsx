import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

export function DashboardPage() {
  const navigate = useNavigate()
  const { logout, user } = useAuth()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <section className="panel">
      <p className="eyebrow">Protected dashboard</p>
      <h1>Dashboard</h1>
      <p>You are signed in as {user?.username}.</p>
      <dl className="user-details">
        <div>
          <dt>Email</dt>
          <dd>{user?.email || 'No email provided'}</dd>
        </div>
      </dl>
      <button className="button" type="button" onClick={handleLogout}>
        Log out
      </button>
    </section>
  )
}
