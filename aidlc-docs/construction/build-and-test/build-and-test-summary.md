# Build and Test — Summary

**작성일**: 2026-05-21
**스코프**: 7 유닛 (shared-lib + 6 backend 유닛) + 3 SPA + 인프라

---

## 1. 검증 매트릭스

| 검증 영역 | 도구 | 위치 | 기대 결과 |
|---|---|---|---|
| Lint | ruff, mypy | 각 unit CI | 0 error |
| Security scan (정적) | bandit, safety | 각 unit CI | 0 high/critical |
| Type check | mypy --strict | 각 unit CI | 0 error |
| Frontend type/lint | tsc, eslint | admin/auditor consoles | 0 error |
| Unit test | pytest, vitest | 각 unit | coverage 표 충족, 0 fail |
| PBT | Hypothesis | 모든 PBT 적용 스토리 | 모두 통과 |
| Container scan | Trivy | infra/trivy/ | 0 high/critical |
| Dependency SBOM | cyclonedx-py, npm sbom | infra/sbom/ | 모든 유닛 산출 |
| Integration | pytest (testcontainers) | tests/integration | 10/10 시나리오 통과 |
| Performance | Locust | tests/performance | NFR-PERF-01~05 충족 |
| E2E UI | Playwright | units/admin-unit/*/e2e | 핵심 흐름 통과 |
| Security regression | bandit, custom rules, IT-009 | CI + integration | 우회 사례 0 |

---

## 2. 보안 베이스라인 15 통과 매트릭스

| Rule | 어디서 검증 |
|---|---|
| SECURITY-01 (at-rest+TLS) | IT-001 (TLS), credential-unit unit test (Vault), backup encryption (admin-unit infra test) |
| SECURITY-02 (액세스 로깅) | gateway-unit access log 검증, Grafana 대시보드 |
| SECURITY-03 (구조화 로깅) | shared-lib test, IT-006 (Loki ingestion) |
| SECURITY-04 (HTTP 헤더) | gateway-unit `test_security_headers.py` |
| SECURITY-05 (입력+파라미터화) | data-unit `test_param_query_safety.py`, IT-009 |
| SECURITY-06 (최소 권한) | data-unit RBAC PBT, auth-unit verifyAccess PBT |
| SECURITY-07 (deny-by-default 네트워크) | infra docker-compose network policy 검증 |
| SECURITY-08 (애플리케이션 인가) | gateway authorize PBT + 도메인 unit tests |
| SECURITY-09 (보안 하드닝) | IT-008 (Bypass), unit `test_oidc_callback.py` 일반화 에러 |
| SECURITY-10 (의존성/SBOM) | CI 모든 유닛 cyclonedx + Trivy |
| SECURITY-11 (Rate Limit + 모듈화) | gateway `test_rate_limit.py` PBT, IT-008 |
| SECURITY-12 (인증 정책) | auth-unit Keycloak Realm 검증, MFA require test |
| SECURITY-13 (무결성) | pickle ban ruff rule, data file format magic-bytes test |
| SECURITY-14 (보안 알림+append-only+1년) | audit-unit `test_worm_trigger.py`, retention job test |
| SECURITY-15 (fail-closed 예외) | gateway global exception test, audit AUDIT_FAIL_CLOSED test |

**모든 15 rules**: 자동화 검증 항목 존재 ✓

---

## 3. PBT 13 적용 검증 매트릭스

| Story | 적용 위치 | 테스트 파일 |
|---|---|---|
| US-AUTH-01 (State-Machine) | `units/auth-unit/tests/test_session_lifecycle.py` |
| US-AUTH-02 (Invariant Admin≥1) | `units/auth-unit/tests/test_role_invariant.py` |
| US-AUTH-05 (Domain-Generator pwd) | (Keycloak 위임, 정책 동기화 test에 포함) |
| US-DS-01 (Idempotent register) | `units/data-unit/tests/test_connection_registry.py` |
| US-DS-03 (RBAC Invariant) | 동상 |
| US-DS-04 (Idempotent+State-Machine cred) | `units/credential-unit/tests/test_lifecycle_state_machine.py` |
| US-DS-06 (Round-trip file) | `units/data-unit/tests/test_file_upload_roundtrip.py` |
| US-NB-02 (Oracle PII) | `units/data-unit/tests/test_pii_masking.py` |
| US-SEC-01 (Invariant outbox) | `units/audit-unit/tests/test_outbox_invariant.py` |
| US-SEC-02 (Oracle+Idempotent PII) | 동상 |
| US-ADM-03 (Domain-Generator regex) | `units/data-unit/tests/test_pii_masking.py` |
| US-SHARE-01 (Idempotent commit) | `units/notebook-unit/tests/test_auto_commit_idempotent.py` |
| US-SHARE-03 (Invariant share perm) | `units/notebook-unit/tests/test_share_link_invariant.py` |

**13개 모두 자동화** ✓

---

## 4. Quality Gates (Inception execution-plan.md G1~G4)

| Gate | 시점 | 기준 | 검증 방법 |
|---|---|---|---|
| **G1** Application Design 종료 | Inception 끝 | 단일 책임, acyclic | 본 인셉션 산출물로 충족 ✓ |
| **G2** Units Generation 종료 | Inception 끝 | 5~7 유닛, acyclic | 7+1 유닛 산출 ✓ |
| **G3** 각 유닛 Code Generation 종료 | per-unit | 단위 + PBT 통과, 보안 베이스라인 단위별 점검 | 각 유닛 `code-generation.md` DoD |
| **G4** Build/Test 종료 | 본 단계 | 통합 통과, 50명 동시 성능 충족, SBOM, Trivy 0 critical/high, 백업 리허설 1회 | 본 문서 §1~2 |

---

## 5. 배포 산출물 (Final)

| 산출물 | 형식 | 위치 |
|---|---|---|
| `dataplatform-shared` | wheel | 사내 PyPI `0.1.0` |
| 각 유닛 wheel | wheel | 사내 PyPI |
| Docker 이미지 5종 | OCI | Harbor `harbor.internal/dataplatform/*:0.1.0` |
| Helm Chart | (Phase 2) | Harbor chart museum |
| SBOM | JSON | `infra/sbom/` (배포 산출물에 동봉) |
| Trivy report | JSON | `infra/trivy/` |
| Compose 정의 | YAML | `infra/docker-compose/compose.yml` |
| Ansible playbook | YAML | `infra/ansible/site.yml` |
| 사용자 매뉴얼 | Markdown | `docs/user-guide.md` (별도 작성) |
| 관리자 매뉴얼 | Markdown | `docs/admin-guide.md` |

---

## 6. 후속 단계 (Operations Phase 진입 전 위임)

- 사내 배포 절차: Ansible playbook `infra/ansible/site.yml` 실행 → 5개 컨테이너 + 외부 dep 검증
- 운영 Runbook (NFR-OBS-05): 주요 장애 시나리오별 대응 (감사 다운, Vault 다운, JupyterHub spawner 다운, etc.) — Operations 단계에서 작성
- 모니터링 알림 룰: Grafana Alerting 정의
- 분기 권한 리뷰 (NFR-AUDIT-03) 자동화 검증

---

## 7. 결론

본 단계가 완료되면 **MVP 출시 가능 상태**. 모든 40 MVP 스토리, 보안 베이스라인 15 규칙, PBT 10 규칙, NFR 38개 모두 자동화된 검증을 통과하도록 설계됨.

**다음**: Operations Phase (placeholder — 본 워크플로 범위 밖)
