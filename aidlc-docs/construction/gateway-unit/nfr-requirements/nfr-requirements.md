# gateway-unit — NFR Requirements

| ID | 요구사항 | 매핑 |
|---|---|---|
| NFR-GW-PERF-01 | 게이트웨이 패스스루 오버헤드 | < 30ms (p95) |
| NFR-GW-PERF-02 | 동시 활성 연결 | ≥ 200 (NFR-PERF-03 50명 × 4 연결) |
| NFR-GW-SEC-01 (SECURITY-04) | 보안 헤더 5종 강제 | CSP/HSTS/XCTO/XFO/Referrer |
| NFR-GW-SEC-02 (SECURITY-01) | TLS 1.2+, 자체 서명 거절 | 사내 PKI |
| NFR-GW-SEC-03 (SECURITY-11) | Rate Limit IP/User | 위 FD §2.4 |
| NFR-GW-SEC-04 (SECURITY-07) | deny-by-default 라우팅 | 화이트리스트만 허용 |
| NFR-GW-SEC-05 (SECURITY-12) | JWT 서명 검증 (JWKS rotation 지원) | 캐시 5분 |
| NFR-GW-OBS-01 | 접근 로그 (액세스 로깅) | NFR-SEC-02 |
| NFR-GW-OBS-02 | `/healthz`, `/readyz` | NFR-OBS-04 |

## 기술 스택

| 항목 | 결정 |
|---|---|
| 언어 | Python 3.11+ |
| Web Framework | **FastAPI + uvicorn (asyncio)** |
| Reverse Proxy 측 | **Envoy 또는 nginx** 외부 종단(TLS) + uvicorn 백엔드. MVP는 단순화 위해 uvicorn 단독 + TLS 옵션 |
| JWT 검증 | `python-jose` 또는 `pyjwt` |
| Redis Client | `redis-py >= 5`, async |
| Rate Limit | shared-lib `SlidingWindowLimiter` |
| 컨테이너 베이스 | `python:3.11-slim` |
