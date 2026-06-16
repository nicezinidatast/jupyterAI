# Component Methods — 내부망 데이터 분석 플랫폼

**작성일**: 2026-05-21
**표기법**: 언어 중립 의사 시그니처 (Q-AD-4=A) — TypeScript-ish
**에러 형식**: `Result<T, E>` 통일 (Q-AD-5=A 사용자 결정)
**상세 비즈니스 룰**: Functional Design (per-unit, CONSTRUCTION) 단계에서 정의

> 모든 메서드는 호출 전 `SecurityKernel.authorize(...)` 통과를 가정합니다(Defense in Depth, Q-AD-13=A).
> 본 문서는 *공개 인터페이스만*. 내부 헬퍼/private 메서드는 Code Generation 단계에서 결정.

---

## 0. 공통 타입 (Common Types)

```typescript
type Result<T, E = DomainError> = { ok: true; value: T } | { ok: false; error: E };

enum DomainError {
  Unauthorized, Forbidden, NotFound, Conflict, Validation,
  ExternalUnavailable, RateLimited, Expired, BadInput, InternalError
}

type UserId = string;        // Keycloak subject claim
type Role = 'Admin' | 'Analyst' | 'Viewer' | 'Auditor';
type CorrelationId = string; // 요청 추적용
type UserContext = { userId: UserId; roles: Role[]; sessionId: string; corrId: CorrelationId };
type DomainEvent = { type: string; actor: UserId; resource?: string; at: ISO8601; payload: object };
```

---

## 1. ApiGateway

```typescript
interface ApiGateway {
  // 외부에서 호출 X — 라우터 자체. 내부 컴포넌트가 의존하지 않음.
  // 구성: Reverse Proxy 룰 + Rate Limiter + 보안 헤더 강제
}
```

---

## 2. OidcCallbackHandler

```typescript
interface OidcCallbackHandler {
  handleCallback(code: string, state: string): Promise<Result<SessionCookie, DomainError>>;
}

type SessionCookie = { token: string; expiresAt: ISO8601; flags: { secure: true; httpOnly: true; sameSite: 'Lax' } };
```

---

## 3. AuthService (얇은 서비스, Q-AD-6=A)

```typescript
interface AuthService {
  authenticate(token: string): Promise<Result<UserContext>>;
  verifyAccess(ctx: UserContext, action: Action, resource: Resource): Promise<Result<Decision>>;
  changeRole(actor: UserContext, target: UserId, role: Role, op: 'assign' | 'revoke'): Promise<Result<void>>;
  // 활성 Admin ≥ 1 invariant — PBT 대상
}

type Action = 'read' | 'execute' | 'write' | 'admin';
type Resource = { kind: 'connection' | 'notebook' | 'audit' | 'system'; id?: string };
type Decision = 'allow' | 'deny';
```

---

## 4. SessionStore

```typescript
interface SessionStore {
  issue(userId: UserId, claims: TokenClaims): Promise<Result<SessionCookie>>;
  validate(token: string): Promise<Result<Session, Expired | Invalid>>;
  invalidate(sessionId: string): Promise<Result<void>>;
  listActive(filter?: { userId?: UserId }): Promise<Result<Session[]>>;
}

type Session = { id: string; userId: UserId; issuedAt: ISO8601; expiresAt: ISO8601 };
```

---

## 5. RoleResolver

```typescript
interface RoleResolver {
  getRoles(userId: UserId): Promise<Result<Role[]>>;
  assignRole(actor: UserContext, target: UserId, role: Role): Promise<Result<void>>;
  revokeRole(actor: UserContext, target: UserId, role: Role): Promise<Result<void>>;
  canExecute(ctx: UserContext, action: Action, resource: Resource): Promise<Result<boolean>>;
}
```

---

## 6. KeycloakAdapter

```typescript
interface KeycloakAdapter {
  exchangeAuthCode(code: string, redirectUri: string): Promise<Result<KeycloakTokens>>;
  introspect(token: string): Promise<Result<TokenClaims>>;
  getUserProfile(userId: UserId): Promise<Result<UserProfile>>;
  rotateKeys(): Promise<Result<void>>; // JWKS 캐시 갱신
}
```

---

## 7. AuditWriter

```typescript
interface AuditWriter {
  write(event: AuditEvent): Promise<Result<void>>;
  // append-only — update/delete 메서드 의도적으로 없음
}

type AuditEvent = DomainEvent & { resource: string; result: 'success' | 'failure'; corrId: CorrelationId };
```

---

## 8. AuditQueryApi

