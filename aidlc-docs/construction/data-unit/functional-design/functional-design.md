# data-unit — Functional Design

**모듈**: ConnectionRegistry, ConnectorFactory, RdbmsConnector, BigDataSqlConnector, QueryExecutor, SchemaIntrospector, PiiPolicyStore, PiiMaskingFilter, FileUploadHandler, DataAccessService

---

## 1. 데이터 모델

```sql
-- connections
CREATE TABLE connections (
    connection_id UUID PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    engine TEXT NOT NULL CHECK (engine IN
        ('postgres','mysql','oracle','mssql','hive','impala','presto','trino')),
    host TEXT NOT NULL,
    port INT NOT NULL,
    database TEXT,
    credential_id UUID NOT NULL,    -- credential-unit
    options JSONB DEFAULT '{}',     -- {kerberos: {principal, keytab_vault_path}}
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT true
);

-- connection_grants (RBAC)
CREATE TABLE connection_grants (
    connection_id UUID NOT NULL REFERENCES connections(connection_id) ON DELETE CASCADE,
    subject_user_id UUID,
    subject_role TEXT,
    action TEXT NOT NULL CHECK (action IN ('read','execute','admin')),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    granted_by UUID,
    CHECK ((subject_user_id IS NULL) <> (subject_role IS NULL)),
    PRIMARY KEY (connection_id, COALESCE(subject_user_id::text, subject_role), action)
);

-- pii_patterns
CREATE TABLE pii_patterns (
    pattern_id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('name','rrn','phone','email','custom')),
    regex TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- column_policies (컬럼 단위 PII)
CREATE TABLE column_policies (
    connection_id UUID NOT NULL REFERENCES connections(connection_id) ON DELETE CASCADE,
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    policy TEXT NOT NULL CHECK (policy IN ('mask','allow','block')),
    set_by UUID,
    set_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (connection_id, table_name, column_name)
);

-- query_executions (히스토리, 백그라운드 잡 추적)
CREATE TABLE query_executions (
    query_handle UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    connection_id UUID NOT NULL,
    sql_hash TEXT NOT NULL,         -- payload 보안
    params_hash TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    rows_returned BIGINT,
    duration_ms INT,
    result_status TEXT,             -- 'success','failed','cancelled'
    is_background BOOLEAN NOT NULL DEFAULT false
);

-- file_uploads
CREATE TABLE file_uploads (
    file_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    filename TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    mime TEXT NOT NULL,
    storage_path TEXT NOT NULL,     -- minio://bucket/key 또는 nas:/path
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 2. 핵심 비즈니스 룰

### 2.1 register connection (US-DS-01·02)
- 사전 검증: engine + 옵션(Kerberos 등) 적절성 + 테스트 연결 1회
- 중복 name → Conflict
- credential_id는 credential-unit에 사전 등록되어 있어야 함

### 2.2 RBAC: list connections (US-DS-03)
```sql
-- 사용자가 볼 수 있는 connection만 SELECT
SELECT c.* FROM connections c
WHERE c.is_active
  AND EXISTS (
    SELECT 1 FROM connection_grants g
    WHERE g.connection_id = c.connection_id
      AND (g.subject_user_id = $user_id OR g.subject_role = ANY($user_roles))
      AND g.action IN ('read','execute','admin')
  );
```
- **Invariant (PBT)**: grant 없는 사용자에게는 connection 자체가 노출 안 됨

### 2.3 QueryExecutor (US-NB-02, 시나리오 A)
```text
run(ctx, conn_id, ParamQuery, opts):
  1. AuthService.verifyAccess(ctx, 'execute', connection:conn_id)
  2. conn_spec = ConnectionRegistry.get(conn_id, ctx)
  3. cred = CredentialVault.resolve(conn_spec.credential_id, ctx)
  4. connector = ConnectorFactory.create(conn_spec, cred)
  5. handle = generate_uuid()
  6. INSERT INTO query_executions(handle, user_id, conn_id, sql_hash, ...)
  7. start async exec with deadline = opts.timeout or 5s
  8. on complete:
     UPDATE query_executions SET ended_at, rows_returned, duration_ms, result_status
     audit emit query_executed
  9. on timeout > 5s:
     return promoteToBackground(handle) — 잡 큐에 enqueue
     return Ok(handle) — 클라이언트는 status polling
