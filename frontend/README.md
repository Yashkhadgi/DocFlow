# DocFlow frontend

The frontend uses React, TypeScript, Vite, Tailwind CSS, React Router, and TanStack Query.

## Local development

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. By default, the app uses in-memory mock data so pages can be reviewed without the backend.

To use the real API, start the backend stack and seed its demo user first, then run:

```bash
VITE_USE_MOCK=false npm run dev
```

The API URL defaults to `http://localhost:8000/api/v1`. Set `VITE_API_BASE_URL` if the backend is elsewhere. The backend's `CORS_ORIGINS` must include the frontend URL used in the browser.

## Checks

```bash
npm run lint
npm run build
```

The `/verify` page exercises the mock API fixtures; it is not an end-to-end test of the backend, storage, or worker.
