# Components — 내부망 데이터 분석 플랫폼

**작성일**: 2026-05-21
**입자 크기**: 중간 (Q-AD-1=B, 도메인당 2~4개 컴포넌트)
**아키텍처 스타일**: Modular Monolith (Q-AD-11=A) — 단일 배포 단위 안에 도메인별 모듈
**횡단 관심사**: 공유 라이브러리(Q-AD-2=A) + Defense in Depth (Q-AD-13=A)
**외부 시스템 결합**: 모든 외부 시스템에 Adapter 컴포넌트 (Q-AD-10=A)

> 상세 비즈니스 룰은 **Functional Design (per-unit, CONSTRUCTION phase)** 으로 위임. 본 문서는 컴포넌트 *책임*과 *인터페이스 형태* 만 다룸.

---

## 0. 컴포넌트 인벤토리 요약

총 **23개 컴포넌트 + 4개 공유 라이브러리** (MVP) + Phase 2 후보 6개.

| # | 컴포넌트 | 도메인 | 분류 |
|---|---|---|---|
| 1 | `ApiGateway` | Gateway | 핵심 |
| 2 | `OidcCallbackHandler` | Gateway | 핵심 |
| 3 | `AuthService` | Auth | 도메인 |
| 4 | `SessionStore` | Auth | 도메인 |
| 5 | `RoleResolver` | Auth | 도메인 |
| 6 | `KeycloakAdapter` | Auth | 외부 어댑터 |
| 7 | `AuditWriter` | Audit | 도메인 |
| 8 | `AuditQueryApi` | Audit | 도메인 |
| 9 | `CredentialVault` | Credential | 도메인 |
| 10 | `VaultAdapter` | Credential | 외부 어댑터 |
| 11 | `ConnectionRegistry` | Connector | 도메인 |
| 12 | `ConnectorFactory` | Connector | 도메인 |
| 13 | `RdbmsConnector` | Connector | 외부 어댑터 |
| 14 | `BigDataSqlConnector` | Connector | 외부 어댑터 |
| 15 | `QueryExecutor` | Connector | 도메인 |
| 16 | `SchemaIntrospector` | Connector | 도메인 |
| 17 | `PiiPolicyStore` | PII | 도메인 |
| 18 | `PiiMaskingFilter` | PII | 도메인 |
| 19 | `NotebookStore` | Notebook | 도메인 |
| 20 | `JupyterHubSpawner` | Notebook | 외부 어댑터 |
| 21 | `KernelManager` | Notebook | 도메인 |
| 22 | `FileUploadHandler` | Notebook | 도메인 |
| 23 | `ChartBuilder` | Visualization | 도메인 |
| 24 | `ShareLinkManager` | Share | 도메인 |
| 25 | `GitAdapter` | Git | 외부 어댑터 |
| 26 | `AutoCommitOrchestrator` | Git | 도메인 |
| 27 | `AdminConsole` | UI | UI (SPA) |
| 28 | `AuditorConsole` | UI | UI (SPA) |
| 29 | `JupyterExtensionsBundle` | UI | UI (JupyterLab Ext) |
| 30 | `BackupScheduler` | Ops | 도메인 |
| 31 | `RestoreVerifier` | Ops | 도메인 |

### 공유 라이브러리 (모든 컴포넌트가 import)
- **SL-1**: `SecurityKernel` — 토큰 검증, Defense-in-Depth 강제, fail-closed 예외 처리
- **SL-2**: `AuditEventEmitter` — 모든 컴포넌트가 도메인 이벤트를 발행 (outbox 패턴)
- **SL-3**: `Telemetry` — 메트릭/로깅/트레이스ID (Prometheus + 구조화 로깅)
- **SL-4**: `ResultTypes` — `Result<T, E>` / `DomainError` 통일 타입 (Q-AD-5=A)

### Phase 2 후보
- `LlmProxyAdapter`, `LlmGovernor`, `ReportRenderer`, `ReportScheduler`, `ColumnLevelGuard`, `NotebookSearchIndexer`

---

## 1. Gateway Layer

### 1.1 ApiGateway

**책임**:
- 외부 트래픽의 단일 진입점 (Reverse Proxy 역할)
- TLS 종단(1.2+), 보안 헤더 강제(SECURITY-04), Rate Limiting(SECURITY-11)
- 라우팅 → AdminConsole / AuditorConsole / JupyterHub / API
- Defense in Depth 1차 인가(`SecurityKernel` 호출)

**인터페이스**:
- HTTP 외부 → HTTPS 내부 라우트
- 다운스트림 컴포넌트에 `X-Auth-User`, `X-Correlation-Id` 헤더 주입

