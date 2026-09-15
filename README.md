# Academic Research Assistant

A full-stack research assistant for academic literature. The application will let users upload legally obtained or open-access academic PDFs, ask questions about their contents, and receive grounded answers with citations.

This repository is being implemented in milestones. Milestone 1 contains only the initial Django and React foundation.

## Current Stack

- Backend: Python, Django, Django REST Framework
- Frontend: React, TypeScript, Vite
- Database: PostgreSQL with pgvector via Docker Compose
- Local development CORS configured for Vite on port `5173`

Ollama, embeddings, authentication, PDF processing, and RAG workflows are intentionally not configured yet.

## Project Structure

```text
academic-research-assistant/
├── backend/
├── frontend/
├── .gitignore
├── AGENTS.md
└── README.md
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

## Token Storage

The frontend keeps the short-lived access token in memory. The refresh token is stored in `localStorage` so a page refresh can restore the session through `/api/auth/token/refresh/`.

This follows the normal Simple JWT JSON response flow and avoids adding a custom cookie/CSRF system in this milestone. The tradeoff is that `localStorage` can be exposed by cross-site scripting bugs, so future frontend work should keep user-generated HTML out of the DOM and revisit HttpOnly refresh-token cookies before production.
