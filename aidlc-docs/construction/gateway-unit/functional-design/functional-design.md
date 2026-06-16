# gateway-unit — Functional Design

**유닛**: `gateway-unit` (Reverse Proxy + OIDC + SecurityKernel host)
**모듈**: ApiGateway, OidcCallbackHandler, SecurityKernel(SL-1 호스팅)

---

## 1. 데이터 모델

```python
# State held in process memory (Redis backed for replicas)

class JwksKey(TypedDict):
    kid: str
    alg: str             # 'RS256' etc.
    public_key_pem: str
    not_after: datetime  # rotation hint

class OidcStateRecord(TypedDict):
    state: str           # random base64
    nonce: str
    return_to: str       # post-login redirect target
    issued_at: datetime
    expires_at: datetime # ≤ 10분
```

---

## 2. 핵심 비즈니스 룰

### 2.1 OIDC Callback (US-AUTH-01)

```text
handleCallback(code, state):
  1. state record load (Redis), 없거나 만료 → Err(VALIDATION) + 감사
  2. nonce 검증
  3. KeycloakAdapter.exchangeAuthCode(code, redirect_uri)
     ↳ 실패 → 일반화된 메시지 ('로그인 실패') + 상세는 감사에만
  4. id_token 서명 검증 (JWKS 캐시, 5분 TTL)
  5. SessionStore.issue(userId, claims)
  6. AuditEventEmitter.emit(login, success)
  7. 302 redirect to state.return_to + Set-Cookie
```

### 2.2 Token Validation (모든 API 진입)

```text
verifyAccessToken(headers):
  1. Authorization Bearer 추출, 없으면 Err(UNAUTHORIZED)
  2. JWKS로 서명 검증
  3. exp / nbf 검증
  4. SessionStore.validate(sessionId from sid claim) — Expired → Err(EXPIRED)
  5. RoleResolver.getRoles(userId)
  6. Ok(UserContext)
```

### 2.3 Authorize (Defense in Depth)

```text
authorize(ctx, action, resource):
  1. role check (Admin/Analyst/Viewer/Auditor → action policy)
  2. 리소스별 ACL (예: connection access list, notebook share permission)
  3. fail-closed: 정책 미정의 시 deny + 감사 발행
```

### 2.4 Rate Limiting

- IP 단위: 분당 200 req
- 사용자 단위: 분당 300 req
- 미인증 경로(/login, /callback): IP 단위만, 분당 60
- 초과 시: 429 + `Retry-After` 헤더

---

## 3. 외부 의존

- Keycloak (OIDC) — `auth-unit` 의 `KeycloakAdapter` 사용
- Redis (Rate Limit 카운터, OIDC state, JWKS 캐시)
- 메타 DB (세션 검증은 `auth-unit` 의 `SessionStore` 호출)

---

## 4. PBT 적용

| 함수 | PBT 기법 | 검증 |
|---|---|---|
| `authorize()` | Invariant | 권한 없는 사용자 → 항상 deny (어떤 입력에도) |
| `verifyAccessToken()` | State-Machine | 미인증 → 인증 → 만료 → 미인증 전이의 일관성 |
| `RateLimiter.check()` | Invariant | window 내 N+1번째 요청은 항상 거절 |

---

## 5. 비기능 룰 (요약, 상세는 NFR-D)

- TLS 1.2+ 종단
- 보안 헤더 5종 강제 (CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy)
- 일반화 에러 메시지 (스택 trace 노출 금지)
