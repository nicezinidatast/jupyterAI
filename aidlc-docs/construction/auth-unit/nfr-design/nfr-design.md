# auth-unit — NFR Design

## 1. verifyAccess 성능

- Redis 캐시: `verify:{user_id}:{resource_hash}:{action}` → bool, TTL 60초
- 캐시 invalidation: role 변경 시 `verify:{user_id}:*` 패턴 삭제
- 캐시 miss 시 Postgres 조회 (인덱스 보장)
- 최종: p95 < 5ms (캐시 적중) / < 30ms (DB)

## 2. SQLAlchemy 모델 (요약)

```python
class User(Base):
    __tablename__ = "users"
    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    roles: Mapped[list["UserRole"]] = relationship(back_populates="user")

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    role: Mapped[str] = mapped_column(primary_key=True)
    user: Mapped["User"] = relationship(back_populates="roles")
```

## 3. Active Admin Invariant 강제

```python
async def revoke_admin(session: AsyncSession, actor: UserContext, target: UUID) -> Result[None, DomainError]:
    async with session.begin():
        count = await session.scalar(
            select(func.count())
            .where(UserRole.role == 'Admin', UserRole.user_id != target)
            .join(User, User.user_id == UserRole.user_id)
            .where(User.is_active == True)
        )
        if count == 0:
            return Err(DomainError.CONFLICT)
        await session.execute(delete(UserRole).where(
            UserRole.user_id == target, UserRole.role == 'Admin'))
        # 같은 트랜잭션에 outbox row insert
        await emit_audit(session, "role_revoked", actor.user_id, str(target), {"role": "Admin"})
    return Ok(None)
```

## 4. 세션 라이프사이클

```text
issue(user_id, claims):
  session_id = uuid4()
  expires_at = now + 8h (config)
  INSERT INTO sessions(...)
  SET sess:{session_id} = JSON.dumps(session) EX <ttl>
  return SessionCookie

validate(token):
  payload = verify_jwt(token)
  session = GET sess:{payload.sid}
  if not session: return Err(EXPIRED)
  if session.invalidated_at: return Err(EXPIRED)
  update last_seen_at (async batch)
  return Ok(Session)

invalidate(session_id):
  UPDATE sessions SET invalidated_at = NOW() WHERE session_id = ?
  DEL sess:{session_id}
```

## 5. Keycloak Adapter

- httpx async client, connection pool
- JWKS 캐시는 gateway-unit이 보유 (중복 방지). auth-unit은 token introspection만 보조 호출.
- `KeycloakAdapter.exchangeAuthCode` — `/protocol/openid-connect/token`
- Circuit Breaker (실패율 50% 이상 30초간 차단) — `tenacity` 또는 직접 구현

## 6. Outbox 발행

- shared-lib `emit_audit(session, ...)`이 `audit_outbox` 테이블에 같은 트랜잭션 row insert
- audit-unit consumer가 5초 주기 폴링 + Redis Streams 알림으로 즉시 처리 트리거

## 7. 메트릭

```
auth_login_attempts_total{result}
auth_login_latency_seconds
auth_role_changes_total{role,op}
auth_active_sessions     (gauge, 주기 측정)
auth_verify_cache_hits_total
auth_verify_cache_miss_total
```

## 8. 에러 매핑 (HTTP)

| DomainError | HTTP |
|---|---|
| UNAUTHORIZED | 401 |
| FORBIDDEN | 403 |
| CONFLICT (must_keep_one_admin) | 409 |
| VALIDATION | 422 |
| EXPIRED | 401 + `WWW-Authenticate: error="invalid_token"` |