```typescript
interface AuditQueryApi {
  search(filter: AuditFilter, page: PageRequest): Promise<Result<AuditPage>>;
  export(filter: AuditFilter, format: 'csv' | 'json'): Promise<Result<DownloadHandle>>;
}

type AuditFilter = {
  userId?: UserId;
  from?: ISO8601; to?: ISO8601;
  actions?: string[];
  resources?: string[];
};
```

---

## 9. CredentialVault

```typescript
interface CredentialVault {
  register(scope: 'shared' | 'personal', name: string, secret: Secret): Promise<Result<CredentialId, Conflict>>;
  rotate(id: CredentialId, newSecret: Secret): Promise<Result<void>>;
  delete(id: CredentialId): Promise<Result<void>>;
  resolve(id: CredentialId, requester: UserContext): Promise<Result<Secret, Forbidden>>;
  // resolve는 사용 직전 호출, 짧은 캐시(TTL ≤ 1분), 메모리 즉시 소거
}

type Secret = string & { readonly __brand: 'Secret' }; // 로그·직렬화 차단 brand
```

---

## 10. VaultAdapter

```typescript
interface VaultAdapter {
  read(path: string): Promise<Result<Secret, NotFound>>;
  write(path: string, value: Secret): Promise<Result<void>>;
  delete(path: string): Promise<Result<void>>;
}
```

---

## 11. ConnectionRegistry

```typescript
interface ConnectionRegistry {
  register(spec: ConnectionSpec): Promise<Result<ConnectionId, Conflict>>;
  update(id: ConnectionId, patch: Partial<ConnectionSpec>): Promise<Result<void>>;
  delete(id: ConnectionId): Promise<Result<void, HasActiveSessions>>;
  list(forUser: UserContext): Promise<Result<Connection[]>>; // RBAC 자동 필터
  get(id: ConnectionId, forUser: UserContext): Promise<Result<Connection, Forbidden>>;
  grantAccess(id: ConnectionId, target: UserId | Role, allow: boolean): Promise<Result<void>>;
}

type ConnectionSpec = {
  name: string;
  engine: 'postgres' | 'mysql' | 'oracle' | 'mssql' | 'hive' | 'impala' | 'presto' | 'trino';
  host: string; port: number; database?: string;
  credentialId: CredentialId;
  options?: { kerberos?: KerberosOptions };
};
```

---

## 12. ConnectorFactory

```typescript
interface ConnectorFactory {
  create(spec: ConnectionSpec, cred: Secret): Result<Connector, UnsupportedType>;
}
```

---

## 13. Connector (RDBMS / BigDataSql 공통)

```typescript
interface Connector {
  execute(query: ParamQuery, opts: ExecOpts): Promise<Result<ResultStream, QueryError>>;
  introspect(scope?: { schema?: string }): Promise<Result<SchemaTree>>;
  close(): Promise<Result<void>>;
}

type ParamQuery = { sql: string; params: Record<string, unknown> };
// 파라미터화 강제 — sql 안에 사용자 입력 직접 결합 금지 (SECURITY-05)

type ExecOpts = { timeoutMs?: number; maxRows?: number; pageSize?: number };
```

---

## 14. QueryExecutor

```typescript
interface QueryExecutor {
  run(ctx: UserContext, connId: ConnectionId, q: ParamQuery, opts?: ExecOpts): Promise<Result<QueryHandle>>;
  fetchPage(ctx: UserContext, handle: QueryHandle, pageNo: number): Promise<Result<ResultPage>>;
  cancel(ctx: UserContext, handle: QueryHandle): Promise<Result<void>>;
  promoteToBackground(handle: QueryHandle): Promise<Result<JobId>>; // 5초 임계 초과 시
}

type QueryHandle = { id: string; connId: ConnectionId; startedAt: ISO8601 };
type ResultPage = { rows: Row[]; pageNo: number; hasNext: boolean; totalEstimate?: number };
```

---

## 15. SchemaIntrospector

```typescript
interface SchemaIntrospector {
  tree(connId: ConnectionId, forUser: UserContext, opts?: { lazy?: boolean }): Promise<Result<SchemaTree>>;
  // 1000+ 객체: lazy=true 시 자식은 onDemand 로 fetch
}
```

---

## 16. PiiPolicyStore

```typescript
interface PiiPolicyStore {
  addPattern(name: string, regex: string, kind: PiiKind): Promise<Result<PolicyId, BadRegex>>;
  // BadRegex: catastrophic backtracking 가능 패턴 사전 차단 (길이/중첩 한도)
  removePattern(id: PolicyId): Promise<Result<void>>;
  listPolicies(): Promise<Result<PiiPolicy[]>>;
  setColumnPolicy(connId: ConnectionId, table: string, col: string, policy: ColumnPolicy): Promise<Result<void>>;
}

type PiiKind = 'name' | 'rrn' | 'phone' | 'email' | 'custom';
type ColumnPolicy = 'mask' | 'allow' | 'block';
```

