# credential-unit — Infrastructure Design

## 배포
- backend 컨테이너 B에 모듈로 동거
- Vault Adapter는 HTTP 호출, 별도 네트워크 정책

## 환경 변수
- `VAULT_ADDR` (https://vault.internal:8200)
- `VAULT_ROLE_ID`, `VAULT_SECRET_ID` (AppRole, Docker secrets로 마운트)
- `VAULT_NAMESPACE` (선택, Vault Enterprise)
- `DATABASE_URL`
- `RESOLVE_CACHE_TTL_SECONDS=60`

## DB 마이그레이션
- Alembic — credentials 테이블 + 인덱스

## Vault 정책 (미리 사내 운영팀과 협의 — `infra/vault-policies/`)
```hcl
path "secret/data/dataplatform/shared/*" {
  capabilities = ["create", "read", "update", "delete"]
}
path "secret/data/dataplatform/personal/{{identity.entity.aliases.auth_approle_<id>.name}}/*" {
  capabilities = ["create", "read", "update", "delete"]
}
```

> 위 정책은 **AppRole 한 개로 모든 personal 자격증명 접근**하는 형태. 더 엄격하게 가려면 사용자별 Vault entity 발급 (Phase 2 검토).

## 외부 의존
- HashiCorp Vault (필수)
- Postgres

## 보안 강화
- AppRole secret_id는 Docker Compose secrets (`/run/secrets/vault_secret_id`)
- Vault 토큰은 메모리에만, env 노출 X
- 토큰 lease 만료 50% 시점에 renewal

## 백업
- Vault 자체는 사내 운영팀이 백업
- `credentials` 테이블은 BackupService 일 1회 (메타데이터만, secret 본문은 Vault에 있음)