**외부 의존**: 없음 (가장 바깥)
**FR/NFR 매핑**: NFR-SEC-01, NFR-SEC-04, NFR-SEC-07, NFR-SEC-11
**스토리 매핑**: US-AUTH-01·03, US-SEC-04·05 진입점

---

### 1.2 OidcCallbackHandler

**책임**:
- Keycloak OIDC redirect_uri 처리
- Authorization Code → ID/Access Token 교환
- 성공 시 `SessionStore`에 세션 발급 요청
- 실패 시 일반화된 에러로 사용자 반환 (SECURITY-09)

**인터페이스**: `handleCallback(code, state) → SessionToken`
**외부 의존**: `KeycloakAdapter`, `SessionStore`, `AuditEventEmitter`
**스토리 매핑**: US-AUTH-01

---

## 2. Auth Domain

### 2.1 AuthService

**책임**:
- 인증·세션·역할 관련 도메인 로직 진입점(얇은 서비스, Q-AD-6=A)
- 트랜잭션 경계 관리 (세션 발급 + 감사 발행)
- 다른 컴포넌트가 사용하는 권한 확인 API 제공

**인터페이스**: `verifyAccess(userId, resource, action) → Result<Decision, AuthError>`
**외부 의존**: `SessionStore`, `RoleResolver`, `KeycloakAdapter`, `AuditEventEmitter`
**스토리 매핑**: US-AUTH-01·02·03·04·05, US-DS-03·08

---

### 2.2 SessionStore

**책임**:
- 세션 TTL 관리, 만료/무효화
- `Secure;HttpOnly;SameSite=Lax` 쿠키 발급
- 활성 세션 조회 (Auditor용)

**인터페이스**:
- `issue(userId, claims) → Result<SessionToken, _>`
- `validate(token) → Result<Session, ExpiredOrInvalid>`
- `invalidate(sessionId) → Result<(), _>`
- `listActive(userId?) → Result<Session[], _>`

**외부 의존**: 메타DB (세션 테이블), `AuditEventEmitter`
**스토리 매핑**: US-AUTH-01·03, US-SEC-03

---

### 2.3 RoleResolver

**책임**:
- 사용자 ↔ 역할(Admin/Analyst/Viewer/Auditor) 매핑 관리
- 권한 확인 (`canExecute(userId, action, resource)`)
- 활성 Admin ≥ 1 invariant 유지 (US-AUTH-02 부정 케이스)

**인터페이스**:
- `getRoles(userId) → Result<Role[], _>`
- `assignRole(userId, role) → Result<(), DomainError>`
- `revokeRole(userId, role) → Result<(), DomainError>`
- `canExecute(userId, action, resource) → Result<bool, _>`

**외부 의존**: 메타DB, `AuditEventEmitter`
**FR/NFR 매핑**: FR-AUTH-02, NFR-SEC-06, NFR-SEC-08
**PBT 적용**: Invariant — `assignRole`/`revokeRole` 후에도 활성 Admin ≥ 1

---

### 2.4 KeycloakAdapter (Anti-Corruption Layer)

**책임**:
- Keycloak 외부 API 호출을 도메인 친화 인터페이스로 감쌈
- OIDC discovery, JWKS 캐싱, token introspection
- 도메인은 이 어댑터에만 의존 (Q-AD-10=A)

**인터페이스**:
- `exchangeAuthCode(code) → Result<KeycloakTokens, _>`
- `introspect(token) → Result<TokenClaims, _>`
- `getUserProfile(userId) → Result<UserProfile, _>`

**외부 의존**: Keycloak 서버 (사내)

---

## 3. Audit Domain

### 3.1 AuditWriter

**책임**:
- append-only 감사 로그 저장 (NFR-SEC-14, NFR-AUDIT-01·02)
- 1년 이상 보존, WORM 또는 권한 분리
- 저장소 일시 불가 시 fail-closed (이벤트 발생 거절) 또는 로컬 큐잉 후 재전송

**인터페이스**:
- `write(event: AuditEvent) → Result<(), AuditError>`
- (내부 큐: outbox 테이블 + 비동기 publisher)

**외부 의존**: 감사 저장소(메타DB의 분리 스키마 또는 별도 DB)
**스토리 매핑**: US-SEC-01

---

### 3.2 AuditQueryApi

**책임**:
- Auditor 콘솔용 검색 API (사용자/기간/액션/리소스 필터)
- CSV/JSON 내보내기 (다운로드 자체도 감사 이벤트)

**인터페이스**:
- `search(filter, page) → Result<AuditPage, _>`
- `export(filter, format) → Result<DownloadHandle, _>`

