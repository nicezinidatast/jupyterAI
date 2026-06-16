# Unit of Work — Story Map

**작성일**: 2026-05-21
**기반**: `stories.md`, `unit-of-work.md`

> 40개 MVP 스토리 + 12 Phase 2/3 outline 스토리를 유닛으로 매핑.
> **원칙**: 한 스토리는 *주(主) 유닛 1개*에 배정. 협력 유닛은 별도 컬럼으로 표기.

---

## 1. MVP Story → Unit 매핑 (40개)

| Story ID | 제목 | 주 유닛 | 협력 유닛 | Persona |
|---|---|---|---|---|
| US-AUTH-01 | SSO 로그인 | auth-unit | gateway-unit, audit-unit | All |
| US-AUTH-02 | 역할 할당 및 가시성 제어 | auth-unit | audit-unit | Admin |
| US-AUTH-03 | 세션 만료와 작업 보호 | auth-unit | notebook-unit, audit-unit | All |
| US-AUTH-04 | Admin MFA 옵션 | auth-unit | (Keycloak 정책 위임) | Admin |
| US-AUTH-05 | 비밀번호 정책 | auth-unit | (Keycloak 정책 위임) | Admin |
| US-DS-01 | 공용 RDBMS 커넥션 등록 | data-unit | credential-unit, admin-unit, audit-unit | Admin |
| US-DS-02 | 빅데이터 SQL 엔진 커넥션 | data-unit | credential-unit, admin-unit, audit-unit | Admin |
| US-DS-03 | 커넥션 권한 부여 (RBAC) | data-unit | auth-unit, audit-unit | Admin |
| US-DS-04 | 개인 자격증명 등록 | credential-unit | auth-unit, audit-unit | Analyst |
| US-DS-05 | 스키마 사이드 패널 탐색 | data-unit | admin-unit(JupyterExt) | Analyst |
| US-DS-06 | 파일 업로드 (로컬) | data-unit | audit-unit | Analyst |
| US-DS-07 | 공유 스토리지 마운트 | data-unit | auth-unit | Analyst |
| US-NB-01 | JupyterHub 멀티유저 진입 | notebook-unit | auth-unit | Analyst |
| US-NB-02 | 셀 단위 SQL 실행 | notebook-unit | data-unit, audit-unit | Analyst |
| US-NB-03 | 셀 단위 Python/R 실행 | notebook-unit | audit-unit | Analyst |
| US-NB-04 | SQL 자동완성·구문 강조 | notebook-unit | data-unit(SchemaIntrospector) | Analyst |
| US-NB-05 | 노트북 자동 저장 | notebook-unit | audit-unit | Analyst |
| US-NB-06 | 백그라운드 셀 실행 | notebook-unit | audit-unit | Analyst |
| US-VIS-01 | 결과 셀 원클릭 차트 변환 | notebook-unit | admin-unit(JupyterExt) | Analyst |
| US-VIS-02 | 인터랙티브 차트 (Plotly/ECharts) | notebook-unit | data-unit(PII 마스킹) | Analyst, Viewer |
| US-VIS-03 | 정적 이미지 차트 | notebook-unit | — | Analyst |
| US-VIS-04 | 차트 표준 셋 | notebook-unit | admin-unit(JupyterExt) | Analyst |
| US-SHARE-01 | Git 자동 커밋 | notebook-unit | (외부 GitLab) | Analyst |
| US-SHARE-02 | 개인/팀 워크스페이스 분리 | notebook-unit | auth-unit | Analyst |
| US-SHARE-03 | 노트북 링크 공유 + 권한 | notebook-unit | auth-unit, audit-unit | Analyst |
| US-SHARE-04 | 공유 노트북 실행 (권한=execute) | notebook-unit | data-unit, audit-unit | Analyst, Viewer |
| US-SEC-01 | 활동 감사 로그 전수 기록 | audit-unit | (모든 유닛) | Auditor |
| US-SEC-02 | PII 자동 마스킹 | data-unit | admin-unit(정책 관리) | All |
| US-SEC-03 | 감사 로그 검색 콘솔 | audit-unit | admin-unit(AuditorConsole), auth-unit | Auditor |
| US-SEC-04 | 보안 헤더 + 입력 검증 | gateway-unit | (모든 유닛에서 입력 검증) | All |
| US-SEC-05 | TLS 1.2+ 및 at-rest 암호화 | gateway-unit | credential-unit, infra/ | Admin |
| US-ADM-01 | 사용자/역할 관리 콘솔 | admin-unit | auth-unit | Admin |
| US-ADM-02 | 커넥션 관리 콘솔 | admin-unit | data-unit, credential-unit | Admin |
| US-ADM-03 | PII 마스킹 패턴 관리 | admin-unit | data-unit | Admin |
| US-ADM-04 | 시스템 헬스 대시보드 | admin-unit | shared-lib(Telemetry), infra/(Prometheus) | Admin |
| US-ADM-05 | 자동 백업 & 복구 검증 | admin-unit | audit-unit, infra/ | Admin |