---

## 17. PiiMaskingFilter

```typescript
interface PiiMaskingFilter {
  mask(row: Row, ctx: MaskContext): Row;             // 동기 — 렌더 직전 호출
  maskValue(value: unknown, kind: PiiKind): unknown; // 단일 값
  // Idempotent: 이미 마스킹된 값에 재적용 시 동일 결과
}

type MaskContext = { connId: ConnectionId; columns: ColumnInfo[]; forUser: UserContext };
```

---

## 18. NotebookStore

```typescript
interface NotebookStore {
  save(ctx: UserContext, notebook: Notebook, opts?: { auto: boolean }): Promise<Result<NotebookVersion>>;
  load(ctx: UserContext, id: NotebookId): Promise<Result<Notebook>>;
  list(ctx: UserContext, workspaceId: WorkspaceId): Promise<Result<Notebook[]>>;
  delete(ctx: UserContext, id: NotebookId): Promise<Result<void>>;
  // save() 후 outbox 이벤트 발행 → AutoCommitOrchestrator 소비
}
```

---

## 19. JupyterHubSpawner

```typescript
interface JupyterHubSpawner {
  spawn(userId: UserId): Promise<Result<KernelEndpoint, ResourceExhausted>>;
  stop(userId: UserId): Promise<Result<void>>;
  status(userId: UserId): Promise<Result<SpawnerStatus>>;
}
```

---

## 20. KernelManager

```typescript
interface KernelManager {
  executeCell(ctx: UserContext, args: CellExec): Promise<Result<ExecResult>>;
  // 5초 임계 초과 → 자동으로 background 옵션 제안
  runBackground(ctx: UserContext, args: CellExec): Promise<Result<JobId>>;
  status(ctx: UserContext, jobId: JobId): Promise<Result<JobStatus>>;
}

type CellExec = {
  notebookId: NotebookId; cellId: string;
  code: string; kernel: 'python' | 'r' | 'sql';
  connId?: ConnectionId; // SQL 셀
};
```

---

## 21. FileUploadHandler

```typescript
interface FileUploadHandler {
  upload(ctx: UserContext, stream: ByteStream, meta: FileMeta): Promise<Result<FileHandle, SizeOrFormatError>>;
  // 1GB 초과: 클라이언트가 사전 차단, 서버는 안전한 거절
  resolveSharedPath(ctx: UserContext, path: string): Promise<Result<FileHandle, Forbidden>>;
  // sandbox 외 경로: 거절
}

type FileMeta = { name: string; sizeBytes: number; mime: string };
```

---

## 22. ChartBuilder

```typescript
interface ChartBuilder {
  build(data: DataFrame, type: ChartType, mapping: AxisMapping): Result<ChartSpec, MappingError>;
  validateMapping(mapping: AxisMapping, schema: ColumnInfo[]): Result<void, MappingError>;
  // 10만 행 초과: build()는 거절 + 샘플링 옵션 제안
}

type ChartType = 'line' | 'bar' | 'pie' | 'scatter' | 'heatmap' | 'box' | 'area';
type AxisMapping = { x?: string; y?: string | string[]; color?: string; size?: string };
type ChartSpec = { engine: 'plotly' | 'echarts' | 'matplotlib'; spec: object };
```

---

## 23. ShareLinkManager

```typescript
interface ShareLinkManager {
  create(ctx: UserContext, notebookId: NotebookId, audience: Audience, permission: SharePermission): Promise<Result<ShareLink>>;
  revoke(ctx: UserContext, linkId: string): Promise<Result<void>>;
  resolve(linkId: string, requester: UserContext): Promise<Result<NotebookAccess, Forbidden>>;
}

type SharePermission = 'read' | 'execute' | 'edit';
type Audience = { userIds?: UserId[]; roles?: Role[] };
type NotebookAccess = { notebookId: NotebookId; permission: SharePermission; useCurrentUserCredentials: boolean };
// execute 권한 시 현재 사용자 자격증명으로 셀 실행 (US-SHARE-04)
```

---

## 24. GitAdapter

```typescript
interface GitAdapter {
  commit(repo: RepoId, files: FileChange[], message: string, author: GitIdentity): Promise<Result<Sha>>;
  push(repo: RepoId, branch: string): Promise<Result<void, NetworkError>>;
  createRepo(name: string, visibility: 'private' | 'internal'): Promise<Result<RepoId>>;
  getStatus(repo: RepoId): Promise<Result<RepoStatus>>;
}
```

