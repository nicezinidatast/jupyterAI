# Platform Login (SPA)

React 18 + Vite + Mantine. The platform entry point served at `/platform/`.
Provides sign up (with email verification code) and login; on a successful
session the browser is redirected to `/analyst/` (the analyst workspace).

```bash
npm install
npm run dev        # Vite dev server on :80 (host 0.0.0.0) — see vite.config.ts
npm run build      # → dist/
npm run typecheck
```

Single page, no router. Auth endpoints are cookie-based and same-origin
(`/api/auth/*`); every request sends `credentials: 'include'`.
