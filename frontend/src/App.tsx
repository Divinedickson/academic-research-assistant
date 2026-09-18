import { Link, Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { useAuth } from './auth/useAuth'
import { ProductLogo } from './components/ProductLogo'
import { CollectionDetailPage } from './pages/CollectionDetailPage'
import { DashboardPage } from './pages/DashboardPage'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'

function App() {
  const { isAuthenticated } = useAuth()

  return (
    <>
      <nav className="top-nav" aria-label="Main navigation">
        <Link className="brand-link" to="/">
          <ProductLogo className="brand-logo" />
          <span>Academic Research Assistant</span>
        </Link>
        <div className="nav-actions">
          {isAuthenticated ? (
            <Link className="button primary small" to="/dashboard">
              Open dashboard
            </Link>
          ) : (
            <>
              <Link to="/login">Sign in</Link>
              <Link className="button primary small" to="/register">
                Get started
              </Link>
            </>
          )}
        </div>
      </nav>
      <main className="app-shell">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/collections/:collectionId"
            element={
              <ProtectedRoute>
                <CollectionDetailPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  )
}

export default App
