# Unit of Work Plan — 내부망 데이터 분석 플랫폼

**작성일**: 2026-05-21
**기반 입력**: `application-design.md`, `execution-plan.md` §5, `stories.md`
**참고**: 사용자 피드백 (memory: feedback-decision-style) 에 따라 권장값으로 채움. 큰 분기만 본문 §C에 명시.

---

## A. 정의

- **Unit of Work (UoW)** = 개발·테스트·배포의 논리적 단위. 본 프로젝트는 **Modular Monolith** (Q-AD-11=A) → 1차에서 *논리 단위*(코드 모듈), Phase 2에서 일부 유닛이 *배포 단위*(컨테이너)로 승격 가능.
- **Module** ⊆ Unit: Q-AD-1=B의 도메인 컴포넌트들이 UoW 안에 모임.
- **Service**: 본 문서 맥락에서는 Phase 2 이후 독립 배포가 가능한 유닛 (k8s 이전).

---

## B. 산출물 체크리스트

- [x] `aidlc-docs/inception/application-design/unit-of-work.md` — 7+1 유닛 정의 + 30 모듈 할당 + monorepo 코드 트리
- [x] `aidlc-docs/inception/application-design/unit-of-work-dependency.md` — 7×7 매트릭스 + Mermaid + 빌드 시퀀스
- [x] `aidlc-docs/inception/application-design/unit-of-work-story-map.md` — 40 MVP + 12 Phase 2/3 outline 모두 매핑
- [x] 검증: 30 모듈 모두 1 유닛 ✓ / acyclic ✓ / 40 스토리 모두 매핑 ✓

---

## C. 결정 사항 (Decisions — 권장 default 적용)

> 큰 분기가 없어 권장값으로 진행. 사용자가 변경을 원하면 본 섹션을 수정해주세요.

| # | 항목 | 결정 | 근거 |
|---|---|---|---|
| **D-UoW-1** | 유닛 개수 | **7개 + 1 (UI/Phase 2 후보)** | execution-plan §5의 권장 시퀀스 |
| **D-UoW-2** | 코드 조직 | **monorepo** — 단일 저장소 안에 `units/<name>/` 트리 | Modular Monolith + 사내 단일 GitLab |
| **D-UoW-3** | 배포 단위 매핑 | **MVP 1~2 컨테이너** (앞단 + 백엔드), Phase 2에 유닛별 컨테이너 분리 후보 | Docker Compose MVP |
| **D-UoW-4** | 팀 정렬 | **유닛당 1명 + 횡단 공유 라이브러리 1명** (10명 미만 부서팀 가정) | MVP 일정 + 인력 효율 |
| **D-UoW-5** | 도메인 경계 = 유닛 경계 | **거의 일치** (예: `auth-unit`은 Auth Domain 전부 + Gateway 일부) | Bounded Context-ish |
| **D-UoW-6** | Phase 2 유닛 사전 위치 | **`phase2-incubation/` 하위로 격리** | MVP 빌드/테스트 격리 |
| **D-UoW-7** | 인프라 코드 | **별도 `infra/` 유닛** (Docker Compose + Ansible) | 변경 빈도·소유권 분리 |

확인 받고 싶은 유일한 항목: **D-UoW-3 (배포 단위 1~2 컨테이너)**. MVP를 더 잘게 컨테이너로 쪼개고 싶다면(예: 보안 격리 강도↑) 알려주세요. 그게 아니면 단순 시작.

---

## D. 실행 단계 (Plan Execution Checkboxes)

- [x] **U1**: 7+1 유닛 정의 + 각 유닛에 30 모듈 할당
- [x] **U2**: 유닛 의존성 매트릭스 + Mermaid + 빌드 시퀀스
- [x] **U3**: MVP 40 + Phase 2/3 outline 12 스토리 매핑
- [x] **U4**: monorepo 코드 트리 (unit-of-work.md 부록 A)
- [x] **U5**: 검증 통과

---

## E. 유닛 후보 (요약 — U1에서 정식화)

1. **`gateway-unit`** — ApiGateway, OidcCallbackHandler, SecurityKernel(SL-1)
2. **`auth-unit`** — AuthService, SessionStore, RoleResolver, KeycloakAdapter, AuthServiceOrchestrator
3. **`audit-unit`** — AuditWriter, AuditQueryApi, AuditService, AuditEventEmitter(SL-2)
4. **`credential-unit`** — CredentialVault, VaultAdapter
5. **`data-unit`** — ConnectionRegistry, ConnectorFactory, RDBMS/BigData Connectors, QueryExecutor, SchemaIntrospector, PiiPolicyStore, PiiMaskingFilter, FileUploadHandler, DataAccessService
6. **`notebook-unit`** — NotebookStore, JupyterHubSpawner, KernelManager, ShareLinkManager, GitAdapter, AutoCommitOrchestrator, ChartBuilder, NotebookService
7. **`admin-unit`** — AdminConsole, AuditorConsole, JupyterExtensionsBundle, AdminService, BackupScheduler, RestoreVerifier, BackupService
8. **`shared-lib`** (가상 유닛 / cross-cutting) — Telemetry(SL-3), ResultTypes(SL-4), SecurityKernel·AuditEventEmitter 본체
9. **`infra/`** (별도) — Docker Compose, Ansible 등 IaC
10. **`phase2-incubation/`** — LlmProxyAdapter, LlmGovernor, ReportRenderer, ReportScheduler 등
