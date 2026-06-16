# AI-DLC State Tracking

## Project Information
- **Project Name**: 내부망 데이터분석 플랫폼 (Internal Data Analytics Platform)
- **Project Type**: Greenfield
- **Start Date**: 2026-05-21T00:00:00Z
- **Current Phase**: 🟢 CONSTRUCTION (code generated + verified)
- **Current Stage**: 1차 verification round 통과 — backend/SPA/copilot/demo-data 실동작 확인

## Workspace State
- **Existing Code**: No (codebase still to be generated per code-generation.md plans)
- **Programming Languages**: Python 3.11+ (backend), TypeScript (SPA + JupyterLab Ext)
- **Build System**: uv (Python), pnpm + Vite (TS)
- **Project Structure**: Documentation only — code trees defined in unit-of-work.md §A
- **Reverse Engineering Needed**: No
- **Workspace Root**: C:\Users\NICE\Documents\workspace\0521_platform

## Code Location Rules
- Application Code: Workspace root `units/<name>/`
- Documentation: `aidlc-docs/`

## Extension Configuration
| Extension | Enabled | Mode |
|---|---|---|
| Security Baseline | Yes | Full (15 rules blocking) |
| Property-Based Testing | Yes | Full (10 rules blocking) |

## Tech Stack (confirmed 2026-05-21)
- Backend: Python 3.11+ / FastAPI / Pydantic / SQLAlchemy 2 + asyncpg / Alembic
- Frontend: React 18 / Vite / TypeScript / Mantine / TanStack Query
- DB: PostgreSQL 16
- Cache/Queue: Redis 7 (Streams)
- Secrets: HashiCorp Vault
- Auth: Keycloak 24
- Git: GitLab/Gitea
- Container: Docker Compose (MVP) → Helm (Phase 2)
- IaC: Ansible
- Observability: Prometheus / Grafana / Loki / OpenTelemetry
- Testing: pytest + Hypothesis (PBT) + Playwright (E2E) + Locust (perf)
- Quality: ruff / mypy / bandit / safety / Trivy / cyclonedx

## Stage Progress

### 🔵 INCEPTION PHASE
- [x] Workspace Detection (2026-05-21)
- [x] Reverse Engineering (skipped — greenfield)
- [x] Requirements Analysis (approved)
- [x] User Stories (approved — 40 MVP + 12 outline)
- [x] Workflow Planning (approved)
- [x] Application Design (approved — 30 modules)
- [x] Units Generation (approved — 7 units + shared-lib + infra/ + phase2-incubation/)

