# Integration Test Execution — 내부망 데이터 분석 플랫폼

## 1. 환경 셋업

```bash
docker compose -f infra/docker-compose/integration.yml up -d
# 포함:
# - postgres:16
# - redis:7
# - vault:1.16 (dev mode)
# - keycloak:24 (사전 seed: realm + 테스트 사용자 5명, 역할 4종)
# - gitea:1.21 (사전 seed: 테스트 사용자 + 빈 저장소)
# - minio:latest (사전 seed: bucket)
# - dataplatform/gateway, dataplatform/backend (이미 빌드된 0.1.0 사용)
# - dataplatform/jupyterhub
```

## 2. 통합 테스트 시나리오

### IT-001: End-to-End SQL Execution (US-NB-02 + 시나리오 A)
```bash
pytest tests/integration/test_sql_e2e.py -v
```
- 분석가 로그인 (Keycloak)
- 등록된 Postgres 커넥션 선택
- 쿼리 실행 → 결과 페이지 1
- PII 컬럼이 마스킹된 상태로 응답되는지 검증
- 감사 로그에 `query_executed` 이벤트 적재 확인

### IT-002: Notebook Save → Git Commit (US-SHARE-01)
```bash
pytest tests/integration/test_notebook_git.py -v
```
- 노트북 저장 → `git_commit_outbox` 적재
- consumer가 Gitea로 commit & push
- `notebook_versions.git_commit_sha` 채워짐 확인
- Gitea API로 실제 commit 존재 확인

### IT-003: 권한 거부 흐름 (US-DS-03, US-SHARE-03)
- grant 없는 사용자가 connection 조회 → 목록에서 누락
- 권한 부족 share link 접근 → 403
- 감사에 `access_denied` 기록

### IT-004: Audit Outbox Invariant (US-SEC-01)
- N개 작업 발행 → audit_log에 N개 row 도착 (timeout 30초)
- 큐 깊이 메트릭 0으로 수렴

### IT-005: Credential Lifecycle (US-DS-04)
- register → rotate → delete → resolve(deleted) → NOT_FOUND
- 다른 사용자가 resolve 시도 → 403 (PBT 통합 시나리오)

### IT-006: Backup → Restore Rehearsal (US-ADM-05)
```bash
pytest tests/integration/test_backup_restore.py -v --timeout=600
```
- BackupService 트리거
- backup row state=success
- restore rehearsal 격리 env에서 복구 검증

### IT-007: 50명 동시 활성 (NFR-PERF-03)
- Locust 50 user 시뮬레이션 5분
- 평균 셀 실행 큐 대기 < 3초 (NFR-PERF-02)
- p95 SQL 응답 < 5초 (단순 쿼리)

### IT-008: Defense-in-Depth Bypass 시도
- gateway 우회 시도 (직접 backend 호출) → 차단 (network policy)
- 만료 토큰으로 API → 401
- 다른 사용자 토큰으로 share link → 403

### IT-009: PII 마스킹 우회 시도
- mask=true 컬럼을 SELECT 후 결과 검증 → 원본 PII 패턴이 응답에 없어야 함

### IT-010: JupyterHub Spawner
- 5명 동시 로그인 → 각자 컨테이너 spawn 5초 내
- 30분 idle 후 자동 culling

## 3. 실행

```bash
pytest tests/integration -v --maxfail=1 --timeout=300 \
       --junitxml=integration-results.xml
```

## 4. 기대값
- 10/10 시나리오 통과
- 어떤 컨테이너도 메모리 OOM 발생 안 함
- 모든 시나리오 끝나면 audit_log 비어있지 않음, outbox 깊이 0

## 5. CI 통합

```yaml
integration:
  stage: integration
  image: docker:24
  services: [docker:24-dind]
  before_script:
    - docker compose -f infra/docker-compose/integration.yml up -d
    - sleep 30
  script:
    - pip install -r infra/test-requirements.txt
    - pytest tests/integration -v --junitxml=junit.xml
  after_script:
    - docker compose logs > integration-logs.txt
    - docker compose down -v
  artifacts:
    when: always
    paths: [integration-logs.txt]
    reports:
      junit: junit.xml
```
