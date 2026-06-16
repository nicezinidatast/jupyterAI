# credential-unit — NFR Requirements

| ID | 요구사항 |
|---|---|
| NFR-CR-PERF-01 | resolve (cache hit) | < 1ms |
| NFR-CR-PERF-02 | resolve (cache miss → Vault) | < 50ms |
| NFR-CR-SEC-01 (SECURITY-01) | secret at-rest 암호화 | Vault에 위임 |
| NFR-CR-SEC-02 | 평문이 로그·메모리에 남지 않음 | `Secret` brand + 사용 후 GC |
| NFR-CR-SEC-03 | 자격증명 사용 직전에만 resolve | TTL 60s 캐시 |
| NFR-CR-SEC-04 | API 응답에 secret 자체 노출 금지 | `vault_path` 만 메타로 노출 |
| NFR-CR-SEC-05 | 타인 자격증명 조회 시도 → 403 | PBT 강제 |
| NFR-CR-AUDIT-01 | 등록·회전·삭제·resolve 모두 감사 | shared-lib emitter |
| NFR-CR-OBS-01 | 메트릭: resolve hits/misses, vault errors | Prometheus |

## 기술 스택
- FastAPI
- SQLAlchemy 2 + asyncpg
- **HashiCorp Vault** (사내) 또는 동등 시크릿 매니저
- Vault client: `hvac` (sync) 또는 `requests + httpx` 자체 wrapper
- (Phase 2) Vault Agent sidecar 검토
