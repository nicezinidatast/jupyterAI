# auth-unit — Functional Design

**모듈**: AuthService, SessionStore, RoleResolver, KeycloakAdapter, AuthServiceOrchestrator

---

## 1. 데이터 모델 (Postgres)

```sql
-- users (Keycloak에서 가져와 캐시)
CREATE TABLE users (
    user_id UUID PRIMARY KEY,           -- Keycloak subject claim
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- user_roles
CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('Admin','Analyst','Viewer','Auditor')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by UUID,
    PRIMARY KEY (user_id, role)
);
CREATE INDEX idx_user_roles_role ON user_roles(role);

-- sessions (TTL 관리는 Redis, Postgres는 검증 + 활성 세션 목록용)
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id),
    issued_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    invalidated_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ
);
CREATE INDEX idx_sessions_user_active ON sessions(user_id) WHERE invalidated_at IS NULL;
```

Redis: `sess:{session_id}` → JSON 직렬화 Session record, TTL = expires_at - now

## 2. 핵심 비즈니스 룰

### 2.1 활성 Admin ≥ 1 Invariant (US-AUTH-02)

```text
revokeRole(actor, target, role='Admin'):
  BEGIN TX
    count = SELECT count(*) FROM user_roles
            WHERE role='Admin'
              AND user_id <> target
              AND user_id IN (SELECT user_id FROM users WHERE is_active);
    IF count = 0:
      ROLLBACK → Err(CONFLICT, "must_keep_one_admin")
    DELETE FROM user_roles WHERE user_id=target AND role='Admin'
    audit emit
  COMMIT
```

### 2.2 세션 만료 & 작업 보호 (US-AUTH-03)
- 만료 즉시: Redis key TTL → 자동 소실. validate 호출 시 Err(EXPIRED)
- DB session row는 `invalidated_at = now()` 마킹 후 30일 보관 (감사 추적)
- 만료 알림: gateway가 401 응답 시 `WWW-Authenticate: Bearer error="invalid_token"` + 일반화 메시지

### 2.3 MFA (US-AUTH-04)
- Keycloak에 위임. `auth-unit` 측은 `claim.amr` 에 `["mfa"]` 포함 여부만 검증
- Admin 진입 endpoint마다 `require_mfa` 데코레이터 — MFA 없는 토큰 → Err(FORBIDDEN, "mfa_required")

### 2.4 비밀번호 정책 (US-AUTH-05)
- Keycloak Realm 정책에 위임 (8자+, HIBP 통합, argon2id 해시)
- `auth-unit`은 정책 설정 API만 노출 (Admin이 Keycloak 정책 동기화 가능)

### 2.5 verifyAccess (모든 유닛이 호출)

```text
verifyAccess(ctx, action, resource):
  IF !ctx.user_id: Err(UNAUTHORIZED)
  IF resource.kind == 'connection':
    SELECT 1 FROM connection_grants
    WHERE connection_id = resource.id
      AND (subject_user = ctx.user_id OR subject_role IN ctx.roles)
      AND action_allowed >= action
  IF resource.kind == 'audit':
    return 'Auditor' in ctx.roles OR 'Admin' in ctx.roles ? Ok(allow) : Err(FORBIDDEN)
  IF resource.kind == 'system' AND action='admin':
    return 'Admin' in ctx.roles
  ... (default deny)
```

## 3. PBT (3 적용)

| 함수 | 기법 | 검증 |
|---|---|---|
| `revokeRole` | Invariant | 임의 순서로 admin 추가/제거 → 항상 ≥ 1 활성 admin |
| `Session lifecycle` | State-Machine | issue → validate(active) → validate(expired) → invalidate 전이 |
| `verifyAccess(connection)` | Invariant | grants 없으면 항상 deny |

## 4. 외부 의존
- Keycloak (IdP), Postgres, Redis

## 5. Story 매핑
US-AUTH-01~05, US-DS-03(권한 검증), US-SEC-03(Auditor 인가)
