# Academic Research Assistant

A full-stack research assistant for academic literature. The application will let users upload legally obtained or open-access academic PDFs, ask questions about their contents, and receive grounded answers with citations.

This repository is being implemented in milestones. Milestone 6 adds local embeddings and semantic retrieval with pgvector.

## Current Stack

- Backend: Python, Django, Django REST Framework
- Frontend: React, TypeScript, Vite
- Database: PostgreSQL with pgvector via Docker Compose
- Local development CORS configured for Vite on port `5173`

Conversations, RAG answer generation, OCR, background workers, and LLM integrations are intentionally not configured yet. A free external LLM API will be added later behind a replaceable provider interface.

## Project Structure

```text
academic-research-assistant/
|-- backend/
|-- frontend/
|-- .gitignore
|-- AGENTS.md
`-- README.md
```

## Backend Setup

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py runserver
```

The API health endpoint is available at:

```text
http://localhost:8000/api/health/
```

The database health endpoint is available at:

```text
http://localhost:8000/api/health/database/
```

Authentication endpoints:

```text
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/token/refresh/
GET  /api/auth/me/
```

Collection and upload endpoints:

```text
GET    /api/collections/
POST   /api/collections/
GET    /api/collections/{id}/
PATCH  /api/collections/{id}/
DELETE /api/collections/{id}/
GET    /api/collections/{collection_id}/documents/
POST   /api/collections/{collection_id}/documents/
GET    /api/documents/{id}/
DELETE /api/documents/{id}/
POST   /api/documents/{id}/process/
GET    /api/documents/{id}/chunks/
POST   /api/documents/{id}/embed/
POST   /api/collections/{id}/search/
```

PDF uploads use `multipart/form-data`, require authentication, and are limited by `DOCUMENT_UPLOAD_MAX_BYTES`.

## PDF Processing

PDF processing is synchronous in this milestone. Before production, background processing should be considered so large uploads do not tie up web requests.

Processing uses PyMuPDF to extract text one page at a time. Page numbers are stored with one-based numbering so later citations can point back to the original PDF page.

Chunking stays within each page. The default chunk size is `DOCUMENT_CHUNK_SIZE=1000` characters with `DOCUMENT_CHUNK_OVERLAP=200` characters. The chunker prefers paragraph, sentence, line, or word boundaries when practical, then falls back to a hard character limit for very long paragraphs. It always advances after each chunk to avoid infinite loops and skips empty chunks.

Scanned or image-only PDFs are unsupported until OCR is added. Those documents are marked `failed` with a safe user-facing error message.

## Embeddings and Search

The initial embedding provider is local Sentence Transformers:

```env
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384
EMBEDDING_BATCH_SIZE=32
```

The `all-MiniLM-L6-v2` model dimension was verified from the Hugging Face model config and by loading the model locally. Chunk embeddings are normalized for cosine similarity and stored in PostgreSQL using pgvector.

The chunk embedding index is HNSW with `vector_cosine_ops`. HNSW is an approximate nearest-neighbor index, so it is designed for fast semantic retrieval as data grows. Search responses include both `cosine_distance` and `similarity_score`; the similarity score is `1 - cosine_distance`, where higher means more similar.

Search concepts:

- Keyword search matches exact words or lexical patterns.
- Semantic vector search compares embedding vectors, so it can match related meaning even when wording differs.
- RAG answer generation retrieves evidence and then asks an LLM to write a grounded answer. That generation stage has not been added yet.

Embedding and semantic search are synchronous in this milestone. Background processing should be considered before production.

## Database Setup

Create `backend/.env` from `backend/.env.example`, then start PostgreSQL:

```powershell
docker compose --env-file backend/.env up -d postgres
```

Run Django migrations:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py migrate
```

Stop the database:

```powershell
docker compose --env-file backend/.env down
```

Stop the database and remove the local database volume:

```powershell
docker compose --env-file backend/.env down -v
```

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

The frontend development server is available at:

```text
http://localhost:5173/
```

## Environment Files

Copy example files before local customization:

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

Never commit real `.env` files.

Useful backend environment settings:

```env
DOCUMENT_UPLOAD_MAX_BYTES=10485760
DOCUMENT_CHUNK_SIZE=1000
DOCUMENT_CHUNK_OVERLAP=200
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384
EMBEDDING_BATCH_SIZE=32
```

## Token Storage

The frontend keeps the short-lived access token in memory. The refresh token is stored in `localStorage` so a page refresh can restore the session through `/api/auth/token/refresh/`.

This follows the normal Simple JWT JSON response flow and avoids adding a custom cookie/CSRF system in this milestone. The tradeoff is that `localStorage` can be exposed by cross-site scripting bugs, so future frontend work should keep user-generated HTML out of the DOM and revisit HttpOnly refresh-token cookies with CSRF protection before production.
