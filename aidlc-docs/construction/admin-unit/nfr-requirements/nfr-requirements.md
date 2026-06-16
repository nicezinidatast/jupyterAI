# admin-unit — NFR Requirements

| ID | 요구사항 |
|---|---|
| NFR-AM-PERF-01 | SPA 초기 로드 (gzipped bundle) | < 500KB, FCP < 1.5s |
| NFR-AM-PERF-02 | 사용자 검색 (≤1000명) | < 200ms |
| NFR-AM-PERF-03 | 감사 검색 페이지네이션 | < 500ms |
| NFR-AM-PERF-04 | 백업 작업 | 비동기, 진행률 표시, 1시간 내 완료 (메타DB 가정) |
| NFR-AM-SEC-01 | Admin/Auditor 외 접근 → 403 | 미들웨어 |
| NFR-AM-SEC-02 (SECURITY-04) | SPA의 CSP nonce 활용 | inline script 최소화 |
| NFR-AM-SEC-03 | 백업 파일 at-rest 암호화 | NAS/S3 layer + 추가 GPG 옵션 |
| NFR-AM-AUDIT-01 | 모든 관리 작업 감사 | shared-lib emitter |
| NFR-AM-OBS-01 | 메트릭: backup_total, backup_duration, restore_rehearsals, admin_actions | Prometheus |

## 기술 스택

| 항목 | 결정 |
|---|---|
| Frontend Framework | **React 18 + Vite + TypeScript** |
| UI Library | **Mantine** 또는 Ant Design (한국어 친화) — Mantine 권장 (가벼움) |
| State | **TanStack Query** + Zustand |
| Routing | React Router 6 |
| Forms | React Hook Form + Zod |
| Chart | Plotly.js (Grafana 임베드 대체 또는 보조) |
| Backend Framework | FastAPI (admin-unit backend 모듈) |
| Backup tools | `pg_dump`, `pg_basebackup`, `tar` |
| Mail | aiosmtplib 또는 사내 메신저 webhook |
| JupyterLab Extension | TypeScript + JupyterLab 4.x plugin API |
