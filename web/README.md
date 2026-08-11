# SAIE — Web (M01)

React + Vite SPA that ships the SAIE front-end. M01 is intentionally
minimal: a single status card that surfaces the backend's `/health`
endpoint so local `docker compose up` proves the full stack is wired
together.

## Requirements

- Node.js 20+
- npm 10+

## Local development

```bash
npm install
npm run dev      # http://localhost:5173 — proxies /api/* to localhost:8000
```

## Build & test

```bash
npm run lint
npm run format:check
npm test
npm run build    # produces dist/
```

## Container

The `Dockerfile` produces a multi-stage image that serves `dist/`
through `nginx:alpine` and reverse-proxies `/api/*` to the backend
service (see `docker-compose.yml`).

## Traceability

- NFR-005 — surfaces backend liveness
- NFR-006 — typed env contract (`VITE_*` prefixed vars)
- NFR-013 — backend-agnostic frontend (talks only to `/api/*`)
