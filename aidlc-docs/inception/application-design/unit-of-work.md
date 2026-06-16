# Unit of Work — 내부망 데이터 분석 플랫폼

**작성일**: 2026-05-21
**아키텍처 컨텍스트**: Modular Monolith (Q-AD-11=A)
**기반 결정**: `unit-of-work-plan.md` §C

> **용어**: 본 문서의 "유닛(Unit)"은 *논리적 개발·테스트 단위*. 배포 단위(컨테이너)와의 매핑은 Infrastructure Design 단계에서 확정.

---

## 0. 유닛 인벤토리 요약

| # | 유닛 | 도메인 책임 | 모듈 수 | MVP/Phase 2 | 배포 매핑 (잠정) |
|---|---|---|---|---|---|
| 1 | `gateway-unit` | 외부 트래픽 진입, 인가 1차 | 2 + SL-1 | MVP | 컨테이너 A (frontproxy) |
| 2 | `auth-unit` | 인증·세션·역할 | 5 + Orchestrator | MVP | 컨테이너 B (backend) |
| 3 | `audit-unit` | 감사 발행·저장·조회 | 2 + Service + SL-2 | MVP | 컨테이너 B |
| 4 | `credential-unit` | 자격증명 관리 + Vault 어댑터 | 2 | MVP | 컨테이너 B |
| 5 | `data-unit` | 커넥션·SQL 실행·파일·PII | 9 + Service | MVP | 컨테이너 B |
| 6 | `notebook-unit` | 노트북·시각화·공유·Git | 9 + Service | MVP | 컨테이너 B + C (JupyterHub) |
| 7 | `admin-unit` | Admin/Audit 콘솔 + Ops | 6 + 2 Services | MVP | 컨테이너 D (SPA) + B |
| 8 | `shared-lib` | 횡단 라이브러리 (의사 유닛) | SL-3, SL-4 | MVP | (라이브러리, 모든 컨테이너에 포함) |
| 9 | `infra/` | IaC + Compose + Ansible | (코드 외) | MVP | (배포 산출물) |
| 10 | `phase2-incubation/` | LLM·Reporting·외부DW 후보 | 6 모듈 | Phase 2 | TBD |

**MVP 유닛 합계**: 7개 + shared-lib + infra. **Phase 2 후보**: 1 (phase2-incubation 내부 분화).

---

## 1. `gateway-unit`

### 1.1 책임
- 외부 → 내부 모든 트래픽의 단일 진입점
- TLS 종단(1.2+), Rate Limiting, 보안 헤더(SECURITY-04), 1차 인가
- OIDC 콜백 처리

### 1.2 포함 모듈
| Module | 출처 |
|---|---|
| `ApiGateway` | components.md §1.1 |
| `OidcCallbackHandler` | components.md §1.2 |
| `SecurityKernel` (SL-1) | components.md §13 — 본 유닛에서 호스팅 |

### 1.3 외부 결합
- Keycloak (인증 전달) — KeycloakAdapter는 `auth-unit` 소유, `gateway-unit`은 호출만

### 1.4 빌드/배포 후보
- 별도 컨테이너 A (Reverse Proxy 역할 — nginx/envoy 기반 or 직접 코드)
- 핫리스타트 가능해야 함 (Cert 갱신·Rate Limit 룰 변경)

---

## 2. `auth-unit`

### 2.1 책임
- 사용자 인증, 세션 라이프사이클, 역할 관리
- 활성 Admin ≥ 1 invariant 보장
- 다른 유닛이 호출하는 `verifyAccess`, `getRoles` API 제공

### 2.2 포함 모듈
| Module | 출처 |
|---|---|
| `AuthService` | components.md §2.1 |
| `SessionStore` | §2.2 |
| `RoleResolver` | §2.3 |
| `KeycloakAdapter` | §2.4 |
| `AuthServiceOrchestrator` | services.md §1 |

### 2.3 외부 결합
- Keycloak (사내 IdP)

### 2.4 PBT 적용
- Invariant (활성 Admin ≥ 1), State-Machine (세션), Domain-Generator (비밀번호)

---

## 3. `audit-unit`

### 3.1 책임
- append-only 감사 로그 저장 + 검색 + 내보내기
- outbox 컨슈머 (다른 유닛이 발행한 이벤트 소비)
- 1년 이상 보존 (NFR-AUDIT-01)

### 3.2 포함 모듈
| Module | 출처 |
|---|---|
| `AuditWriter` | components.md §3.1 |
| `AuditQueryApi` | §3.2 |
| `AuditEventEmitter` (SL-2) | §13 — 본 유닛에서 호스팅 |
| `AuditService` | services.md §5 |