**외부 의존**: 감사 저장소(읽기 전용), `AuditWriter` (export 이벤트 자기 발행)
**스토리 매핑**: US-SEC-03

---

## 4. Credential Domain

### 4.1 CredentialVault

**책임**:
- 자격증명 등록/회전/삭제 (공용·개인 둘 다)
- 사용자별 namespace 격리
- 평문은 메모리에서 즉시 소거

**인터페이스**:
- `register(scope, name, secret) → Result<CredentialId, _>`
- `rotate(id, newSecret) → Result<(), _>`
- `delete(id) → Result<(), _>`
- `resolve(id, requester) → Result<Secret, AccessDenied>` (사용 직전 호출, 짧은 캐시)

**외부 의존**: `VaultAdapter`, `AuthService` (인가), `AuditEventEmitter`
**FR/NFR 매핑**: FR-DS-07, NFR-SEC-01, NFR-SEC-12
**PBT 적용**: Idempotent (재등록), State-Machine (등록→회전→삭제)

---

### 4.2 VaultAdapter

**책임**: HashiCorp Vault 또는 동등 시크릿 매니저 호출 추상화 (Q-AD-10=A)
**인터페이스**: `read(path)`, `write(path, value)`, `delete(path)`
**외부 의존**: Vault 서버

---

## 5. Connector Domain

### 5.1 ConnectionRegistry

**책임**: 등록된 커넥션 목록 관리 (메타데이터만, 자격증명은 Vault)
**인터페이스**:
- `register(spec: ConnectionSpec) → Result<ConnectionId, DuplicateName>`
- `update(id, partial) → Result<(), _>`
- `delete(id) → Result<(), HasActiveSessions>`
- `list(forUser) → Result<Connection[], _>` (RBAC 적용 — 권한 없는 것은 목록에서 제외)
- `get(id, forUser) → Result<Connection, AccessDenied>`

**외부 의존**: 메타DB, `AuthService`, `AuditEventEmitter`
**FR/NFR 매핑**: FR-DS-01·02·07·08, NFR-SEC-06·08
**PBT 적용**: Idempotent (동일 이름 재등록 거절/멱등)

---

### 5.2 ConnectorFactory

**책임**: ConnectionSpec → 적절한 Connector 인스턴스 dispatch (RDBMS/BigDataSql/...)
**인터페이스**: `create(spec) → Result<Connector, UnsupportedType>`
**외부 의존**: 없음 (Pure factory)

---

### 5.3 RdbmsConnector (외부 어댑터)

**책임**: PostgreSQL/MySQL/Oracle/MSSQL JDBC/ODBC 호출 캡슐화
**인터페이스**:
- `execute(query: ParamQuery, opts) → Result<ResultStream, QueryError>`
- `introspect(schema?) → Result<SchemaTree, _>`

**외부 의존**: 사내 DB

---

### 5.4 BigDataSqlConnector (외부 어댑터)

**책임**: Hive/Impala/Presto/Trino — Kerberos 인증 옵션 포함
**인터페이스**: RdbmsConnector와 동일 시그니처 (다형성)
**외부 의존**: 사내 빅데이터 클러스터, KerberosTicketCache(내부)

---

### 5.5 QueryExecutor

**책임**:
- 도메인 진입점: 권한 검사 → 자격증명 resolve → ConnectorFactory → 파라미터화 강제(SECURITY-05)
- 결과 페이지네이션 (100 행/페이지)
- 5초 이상 걸리면 백그라운드 잡으로 승격 (US-NB-02·06)
- 결과 단일 한도 10GB/1억 행 초과 시 거절 (NFR-PERF-05)

**인터페이스**:
- `run(userId, connId, sqlParam, opts) → Result<QueryHandle, _>`
- `fetchPage(handle, pageNo) → Result<ResultPage, _>`
- `cancel(handle) → Result<(), _>`

**외부 의존**: `AuthService`, `CredentialVault`, `ConnectorFactory`, `PiiMaskingFilter`(렌더 직전), `AuditEventEmitter`

---

### 5.6 SchemaIntrospector

**책임**: 사이드 패널용 스키마 트리 구축, 1000+ 객체 lazy load, RBAC 적용
**인터페이스**: `tree(connId, forUser) → Result<SchemaTree, _>`
**스토리 매핑**: US-DS-05

---

## 6. PII Domain

### 6.1 PiiPolicyStore

**책임**: PII 마스킹 규칙(정규식 + 컬럼 화이트/블랙리스트) CRUD
**인터페이스**:
- `addPattern(name, regex, kind) → Result<PolicyId, BadRegex>` (catastrophic backtracking 차단)
- `listPolicies() → Policy[]`
- `setColumnPolicy(connId, col, policy) → Result<(), _>`

