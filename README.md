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
