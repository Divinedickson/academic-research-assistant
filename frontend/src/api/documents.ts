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
  uploaded_at: string
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