### 1.1 MVP 유닛별 스토리 수 요약

| 유닛 | 주 스토리 수 | 협력 빈도 |
|---|---|---|
| gateway-unit | 2 (US-SEC-04·05) | 거의 모든 흐름 (라우팅) |
| auth-unit | 5 (US-AUTH-01~05) | 거의 모든 흐름 (인가) |
| audit-unit | 2 (US-SEC-01·03) | 모든 도메인 유닛에서 emit |
| credential-unit | 1 (US-DS-04) | data-unit, admin-unit |
| data-unit | 9 (US-DS-01~03·05~07, US-SEC-02, US-VIS-02(부분)) | notebook-unit, admin-unit |
| notebook-unit | 16 (US-NB-01~06, US-VIS-01~04, US-SHARE-01~04) | data-unit, auth-unit 빈번 |
| admin-unit | 5 (US-ADM-01~05) | 거의 모든 도메인 유닛 |
| **합계** | **40** | — |

**관찰**: `notebook-unit`이 16개로 가장 무거움 (분석가 핵심 사용성). 후속 단계에서 내부 모듈을 더 분리 가능성 있음 (예: visualization, sharing을 후속 incubation으로 분기).

---

## 2. Phase 2 Story → Unit 매핑 (Outline, 12개)

| Story ID | 제목 | 주 유닛 (Phase 2) | Persona |
|---|---|---|---|
| US-LLM-01 | Text-to-SQL | phase2-incubation/llm-proxy + data-unit | Analyst |
| US-LLM-02 | 데이터 요약/인사이트 | phase2-incubation/llm-proxy + notebook-unit | Analyst |
| US-LLM-03 | 코드 어시스턴트 | phase2-incubation/llm-proxy + notebook-unit | Analyst |
| US-LLM-04 | 사내 프록시 + 화이트리스트 | phase2-incubation/llm-proxy | Admin, Auditor |
| US-LLM-05 | 송신 데이터 정책 | phase2-incubation/llm-proxy + audit-unit | Auditor |
| US-RPT-01 | 노트북 → PDF | phase2-incubation/reporting + notebook-unit | Analyst |
| US-RPT-02 | 노트북 → 웹 URL 공유 | phase2-incubation/reporting + notebook-unit | Analyst, Viewer |
| US-RPT-04 | 보고서 템플릿 관리 | phase2-incubation/reporting + admin-unit | Admin |
| US-RPT-05 | 정기 발송 스케줄 | phase2-incubation/reporting | Analyst |
| US-VIS-Phase2 | Superset 임베드 | notebook-unit | Analyst, Viewer |
| US-DS-Phase2-DW | 외부 DW 커넥터 | data-unit (확장) | Admin, Analyst |
| US-DS-Phase2-NoSQL | NoSQL 커넥터 | data-unit (확장) | Admin, Analyst |
| US-SEC-Phase2-Column | 컬럼 단위 권한 | data-unit (확장) | Admin |
| US-SEC-Phase2-QueryReview | 위험 쿼리 검토 | data-unit (확장) | Admin |
| US-NB-Phase2-Search | 노트북 검색 | notebook-unit (확장) + 검색 인덱서 | Analyst |
| US-OBS-Phase2-Trace | 분산 추적 | shared-lib (Telemetry 확장) | Admin |
| US-DEPLOY-Phase2-K8s | Kubernetes 마이그레이션 | infra/ (전면 개편) | Admin |

