# Services — 내부망 데이터 분석 플랫폼

**작성일**: 2026-05-21
**오케스트레이션 패턴**: 얇은 서비스 + 도메인 컴포넌트가 일을 함 (Q-AD-6=A)
**서비스 경계**: 도메인 단위 (Q-AD-7=A) — UseCase는 Functional Design에서

> **서비스 ≠ 마이크로서비스**. 본 문서의 "서비스"는 *오케스트레이션 레이어*. Modular Monolith(Q-AD-11=A) 안의 내부 모듈.

---

## 0. 서비스 인벤토리

| 서비스 | 도메인 | 책임 요약 |
|---|---|---|
| `AuthServiceOrchestrator` | Auth | 로그인 흐름, 역할 변경 트랜잭션 |
| `DataAccessService` | Connector + PII | 쿼리 실행의 전체 흐름 오케스트레이션 |
| `NotebookService` | Notebook + Git + Share | 노트북 저장/공유/실행 오케스트레이션 |
| `AdminService` | Admin | 사용자/커넥션/PII/감사 정책 콘솔 백엔드 |
| `AuditService` | Audit | 감사 발행/검색/내보내기 트랜잭션 |
| `BackupService` | Ops | 백업·복구 리허설 스케줄링 |

---

## 1. AuthServiceOrchestrator

### 책임
- OIDC 로그인의 처음부터 끝까지 한 단위로 묶음 (외부 토큰 교환 + 세션 발급 + 감사)
- 역할 변경 트랜잭션 (역할 변경 + invariant 검사 + 감사)
- 세션 만료 + 재로그인 흐름의 일관성 유지

### 오케스트레이션 사례

**A. 로그인 흐름** (US-AUTH-01)
```text
1. OidcCallbackHandler.handleCallback(code, state)
2. → KeycloakAdapter.exchangeAuthCode(code)
3. → KeycloakAdapter.getUserProfile(userId)
4. → RoleResolver.getRoles(userId)
5. → SessionStore.issue(userId, claims)
6. → AuditEventEmitter.emit({type: 'login', actor: userId, result: 'success'})
7. ← SessionCookie 반환
```

**B. 역할 변경** (US-AUTH-02)
```text
TRANSACTION {
  1. RoleResolver.assignRole(actor, target, role) | revokeRole(...)
  2. // invariant: 활성 Admin ≥ 1 검사 — 위반 시 ROLLBACK
  3. AuditEventEmitter.emit({type: 'role_changed', actor, target, old, new})
} COMMIT
```

### 외부 시스템 결합
- Keycloak (auth-only) — `KeycloakAdapter` 경유

---

## 2. DataAccessService

### 책임
- **사용자가 SQL을 실행한다**라는 의미를 끝까지 책임짐 (시나리오 A의 모든 단계)
- 인가 + 자격증명 + 연결 + 쿼리 + 마스킹 + 감사를 단일 흐름으로

### 오케스트레이션 사례 — 쿼리 실행 (US-NB-02)

```text
DataAccessService.runQuery(ctx, connId, paramQuery, opts):
  1. SecurityKernel.authorize(ctx, 'execute', connection:connId)
     ↳ Forbidden → 즉시 Err(Forbidden) + 감사 발행
  2. ConnectionRegistry.get(connId, ctx)
     ↳ NotFound | Forbidden → 즉시 Err
  3. CredentialVault.resolve(connection.credentialId, ctx)
     ↳ Forbidden → 즉시 Err
  4. ConnectorFactory.create(spec, cred)
  5. connector.execute(paramQuery, opts)
     ↳ timeout 5s 초과 → QueryExecutor.promoteToBackground()
     ↳ error → Err(QueryError) + 감사 발행
  6. result row stream:
     foreach page:
       PiiMaskingFilter.mask(row, ctx) on each row
       yield ResultPage
  7. AuditEventEmitter.emit({type: 'query_executed', actor, connId, rowsReturned, durationMs})
```

### 특이 사항
- 단계 5 이전에 SQL은 반드시 파라미터화된 ParamQuery 형태(SECURITY-05)
- 단계 6에서 마스킹이 **렌더 직전**(Q-AD-15=A) 적용
- 모든 분기(권한 거부, 자격증명 거부, 쿼리 오류)에서 감사 이벤트 발행 — fail-closed (SECURITY-15)

