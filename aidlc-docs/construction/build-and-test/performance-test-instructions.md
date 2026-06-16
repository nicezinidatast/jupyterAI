# Performance Test Execution — 내부망 데이터 분석 플랫폼

## 1. 도구
- **Locust** (Python) — 시나리오 기반 부하
- **k6** (선택, JS) — 더 가벼운 부하 패턴

## 2. 부하 시나리오 (NFR-PERF-01~05)

### PT-001: 50명 동시 활성 (NFR-PERF-03)
```bash
locust -f tests/performance/locustfile_concurrent_users.py \
       --headless -u 50 -r 5 -t 5m \
       --html=perf-report.html \
       --host=https://gateway.test.internal
```

**시나리오 분포**:
- 60% — SQL 쿼리 실행 (3가지 쿼리 random)
- 20% — 노트북 저장 + 자동 커밋
- 10% — 스키마 트리 탐색
- 5% — 파일 업로드 (10MB)
- 5% — 차트 빌드

**기대값**:
- p50 응답 시간:
  - SQL 단순 쿼리 < 1s
  - 노트북 저장 < 500ms
  - 스키마 탐색 < 1s
- p95:
  - SQL < 5s (그 이상은 백그라운드)
  - 노트북 저장 < 2s
- 셀 실행 큐 평균 대기 < 3s (NFR-PERF-02)
- 에러율 < 1%

### PT-002: 백그라운드 잡 처리량 (NFR-PERF-01)
```bash
locust -f tests/performance/locustfile_long_queries.py -u 30 -r 3 -t 10m
```
- 모든 쿼리가 5초 이상 → 백그라운드 승격
- jobs queue depth < 100 유지

### PT-003: 파일 업로드 부하 (NFR-PERF-04)
- 50MB / 100MB / 500MB / 1GB 4단계
- 1GB는 클라이언트에서 거절 시뮬레이션 + 실제 시도 모두 검증
- 10명 동시 100MB 업로드 → 모두 성공

### PT-004: 큰 결과 거절 (NFR-PERF-05)
- 1억 행 SELECT 시뮬레이션 → 거절 응답 < 1s 내
- 잘못된 LIMIT 미지정 쿼리 안전 거절

### PT-005: 감사 outbox 부하 (NFR-AD-PERF-02)
- 1초당 1000 events 발행 5분
- audit_log row 수 = 발행 수 (유실 0)
- consumer lag < 10s

### PT-006: Vault 응답성 (NFR-CR-PERF-02)
- 1000 resolve 호출, 캐시 적중률 95%+
- p95 < 50ms

## 3. 리소스 측정
- backend CPU < 70% sustained
- backend memory < 4GB
- Postgres connections < 80% of max (default 100, 50명 가정)

## 4. 보고서
- Locust HTML 리포트
- Grafana 대시보드 캡처 (CPU/mem/req-rate)
- 결론: 모든 NFR-PERF 충족 여부

## 5. 회귀 감지
- CI에 `--exit-code-on-error 1` + threshold (예: p95 > 6초 fail)
- 매 릴리스마다 perf baseline 갱신

## 6. CI 통합

```yaml
performance:
  stage: performance
  image: locustio/locust:2.27
  services:
    - name: ${REGISTRY}/dataplatform/backend:${CI_COMMIT_SHA}
      alias: backend
  before_script:
    - apk add curl
  script:
    - locust -f tests/performance/locustfile_concurrent_users.py \
             --headless -u 50 -r 5 -t 5m --csv=perf
  artifacts:
    paths: [perf_*.csv]
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"  # 야간 수행
```
