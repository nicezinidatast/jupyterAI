# shared-lib — Infrastructure Design

**유닛**: `shared-lib`
**배포 단위**: **라이브러리 (컨테이너 없음)** — 다른 모든 유닛의 wheel 의존성

---

## 1. 배포 모델

- 빌드 산출물: Python wheel (`dataplatform_shared-0.x.y-py3-none-any.whl`)
- 게시 대상: **사내 PyPI 미러** (예: `https://pypi.internal/`)
- 다른 유닛은 `pyproject.toml`에 `dataplatform-shared = "^0.x"` 으로 의존

---

## 2. 버전 정책

- SemVer
- MVP 진입 시 `0.1.0`, 이후 호환 변경마다 minor bump
- breaking change는 명시적 release note + 모든 유닛 pyproject 업데이트 PR

---

## 3. 빌드 파이프라인 (GitLab CI)

```yaml
# units/shared-lib/.gitlab-ci.yml
shared-lib:
  stage: build
  image: python:3.11-slim
  before_script:
    - pip install --index-url ${INTERNAL_PYPI} uv
  script:
    - cd units/shared-lib
    - uv pip install --system -r requirements.lock
    - ruff check src tests
    - mypy --strict src
    - bandit -r src
    - safety check
    - pytest --cov=src --cov-fail-under=90
    - uv build
    - cyclonedx-py -o dist/sbom.json
  artifacts:
    paths: [units/shared-lib/dist/]
  rules:
    - changes: [units/shared-lib/**]
```

---

## 4. 환경 변수

- `INTERNAL_PYPI` (CI) — 사내 PyPI 미러 URL
- `LOG_LEVEL` (런타임, default `INFO`)
- `OTLP_ENDPOINT` (런타임, optional — 미설정 시 tracing 비활성)
- `PROM_ENABLED` (런타임, default `true`)

---

## 5. 외부 인프라 의존

- 사내 PyPI 미러 (필수)
- (런타임) Prometheus scrape target — `/metrics` endpoint, 호스팅은 각 유닛
- (런타임, Phase 2) OTLP collector — Tempo/Jaeger

---

## 6. 관측성 통합 (사용 측)

- 모든 유닛이 startup 시 `shared_lib.configure_logging()`, `configure_metrics()`, `configure_tracing(service_name=...)` 호출
- Telemetry 자체는 stateless — 각 프로세스 안에서 동작

---

## 7. 보안 고려

- 라이브러리는 시크릿을 직접 다루지 않음. `Secret` 타입만 *brand*로 제공
- SBOM이 매 빌드마다 산출됨 (SECURITY-10)
- 침해 비밀번호 차단 등 정책 검증 헬퍼는 별도 모듈 — Phase 2에서 도입 가능

---

## 8. 배포 단계

1. PR merge → CI build → wheel + SBOM 산출
2. CI가 사내 PyPI에 publish (tag push 시에만)
3. 다른 유닛의 `requirements.lock` 갱신 PR 자동 생성 (renovate 또는 수동)