### 2.1 Phase 3
| Story ID | 제목 | 유닛 |
|---|---|---|
| US-RPT-Phase3-PPTWord | PPT/Word 자동 생성 | phase2-incubation/reporting |
| US-AVL-Phase3-HA | 24/7 HA 구성 | infra/ + 전체 |

---

## 3. 협력 그래프 (Story Heatmap)

스토리가 유닛 간 협력을 얼마나 강하게 요구하는지:

| 협력 쌍 | 협력 스토리 수 |
|---|---|
| `notebook-unit ↔ data-unit` | 5 (US-NB-02·04, US-VIS-02, US-SHARE-04, etc.) |
| `notebook-unit ↔ auth-unit` | 5 |
| `*` ↔ `audit-unit` | 20+ (감사 발행이 거의 모든 흐름에 부착) |
| `admin-unit ↔ data-unit` | 3 (US-ADM-02·03, US-DS-01~03 협력) |
| `data-unit ↔ credential-unit` | 5 (모든 쿼리·커넥션 등록) |

**핵심 의존**:
1. `notebook-unit → data-unit` (SQL 셀 실행)
2. 모든 유닛 → `audit-unit` (감사)
3. 모든 유닛 → `auth-unit` (인가)
4. `data-unit → credential-unit` (자격증명)

---

## 4. 매핑 검증 (Step U5)

### 4.1 모든 모듈이 정확히 1 유닛에 속함?
| 모듈 | 유닛 | OK |
|---|---|---|
| ApiGateway, OidcCallbackHandler, SecurityKernel(SL-1) | gateway-unit | ✓ |
| AuthService, SessionStore, RoleResolver, KeycloakAdapter, AuthServiceOrchestrator | auth-unit | ✓ |
| AuditWriter, AuditQueryApi, AuditEventEmitter(SL-2), AuditService | audit-unit | ✓ |
| CredentialVault, VaultAdapter | credential-unit | ✓ |
| ConnectionRegistry, ConnectorFactory, RdbmsConnector, BigDataSqlConnector, QueryExecutor, SchemaIntrospector, PiiPolicyStore, PiiMaskingFilter, FileUploadHandler, DataAccessService | data-unit | ✓ |
| NotebookStore, JupyterHubSpawner, KernelManager, ChartBuilder, ShareLinkManager, GitAdapter, AutoCommitOrchestrator, NotebookService | notebook-unit | ✓ |
| AdminConsole, AuditorConsole, JupyterExtensionsBundle, BackupScheduler, RestoreVerifier, AdminService, BackupService | admin-unit | ✓ |
| Telemetry(SL-3), ResultTypes(SL-4) | shared-lib | ✓ |

**결과**: 30 모듈 모두 1 유닛 배정 완료. 중복 없음. 누락 없음.

### 4.2 모든 MVP 스토리(40) 매핑 완료?
✓ Section 1에서 40개 모두 주 유닛 + 협력 유닛 부여

### 4.3 의존성 acyclic?
✓ `unit-of-work-dependency.md` §3 검증

---

## 5. 후속 단계 권장 진입 순서 (CONSTRUCTION)

`unit-of-work-dependency.md` §5 의 빌드 시퀀스 + 본 문서의 스토리 무게 결합:

| Order | 유닛 | 진입 우선순위 근거 |
|---|---|---|
| 1 | **shared-lib** | 모든 유닛 dependency |
| 2 | **gateway-unit** + **auth-unit** | 모든 흐름의 진입점 + 다른 유닛의 인가 의존 |
| 3 | **audit-unit** + **credential-unit** | data-unit이 시작되기 전에 준비되어야 함 |
| 4 | **data-unit** | notebook-unit의 의존, 가장 무거운 단일 유닛 중 하나 |
| 5 | **notebook-unit** | 분석가 UX의 핵심 (16 스토리) |
| 6 | **admin-unit** | 마지막 — 다른 유닛 API에 의존 |
| 7 | **infra/** | 전 과정 병행 + 통합 단계에서 마무리 |

이 순서로 Construction의 per-unit 루프(Functional Design → NFR-R → NFR-D → Infra Design → Code Generation)를 진행합니다.