### 🟢 CONSTRUCTION PHASE — design + code complete, 1st verification round passed
- [x] shared-lib (FD + NFR-R + NFR-D + Infra + Code Plan + code)
- [x] gateway-unit (+ code, Dockerfile)
- [x] auth-unit (+ code)
- [x] audit-unit (+ code)
- [x] credential-unit (+ code, Vault local-KMS adapter)
- [x] data-unit (+ code, real connectors: asyncpg/aiomysql/pyhive)
- [x] notebook-unit (+ code)
- [x] admin-unit (+ backend code + 4 SPAs: admin-console/auditor-console/analyst-workspace/viewer-portal + jupyter-extensions)
- [x] copilot-unit (added Phase 2 → MVP: Anthropic + Ollama providers, streaming, PII mask, rate limit)
- [x] Build & Test (instructions, summary, security/PBT verification matrix)
- [x] Code Generation Part 2 (units/*/src/** + backend/src/backend + 4 SPAs all generated)
- [x] Integration deployment (infra/docker-compose stack: postgres/redis/demo-postgres/demo-mysql/backend/gateway/portal/4 SPAs/jupyter; ollama profile)
- [x] Verification Round 1 (2026-05-22) — backend e2e smoke 5/5 통과, real SQL on demo-postgres, real Anthropic copilot streaming, audit_log 적재 확인
- [x] Verification Round 2 (2026-05-22) — SPA(4종) portal 200, Vite/HMR 정상, /analyst/sql Playwright headless에서 자동 connection→SQL fill→실행→마스킹 표 렌더링까지 통과 (7/7). 부산물: Mantine AppShell padding 버그 fix (▶ 실행 버튼이 navbar 뒤에 가려지던 UX 결함), SAMPLE_SQL[sales_db] 잘못된 컬럼(orders.customer_name) 실 스키마(sales.customers)로 수정. 스크린샷: `tests/e2e/analyst-workspace.png`
- [x] Verification Round 3 (2026-05-22) — NL → Anthropic copilot → ```sql``` 코드 블록 → "📥 셀로 삽입" → Jupyter REST PUT으로 copilot.ipynb 셀 적재 + `/api/copilot/cell-inserted` audit 적재 (e2e 8/8). copilot.ipynb 셀 source 검증 + audit_log payload `{notebook_path, language=sql, source_length>0}` 검증. 스크린샷: `tests/e2e/analyst-copilot-jupyter.png`
- [x] Keycloak OIDC (2026-05-22 저녁, state 파일 누락분 소급 기록) — `infra/keycloak` realm import(dataplatform realm + 4 seeded users), backend `OidcVerifier`(JWKS RS256 검증, hybrid: 토큰 없으면 demo fallback), e2e `test_oidc_integration.py` 4/4 (real token 수락 / bogus 401 / role propagation / demo fallback)
- [x] Jupyter 실행환경 하드닝 (2026-05-26, state 파일 누락분 소급 기록) — 커스텀 이미지 `infra/jupyter/`(scipy-notebook + jupysql/sqlalchemy/psycopg2/pymysql/plotly/pyarrow/openpyxl), IPython startup `00-platform.py`로 `sales_engine`/`crm_engine` 자동 등록 + `%%sql` 기본 바인딩 → copilot이 삽입한 `%%sql` 셀이 보일러플레이트 없이 즉시 실행. e2e 추가: `test_copilot_scroll.py`, `test_copilot_refactor.py`(노트북 셀 컨텍스트 주입 후속턴), `test_jupyter_visible_cell.py`(iframe 내 셀 가시화)
- [x] Verification Round 4 (2026-06-05) — **e2e 16/16 통과 (66s)**. ① 활성 노트북 셀 삽입: compose `--LabApp.expose_app_in_browser=True` + `getActiveNotebookPanel`(currentWidget → isVisible 탭 → 첫 노트북) + live `sharedModel.addCell`+`context.save()`(mid-boot 클로버 방지 `context.isReady` 가드, 실패 시 REST copilot.ipynb fallback — fallback일 때만 iframe reload), audit payload에 실제 notebook_path 기록. ② 채팅 짜부 fix: flex column 내 메시지 Card `flexShrink:0`. ③ 신규 e2e `test_copilot_active_notebook.py`(scratch.ipynb 활성 → 셀이 scratch에 적재 + copilot.ipynb 불변 + audit 검증 + 카드 비압축 검증). 시각 증거: `tests/e2e/analyst-active-notebook-insert.png`. **이번 라운드에서 잡은 실결함 4건**: (a) portal nginx SPA `proxy_read_timeout 30s` → HMR WS 컷 → vite가 30초 idle마다 SPA 강제 리로드(채팅 증발) → 3600s, (b) 자동삽입 dedup 키가 React 18 setHistory updater 지연으로 `-1:0` 충돌 → 2번째 답변부터 셀 삽입 무음 스킵 → per-send seq 키, (c) 플랫폼 DB asyncpg stale pooled connection → 간헐 500 → `pool_pre_ping=True`, (d) mid-boot 노트북 패널에 live insert 시 빈 모델 save로 파일 클로버 위험 → isReady 가드. 잔여: testcontainers integration, Locust perf, Ollama 폐쇄망 모드 검증 (`/jupyter/api/events/subscribe` WS upgrade는 5/26에 이미 nginx 반영됨)

### 🟡 OPERATIONS PHASE
- [ ] Operations (placeholder — out of scope for this workflow)

## Current Status (2026-06-05 갱신)
- **Verification Round 4 완료 — e2e 16/16**: 활성 노트북 셀 삽입(코파일럿 코드가 사용자가 보고 있는 노트북으로), 채팅 짜부 fix, OIDC 4종(5/22 소급), jupysql 커널 환경(5/26 소급) 모두 실검증
- 잔여: testcontainers integration, Locust perf, Ollama 폐쇄망 모드

## Status History (Round 1~3, 2026-05-22)
- 모든 design/planning + 실 코드 생성 완료
- 1차 verification: backend healthz/readyz, sales_db 실 SQL, PII 마스킹(name/email/phone/rrn), 스키마 introspection, Anthropic copilot 스트리밍, copilot_chat audit row 적재
- 2차 verification: SPA 4종 portal 200 + Vite dev 정상, /analyst/sql Playwright headless로 connection 자동 선택 → SQL 실행 → 마스킹된 결과 표 렌더링 + 차트/저장 버튼 가시화 (7/7 통과). 동시에 Analyst Workspace 시각 증거 캡처(`tests/e2e/analyst-workspace.png`)
- 3차 verification: **핵심 차별점(NL→코드 셀→Jupyter 삽입→audit)** Playwright headless에서 한 사이클 9.31s 통과 (e2e 8/8). Anthropic 응답 ```sql``` 블록 + 셀 삽입 + `copilot.ipynb` 서버 측 검증 + `audit_log copilot_cell_inserted` payload 검증. 시각 증거: `tests/e2e/analyst-copilot-jupyter.png`
- **Copilot UX 하드닝 (2026-05-22)**: 사용자 피드백에 따라 (1) 코드 블록은 사용자 추가 클릭 없이 자동으로 copilot.ipynb에 셀 추가, (2) 긴 답변 채팅 스크롤 동작 확보(viewport 기반 height + scrollTop pin to bottom). 통합 테스트 + 시각 증거: `tests/e2e/analyst-copilot-autoinsert.png`
- 잔여: gateway+Keycloak OIDC, testcontainers integration, Locust perf, Ollama 폐쇄망 모드, nginx WS upgrade for `/jupyter/api/events/subscribe`

## Documentation Index
- `aidlc-docs/inception/requirements/requirements.md`
- `aidlc-docs/inception/user-stories/{stories,personas}.md`
- `aidlc-docs/inception/plans/{user-stories-assessment,story-generation-plan,application-design-plan,unit-of-work-plan,execution-plan}.md`
- `aidlc-docs/inception/application-design/{components,component-methods,services,component-dependency,application-design,unit-of-work,unit-of-work-dependency,unit-of-work-story-map}.md`
- `aidlc-docs/construction/<unit>/{functional-design,nfr-requirements,nfr-design,infrastructure-design,code}/*.md` × 7 units
- `aidlc-docs/construction/build-and-test/{build,unit-test,integration-test,performance-test,build-and-test-summary}.md`
- `aidlc-docs/audit.md` — full audit log
- Memory: `~/.claude/projects/.../memory/{feedback_decision_style,feedback_autonomous_drive}.md`
