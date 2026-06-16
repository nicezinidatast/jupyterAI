# Build Instructions — 내부망 데이터 분석 플랫폼

## Prerequisites

| 항목 | 버전 |
|---|---|
| OS | Linux (Ubuntu 22.04 LTS 또는 RHEL 8/9) |
| Python | 3.11+ |
| Node.js | 20 LTS |
| pnpm | 9.x |
| Docker | 24+ |
| Docker Compose | v2 |
| uv (또는 Poetry) | 0.5+ |
| GitLab CI runner | shell/docker executor |
| 메모리 | 16GB+ (개발), 32GB+ (CI) |
| 디스크 | 80GB+ |

## 사내 미러 설정 (Closed Network — NFR-DEPLOY-03)

```bash
# PyPI
export PIP_INDEX_URL=https://pypi.internal.example.com/simple/
export UV_INDEX_URL=$PIP_INDEX_URL

# NPM
echo "registry=https://npm.internal.example.com" > ~/.npmrc

# Docker images
docker login harbor.internal.example.com
```

## 환경 변수 (개발)

```bash
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dataplatform
export REDIS_URL=redis://localhost:6379/0
export KEYCLOAK_ISSUER=https://sso.internal/realms/dataplatform
export VAULT_ADDR=https://vault.internal:8200
export LOG_LEVEL=DEBUG
```

## Build Steps

### 1. 의존성 미러 검증
```bash
pip install --dry-run dataplatform-shared
pnpm install --dry-run
```

### 2. shared-lib 먼저 빌드
```bash
cd units/shared-lib
uv sync
uv build
uv publish --repository internal-pypi
```

### 3. 백엔드 유닛들 (병렬 가능 — Stage 2~6)
```bash
# Stage 2 (병렬): gateway, auth, audit, credential
for unit in gateway-unit auth-unit audit-unit credential-unit; do
  (cd units/$unit && uv sync && uv build) &
done
wait

# Stage 3: data-unit
cd units/data-unit && uv sync && uv build

# Stage 4: notebook-unit
cd units/notebook-unit && uv sync && uv build

# Stage 5: admin-unit backend
cd units/admin-unit/backend && uv sync && uv build
```

### 4. SPA 빌드 (admin-unit)
```bash
cd units/admin-unit/admin-console
pnpm install
pnpm typecheck
pnpm build   # → dist/

cd ../auditor-console
pnpm install && pnpm typecheck && pnpm build
```

### 5. JupyterLab Extensions 빌드
```bash
cd units/admin-unit/jupyter-extensions
pnpm install
pnpm build
jupyter labextension build .
# wheel 산출물: dataplatform_jupyter_ext-*.whl
```

### 6. Docker 이미지 빌드
```bash
# Gateway (컨테이너 A)
docker build -t harbor.internal/dataplatform/gateway:0.1.0 -f units/gateway-unit/Dockerfile .

# Backend (컨테이너 B) — 여러 유닛 통합
docker build -t harbor.internal/dataplatform/backend:0.1.0 -f infra/docker/backend.Dockerfile .

# JupyterHub (컨테이너 C)
docker build -t harbor.internal/dataplatform/jupyterhub:0.1.0 -f infra/jupyterhub/Dockerfile infra/jupyterhub/

# User notebook image
docker build -t harbor.internal/dataplatform/notebook-user:0.1.0 -f infra/jupyterhub/user-image/Dockerfile .

# SPA static (컨테이너 D)
docker build -t harbor.internal/dataplatform/admin-spa:0.1.0 -f units/admin-unit/Dockerfile.spa units/admin-unit/
```

### 7. 빌드 검증
```bash
# 컨테이너 사이즈 검증 (< 1GB 권장)
docker images | grep dataplatform

# SBOM 생성
docker sbom harbor.internal/dataplatform/backend:0.1.0 > infra/sbom/backend.json

# Trivy 스캔
trivy image --severity HIGH,CRITICAL --exit-code 1 harbor.internal/dataplatform/backend:0.1.0
```

## Build Artifacts

| 산출물 | 위치 |
|---|---|
| `dataplatform-shared-0.1.0-py3-none-any.whl` | `units/shared-lib/dist/` |
| 각 유닛 wheel | `units/*/dist/*.whl` |
| admin SPA | `units/admin-unit/admin-console/dist/` |
| auditor SPA | `units/admin-unit/auditor-console/dist/` |
| JupyterLab Ext wheel | `units/admin-unit/jupyter-extensions/dist/*.whl` |
| Docker 이미지 5개 | Harbor `harbor.internal/dataplatform/*` |
| SBOM | `infra/sbom/*.json` |
| Trivy report | `infra/trivy/*.json` |

## 공통 경고 (수용 가능)
- `uv` 캐시 클린 권고 메시지
- TypeScript strict 모드에서 일부 third-party @types/* 경고

## Troubleshooting

### "package not found" — PyPI 미러
- `pip config list` 로 index-url 확인
- 사내 미러에 해당 패키지·버전 미러링 요청

### Trivy critical CVE 발견
- 베이스 이미지 업그레이드 (python:3.11-slim → 최신 patch)
- 또는 임시 무시: 해당 CVE 분석 + `.trivyignore` 등록 (요청 시 보안팀 승인 필요)

### JupyterLab Extension 빌드 실패
- Node 버전 확인 (>= 20)
- `jupyter-labextension build` 시 메모리 부족 → `NODE_OPTIONS=--max-old-space-size=4096`
