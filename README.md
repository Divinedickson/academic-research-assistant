# Academic Research Assistant

A full-stack research assistant for academic literature. The application will let users upload legally obtained or open-access academic PDFs, ask questions about their contents, and receive grounded answers with citations.

The implemented application includes authentication, private research collections, secure PDF uploads, page-aware extraction and chunking, local embeddings, semantic retrieval, and grounded answer generation through a replaceable external LLM provider.

## Current Stack

- Backend: Python, Django, Django REST Framework
- Frontend: React, TypeScript, Vite
- Database: PostgreSQL with pgvector via Docker Compose
- Local development CORS configured for Vite on port `5173`

Conversation history, streaming, OCR, background workers, automatic summaries, and deployment automation are intentionally not configured yet.

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

The lightweight application health endpoint is available at:

```text
http://localhost:8000/api/health/
```

The database health endpoint verifies that Django can query PostgreSQL:

```text
http://localhost:8000/api/health/database/
```

These endpoints are retained for local diagnostics and future deployment monitoring. The public frontend does not use them as a connectivity demonstration.

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
POST   /api/collections/{id}/ask/
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
- RAG answer generation retrieves evidence and then asks an LLM to write a grounded answer with citations.

Embedding and semantic search are synchronous in this milestone. Background processing should be considered before production.

## Grounded Answer Generation

The initial LLM provider is Groq:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=replace-with-your-groq-api-key
LLM_MODEL=openai/gpt-oss-20b
LLM_API_BASE_URL=https://api.groq.com/openai/v1
LLM_TIMEOUT_SECONDS=30
LLM_MAX_CONTEXT_CHARS=12000
LLM_MAX_SOURCE_CHARS=2500
LLM_MAX_OUTPUT_TOKENS=700
LLM_MODEL_CONTEXT_WINDOW=131072
LLM_PROMPT_OVERHEAD_TOKENS=1200
LLM_QUESTION_MAX_CHARS=1000
LLM_ASK_TOP_K_MAX=10
LLM_TEMPERATURE=0.1
LLM_ASK_THROTTLE_RATE=10/minute
```

The backend does not require `GROQ_API_KEY` at Django startup. If the key is missing, answer generation returns a safe configuration error only when `/api/collections/{id}/ask/` is requested.

The answer flow is:

1. Validate the authenticated user's collection ownership.
2. Reuse collection-scoped semantic retrieval to fetch embedded chunks.
3. Assign backend source IDs such as `S1` and `S2`.
4. Send the question and bounded source passages to the configured LLM provider.
5. Require inline citations like `[S1]`.
6. Validate that cited source IDs were retrieved.
7. Return cited sources with paper title, original filename, PDF page number, and the exact passage supplied to the model.

Citation validation checks source references only. It does not prove factual support and does not guarantee hallucination-free answers.

Questions and selected excerpts are sent to the external LLM provider. Use legally obtained or open-access papers, avoid sensitive or confidential content on free tiers, and review the provider's current terms before demonstrations. Free-tier availability and rate limits can change.

Groq-specific code is isolated behind the LLM provider interface. Local Sentence Transformers embeddings remain unchanged.

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
LLM_PROVIDER=groq
GROQ_API_KEY=replace-with-your-groq-api-key
LLM_MODEL=openai/gpt-oss-20b
LLM_TIMEOUT_SECONDS=30
LLM_MAX_CONTEXT_CHARS=12000
LLM_MAX_OUTPUT_TOKENS=700
```

## Optional Real API Smoke Test

Automated tests mock the LLM provider and make no real API calls. To manually test Groq with an open-access PDF:

1. Add your Groq key to `backend/.env` as `GROQ_API_KEY`.
2. Start PostgreSQL, the Django server, and the Vite frontend.
3. Register or log in.
4. Create a collection.
5. Upload a small open-access, text-based academic PDF.
6. Process the paper.
7. Embed the paper.
8. Ask a question whose answer appears in the paper.
9. Confirm the answer cites source IDs and that each citation expands to the correct paper title, PDF page number, and passage.

Do not paste the API key into chat, commit it, or put it in frontend code.

## Token Storage

The frontend keeps the short-lived access token in memory. The refresh token is stored in `localStorage` so a page refresh can restore the session through `/api/auth/token/refresh/`.

This follows the normal Simple JWT JSON response flow and avoids adding a custom cookie/CSRF system. The tradeoff is that `localStorage` can be exposed by cross-site scripting bugs, so future frontend work should keep user-generated HTML out of the DOM and revisit HttpOnly refresh-token cookies with CSRF protection before production.

## Current Limitations

- PDF processing, embedding, and answer generation run synchronously and can occupy a web request.
- Scanned and image-only PDFs require OCR, which is not implemented.
- Refresh tokens are stored in `localStorage`; HttpOnly cookie storage with CSRF protection should be evaluated before production.
- Uploaded files use Django media storage. Production needs private object storage or an authenticated download path, malware scanning, and retention controls.
- Groq receives the question and selected source excerpts. Provider terms, retention, regional requirements, and rate limits must be reviewed for the intended deployment.
- Citation validation confirms that cited source IDs were retrieved; it does not prove that every generated claim is supported.
- Conversation history, streaming responses, background workers, deployment automation, and automatic summaries are not implemented.