**외부 의존**: 메타DB, `AuditEventEmitter`
**스토리 매핑**: US-ADM-03
**PBT 적용**: Domain-Generator (PII 후보 문자열 생성기 + 마스킹 룰 견고성)

---

### 6.2 PiiMaskingFilter

**책임**:
- 결과가 사용자에게 응답되기 *직전* 적용 (Q-AD-15=A)
- 가능 시 사전 컬럼 메타 기반 차단(쿼리 단계)도 보조 적용
- Idempotent 보장 (이미 마스킹된 값에 재적용 시 동일)

**인터페이스**: `mask(row, ctx) → Row`
**외부 의존**: `PiiPolicyStore` (정책 캐시)
**스토리 매핑**: US-NB-02, US-SEC-02, US-VIS-02
**PBT 적용**: Oracle (마스킹 함수 vs 레퍼런스 정규식) + Idempotent

---

## 7. Notebook Domain

### 7.1 NotebookStore

**책임**: 노트북 파일/메타데이터 저장, 자동 저장(분 단위)
**인터페이스**:
- `save(notebook, options) → Result<NotebookVersion, _>`
- `load(id, forUser) → Result<Notebook, _>`
- `list(workspace, forUser) → Result<Notebook[], _>`

**외부 의존**: 메타DB + 워크스페이스 디스크, `AuthService`, `AuditEventEmitter`, `AutoCommitOrchestrator`(저장 후 outbox로 신호)
**스토리 매핑**: US-NB-05, US-SHARE-02

---

### 7.2 JupyterHubSpawner (외부 어댑터)

**책임**: 사용자별 격리 컨테이너 spawn (JupyterHub 확장 포인트 활용)
**인터페이스**: `spawn(userId) → Result<KernelUrl, _>`, `stop(userId) → Result<(), _>`
**외부 의존**: JupyterHub, Docker 또는 (Phase 2) k8s
**스토리 매핑**: US-NB-01

---

### 7.3 KernelManager

**책임**: SQL/Python/R 커널 라이프사이클, 셀 실행 큐, 백그라운드 잡 관리
**인터페이스**:
- `executeCell(notebookId, cellId, code, kernel) → Result<ExecHandle, _>`
- `runBackground(notebookId, cellId, code, kernel) → Result<JobId, _>`
- `status(jobId) → Result<JobStatus, _>`

**외부 의존**: `JupyterHubSpawner`, `QueryExecutor`(SQL 셀의 경우), `AuditEventEmitter`
**스토리 매핑**: US-NB-02·03·06

---

### 7.4 FileUploadHandler

**책임**:
- 단일 파일 ≤ 1GB 업로드 처리 (NFR-PERF-04, 클라이언트에서 사이즈 사전 거절)
- CSV/TSV/Excel/Parquet/JSON/Feather 포맷 인식
- 공유 스토리지(NAS/MinIO) 마운트 경로 검증 (sandbox 외 거절)

**인터페이스**:
- `upload(stream, meta) → Result<FileHandle, SizeOrFormatError>`
- `resolveSharedPath(path, forUser) → Result<FileHandle, AccessDenied>`

**외부 의존**: 로컬 디스크/MinIO/NAS, `AuthService`, `AuditEventEmitter`
**스토리 매핑**: US-DS-06·07
**PBT 적용**: Round-trip (CSV/Parquet 업로드-읽기-직렬화 동일성)

---

## 8. Visualization Domain

### 8.1 ChartBuilder

**책임**:
- 7종 표준 차트(line/bar/pie/scatter/heatmap/box/area)의 데이터 → 차트 스펙 변환
- Plotly(인터랙티브) / Matplotlib(정적) 결과 두 렌더 후보 지원
- 10만 행 초과 시 샘플링/집계 옵션 제안

**인터페이스**:
- `build(data, chartType, mapping) → Result<ChartSpec, BadMapping>`
- `validate(mapping, dataSchema) → Result<(), MismatchError>` (축 타입 불일치 사전 차단)

**외부 의존**: 없음 (순수 도메인 로직). PII가 포함된 데이터는 호출 전 마스킹 가정.
**스토리 매핑**: US-VIS-01~04

---

## 9. Share Domain

### 9.1 ShareLinkManager

**책임**: 노트북·대시보드 링크 발급, 권한 레벨(읽기/실행/편집), SSO 인증 강제, 도용 시 401
**인터페이스**:
- `create(notebookId, audience, permission) → Result<ShareLink, _>`
- `revoke(linkId) → Result<(), _>`
- `resolve(linkId, requester) → Result<NotebookAccess, AccessDenied>`

