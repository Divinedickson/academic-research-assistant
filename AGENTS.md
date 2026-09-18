# Academic Research Assistant Agent Notes

This repository is being built milestone by milestone. Keep changes scoped to the approved milestone.

## Implemented Application

- Django backend in `backend/`
- React TypeScript Vite frontend in `frontend/`
- DRF and local CORS configuration
- Health endpoint at `/api/health/`
- Database health endpoint at `/api/health/database/`
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
- Public product homepage and a responsive blue-and-white workspace UI

The health endpoints are intentionally retained for local diagnostics and future deployment
monitoring. They are not presented as a user-facing product feature.

## Guardrails

- Do not add conversation history, streaming, OCR, Celery/background workers, automatic summaries, or deployment features until those milestones are approved.
- Citation validation checks that referenced source IDs were retrieved; it does not guarantee hallucination-free answers.
- Do not commit `.env` files, uploaded PDFs, model weights, virtual environments, `node_modules`, or generated build outputs.
- Preserve provider boundaries in future RAG milestones so LLM and embedding providers remain replaceable.
- Keep ownership and citation requirements central when later adding user data and document retrieval.
- Preserve `/api/health/` and `/api/health/database/` unless the monitoring strategy is deliberately
  replaced.
- Keep automated tests isolated from real embedding and LLM providers by using deterministic fakes.
- Never read, print, or commit real values from `backend/.env`.
