# Academic Research Assistant Agent Notes

This repository is being built milestone by milestone. Keep changes scoped to the approved milestone.

## Current Milestone

Milestone 2 adds local database infrastructure:

- Django backend in `backend/`
- React TypeScript Vite frontend in `frontend/`
- DRF and local CORS configuration
- Health endpoint at `/api/health/`
- Database health endpoint at `/api/health/database/`
- Frontend health check page
- PostgreSQL with pgvector through Docker Compose
- Django PostgreSQL settings loaded from `backend/.env`
- Migration enabling the PostgreSQL `vector` extension

## Guardrails

- Do not add document, collection, chunk, authentication, embedding, retrieval, LLM, PDF processing, or RAG workflows until those milestones are approved.
- Do not commit `.env` files, uploaded PDFs, model weights, virtual environments, `node_modules`, or generated build outputs.
- Preserve provider boundaries in future RAG milestones so LLM and embedding providers remain replaceable.
- Keep ownership and citation requirements central when later adding user data and document retrieval.
