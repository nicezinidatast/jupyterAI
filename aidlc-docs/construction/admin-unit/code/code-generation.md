# admin-unit — Code Generation Plan

**실제 코드 위치**: `units/admin-unit/`

## Plan — Backend (Python)
- [ ] `units/admin-unit/backend/pyproject.toml`
- [ ] `units/admin-unit/backend/migrations/0001_admin_tables.py`
- [ ] `src/admin_backend/models.py`
- [ ] `src/admin_backend/schemas.py`
- [ ] `src/admin_backend/services/admin_service.py`
- [ ] `src/admin_backend/services/backup_service.py`
- [ ] `src/admin_backend/services/restore_verifier.py`
- [ ] `src/admin_backend/services/quarterly_review.py`
- [ ] `src/admin_backend/adapters/grafana.py`
- [ ] `src/admin_backend/adapters/smtp.py`
- [ ] `src/admin_backend/cron.py` (APScheduler 또는 asyncio task)
- [ ] `src/admin_backend/api/router.py`
- [ ] `src/admin_backend/main.py`
- [ ] `tests/test_backup_invariant.py`
- [ ] `tests/test_quarterly_review.py`
- [ ] `tests/integration/test_full_backup_restore.py`

## Plan — AdminConsole SPA (TypeScript)
- [ ] `units/admin-unit/admin-console/package.json` (react, vite, mantine, @tanstack/react-query, zustand, react-hook-form, zod)
- [ ] `vite.config.ts`
- [ ] `tsconfig.json`
- [ ] `src/main.tsx`
- [ ] `src/App.tsx` (router)
- [ ] `src/pages/Dashboard.tsx`
- [ ] `src/pages/Users.tsx`
- [ ] `src/pages/Connections.tsx`
- [ ] `src/pages/PiiPatterns.tsx`
- [ ] `src/pages/Backups.tsx`
- [ ] `src/api/client.ts` (OpenAPI generated)
- [ ] `src/hooks/useAuth.ts`
- [ ] `src/components/...`
- [ ] `tests/` (Vitest + Testing Library)
- [ ] `e2e/` (Playwright)

## Plan — AuditorConsole SPA
- [ ] `units/admin-unit/auditor-console/` (구조 동일)
- [ ] `src/pages/AuditSearch.tsx`
- [ ] `src/pages/AccessReview.tsx`

## Plan — JupyterLab Extensions
- [ ] `units/admin-unit/jupyter-extensions/package.json` (@jupyterlab/application, @jupyterlab/builder, react)
- [ ] `src/plugins/connection-panel.tsx`
- [ ] `src/plugins/sql-editor.tsx`
- [ ] `src/plugins/chart-button.tsx`
- [ ] `src/index.ts`
- [ ] `style/` (CSS)
- [ ] `tsconfig.json`
- [ ] `Dockerfile.builder` (선택 — JupyterLab 빌드 환경)

## Plan — CI
- [ ] `.gitlab-ci.yml` (backend Python + SPA × 2 + Jupyter Ext 빌드)
- [ ] Trivy + npm audit + bandit
- [ ] E2E Playwright run in CI

## Definition of Done
- Backend coverage ≥ 80%, SPA test coverage ≥ 60% (E2E로 보완)
- AdminConsole/AuditorConsole 모두 RBAC 미들웨어 통과
- 백업 → 격리 환경 복구 리허설 1회 성공
- JupyterLab Extension이 사용자 컨테이너에 정상 로드

## 비고
- admin-unit은 가장 폴리글랏 (Python + TypeScript × 3)
- CI 파이프라인 가장 복잡 — 4개 빌드 산출물(backend wheel, admin SPA, auditor SPA, jupyter ext)
