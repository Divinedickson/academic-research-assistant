# Academic Research Assistant Agent Notes

This repository is being built milestone by milestone. Keep changes scoped to the approved milestone.

## Current Milestone

Milestone 7 adds grounded answer generation with an external LLM provider:

- Django backend in `backend/`
- React TypeScript Vite frontend in `frontend/`
- DRF and local CORS configuration
- Health endpoint at `/api/health/`
- Database health endpoint at `/api/health/database/`
- Frontend health check page
- PostgreSQL with pgvector through Docker Compose
- Django PostgreSQL settings loaded from `backend/.env`
- Migration enabling the PostgreSQL `vector` extension
- Accounts app using Django's built-in User model
- Simple JWT endpoints for registration, login, token refresh, and current user
- Basic frontend register/login pages and protected dashboard
- Documents app with owner-scoped research collections
- Authenticated PDF upload endpoints with validation and stored-file cleanup
- Dashboard collection management and collection detail upload UI
- PyMuPDF text extraction with one-based page numbers
- Page-local `DocumentChunk` records
- Synchronous document processing endpoint at `/api/documents/{id}/process/`
- Read-only chunk endpoint at `/api/documents/{id}/chunks/`
- Collection detail process controls and chunk preview
- Replaceable embedding provider interface
- Local Sentence Transformers provider for `sentence-transformers/all-MiniLM-L6-v2`
- 384-dimensional pgvector chunk embeddings with HNSW cosine index
- Synchronous document embedding endpoint at `/api/documents/{id}/embed/`
- Collection semantic search endpoint at `/api/collections/{id}/search/`
- Collection detail embed controls and semantic search UI
- Replaceable LLM provider interface
- Groq-backed LLM provider using the documented OpenAI-compatible chat completions API
- Collection-scoped grounded answer endpoint at `/api/collections/{id}/ask/`
- Backend-assigned source IDs and citation validation for retrieved source references
- Collection detail question-and-answer panel with expandable citation passages

## Guardrails

- Do not add conversation history, streaming, OCR, Celery/background workers, automatic summaries, or deployment features until those milestones are approved.
- Citation validation checks that referenced source IDs were retrieved; it does not guarantee hallucination-free answers.
- Do not commit `.env` files, uploaded PDFs, model weights, virtual environments, `node_modules`, or generated build outputs.
- Preserve provider boundaries in future RAG milestones so LLM and embedding providers remain replaceable.
- Keep ownership and citation requirements central when later adding user data and document retrieval.
