# gateway-unit — Infrastructure Design

## 1. 배포 단위

- **컨테이너 A** — `dataplatform/gateway:0.x`
- Docker Compose 서비스명: `gateway`
- 포트: `:443` (외부 HTTPS), `:9090` (내부 Prometheus scrape)

## 2. Dockerfile (요약)

```dockerfile
FROM python:3.11-slim AS base
WORKDIR /app
RUN useradd -r -u 10001 app
COPY --chown=app units/gateway-unit/dist/ ./
RUN pip install --index-url ${INTERNAL_PYPI} --no-deps gateway_unit-*.whl
USER app
EXPOSE 443
HEALTHCHECK --interval=30s --timeout=3s CMD curl -fk https://localhost/healthz || exit 1
ENTRYPOINT ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "443", "--ssl-keyfile", "/run/secrets/tls.key", "--ssl-certfile", "/run/secrets/tls.crt"]
```

## 3. Docker Compose (MVP, infra/ 유닛에 통합)

```yaml
gateway:
  image: dataplatform/gateway:0.1.0
  ports: ["443:443"]
  environment:
    REDIS_URL: redis://redis:6379/0
    KEYCLOAK_ISSUER: https://sso.internal/realms/dataplatform
    BACKEND_URL: http://backend:8000
    LOG_LEVEL: INFO
    OTLP_ENDPOINT: ""    # Phase 2
  volumes:
    - /etc/dataplatform/certs:/run/secrets:ro
  depends_on: [backend, redis]
  restart: unless-stopped
  deploy:
    resources:
      limits:
        cpus: "2.0"
        memory: 1Gi
```

## 4. 인증서

- 사내 PKI에서 발급한 와일드카드 또는 plat 도메인 인증서
- `/etc/dataplatform/certs/tls.{crt,key}`
- 갱신: certbot 또는 사내 PKI 자동화 → SIGHUP 핫리로드

## 5. 외부 결합

| 외부 | 용도 |
|---|---|
| Keycloak | OIDC issuer + JWKS endpoint |
| Redis | Rate Limit / OIDC state / JWKS 캐시(선택) |
| backend 컨테이너 B | 모든 /api/* passthrough |
| JupyterHub | /hub/*, /jupyter/* passthrough |

## 6. 네트워크 정책

- 외부 inbound: `:443` 만 노출
- 내부 outbound: Keycloak, Redis, backend, JupyterHub만 허용 (deny-by-default, SECURITY-07)
- `:9090` Prometheus scrape: 내부 모니터링 네트워크에서만

## 7. 관측성

- `/metrics` Prometheus scrape
- 구조화 로그 → stdout → Loki collector
- (Phase 2) OTLP → Tempo

## 8. 백업/HA

- gateway는 stateless. 백업 대상 아님.
- 다중 인스턴스 가능 (Phase 2 K8s에서 replica=2~3)

## 9. 보안 강화

- Read-only 파일시스템 (`/tmp` 만 tmpfs)
- non-root user (uid 10001)
- `cap_drop: ALL`
- 컨테이너 이미지 Trivy 스캔 0 critical/high (NFR-SEC-10)
