# Academic Research Assistant

A full-stack research assistant for academic literature. The application will let users upload legally obtained or open-access academic PDFs, ask questions about their contents, and receive grounded answers with citations.

This repository is being implemented in milestones. Milestone 1 contains only the initial Django and React foundation.

## Current Stack

- Backend: Python, Django, Django REST Framework
- Frontend: React, TypeScript, Vite
- Local development CORS configured for Vite on port `5173`

PostgreSQL, pgvector, Ollama, embeddings, authentication, PDF processing, and RAG workflows are intentionally not configured yet.

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
