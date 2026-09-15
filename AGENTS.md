# Academic Research Assistant Agent Notes

This repository is being built milestone by milestone. Keep changes scoped to the approved milestone.

## Current Milestone

Milestone 4 adds research collections and PDF uploads:

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

## Guardrails

- Do not add text extraction, chunking, embedding, retrieval, LLM, PDF processing beyond upload validation/storage, conversations, or RAG workflows until those milestones are approved.
- Do not commit `.env` files, uploaded PDFs, model weights, virtual environments, `node_modules`, or generated build outputs.
- Preserve provider boundaries in future RAG milestones so LLM and embedding providers remain replaceable.
- Keep ownership and citation requirements central when later adding user data and document retrieval.
