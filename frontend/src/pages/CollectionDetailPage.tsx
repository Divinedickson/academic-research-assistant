import { type FormEvent, useCallback, useEffect, useId, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../api/client'
import {
  type CollectionAnswerResponse,
  type Document,
  type DocumentChunk,
  type ResearchCollection,
  askCollection,
  deleteDocument,
  embedDocument,
  getCollection,
  listDocumentChunks,
  listDocuments,
  processDocument,
  uploadDocument,
} from '../api/documents'

const DEFAULT_EVIDENCE_COUNT = 5

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function getPreparationState(document: Document, isPreparing: boolean) {
  if (isPreparing || document.processing_status === 'processing') {
    return { label: 'Preparing', tone: 'working', guidance: 'Please keep this page open.' }
  }
  if (document.processing_status === 'failed' || document.embedding_status === 'failed') {
    return {
      label: 'Preparation failed',
      tone: 'failed',
      guidance: 'Review the message below, then try preparing the paper again.',
    }
  }
  if (document.processing_status === 'ready' && document.embedding_status === 'embedded') {
    return {
      label: 'Ready to ask',
      tone: 'ready',
      guidance: 'This paper can now be used to answer questions.',
    }
  }
  if (document.processing_status === 'ready') {
    return {
      label: 'Uploaded',
      tone: 'uploaded',
      guidance: 'One more preparation step is needed before you can ask questions.',
    }
  }
  return {
    label: 'Uploaded',
    tone: 'uploaded',
    guidance: 'Prepare this paper before asking questions.',
  }
}

function UploadIcon() {
  return (
    <svg aria-hidden="true" className="upload-icon" viewBox="0 0 24 24">
      <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14v4.5A1.5 1.5 0 0 0 6.5 20h11a1.5 1.5 0 0 0 1.5-1.5V14" />
    </svg>
  )
}

export function CollectionDetailPage() {
  const params = useParams()
  const collectionId = Number(params.collectionId)
  const fileInputId = useId()
  const [collection, setCollection] = useState<ResearchCollection | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [pageError, setPageError] = useState('')
  const [uploadMessage, setUploadMessage] = useState('')
  const [uploadError, setUploadError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [processingDocumentId, setProcessingDocumentId] = useState<number | null>(null)
  const [embeddingDocumentId, setEmbeddingDocumentId] = useState<number | null>(null)
  const [deletingDocumentId, setDeletingDocumentId] = useState<number | null>(null)
  const [expandedDocumentId, setExpandedDocumentId] = useState<number | null>(null)
  const [chunksByDocumentId, setChunksByDocumentId] = useState<Record<number, DocumentChunk[]>>({})
  const [question, setQuestion] = useState('')
  const [answerResponse, setAnswerResponse] = useState<CollectionAnswerResponse | null>(null)
  const [askError, setAskError] = useState('')
  const [isAsking, setIsAsking] = useState(false)

  const loadCollection = useCallback(async () => {
    try {
      const [collectionResponse, documentResponse] = await Promise.all([
        getCollection(collectionId),
        listDocuments(collectionId),
      ])
      setCollection(collectionResponse)
      setDocuments(documentResponse)
      setPageError('')
    } catch (caughtError) {
      setPageError(getApiErrorMessage(caughtError, 'We could not load this collection. Return to the dashboard and try again.'))
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
    const form = event.currentTarget
    if (!file) {
      setUploadError('Choose a PDF file before uploading.')
      return
    }
    setIsUploading(true)
    setUploadError('')
    setUploadMessage('')
    try {
      const document = await uploadDocument(collectionId, { title, file })
      setDocuments((current) => [document, ...current])
      setTitle('')
      setFile(null)
      setUploadMessage(`${document.original_filename} was uploaded. Prepare it next.`)
      form.reset()
    } catch (caughtError) {
      setUploadError(getApiErrorMessage(caughtError, 'The PDF could not be uploaded. Check the file and try again.'))
    } finally {
      setIsUploading(false)
    }
  }

  async function handleDeleteDocument(document: Document) {
    if (!window.confirm(`Delete "${document.title}"?`)) return
    setDeletingDocumentId(document.id)
    setPageError('')
    try {
      await deleteDocument(document.id)
      setDocuments((current) => current.filter((item) => item.id !== document.id))
      setChunksByDocumentId((current) => {
        const next = { ...current }
        delete next[document.id]
        return next
      })
    } catch (caughtError) {
      setPageError(getApiErrorMessage(caughtError, 'The paper could not be deleted. Please try again.'))
    } finally {
      setDeletingDocumentId(null)
    }
  }

  async function handleProcessDocument(document: Document) {
    setProcessingDocumentId(document.id)
    setPageError('')
    try {
      const updated = await processDocument(document.id)
      setDocuments((current) => current.map((item) => (item.id === document.id ? updated : item)))
      setChunksByDocumentId((current) => {
        const next = { ...current }
        delete next[document.id]
        return next
      })
    } catch (caughtError) {
      setPageError(getApiErrorMessage(caughtError, 'This paper could not be prepared. Review its status and try again.'))
    } finally {
      setProcessingDocumentId(null)
    }
  }

  async function handleEmbedDocument(document: Document) {
    setEmbeddingDocumentId(document.id)
    setPageError('')
    try {
      const updated = await embedDocument(document.id)
      setDocuments((current) => current.map((item) => (item.id === document.id ? updated : item)))
    } catch (caughtError) {
      setPageError(getApiErrorMessage(caughtError, 'Preparation could not be finished. Please try again.'))
    } finally {
      setEmbeddingDocumentId(null)
    }
  }

  async function handleToggleText(document: Document) {
    if (expandedDocumentId === document.id) {
      setExpandedDocumentId(null)
      return
    }
    setExpandedDocumentId(document.id)
    if (chunksByDocumentId[document.id]) return
    try {
      const chunks = await listDocumentChunks(document.id)
      setChunksByDocumentId((current) => ({ ...current, [document.id]: chunks }))
    } catch (caughtError) {
      setPageError(getApiErrorMessage(caughtError, 'The extracted text could not be loaded. Please try again.'))
    }
  }

  async function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsAsking(true)
    setAskError('')
    setAnswerResponse(null)
    try {
      setAnswerResponse(await askCollection(collectionId, { question, top_k: DEFAULT_EVIDENCE_COUNT }))
    } catch (caughtError) {
      setAskError(getApiErrorMessage(caughtError, 'Your question could not be answered right now. Please try again.'))
    } finally {
      setIsAsking(false)
    }
  }

  if (isLoading) return <p className="page-message">Loading collection...</p>

  const readyDocumentCount = documents.filter(
    (document) => document.processing_status === 'ready' && document.embedding_status === 'embedded',
  ).length

  return (
    <div className="page-stack collection-page">
      <header className="collection-header">
        <Link className="back-link" to="/dashboard">Back to collections</Link>
        <p className="eyebrow">Research collection</p>
        <h1>{collection?.name ?? 'Collection unavailable'}</h1>
        <p>{collection?.description || 'Upload papers and ask questions about their contents.'}</p>
      </header>

      <ol className="collection-steps" aria-label="Collection workflow">
        <li className="complete"><span>1</span>Create collection</li>
        <li className={documents.length > 0 ? 'complete' : ''}><span>2</span>Upload papers</li>
        <li className={readyDocumentCount > 0 ? 'complete' : ''}><span>3</span>Prepare papers</li>
        <li><span>4</span>Ask questions</li>
      </ol>

      {pageError ? <p className="form-error" role="alert">{pageError}</p> : null}

      <section className="panel workflow-panel" aria-labelledby="upload-heading">
        <div className="section-intro">
          <p className="step-label">Step 2</p>
          <h2 id="upload-heading">Upload papers</h2>
          <p>Add a text-based PDF, up to 10 MB.</p>
        </div>
        <form className="upload-form" onSubmit={handleUpload}>
          <label className="field-label" htmlFor={`${fileInputId}-title`}>Paper title <span>(optional)</span></label>
          <input id={`${fileInputId}-title`} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Uses the filename when left blank" />
          <label className="file-picker" htmlFor={fileInputId}>
            <UploadIcon />
            <span className="file-picker-copy">
              <strong>{file ? file.name : 'Choose a PDF'}</strong>
              <small>{file ? `${formatFileSize(file.size)} selected` : 'PDF files only | Maximum 10 MB'}</small>
            </span>
          </label>
          <input className="file-input" id={fileInputId} accept="application/pdf,.pdf" type="file" onChange={(event) => {
            setFile(event.target.files?.[0] ?? null)
            setUploadError('')
            setUploadMessage('')
          }} required />
          {uploadError ? <p className="form-error" role="alert">{uploadError}</p> : null}
          {uploadMessage ? <p className="form-success" role="status">{uploadMessage}</p> : null}
          <button className="button primary" disabled={isUploading} type="submit">{isUploading ? 'Uploading PDF...' : 'Upload PDF'}</button>
        </form>
      </section>

      <section className="panel workflow-panel" aria-labelledby="papers-heading">
        <div className="section-intro">
          <p className="step-label">Step 3</p>
          <h2 id="papers-heading">Papers in this collection</h2>
          <p>Prepare each paper once so it can be used to answer questions.</p>
        </div>
        {documents.length === 0 ? (
          <div className="empty-state"><h3>No papers yet</h3><p>Upload your first PDF above to continue.</p></div>
        ) : (
          <div className="document-list">
            {documents.map((document) => {
              const isPreparing = processingDocumentId === document.id || embeddingDocumentId === document.id
              const status = getPreparationState(document, isPreparing)
              const canExtract = document.processing_status === 'uploaded' || document.processing_status === 'failed'
              const canFinish = document.processing_status === 'ready' && document.embedding_status !== 'embedded'
              const isDeleting = deletingDocumentId === document.id
              return (
                <article className="document-card" key={document.id}>
                  <div className="document-main">
                    <div className="document-heading">
                      <div><h3>{document.title}</h3><p className="filename">{document.original_filename}</p></div>
                      <span className={`status-badge ${status.tone}`}>{status.label}</span>
                    </div>
                    <p className="document-meta">{formatFileSize(document.file_size)} | Uploaded {new Date(document.uploaded_at).toLocaleDateString()}{document.page_count > 0 ? ` | ${document.page_count} PDF pages` : ''}</p>
                    <p className="next-step">{status.guidance}</p>
                    {document.processing_status === 'failed' && document.processing_error ? <p className="form-error" role="alert">{document.processing_error}</p> : null}
                    {document.embedding_status === 'failed' && document.embedding_error ? <p className="form-error" role="alert">{document.embedding_error}</p> : null}
                    {expandedDocumentId === document.id ? (
                      <div className="chunk-preview">
                        {(chunksByDocumentId[document.id] ?? []).length === 0 ? <p>No extracted text is available.</p> : chunksByDocumentId[document.id].map((chunk) => (
                          <section key={chunk.chunk_index}><strong>PDF page {chunk.page_number}</strong><p>{chunk.content}</p></section>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  <div className="document-actions">
                    {canExtract ? <button className="button primary" disabled={isPreparing || isDeleting} type="button" onClick={() => handleProcessDocument(document)}>{processingDocumentId === document.id ? 'Preparing...' : 'Prepare paper'}</button> : null}
                    {canFinish ? <button className="button primary" disabled={isPreparing || isDeleting} type="button" onClick={() => handleEmbedDocument(document)}>{embeddingDocumentId === document.id ? 'Finishing preparation...' : 'Finish preparation'}</button> : null}
                    {document.processing_status === 'ready' ? <button className="button" disabled={isPreparing || isDeleting} type="button" onClick={() => handleToggleText(document)}>{expandedDocumentId === document.id ? 'Hide extracted text' : 'Review extracted text'}</button> : null}
                    <button className="button danger" disabled={isPreparing || isDeleting} type="button" onClick={() => handleDeleteDocument(document)}>{isDeleting ? 'Deleting...' : 'Delete paper'}</button>
                  </div>
                </article>
              )
            })}
          </div>
        )}
      </section>

      <section className="panel workflow-panel ask-panel" aria-labelledby="ask-heading">
        <div className="section-intro">
          <p className="step-label">Step 4</p>
          <h2 id="ask-heading">Ask this collection</h2>
          <p>Get an answer based on the papers you prepared, with sources you can check.</p>
        </div>
        {readyDocumentCount === 0 ? (
          <div className="empty-state"><h3>Prepare a paper first</h3><p>Once a paper says "Ready to ask," you can ask questions here.</p></div>
        ) : (
          <>
            <form className="question-form" onSubmit={handleAsk}>
              <label className="field-label" htmlFor="collection-question">Your question</label>
              <textarea id="collection-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What did the researchers find?" required />
              <p className="privacy-note">Your question and selected paper excerpts are sent to an external AI service.</p>
              {askError ? <p className="form-error" role="alert">{askError}</p> : null}
              <button className="button primary" disabled={isAsking} type="submit">{isAsking ? 'Preparing your answer...' : 'Ask question'}</button>
            </form>
            {answerResponse ? (
              <div className="answer-box" aria-live="polite">
                <p className="answer-label">Answer from your papers</p>
                {answerResponse.insufficient_evidence ? <div className="insufficient-answer"><h3>Not enough evidence</h3><p>{answerResponse.answer}</p></div> : <p className="answer-text">{answerResponse.answer}</p>}
                {answerResponse.citations.length > 0 ? (
                  <div className="citation-list"><h3>Supporting sources</h3>{answerResponse.citations.map((citation) => (
                    <details key={citation.source_id}><summary>[{citation.source_id}] {citation.document_title} | PDF page {citation.page_number}</summary><p>{citation.passage}</p></details>
                  ))}</div>
                ) : null}
              </div>
            ) : null}
          </>
        )}
      </section>
    </div>
  )
}