---

## 25. AutoCommitOrchestrator

```typescript
interface AutoCommitOrchestrator {
  // 이벤트 컨슈머 — 공개 API는 상태 조회만
  getStatus(ctx: UserContext, notebookId: NotebookId): Promise<Result<CommitState>>;
}

type CommitState =
  | { kind: 'queued' }
  | { kind: 'committed'; sha: Sha; pushedAt: ISO8601 }
  | { kind: 'retrying'; attempt: number; lastError: string }
  | { kind: 'failed'; reason: string };
```

---

## 26. AdminConsole / AuditorConsole

```typescript
// SPA — 백엔드 도메인 컴포넌트의 API에 HTTP로 의존.
// 별도 메서드 정의 없음 — UI 코드의 콜 사이트가 곧 사용.
```

---

## 27. JupyterExtensionsBundle

```typescript
// JupyterLab Extension 패키지. 호스트 JupyterLab의 plugin 모델 따름.
// 내부적으로 백엔드 API 호출(예: SchemaIntrospector, QueryExecutor, ChartBuilder).
```

---

## 28. BackupScheduler / RestoreVerifier

```typescript
interface BackupScheduler {
  enqueueBackup(target: BackupTarget): Promise<Result<JobId>>;
  status(jobId: JobId): Promise<Result<JobStatus>>;
  // 스케줄(cron)은 Infrastructure Design 단계에서 정의
}

interface RestoreVerifier {
  scheduleRehearsal(target: BackupTarget): Promise<Result<RehearsalId>>;
  getReport(id: RehearsalId): Promise<Result<RehearsalReport>>;
}
```

---

## 29. 공유 라이브러리 시그니처

### SL-1 SecurityKernel
```typescript
namespace SecurityKernel {
  function authenticate(headers: Record<string, string>): Promise<Result<UserContext, Unauthorized>>;
  function authorize(ctx: UserContext, action: Action, resource: Resource): Promise<Result<void, Forbidden>>;
}
```

### SL-2 AuditEventEmitter
```typescript
namespace Audit {
  function emit(event: DomainEvent): void;  // 즉시 반환, outbox 적재
}
```

### SL-3 Telemetry
```typescript
namespace Telemetry {
  const metric: { counter(name: string, labels?: object): Counter; histogram(name: string, value: number, labels?: object): void };
  const log: { info(msg: string, fields?: object): void; warn(...): void; error(...): void };
  const trace: { span(name: string): Span };
}
```

### SL-4 ResultTypes
(공통 타입 §0 참조)

---

## 30. 호출 관계 요약 — 대표 시나리오

### 시나리오 A: 분석가 SQL 실행 (US-NB-02)

```text
JupyterLabClient
  → KernelManager.executeCell(sql)
    → SecurityKernel.authorize(execute, connection:X)
    → QueryExecutor.run(...)
      → ConnectionRegistry.get(connId, ctx)
      → CredentialVault.resolve(credId, ctx)
      → ConnectorFactory.create(spec, cred)
      → connector.execute(paramQuery)
      → PiiMaskingFilter.mask(row, ctx)   // 결과 페이지 직전
      → AuditEventEmitter.emit(query_executed)
```

### 시나리오 B: 노트북 저장 → Git 자동 커밋 (US-SHARE-01, Q-AD-14=A)

```text
JupyterLabClient
  → NotebookStore.save(ctx, notebook, auto:true)
    → 메타DB 트랜잭션 [노트북 버전 insert + outbox 이벤트 insert]
    → AuditEventEmitter.emit(notebook_saved)
  ┄┄ (트랜잭션 종료) ┄┄
  AutoCommitOrchestrator (consumer, async)
    → GitAdapter.commit(...)
    → GitAdapter.push(...)
    → 재시도 정책 (3회) + outbox 보존 (서버 다운 시)
```

---

## 31. 다음 단계로의 위임

| 결정 보류 | 위임 단계 |
|---|---|
| 구현 언어 (Java/Kotlin/Go/Python/TS) | NFR Requirements |
| HTTP vs gRPC vs in-process | NFR Design |
| 데이터 모델 스키마 (테이블/컬럼) | Functional Design |
| 알고리즘(예: 마스킹 정규식 매처) | Functional Design |
| 컨테이너 분할(어떤 컴포넌트가 어느 컨테이너에) | Infrastructure Design |
| Rate Limit 수치, 타임아웃 값 | NFR Design |
