# Academic Research Assistant

A full-stack research assistant for academic literature. The application will let users upload legally obtained or open-access academic PDFs, ask questions about their contents, and receive grounded answers with citations.

The implemented application includes authentication, private research collections, secure PDF uploads, page-aware extraction and chunking, local embeddings, semantic retrieval, and grounded answer generation through a replaceable external LLM provider.

## Current Stack

- Backend: Python, Django, Django REST Framework
- Frontend: React, TypeScript, Vite
- Database: PostgreSQL with pgvector via Docker Compose
- Local development CORS configured for Vite on port `5173`

Conversation history, streaming, OCR, background workers, and automatic summaries are intentionally not configured yet. Deployment configuration is prepared but no cloud resources are provisioned.

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

The database readiness endpoint verifies both PostgreSQL connectivity and the `vector` extension:

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

### Lightweight ONNX deployment option

The optional `onnx` provider reproduces the existing `all-MiniLM-L6-v2` pipeline without
importing PyTorch, Transformers, or Sentence Transformers. It uses the same 256-token limit
(including special tokens), attention-mask mean pooling, L2 normalization, and 384 output
dimensions. The normal local provider remains `sentence_transformers`; changing providers does
not modify stored vectors automatically.

The model is pinned to Hugging Face revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Artifact SHA-256 checksums live in
`backend/embedding-artifacts.json`, and the downloader refuses mismatched files:

```powershell
backend\.venv\Scripts\python.exe backend\tools\download_embedding_artifacts.py backend\.models\minilm
```

To select it after downloading the artifacts:

```env
EMBEDDING_PROVIDER=onnx
EMBEDDING_ONNX_MODEL_PATH=.models/minilm/model.onnx
EMBEDDING_ONNX_TOKENIZER_PATH=.models/minilm/tokenizer.json
EMBEDDING_ONNX_BATCH_SIZE=8
EMBEDDING_ONNX_MAX_SEQUENCE_LENGTH=256
EMBEDDING_ONNX_INTRA_OP_THREADS=1
EMBEDDING_ONNX_INTER_OP_THREADS=1
```

`requirements-deploy.txt` intentionally excludes `torch`, `transformers`, and
`sentence-transformers`. Keep `requirements.txt` for local compatibility comparisons. Run the
real-model comparison separately from automated tests with `tools/compare_embedding_providers.py`.
Compatibility requires a maximum component difference no greater than `1e-4`, same-text cosine
agreement of at least `0.99999`, and identical ranking for the representative retrieval cases.
These tolerances allow harmless FP32 runtime variation while rejecting changes large enough to
risk mixing different embedding spaces.

The disposable `Dockerfile.benchmark` installs only deployment dependencies, verifies the heavy
packages are absent, and runs the full-process benchmark. It is a feasibility tool, not a
production image. An operating-system OOM kill cannot be caught reliably by application code.

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

## Deployment Preparation

The production container uses `requirements-deploy.txt`, which excludes PyTorch, Transformers,
and Sentence Transformers. Its build downloads the pinned ONNX model and tokenizer, verifies the
checksums in `embedding-artifacts.json`, and collects static files. At startup, `entrypoint.sh`
runs idempotent Django migrations, verifies pgvector, and starts one Gunicorn worker on Render's
`PORT`. The default timeout is 180 seconds because processing and embedding are synchronous;
Render or another proxy can still terminate a request earlier.

Production requires these Render environment variables:

```env
DJANGO_ENVIRONMENT=production
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_ALLOWED_HOSTS=your-service.onrender.com
CORS_ALLOWED_ORIGINS=https://your-project.vercel.app
CSRF_TRUSTED_ORIGINS=https://your-project.vercel.app
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_SECURE_HSTS_PRELOAD=True
DJANGO_SECURE_PROXY_SSL_HEADER_ENABLED=True
DATABASE_URL=postgresql://user:password@host:6543/database
DATABASE_SSL_REQUIRE=True
DATABASE_DISABLE_SERVER_SIDE_CURSORS=True
DOCUMENT_STORAGE_BACKEND=s3
DOCUMENT_STORAGE_BUCKET=private-papers
DOCUMENT_STORAGE_ENDPOINT_URL=https://your-project.supabase.co/storage/v1/s3
DOCUMENT_STORAGE_ACCESS_KEY=replace-with-server-side-s3-access-key
DOCUMENT_STORAGE_SECRET_KEY=replace-with-server-side-s3-secret-key
DOCUMENT_STORAGE_REGION=us-east-1
DOCUMENT_STORAGE_ADDRESSING_STYLE=path
EMBEDDING_PROVIDER=onnx
GROQ_API_KEY=replace-with-your-groq-api-key
GUNICORN_TIMEOUT=180
```