### 3.3 외부 결합
- 감사 저장소(메타DB 분리 스키마 또는 별도 DB — Infrastructure Design)
- Redis Streams / outbox 테이블

---

## 4. `credential-unit`

### 4.1 책임
- 자격증명 등록·회전·삭제 (공용·개인)
- Vault 어댑터 캡슐화

### 4.2 포함 모듈
| Module | 출처 |
|---|---|
| `CredentialVault` | components.md §4.1 |
| `VaultAdapter` | §4.2 |

### 4.3 외부 결합
- HashiCorp Vault 또는 동등 시크릿 매니저

### 4.4 PBT 적용
- Idempotent (재등록), State-Machine (등록→회전→삭제)

---

## 5. `data-unit`

### 5.1 책임
- 데이터 커넥션 + SQL 실행 + 파일 업로드 + PII 마스킹의 모든 코어 로직
- `DataAccessService`의 단일 도메인 흐름 호스팅

### 5.2 포함 모듈
| Module | 출처 |
|---|---|
| `ConnectionRegistry` | components.md §5.1 |
| `ConnectorFactory` | §5.2 |
| `RdbmsConnector` | §5.3 |
| `BigDataSqlConnector` | §5.4 |
| `QueryExecutor` | §5.5 |
| `SchemaIntrospector` | §5.6 |
| `PiiPolicyStore` | §6.1 |
| `PiiMaskingFilter` | §6.2 |
| `FileUploadHandler` | §7.4 (Notebook Domain이지만 데이터 진입점이라 본 유닛 귀속) |
| `DataAccessService` | services.md §2 |

### 5.3 외부 결합
- 사내 RDBMS (PG/MySQL/Oracle/MSSQL), 빅데이터(Hive/Impala/Presto/Trino)
- NAS/MinIO (FileUploadHandler 경유)

### 5.4 PBT 적용
- Round-trip (CSV/Parquet), Oracle + Idempotent (PiiMaskingFilter), Domain-Generator (PiiPolicy 정규식), Idempotent + Invariant (ConnectionRegistry)

### 5.5 비고
- **`FileUploadHandler`를 `notebook-unit`이 아닌 본 유닛에 둔 이유**: 파일도 데이터 소스이고, PII 정책 적용 대상이며, `DataAccessService`와 같은 도메인 흐름을 공유. Functional Design에서 검토 후 이동 가능.

---

## 6. `notebook-unit`

### 6.1 책임
- JupyterHub 통합 + 노트북 저장/공유 + 차트 빌드 + Git 자동 커밋

### 6.2 포함 모듈
| Module | 출처 |
|---|---|
| `NotebookStore` | components.md §7.1 |
| `JupyterHubSpawner` | §7.2 |
| `KernelManager` | §7.3 |
| `ChartBuilder` | §8.1 |
| `ShareLinkManager` | §9.1 |
| `GitAdapter` | §10.1 |
| `AutoCommitOrchestrator` | §10.2 |
| `NotebookService` | services.md §3 |

### 6.3 외부 결합
- JupyterHub (사내 호스팅, 본 유닛에 의해 spawn 위탁)
- GitLab/Gitea (사내)

### 6.4 PBT 적용
- Idempotent (AutoCommit), Invariant (ShareLink 권한 거부)

### 6.5 비고
- JupyterHub 자체는 외부 의존이지만 본 유닛이 spawner 어댑터를 갖고 통합 책임을 짐.
- Phase 2에서 `share-svc` + `git-integration`을 별도 유닛으로 분리 후보.

---

## 7. `admin-unit`

### 7.1 책임
- Admin Console + Auditor Console SPA
- JupyterLab Extensions (분석가 UI 부착)
- 백업·복구 리허설 운영

### 7.2 포함 모듈
| Module | 출처 |
|---|---|
| `AdminConsole` | components.md §11.1 |
| `AuditorConsole` | §11.2 |
| `JupyterExtensionsBundle` | §11.3 |
| `BackupScheduler` | §12.1 |
| `RestoreVerifier` | §12.2 |
| `AdminService` | services.md §4 |
| `BackupService` | services.md §6 |

### 7.3 외부 결합
- 사내 백업 스토리지

### 7.4 비고
- UI SPA 코드는 React/Vite 기반 가정 (NFR Requirements에서 확정)
- JupyterExtensionsBundle은 JupyterLab plugin spec 따름

---

## 8. `shared-lib` (가상 유닛)

