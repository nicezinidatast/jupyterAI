# gateway-unit — NFR Design

## 1. FastAPI 미들웨어 스택 (순서 중요)

```
1. HTTPSRedirect → TLS 강제
2. SecurityHeaders → CSP/HSTS/...
3. CORS → 화이트리스트만
4. RateLimiter (IP + User)
5. RequestId (corr_id 주입)
6. AccessLog (NFR-SEC-02)
7. JWTAuth (verifyAccessToken)
8. Tracing (OTel)
9. Routes
10. ExceptionHandler (fail-closed, 일반화 메시지)
```

## 2. 보안 헤더 (SECURITY-04)

```python
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:",
    # CSP는 JupyterLab의 inline script 필요성 때문에 일부 완화. Phase 2에 nonce 도입 검토.
}
```

## 3. Rate Limit

- Redis sliding window (`shared_lib.SlidingWindowLimiter`)
- 키: `rl:ip:{ip}`, `rl:user:{uid}`, `rl:anon:{ip}:login`
- 응답: 429 + `Retry-After: <seconds>` + `RateLimit-*` 표준 헤더

## 4. JWT 검증

- JWKS 캐시: in-process dict, 5분 TTL, 백그라운드 refresh
- `kid` 미일치 시 강제 refresh 1회 후 거절
- 알고리즘 화이트리스트: `RS256`, `ES256` (none, HS* 거절)

## 5. OIDC State 저장

- Redis key: `oidc:state:{state_id}`, TTL 600s
- 1회 사용 후 삭제 (replay 방지)

## 6. Routing 화이트리스트 (SECURITY-07 deny-by-default)

```
/                       → AdminConsole SPA (정적)
/auditor                → AuditorConsole SPA (정적, RBAC=Auditor)
/api/auth/*             → auth-unit
/api/connections/*      → admin-unit / data-unit
/api/queries/*          → data-unit
/api/notebooks/*        → notebook-unit
/api/files/*            → data-unit
/api/share/*            → notebook-unit
/api/audit/*            → audit-unit (RBAC=Auditor/Admin)
/api/admin/*            → admin-unit
/hub/*                  → JupyterHub (passthrough)
/jupyter/*              → JupyterHub spawner outputs
/healthz, /readyz       → public
/metrics                → 내부 Prometheus 만 (네트워크 정책 차단)

전부 외 → 404 (deny-by-default)
```

## 7. 예외 처리 (SECURITY-15)

```python
@app.exception_handler(DomainException)
async def domain_exc(req, exc): return JSONResponse({"error": exc.code}, status_code=exc.http_status)

@app.exception_handler(Exception)
async def unknown_exc(req, exc):
    logger.error("unhandled", exc_info=True)
    return JSONResponse({"error": "internal_error"}, status_code=500)
```

## 8. 메트릭

- `gateway_requests_total{route,code}`
- `gateway_request_latency_seconds{route}`
- `gateway_rate_limited_total{scope}`
- `gateway_oidc_callbacks_total{result}`
