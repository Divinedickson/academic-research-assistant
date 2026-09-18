# Academic Research Assistant Frontend

React and TypeScript frontend for the Academic Research Assistant. It provides registration and
login, protected collection management, PDF upload and processing controls, semantic search, and
grounded question answering with expandable source passages.

## Local Development

```powershell
npm install
npm run dev
```

Set `VITE_API_BASE_URL` in `frontend/.env` when the Django API is not available at
`http://localhost:8000`.

## Checks

```powershell
npm run lint
npm run build
```

The generated `dist/` directory and local `.env` files are ignored by Git.
