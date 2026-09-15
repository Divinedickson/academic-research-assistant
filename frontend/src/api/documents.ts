import { apiClient } from './client'

export type ResearchCollection = {
  id: number
  name: string
  description: string
  document_count: number
  created_at: string
  updated_at: string
}

export type Document = {
  id: number
  collection: number
  title: string
  original_filename: string
  file_size: number
  processing_status: string
  page_count: number
  processed_at: string | null
  processing_error: string
  embedding_status: string
  embedding_error: string
  uploaded_at: string
}

export type DocumentChunk = {
  page_number: number
  chunk_index: number
  content: string
  character_count: number
}

export type SemanticSearchResult = {
  chunk_id: number
  document_id: number
  document_title: string
  original_filename: string
  page_number: number
  chunk_index: number
  content: string
  cosine_distance: number
  similarity_score: number
}

export type SemanticSearchResponse = {
  query: string
  top_k: number
  score_description: string
  results: SemanticSearchResult[]
}

export function listCollections() {
  return apiClient.request<ResearchCollection[]>('/api/collections/')
}

export function getCollection(id: number) {
  return apiClient.request<ResearchCollection>(`/api/collections/${id}/`)
}

export function createCollection(input: { name: string; description: string }) {
  return apiClient.request<ResearchCollection>('/api/collections/', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function updateCollection(
  id: number,
  input: Partial<Pick<ResearchCollection, 'name' | 'description'>>,
) {
  return apiClient.request<ResearchCollection>(`/api/collections/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

export function deleteCollection(id: number) {
  return apiClient.request<null>(`/api/collections/${id}/`, {
    method: 'DELETE',
  })
}

export function listDocuments(collectionId: number) {
  return apiClient.request<Document[]>(`/api/collections/${collectionId}/documents/`)
}

export function uploadDocument(collectionId: number, input: { title: string; file: File }) {
  const formData = new FormData()
  formData.append('file', input.file)

  if (input.title.trim()) {
    formData.append('title', input.title.trim())
  }

  return apiClient.request<Document>(`/api/collections/${collectionId}/documents/`, {
    method: 'POST',
    body: formData,
  })
}

export function deleteDocument(id: number) {
  return apiClient.request<null>(`/api/documents/${id}/`, {
    method: 'DELETE',
  })
}

export function processDocument(id: number) {
  return apiClient.request<Document>(`/api/documents/${id}/process/`, {
    method: 'POST',
  })
}

export function embedDocument(id: number) {
  return apiClient.request<Document>(`/api/documents/${id}/embed/`, {
    method: 'POST',
  })
}

export function listDocumentChunks(id: number) {
  return apiClient.request<DocumentChunk[]>(`/api/documents/${id}/chunks/`)
}

export function searchCollection(collectionId: number, input: { query: string; top_k: number }) {
  return apiClient.request<SemanticSearchResponse>(`/api/collections/${collectionId}/search/`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}
