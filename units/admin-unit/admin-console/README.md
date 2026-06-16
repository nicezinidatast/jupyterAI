# Admin Console (SPA skeleton)

React 18 + Vite + Mantine. Phase 1 ships the routing skeleton; concrete pages
(Users / Connections / PII / Backups) wire to `/api/admin/*` in subsequent
iterations.

```bash
pnpm install
pnpm dev          # http://localhost:5173/admin/
pnpm build        # → dist/  (served by nginx via infra/nginx/spa.conf)
pnpm typecheck
```