**외부 의존**: 메타DB, `AuthService`, `AuditEventEmitter`
**스토리 매핑**: US-SHARE-03·04
**PBT 적용**: Invariant (권한 < 요구권한 → 항상 거절)

---

## 10. Git Domain

### 10.1 GitAdapter (외부 어댑터)

**책임**: GitLab/Gitea REST API 호출 추상화 (commit, push, repository CRUD)
**인터페이스**:
- `commit(repo, files, message, author) → Result<Sha, _>`
- `push(repo, branch) → Result<(), _>`
- `createRepo(name, visibility) → Result<RepoId, _>`

**외부 의존**: 사내 GitLab/Gitea

---

### 10.2 AutoCommitOrchestrator

**책임**:
- NotebookStore 저장 후 outbox 이벤트를 받아 백그라운드로 Git 커밋·push
- 메시지 없으면 "auto: <노트북명> @ <ts>", 최대 3회 재시도
- 동일 콘텐츠 재커밋 = no-op (Idempotent)
- Git 서버 다운 시 로컬 outbox 보존

**인터페이스**: 이벤트 컨슈머. 내부 작업이지만 status API 제공.
- `getStatus(notebookId) → Result<CommitState, _>`

**외부 의존**: outbox 큐(Redis Streams 또는 outbox 테이블, Q-AD-9=A), `GitAdapter`, `AuthService` (사용자 자격증명 자동 커밋 시)
**스토리 매핑**: US-SHARE-01
**PBT 적용**: Idempotent

---

## 11. UI Components

### 11.1 AdminConsole (SPA)

**책임**: 사용자·역할·커넥션·PII 패턴·헬스 대시보드 (분리된 SPA, Q-AD-3=A)
**인터페이스**: HTTP 호출만 — 도메인 컴포넌트의 API 표면 사용
**스토리 매핑**: US-ADM-01~05

### 11.2 AuditorConsole (SPA)

**책임**: 감사 로그 검색·내보내기 콘솔
**스토리 매핑**: US-SEC-03

### 11.3 JupyterExtensionsBundle

**책임**: JupyterLab Extension 패키지 (커넥션 사이드 패널, SQL 에디터 자동완성, 차트 변환 버튼)
**스토리 매핑**: US-DS-05, US-NB-02·04, US-VIS-01

---

## 12. Ops Domain

### 12.1 BackupScheduler

**책임**: 일 1회 이상 자동 백업 (메타DB + 사용자 워크스페이스), Prometheus 메트릭 노출
**스토리 매핑**: US-ADM-05

### 12.2 RestoreVerifier

**책임**: 월 1회 자동 복구 리허설 보고서 (격리 환경에서 백업 → 복구 → 검증)
**스토리 매핑**: US-ADM-05

---

## 13. 공유 라이브러리 상세

### SL-1: SecurityKernel
- `authenticate(headers) → Result<UserContext, Unauthorized>`
- `authorize(userCtx, action, resource) → Result<(), Forbidden>`
- 모든 컴포넌트 진입점에서 의무 호출 (Defense in Depth, Q-AD-13=A)
- fail-closed: 검증 실패 시 일반화 메시지(SECURITY-15)

### SL-2: AuditEventEmitter
- `emit(event: DomainEvent) → ()` (in-memory, 즉시 반환)
- 내부적으로 outbox 큐에 적재 → `AuditWriter`가 비동기 소비
- 모든 도메인 컴포넌트가 사용

### SL-3: Telemetry
- `metric.counter(name, labels)`, `metric.histogram(name, value, labels)`
- `log.info|warn|error(msg, fields)` — 구조화 JSON
- `trace.span(name)` — correlation-id 자동 전파 (Phase 2 OpenTelemetry 풀)

### SL-4: ResultTypes
- `type Result<T, E> = Ok(T) | Err(E)`
- 공통 `DomainError` enum (Unauthorized, NotFound, Conflict, Validation, ExternalUnavailable, …)
- 모든 컴포넌트가 동일 에러 형식 사용 (Q-AD-5=A 사용자 결정)

---

## 14. 상세 비즈니스 룰은 어디로 가는가

본 문서는 *책임*만 기술. 다음 단계 매핑:
- **Functional Design (per-unit)**: 각 컴포넌트의 데이터 모델 + 비즈니스 룰 + 알고리즘
- **NFR Requirements/Design (per-unit)**: 보안·성능·관측성 적용 디테일
- **Infrastructure Design (per-unit)**: 배포 단위, 컨테이너 정의, 사내 인프라 매핑
- **Code Generation (per-unit)**: 실제 구현
