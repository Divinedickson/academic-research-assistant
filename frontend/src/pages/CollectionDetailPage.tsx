import { type FormEvent, useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  type Document,
  type DocumentChunk,
  type SemanticSearchResult,
  type ResearchCollection,
  deleteDocument,
  embedDocument,
  getCollection,
  listDocumentChunks,
  listDocuments,
  processDocument,
  searchCollection,
  uploadDocument,
} from '../api/documents'

function formatFileSize(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError && typeof error.data === 'object' && error.data) {
    return Object.values(error.data).flat().join(' ')
  }

  return 'Something went wrong.'
}

export function CollectionDetailPage() {
  const params = useParams()
  const collectionId = Number(params.collectionId)
  const [collection, setCollection] = useState<ResearchCollection | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [processingDocumentId, setProcessingDocumentId] = useState<number | null>(null)
  const [embeddingDocumentId, setEmbeddingDocumentId] = useState<number | null>(null)
  const [expandedDocumentId, setExpandedDocumentId] = useState<number | null>(null)
  const [chunksByDocumentId, setChunksByDocumentId] = useState<Record<number, DocumentChunk[]>>({})
  const [searchQuery, setSearchQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [searchResults, setSearchResults] = useState<SemanticSearchResult[]>([])
  const [scoreDescription, setScoreDescription] = useState('')
  const [isSearching, setIsSearching] = useState(false)

  const loadCollection = useCallback(async () => {
    try {
      const [collectionResponse, documentResponse] = await Promise.all([
        getCollection(collectionId),
        listDocuments(collectionId),
      ])
      setCollection(collectionResponse)
      setDocuments(documentResponse)
      setError('')
    } catch (caughtError) {
      setError(getErrorMessage(caughtError))
    } finally {
      setIsLoading(false)
    }
  }, [collectionId])

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    loadCollection()
  }, [loadCollection])

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!file) {
      setError('Choose a PDF file to upload.')
      return
    }

    setIsUploading(true)
    setError('')

    try {
      const document = await uploadDocument(collectionId, { title, file })
      setDocuments((current) => [document, ...current])
      setTitle('')
      setFile(null)
      event.currentTarget.reset()
    } catch (caughtError) {
      setError(getErrorMessage(caughtError))
    } finally {
      setIsUploading(false)
    }
  }

  async function handleDeleteDocument(document: Document) {
    const confirmed = window.confirm(`Delete "${document.title}"?`)

    if (!confirmed) {
      return
    }

    try {
      await deleteDocument(document.id)
      setDocuments((current) => current.filter((item) => item.id !== document.id))
      setChunksByDocumentId((current) => {
        const next = { ...current }
        delete next[document.id]
        return next
      })
    } catch (caughtError) {
      setError(getErrorMessage(caughtError))
    }
  }

  async function handleProcessDocument(document: Document) {
    setProcessingDocumentId(document.id)
    setError('')

    try {
      const processedDocument = await processDocument(document.id)
      setDocuments((current) =>
        current.map((item) => (item.id === document.id ? processedDocument : item)),
      )
      setChunksByDocumentId((current) => {
        const next = { ...current }
        delete next[document.id]
        return next
      })
    } catch (caughtError) {
      setError(getErrorMessage(caughtError))
    } finally {
      setProcessingDocumentId(null)
    }
  }

  async function handleEmbedDocument(document: Document) {
    setEmbeddingDocumentId(document.id)
    setError('')

    try {
      const embeddedDocument = await embedDocument(document.id)
      setDocuments((current) =>
        current.map((item) => (item.id === document.id ? embeddedDocument : item)),
      )
    } catch (caughtError) {
      setError(getErrorMessage(caughtError))
    } finally {
      setEmbeddingDocumentId(null)
    }
  }

  async function handleToggleChunks(document: Document) {
    if (expandedDocumentId === document.id) {
      setExpandedDocumentId(null)
      return
    }

    setExpandedDocumentId(document.id)

    if (chunksByDocumentId[document.id]) {
      return
    }

    try {
      const chunks = await listDocumentChunks(document.id)
      setChunksByDocumentId((current) => ({
        ...current,
        [document.id]: chunks,
      }))
    } catch (caughtError) {
      setError(getErrorMessage(caughtError))
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSearching(true)
    setError('')

    try {
      const response = await searchCollection(collectionId, {
        query: searchQuery,
        top_k: topK,
      })
      setSearchResults(response.results)
      setScoreDescription(response.score_description)
    } catch (caughtError) {
      setError(getErrorMessage(caughtError))
    } finally {
      setIsSearching(false)
    }
  }

  if (isLoading) {
    return <p className="page-message">Loading collection...</p>
  }

  return (
    <div className="page-stack">
      <section className="panel">
        <Link to="/dashboard">Back to dashboard</Link>
        <p className="eyebrow">Collection</p>
        <h1>{collection?.name ?? 'Collection unavailable'}</h1>
        <p>{collection?.description || 'No description'}</p>
      </section>

      <section className="panel">
        <h2>Upload PDF</h2>
        <form className="auth-form" onSubmit={handleUpload}>
          <label>
            Title
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label>
            PDF file
            <input
              accept="application/pdf,.pdf"
              type="file"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              required
            />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="button primary" disabled={isUploading} type="submit">
            {isUploading ? 'Uploading...' : 'Upload PDF'}
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>Documents</h2>
        {documents.length === 0 ? <p>No documents uploaded yet.</p> : null}
        <div className="item-list">
          {documents.map((document) => (
            <article className="item-row" key={document.id}>
              <div>
                <h3>{document.title}</h3>
                <p>{document.original_filename}</p>
                <small>
                  {formatFileSize(document.file_size)} | {document.processing_status} |{' '}
                  {new Date(document.uploaded_at).toLocaleString()}
                </small>
                {document.processing_status === 'ready' ? (
                  <p className="status-note">
                    {document.page_count} page(s) processed
                    {document.processed_at
                      ? ` on ${new Date(document.processed_at).toLocaleString()}`
                      : ''}
                  </p>
                ) : null}
                {document.processing_status === 'ready' ? (
                  <p className="status-note">Embedding status: {document.embedding_status}</p>
                ) : null}
                {document.processing_status === 'failed' && document.processing_error ? (
                  <p className="form-error">{document.processing_error}</p>
                ) : null}
                {document.embedding_status === 'failed' && document.embedding_error ? (
                  <p className="form-error">{document.embedding_error}</p>
                ) : null}
                {expandedDocumentId === document.id ? (
                  <div className="chunk-preview">
                    {(chunksByDocumentId[document.id] ?? []).length === 0 ? (
                      <p>No chunks available.</p>
                    ) : (
                      chunksByDocumentId[document.id].map((chunk) => (
                        <section key={chunk.chunk_index}>
                          <strong>
                            Page {chunk.page_number}, chunk {chunk.chunk_index + 1}
                          </strong>
                          <p>{chunk.content}</p>
                        </section>
                      ))
                    )}
                  </div>
                ) : null}
              </div>
              <div className="row-actions">
                {document.processing_status === 'uploaded' ||
                document.processing_status === 'failed' ? (
                  <button
                    className="button primary"
                    disabled={processingDocumentId === document.id}
                    type="button"
                    onClick={() => handleProcessDocument(document)}
                  >
                    {processingDocumentId === document.id ? 'Processing...' : 'Process paper'}
                  </button>
                ) : null}
                {document.processing_status === 'ready' &&
                document.embedding_status !== 'embedded' ? (
                  <button
                    className="button primary"
                    disabled={embeddingDocumentId === document.id}
                    type="button"
                    onClick={() => handleEmbedDocument(document)}
                  >
                    {embeddingDocumentId === document.id ? 'Embedding...' : 'Embed paper'}
                  </button>
                ) : null}
                <button
                  className="button"
                  type="button"
                  onClick={() => handleToggleChunks(document)}
                >
                  {expandedDocumentId === document.id ? 'Hide chunks' : 'Preview chunks'}
                </button>
                <button
                  className="button danger"
                  type="button"
                  onClick={() => handleDeleteDocument(document)}
                >
                  Delete
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Semantic search</h2>
        <p>
          This searches embedded chunks by meaning. It does not generate AI answers.
        </p>
        <form className="auth-form" onSubmit={handleSearch}>
          <label>
            Question or search phrase
            <input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              required
            />
          </label>
          <label>
            Number of results
            <input
              max={20}
              min={1}
              type="number"
              value={topK}
              onChange={(event) => setTopK(Number(event.target.value))}
            />
          </label>
          <button className="button primary" disabled={isSearching} type="submit">
            {isSearching ? 'Searching...' : 'Search embedded chunks'}
          </button>
        </form>
        {scoreDescription ? <p className="status-note">{scoreDescription}</p> : null}
        <div className="item-list">
          {searchResults.map((result) => (
            <article className="search-result" key={result.chunk_id}>
              <strong>
                {result.document_title}, page {result.page_number}
              </strong>
              <small>
                similarity {result.similarity_score.toFixed(3)} | distance{' '}
                {result.cosine_distance.toFixed(3)}
              </small>
              <p>{result.content}</p>
            </article>
          ))}
        </div>
        {scoreDescription && searchResults.length === 0 ? (
          <p>No embedded chunks matched this search.</p>
        ) : null}
      </section>
    </div>
  )
}
