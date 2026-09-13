# Academic Research Assistant Agent Notes

This repository is being built milestone by milestone. Keep changes scoped to the approved milestone.

## Current Milestone

Milestone 1 creates the initial foundation only:

- Django backend in `backend/`
- React TypeScript Vite frontend in `frontend/`
- DRF and local CORS configuration
- Health endpoint at `/api/health/`
- Frontend health check page

## Guardrails

- Do not add PostgreSQL, pgvector, Ollama, embeddings, authentication, PDF processing, or RAG workflows until those milestones are approved.
- Do not commit `.env` files, uploaded PDFs, model weights, virtual environments, `node_modules`, or generated build outputs.
- Preserve provider boundaries in future RAG milestones so LLM and embedding providers remain replaceable.
- Keep ownership and citation requirements central when later adding user data and document retrieval.