### 외부 시스템 결합
- 사내 DB/빅데이터 (Connector 경유) — 다른 외부 시스템 없음
- Vault (CredentialVault 경유)

---

## 3. NotebookService

### 책임
- 노트북 저장·실행·공유 흐름의 트랜잭션 경계 관리
- "노트북을 저장하면 Git 백그라운드 커밋이 일어난다"의 보장 (outbox 패턴, Q-AD-14=A)

### 오케스트레이션 사례

**A. 노트북 저장 + Git 자동 커밋** (US-SHARE-01)

```text
NotebookService.saveAndCommit(ctx, notebook, opts: {auto: true}):
  TRANSACTION (메타DB) {
    1. NotebookStore.save(ctx, notebook, auto:true)  // 새 NotebookVersion + outbox row insert
    2. AuditEventEmitter.emit({type: 'notebook_saved', actor, notebookId, version})
  } COMMIT
  // 이후는 비동기:
  AutoCommitOrchestrator (consumer) reads outbox →
    GitAdapter.commit(...) → push(...) → 재시도 3회 → 실패 시 outbox 유지
```

**B. 공유 노트북 실행 (권한=execute)** (US-SHARE-04)

```text
NotebookService.executeShared(ctx, linkId):
  1. ShareLinkManager.resolve(linkId, ctx)
     ↳ link.permission < 'execute' → Err(Forbidden)
  2. NotebookStore.load(ctx, link.notebookId)
  3. 각 셀:
     If kernel == 'sql':
       DataAccessService.runQuery(ctx, conn, query)   // **현재 사용자**의 ctx 사용 — 격리 보장
     If kernel in ('python', 'r'):
       KernelManager.executeCell(ctx, cellExec)
  4. AuditEventEmitter.emit({type: 'shared_notebook_executed', actor, linkId, notebookId})
```

### 외부 시스템 결합
- GitLab/Gitea (`GitAdapter` 경유)

---

## 4. AdminService

### 책임
- AdminConsole(SPA)이 호출하는 백엔드 진입점
- 한 화면 = 한 트랜잭션 (편집·삭제·정책 변경)
- 도메인 컴포넌트의 단순 wrapper에 가깝지만 **여러 컴포넌트가 합쳐지는 흐름만 모음**

### 오케스트레이션 사례

**A. 신규 커넥션 등록** (US-DS-01)

```text
AdminService.registerConnection(ctx, spec):
  1. SecurityKernel.authorize(ctx, 'admin', system)
  2. CredentialVault.register('shared', spec.name + '-cred', spec.secret)
  3. ConnectionRegistry.register({...spec, credentialId: from step 2})
  4. AuditEventEmitter.emit({type: 'connection_registered', actor, connId, engine})
  5. testConnection 옵션 → connector.execute('SELECT 1')
  6. 결과 응답
  // 실패 시 보상: step 2/3 모두 롤백 (또는 ROLLBACK 트랜잭션 가능 시)
```

**B. PII 패턴 추가** (US-ADM-03)

```text
AdminService.addPiiPattern(ctx, name, regex, kind):
  1. authorize
  2. validateRegex(regex) — catastrophic backtracking 차단 (길이/중첩 한도)
  3. PiiPolicyStore.addPattern(...)
  4. // 마스킹 엔진 캐시 즉시 무효화 (in-process 이벤트)
  5. AuditEventEmitter.emit({type: 'pii_pattern_added', ...})
```

### 외부 시스템 결합
- 없음 (도메인 내부)

---

## 5. AuditService

### 책임
- 감사 이벤트의 발행·저장·검색·내보내기를 한 도메인으로
- `AuditEventEmitter`(SL-2)는 *발행*만, 본 서비스는 *처리·소비·조회*까지 포함

### 오케스트레이션 사례

**A. 감사 이벤트 비동기 처리**

```text
AuditService (consumer loop):
  events = outbox.poll()
  foreach event:
    AuditWriter.write(event)         // append-only 저장
    if write fails persistently:
      fail-closed alert + retry
```