The Docker image supplies the pinned ONNX paths, batch size, and thread limits. Do not put the
database URL, storage credentials, Django secret, or Groq key in Vercel. Vercel needs only:

```env
VITE_API_BASE_URL=https://your-service.onrender.com
```

`frontend/vercel.json` rewrites direct SPA visits such as `/dashboard` to `index.html`.
Production Vite builds reject a missing or localhost API URL.

### Database and private PDFs

The existing migration enables pgvector with `CREATE EXTENSION IF NOT EXISTS vector`; the startup
check fails before Gunicorn if it is unavailable. Supabase PostgreSQL supports pgvector. Its free
plan is practical for a student demo but is quota-limited and may pause inactive projects.

Render Free has an ephemeral filesystem, so production PDFs must not use local media storage.
The production configuration uses Django's replaceable storage API with a private S3-compatible
bucket. Supabase Storage supports S3 and offers a recurring free allowance, but free limits and
terms can change. Keep the bucket private, keep S3 credentials only on Render, and configure a
10 MB PDF bucket limit where available. PDF processing copies the authenticated document to a
controlled temporary file because remote storage does not implement `file.path`.

Supabase Storage has no S3 object versioning, and free deployments do not provide a complete
backup strategy. Maintain separate exports of important PDFs and PostgreSQL data.

Official references: [Render Free limitations](https://render.com/docs/free),
[Render health checks](https://render.com/docs/health-checks),
[Supabase pgvector](https://supabase.com/docs/guides/ai/vector-columns),
[Supabase S3 compatibility](https://supabase.com/docs/guides/storage/s3/compatibility),
[Supabase private buckets](https://supabase.com/docs/guides/storage/buckets/fundamentals), and
[Supabase Free project pausing](https://supabase.com/docs/guides/platform/free-project-pausing).

### Authentication decision

Access tokens remain in memory and refresh tokens remain in `localStorage` for compatibility.
This leaves refresh tokens exposed to successful XSS. The smallest safe migration is a backend
refresh/logout flow using an HttpOnly, Secure cookie with `SameSite=None` for the cross-site
Vercel-to-Render deployment, explicit credentialed CORS, CSRF cookies and headers, refresh-token
rotation, and blacklist-backed logout. That coordinated API and frontend change is intentionally
deferred rather than partially implementing a security-sensitive authentication rewrite.

### Deployment checklist

1. Create a PostgreSQL database that supports pgvector and enable the `vector` extension.
2. Create a private S3-compatible bucket and server-side access credentials.
3. Back up local database records and PDFs before any migration.
4. Build the production image and confirm checksum and heavyweight-package assertions pass.
5. Create the Render Docker web service from `backend/Dockerfile` with the variables above.
6. Set Render's health check path to `/api/health/database/`.
7. Confirm migrations, pgvector check, `/api/health/`, and database readiness in Render logs.
8. Create the Vercel project with root `frontend`, build command `npm run build`, and output `dist`.
9. Set `VITE_API_BASE_URL`, deploy, then test direct SPA routes and the complete user workflow.
10. Verify anonymous access to stored PDFs fails and PDFs survive a backend restart.

Rollback the frontend through Vercel's previous deployment. Roll back the backend to one of
Render's retained previous deploys. Database migrations must be backward-compatible; take a
manual database export before schema changes because application rollback does not undo data
migrations. Keep the previous object-storage configuration until rollback testing is complete.

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
- Refresh tokens are stored in `localStorage`; the documented HttpOnly-cookie migration remains unresolved.
- Production supports private S3-compatible storage, but malware scanning, retention controls, and automated backups are not implemented.
- Groq receives the question and selected source excerpts. Provider terms, retention, regional requirements, and rate limits must be reviewed for the intended deployment.
- Citation validation confirms that cited source IDs were retrieved; it does not prove that every generated claim is supported.
- Conversation history, streaming responses, background workers, deployment automation, and automatic summaries are not implemented.