```

### 2.4 ParamQuery 강제 (SECURITY-05)
- 입력 받을 때 `sql: str` + `params: dict` 별도. SQL에 `:placeholder` 만 허용.
- ruff 사용자 룰: `sql + user_input` 또는 `f"... {user_input} ..."` 패턴 검출

### 2.5 결과 페이지네이션
- 100 rows/page 기본, 옵션으로 50~500
- ResultStream → in-memory 페이지 캐시 (TTL 15분, ≤ 1M rows)
- 1억 행 초과: Err(VALIDATION, "result_too_large")

### 2.6 백그라운드 잡 (US-NB-06)
- Redis Stream `jobs:query` 에 enqueue
- worker가 polling, 결과는 `query_executions.result_status`로 표시
- 결과 데이터는 ResultStream 캐시 (Redis or 디스크 임시 파일)
- 잡 누적 한도 (예: 사용자당 10개) 초과 시 큐잉 + 안내

### 2.7 PiiMaskingFilter (US-SEC-02)
```text
mask(row, ctx):
  for col, value in row.items():
    policy = lookup(connection_id, table, col)
    if policy == 'block': value = None
    elif policy == 'allow': pass
    elif policy == 'mask':
      kind = column_kind or detect_kind(value, pii_patterns)
      value = apply_mask(value, kind)
    elif policy is None:
      # 표준 PII 정규식 자동 매칭
      if matches_pattern(value):
        value = apply_mask(value, kind)
  return row
```

마스킹 형식:
- 이름: `홍*동` (2자 이상 시 가운데 마스킹)
- 주민번호: `123456-*******`
- 전화: `010-****-1234`
- 이메일: `a***@example.com`

### 2.8 PII 정규식 등록 (US-ADM-03)
- 정규식 사전 검증: 길이 ≤ 256자, 중첩 그룹 ≤ 5, 백트래킹 위험 패턴(`.*.*`, `(.*)*` 등) 차단
- `regex.compile(pattern, flags=re.DOTALL)` + timeout 100ms 보호

### 2.9 SchemaIntrospector
- lazy load: 첫 호출 시 DB 트리 루트만, 자식은 expand 시 fetch
- 1000+ 객체 시 페이지네이션
- RBAC 적용 (column_policy='block'인 컬럼은 트리에 노출 X)

### 2.10 FileUploadHandler
- 클라이언트에서 사이즈 사전 거절 (`Content-Length` > 1GB → 클라이언트 측에서 거절)
- 서버는 streaming 수신, 총 사이즈 초과 시 즉시 중단 + 임시 파일 삭제
- 포맷 검증: 확장자 + magic bytes 둘 다
- 저장: NAS 마운트 경로 또는 MinIO bucket (`s3://uploads/{user_id}/{file_id}`)
- 공유 스토리지 접근: 사전 등록된 마운트 경로 화이트리스트, sandbox 외 경로 거절

## 3. PBT (5 적용)

| 함수 | 기법 | 검증 |
|---|---|---|
| `ConnectionRegistry.register` | Idempotent | 동일 name 두 번 → 두 번째 Err(CONFLICT) |
| `ConnectionRegistry.list(user_without_grant)` | Invariant | 권한 없는 사용자 결과에 그 connection 없음 |
| `PiiMaskingFilter.mask` | Oracle + Idempotent | mask(mask(x)) == mask(x), 정규식 매칭과 일치 |
| `PiiPolicyStore.add_pattern` | Domain-Generator | Hypothesis 생성기로 PII 후보 문자열 → 마스킹 결과가 패턴 매치 |
| `FileUploadHandler.upload (CSV)` | Round-trip | CSV upload → parquet 변환 → CSV 변환 결과 동일 (스키마+데이터) |

## 4. 외부 의존
- credential-unit (resolve)
- auth-unit (verify)
- audit-unit (emit)
- 사내 DB 다수, NAS/MinIO
- Redis Streams (job queue)

## 5. Story 매핑
US-DS-01~07, US-NB-02, US-NB-04(SchemaIntrospect), US-NB-06, US-SEC-02, US-VIS-02(부분 — PII 마스킹)