**B. Auditor 검색·내보내기** (US-SEC-03)

```text
AuditService.search(ctx, filter, page):
  1. SecurityKernel.authorize(ctx, 'read', audit)
     ↳ Analyst/Viewer/Admin이 호출 시 정책에 따라 결정 (Auditor만 default allow)
  2. AuditQueryApi.search(filter, page)
  3. AuditEventEmitter.emit({type: 'audit_searched', actor, filter})  // 감사도 감사
```

```text
AuditService.export(ctx, filter, format):
  1. authorize
  2. AuditQueryApi.export(filter, format) — 큰 결과는 비동기 download handle
  3. AuditEventEmitter.emit({type: 'audit_exported', actor, recordsExported, format})
```

### 외부 시스템 결합
- 없음 (append-only 저장소는 내부)

---

## 6. BackupService

### 책임
- 일 1회 자동 백업 + 월 1회 복구 리허설 (US-ADM-05)
- 실패 시 Admin/Auditor 알림

### 오케스트레이션 사례

```text
BackupService.runScheduled():
  for each target in (metaDB, workspaces, vault-export):
    1. BackupScheduler.enqueueBackup(target)
    2. wait for completion
    3. emit metric (Prometheus)
    4. on failure 3 consecutive → alert via Telemetry

BackupService.monthlyRehearsal():
  1. RestoreVerifier.scheduleRehearsal(latestBackup)
  2. 격리 환경에서 복구 후 sanity-check
  3. RehearsalReport 발행 + AuditEventEmitter.emit('rehearsal_completed')
```

### 외부 시스템 결합
- 사내 백업 스토리지 (Infrastructure Design에서 결정)

---

## 7. 서비스가 의도적으로 *없는* 영역

본 단계에서는 도메인 결합도가 낮아 단일 컴포넌트만으로 충분한 영역에는 서비스를 두지 않음.

- **Visualization**: `ChartBuilder` 단일 컴포넌트만 사용. 사용자(JupyterExtensionsBundle)가 직접 호출.
- **PII Masking 자체**: `PiiMaskingFilter`는 `DataAccessService`의 흐름 안에서만 사용됨.
- **File Upload**: 분석가가 직접 `FileUploadHandler` 호출. 외부 의존 없음.

(필요해지면 Functional Design 단계에서 서비스로 승격 가능)

---

## 8. 횡단 관심사가 서비스에 미치는 영향

각 서비스는 **공통적으로** 다음을 보장:
- `SecurityKernel.authorize(...)` — 진입 직후 1회 (Defense in Depth, Q-AD-13=A)
- `Telemetry.trace.span(serviceName + '.' + method)` — 모든 호출 추적
- 모든 분기에서 `AuditEventEmitter.emit(...)` — 성공/실패 둘 다
- 도메인 오류는 `Result<T, DomainError>` 반환, 시스템 오류는 fail-closed 예외 → 전역 핸들러 → 일반화 메시지 + 상세 로그

---

## 9. 서비스 의존 그래프 (요약)

```text
AuthServiceOrchestrator → AuthService(comp) → SessionStore + RoleResolver + KeycloakAdapter
                       → AuditEventEmitter
DataAccessService → AuthService + ConnectionRegistry + CredentialVault
                  → ConnectorFactory → Rdbms/BigData Connectors
                  → PiiMaskingFilter ← PiiPolicyStore
                  → AuditEventEmitter
NotebookService → NotebookStore + ShareLinkManager + KernelManager
                → DataAccessService (셀이 SQL일 때)
                → AuditEventEmitter
                ⇢ (async outbox) AutoCommitOrchestrator → GitAdapter
AdminService → CredentialVault + ConnectionRegistry + PiiPolicyStore + RoleResolver
             → AuditEventEmitter
AuditService → AuditQueryApi + AuditWriter
             ← (consumer) outbox
BackupService → BackupScheduler + RestoreVerifier
             → Telemetry + AuditEventEmitter
```

**Acyclic 확인**: 위 그래프에 순환 없음. `DataAccessService`가 `AuthService`에 의존하지만 역방향 없음. 트랜잭션·outbox로 시간 비동기 처리는 화살표 `⇢`로 표시 (런타임 디커플링).
