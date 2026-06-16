# credential-unit — Functional Design

**모듈**: CredentialVault, VaultAdapter

## 1. 데이터 모델

### Postgres (메타데이터만, 평문 secret은 Vault)
```sql
CREATE TABLE credentials (
    credential_id UUID PRIMARY KEY,
    scope TEXT NOT NULL CHECK (scope IN ('shared', 'personal')),
    owner_user_id UUID,    -- scope='personal' 일 때만 NOT NULL
    name TEXT NOT NULL,
    vault_path TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rotated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    CONSTRAINT scope_owner_consistent CHECK (
        (scope = 'shared' AND owner_user_id IS NULL) OR
        (scope = 'personal' AND owner_user_id IS NOT NULL)
    ),
    UNIQUE (scope, owner_user_id, name)
);
CREATE INDEX idx_credentials_owner ON credentials(owner_user_id) WHERE deleted_at IS NULL;
```

### Vault paths
- 공용: `secret/data/dataplatform/shared/{credential_id}`
- 개인: `secret/data/dataplatform/personal/{owner_user_id}/{credential_id}`

## 2. 비즈니스 룰

### 2.1 register (Idempotent)
```text
register(scope, owner, name, secret):
  vault_path = build_path(scope, owner, credential_id)
  try:
    INSERT INTO credentials (...) RETURNING credential_id
  except UniqueViolation:
    return Err(CONFLICT)
  vault.write(vault_path, secret)
  audit emit credential_registered
  return Ok(credential_id)
```

### 2.2 rotate (State-Machine)
```text
rotate(id, new_secret):
  cred = SELECT ... WHERE credential_id = id AND deleted_at IS NULL
  if not cred: return Err(NOT_FOUND)
  vault.write(cred.vault_path, new_secret)  # 신규 secret이 즉시 활성
  UPDATE credentials SET rotated_at = NOW() WHERE credential_id = id
  audit emit credential_rotated
```

### 2.3 delete (Soft + Vault hard delete)
```text
delete(id):
  cred = ...
  UPDATE credentials SET deleted_at = NOW() WHERE credential_id = id
  vault.delete(cred.vault_path)             # Vault에서 완전 삭제
  audit emit credential_deleted
```

### 2.4 resolve (정책)
```text
resolve(id, requester):
  cred = ... WHERE credential_id = id AND deleted_at IS NULL
  if not cred: return Err(NOT_FOUND)
  if cred.scope == 'personal' AND cred.owner != requester:
    return Err(FORBIDDEN)
  if cred.scope == 'shared':
    # connection_grants로 사용 인가 확인
    if not auth_service.verify_connection_credential_access(requester, cred):
      return Err(FORBIDDEN)
  secret = vault.read(cred.vault_path)
  cache resolve in-process (TTL 60s, Secret brand)
  return Ok(Secret(secret))
```

### 2.5 사용 직전 소거
- `Secret` 객체는 사용 후 명시적 `wipe()` 호출 (in-place overwrite 가능 시) — Python에서는 GC 의존
- `resolve` 캐시는 weakref 보관 + TTL

## 3. PBT
| 함수 | 기법 | 검증 |
|---|---|---|
| register 두 번 | Idempotent | 같은 name+scope → 두 번째 호출은 Err(CONFLICT) 또는 같은 credential_id |
| 등록→회전→삭제 흐름 | State-Machine | resolve 결과 = 마지막 write 값 |
| resolve(personal, other_user) | Invariant | owner != requester → 항상 FORBIDDEN |

## 4. 외부 의존
Vault, Postgres, auth-unit (verify access)

## 5. Story 매핑
US-DS-01 (공용 자격증명 등록), US-DS-04 (개인 자격증명)
