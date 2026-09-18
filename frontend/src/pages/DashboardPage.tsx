import { type FormEvent, useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/client'
import {
  type ResearchCollection,
  createCollection,
  deleteCollection,
  listCollections,
  updateCollection,
} from '../api/documents'
import { useAuth } from '../auth/useAuth'

export function DashboardPage() {
  const navigate = useNavigate()
  const { logout, user } = useAuth()
  const [collections, setCollections] = useState<ResearchCollection[]>([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingName, setEditingName] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const loadCollections = useCallback(async () => {
    try {
      const collectionResponse = await listCollections()
      setCollections(collectionResponse)
      setError('')
    } catch (caughtError) {
      setError(getApiErrorMessage(caughtError))
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    loadCollections()
  }, [loadCollections])

  function handleLogout() {
    logout()
    navigate('/login')
  }

  async function handleCreateCollection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSubmitting(true)
    setError('')

    try {
      const collection = await createCollection({ name, description })
      setCollections((current) => [collection, ...current])
      setName('')
      setDescription('')
    } catch (caughtError) {
      setError(getApiErrorMessage(caughtError))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleRename(collection: ResearchCollection) {
    if (!editingName.trim()) {
      setError('Collection name is required.')
      return
    }

    try {
      const updatedCollection = await updateCollection(collection.id, {
        name: editingName.trim(),
      })
      setCollections((current) =>
        current.map((item) => (item.id === collection.id ? updatedCollection : item)),
      )
      setEditingId(null)
      setEditingName('')
    } catch (caughtError) {
      setError(getApiErrorMessage(caughtError))
    }
  }

  async function handleDeleteCollection(collection: ResearchCollection) {
    const confirmed = window.confirm(`Delete "${collection.name}" and its documents?`)

    if (!confirmed) {
      return
    }

    try {
      await deleteCollection(collection.id)
      setCollections((current) => current.filter((item) => item.id !== collection.id))
    } catch (caughtError) {
      setError(getApiErrorMessage(caughtError))
    }
  }

  return (
    <div className="page-stack">
      <section className="panel">
        <p className="eyebrow">Your workspace</p>
        <h1>Research collections</h1>
        <p>You are signed in as {user?.username}.</p>
        <button className="button" type="button" onClick={handleLogout}>
          Log out
        </button>
      </section>

      <section className="panel">
        <h2>Create collection</h2>
        <form className="auth-form" onSubmit={handleCreateCollection}>
          <label>
            Name
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
            />
          </label>
          <label>
            Description
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
            />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="button primary" disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Creating...' : 'Create collection'}
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>Your collections</h2>
        {isLoading ? <p>Loading collections...</p> : null}
        {!isLoading && collections.length === 0 ? <p>No collections yet.</p> : null}
        <div className="item-list">
          {collections.map((collection) => (
            <article className="item-row" key={collection.id}>
              {editingId === collection.id ? (
                <div className="edit-row">
                  <input
                    value={editingName}
                    onChange={(event) => setEditingName(event.target.value)}
                  />
                  <button
                    className="button primary"
                    type="button"
                    onClick={() => handleRename(collection)}
                  >
                    Save
                  </button>
                  <button
                    className="button"
                    type="button"
                    onClick={() => setEditingId(null)}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <>
                  <div>
                    <h3>
                      <Link to={`/collections/${collection.id}`}>{collection.name}</Link>
                    </h3>
                    <p>{collection.description || 'No description'}</p>
                    <small>{collection.document_count} document(s)</small>
                  </div>
                  <div className="row-actions">
                    <button
                      className="button"
                      type="button"
                      onClick={() => {
                        setEditingId(collection.id)
                        setEditingName(collection.name)
                      }}
                    >
                      Rename
                    </button>
                    <button
                      className="button danger"
                      type="button"
                      onClick={() => handleDeleteCollection(collection)}
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