### 8.1 책임
- 모든 유닛이 import하는 공유 코드 (라이브러리, 컨테이너 아님)

### 8.2 포함 모듈
| Module | 출처 |
|---|---|
| `Telemetry` (SL-3) | components.md §13 |
| `ResultTypes` (SL-4) | §13 |
| `SecurityKernel` (SL-1) 인터페이스 정의 | (호스팅은 gateway-unit) |
| `AuditEventEmitter` (SL-2) 인터페이스 정의 | (호스팅은 audit-unit) |
| 공통 DTO·타입 | (정의 위치) |

### 8.3 배포
- 빌드 산출물은 라이브러리(jar/wheel/package). 컨테이너에 함께 패키징.

---

## 9. `infra/` (코드 외)

### 9.1 책임
- Docker Compose 정의 (MVP)
- Ansible / Terraform (NFR-DEPLOY-05)
- 컨테이너 레지스트리 / PyPI 미러 설정
- TLS 인증서, 보안 헤더 룰

### 9.2 배포 매핑 (MVP)
- 컨테이너 A: `gateway-unit` (frontproxy)
- 컨테이너 B: backend (auth + audit + credential + data + notebook(노트북 서버 메타 부분) + admin)
- 컨테이너 C: JupyterHub spawner (`notebook-unit`의 일부 — 사용자별 spawn 컨테이너 host)
- 컨테이너 D: AdminConsole/AuditorConsole SPA (정적 서빙)
- 외부: Keycloak, Vault, GitLab/Gitea, 메타 DB, Redis, Prometheus/Grafana

> Phase 2 K8s 마이그레이션 시 컨테이너 B를 `auth`/`audit`/`data`/`notebook` 등으로 추출.

---

## 10. `phase2-incubation/`

### 10.1 책임
- Phase 2 후보 컴포넌트들의 격리된 incubation 영역
- 본 디렉터리 코드는 MVP 빌드/테스트에 포함되지 않음

### 10.2 포함 모듈 (Phase 2)
- LlmProxyAdapter, LlmGovernor
- ReportRenderer, ReportScheduler
- ColumnLevelGuard
- NotebookSearchIndexer
- (외부 DW 커넥터) ClickHouseConnector, SnowflakeConnector, BigQueryConnector

---

# 부록 A. 코드 조직 전략 (Greenfield 의무)

## A.1 디렉터리 구조 (monorepo)

```text
0521_platform/                      # 워크스페이스 루트 (앱 코드는 여기 — aidlc-docs/ 밖)
├── units/
│   ├── gateway-unit/
│   │   ├── src/
│   │   ├── tests/
│   │   └── BUILD                   # 또는 Cargo.toml / package.json / pyproject.toml
│   ├── auth-unit/
│   ├── audit-unit/
│   ├── credential-unit/
│   ├── data-unit/
│   ├── notebook-unit/
│   ├── admin-unit/
│   │   ├── admin-console/          # React SPA
│   │   ├── auditor-console/        # React SPA
│   │   ├── jupyter-extensions/     # JupyterLab plugin
│   │   └── backend/                # AdminService + BackupService
│   └── shared-lib/
│       ├── src/
│       └── tests/
├── infra/
│   ├── docker-compose/
│   │   ├── compose.yml
│   │   ├── compose.dev.yml
│   │   └── .env.example
│   ├── ansible/
│   └── certs/
├── phase2-incubation/
│   ├── llm-proxy/
│   ├── reporting/
│   └── ...
├── tests/
│   ├── integration/                # 유닛 간 통합 테스트
│   ├── performance/                # 50명 동시 시나리오
│   └── property/                   # PBT 공통 (cross-unit)
├── aidlc-docs/                     # 본 디렉터리 (문서 전용)
└── README.md
```

## A.2 빌드 규칙
- 각 유닛은 *독립적으로 빌드/테스트 가능* — `units/<name>` 안에서 `make test` 등이 자체 완결.
- `shared-lib`는 모든 유닛이 dev-dependency로 참조 (in-source 또는 사내 패키지 레지스트리).
- `phase2-incubation/`은 MVP CI에서 제외 (별도 워크플로).

## A.3 사내 의존성 미러
- `infra/`의 미러 설정으로 PyPI / Conda / NPM / Maven 사내 미러 강제 (NFR-DEPLOY-03)

## A.4 보안 베이스라인 강제 위치
- `shared-lib`에 lint/검증 규칙 모음 (예: SQL 직접 결합 금지 ESLint/ruff 룰, 평문 시크릿 grep guard)
- CI에서 모든 유닛에 일괄 적용 (SECURITY-10)
