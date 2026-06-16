# Requirements — 내부망 데이터 분석 플랫폼

**프로젝트**: 내부망 데이터 분석 플랫폼 (Internal Data Analytics Platform)
**작성일**: 2026-05-21
**프로젝트 유형**: Greenfield (신규)
**요구사항 깊이**: Comprehensive

---

## 0. 의도 분석 (Intent Analysis Summary)

| 항목 | 결과 |
|---|---|
| 사용자 요청 | "내부망에서 주피터랩처럼 데이터분석가들이 자율적으로 인터랙션하면서 분석할 수 있는 플랫폼" — 여러 DB/파일 연결, SQL 작성, 그래프/차트, 보고서 생성 |
| 요청 유형 | New Project (신규 플랫폼) |
| 범위 추정 | System-wide (인증·데이터 커넥터·노트북 런타임·시각화·리포트·운영 모니터링) |
| 복잡도 추정 | Complex |
| 깊이 결정 | Comprehensive |

**핵심 비전**: 부서 단위(10~50명) 데이터 분석가/사이언티스트/비즈니스 사용자가 사내망 안에서 자율적으로 분석·시각화·보고를 할 수 있는 JupyterLab 기반 통합 플랫폼.

---

## 1. 기능 요구사항 (Functional Requirements)

### 1.1 인증 및 권한 (Authentication & Authorization)

| ID | 요구사항 | 우선순위 | 비고 |
|---|---|---|---|
| FR-AUTH-01 | Keycloak 기반 인증 (OAuth2/OIDC) | MVP | 향후 사내 LDAP/AD 연동 가능하도록 어댑터 활성화 |
| FR-AUTH-02 | RBAC: `Admin`, `Analyst`, `Viewer` 세 가지 기본 역할 | MVP | 역할별 메뉴·기능 가시성 제어 |
| FR-AUTH-03 | 세션 관리(만료, 로그아웃 시 무효화), `Secure/HttpOnly/SameSite` 쿠키 | MVP | SECURITY-12 |
| FR-AUTH-04 | 관리자 계정 MFA 옵션 지원 | MVP | SECURITY-12 |
| FR-AUTH-05 | 비밀번호 정책(8자+, 침해 비밀번호 차단) — 자체 가입 시 | MVP | SECURITY-12 |

### 1.2 데이터 소스 커넥션 (Data Source Connectors)

| ID | 요구사항 | 우선순위 | 비고 |
|---|---|---|---|
| FR-DS-01 | RDBMS 커넥터: PostgreSQL, MySQL, Oracle, MS SQL Server | MVP | JDBC/ODBC 드라이버 사내 미러에서 제공 |
| FR-DS-02 | 빅데이터 SQL 엔진 커넥터: Hive, Impala, Presto, Trino | MVP | Kerberos 인증 옵션 포함 |
| FR-DS-03 | 분석 DW 커넥터: ClickHouse, Snowflake, BigQuery | Phase 2 | 외부 DW는 화이트리스트 허용 시 |
| FR-DS-04 | NoSQL 커넥터: MongoDB, Elasticsearch | Phase 2 | SQL 추상화 어댑터 필요 |
| FR-DS-05 | **파일 데이터 소스**: CSV, TSV, Excel, Parquet, JSON, Feather | MVP | 모든 일반 포맷 |
| FR-DS-06 | 파일 업로드: 사용자 로컬 업로드 + 공유 스토리지(NAS/MinIO) 마운트 둘 다 지원 | MVP | 업로드 파일 사이즈 한도는 NFR-PERF-04 참조 |
| FR-DS-07 | 자격증명 관리: 관리자가 등록한 공용 커넥션 + 사용자별 개인 자격증명 둘 다 지원 | MVP | Vault/Secrets Manager에 암호화 저장. SECURITY-12 |
| FR-DS-08 | 데이터 소스 단위 권한 부여(RBAC 확장: 어떤 사용자가 어떤 커넥션을 사용 가능) | MVP | SECURITY-08 |

### 1.3 분석 인터페이스 (Analysis Interface)

| ID | 요구사항 | 우선순위 | 비고 |
|---|---|---|---|
| FR-UI-01 | JupyterLab/JupyterHub 기반 멀티유저 노트북 환경 | MVP | BSD 3-Clause 라이선스 → 상업 사용 가능 |
| FR-UI-02 | 셀 단위 실행: SQL, Python, R 커널 지원 | MVP | Q11=C |
| FR-UI-03 | 커넥션 사이드 패널: 분석가는 등록된 커넥션에서 테이블/스키마 탐색 가능 | MVP | UI 확장 (JupyterLab Extension) |
| FR-UI-04 | SQL 에디터: 자동 완성, 구문 강조, 결과 테이블 페이지네이션 | MVP | |
| FR-UI-05 | 결과 셀 → 차트 변환 버튼(원클릭 시각화) | MVP | |
| FR-UI-06 | 노트북 파일 자동 저장(분 단위) | MVP | |
| FR-UI-07 | 노트북 검색(파일명/내용/태그) | Phase 2 | |

### 1.4 시각화 (Visualization)

| ID | 요구사항 | 우선순위 | 비고 |
|---|---|---|---|
| FR-VIS-01 | 인터랙티브 차트(Plotly, ECharts) — 줌·호버·필터 지원 | MVP | |
| FR-VIS-02 | 정적 이미지 차트(Matplotlib, Seaborn) | MVP | Python 커널에서 직접 사용 |
| FR-VIS-03 | Apache Superset 임베드(대시보드 패널) | Phase 2 | |
| FR-VIS-04 | 차트 종류: line, bar, pie, scatter, heatmap, box, area 등 표준 셋 | MVP | |

### 1.5 보고서 (Reporting)

| ID | 요구사항 | 우선순위 | 비고 |
|---|---|---|---|
| FR-RPT-01 | 노트북/대시보드 → PDF 다운로드 | Phase 2 | 보고서 우선순위 = Q28에서 제외 |
| FR-RPT-02 | 노트북/대시보드 → 웹 URL 공유(읽기 전용 대시보드) | Phase 2 | |
| FR-RPT-03 | 노트북/대시보드 → PPT/Word 자동 생성 | Phase 3 | |
| FR-RPT-04 | 관리자가 보고서 템플릿 등록 → 분석가가 데이터 매핑하여 재사용 | Phase 2 | |
| FR-RPT-05 | 정기 발송(스케줄): 사내 메일/메신저로 PDF/링크 전송 | Phase 2 | |

### 1.6 공유 및 버전 관리 (Sharing & Version Control)

| ID | 요구사항 | 우선순위 | 비고 |
|---|---|---|---|
| FR-VCS-01 | 사내 Git(GitLab/Gitea) 연동: 노트북/쿼리/대시보드 자동 커밋 | MVP | CQ2=A. 백그라운드 자동 커밋 + 사용자가 수동 커밋 메시지 작성 옵션 |
| FR-VCS-02 | 사용자별 워크스페이스(개인 Git 저장소) + 팀 워크스페이스(공유 저장소) | MVP | |
| FR-VCS-03 | 노트북 diff/history 보기(웹 UI) | Phase 2 | 초기엔 GitLab/Gitea UI로 위임 |
| FR-VCS-04 | 노트북/대시보드 링크 공유 + 권한 제어(읽기/실행/편집) | MVP | |

### 1.7 보안 및 감사 (Security & Audit)

| ID | 요구사항 | 우선순위 | 비고 |
|---|---|---|---|
| FR-SEC-01 | 사용자 활동 감사 로그: 로그인, 쿼리 실행, 파일 업로드/다운로드, 권한 변경 — 전수 기록 | MVP | SECURITY-14, append-only 저장소 |
| FR-SEC-02 | PII 자동 마스킹: 이름·주민번호·전화·이메일 등 표준 패턴 | MVP | 결과 테이블 렌더링 시 적용. 관리자가 화이트리스트/블랙리스트 컬럼 지정 가능 |
| FR-SEC-03 | 컬럼 단위 권한: 권한 없는 사용자에게 컬럼 자체를 숨김 | Phase 2 | |
| FR-SEC-04 | 쿼리 검토: 위험 쿼리(전체 테이블 SELECT * 등) 경고 | Phase 2 | |

### 1.8 LLM 어시스턴트 (Phase 2)

| ID | 요구사항 | 우선순위 | 비고 |
|---|---|---|---|
| FR-LLM-01 | **자연어 → SQL 변환** (Text-to-SQL) | Phase 2 | CQ4-1 |
| FR-LLM-02 | **데이터 요약/인사이트 추출** (자동 보고서 코멘트) | Phase 2 | CQ4-1 |
| FR-LLM-03 | **코드 어시스턴트** (Python/R 셀 자동 완성/제안) | Phase 2 | CQ4-1 |
| FR-LLM-04 | LLM 호출은 사내 프록시 경유, 화이트리스트된 상용 API에만 송신 | Phase 2 | CQ4-3, SECURITY-07 |
| FR-LLM-05 | 외부 송신 데이터는 **메타데이터(스키마)만**으로 시작, 실데이터는 보안팀 협의 후 허용 | Phase 2 | CQ4-2=D. 송신 데이터 전수 로깅 |

### 1.9 관리자 기능 (Administration)

| ID | 요구사항 | 우선순위 | 비고 |
|---|---|---|---|
| FR-ADM-01 | 사용자/역할 관리 콘솔 | MVP | |
| FR-ADM-02 | 커넥션 등록/편집/삭제 | MVP | |
| FR-ADM-03 | 감사 로그 조회 콘솔 | MVP | |
| FR-ADM-04 | PII 마스킹 패턴 관리 | MVP | |
| FR-ADM-05 | 시스템 헬스 대시보드(서비스 상태, 리소스, 오류율) | MVP | NFR-OBS 참조 |

---

## 2. 비기능 요구사항 (Non-Functional Requirements)

### 2.1 성능 (Performance)

| ID | 요구사항 | 목표값 |
|---|---|---|
| NFR-PERF-01 | 일반 SQL 쿼리 응답 시간 | 베스트 에포트 (SLA 없음, Q23=C) — 단, 5초 이상 시 백그라운드 옵션 제공 |
| NFR-PERF-02 | 노트북 셀 실행 큐 대기 | 평균 < 3초 |
| NFR-PERF-03 | 동시 활성 사용자 | 최대 50명 안정 동작 (Q22=B) |
| NFR-PERF-04 | 파일 업로드 크기 한도 | 단일 파일 1GB (Q9=B 기반) |
| NFR-PERF-05 | 단일 쿼리/결과 데이터 한도 | ≤ 10GB 또는 1억 행 (초과 시 분할 또는 거절) |

### 2.2 가용성 (Availability)

| ID | 요구사항 | 목표값 |
|---|---|---|
| NFR-AVL-01 | 운영 시간 가용성 | 평일 09:00–18:00, 99% (Q24=B) |
| NFR-AVL-02 | 점검 시간 | 야간/주말 사전 공지 후 점검 가능 |
| NFR-AVL-03 | HA(고가용성) 구성 | MVP에서는 불필요. Phase 2 검토 |

### 2.3 보안 (Security) — Security Baseline 확장 적용

| ID | 요구사항 | 매핑 |
|---|---|---|
| NFR-SEC-01 | 저장 데이터 암호화(at-rest) + 전송 암호화(TLS 1.2+) | SECURITY-01 |
| NFR-SEC-02 | 모든 API 게이트웨이/로드밸런서 액세스 로깅 | SECURITY-02 |
| NFR-SEC-03 | 구조화된 애플리케이션 로깅 (timestamp, correlation ID, level, message) | SECURITY-03 |
| NFR-SEC-04 | HTTP 보안 헤더 (CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy) | SECURITY-04 |
| NFR-SEC-05 | 모든 API 입력값 검증 + 파라미터화 쿼리 (SQL 인젝션 방지) | SECURITY-05 |
| NFR-SEC-06 | 최소 권한 원칙 (IAM/RBAC, 와일드카드 금지) | SECURITY-06 |
| NFR-SEC-07 | 제한적 네트워크 구성 (deny-by-default 방화벽) | SECURITY-07 |
| NFR-SEC-08 | 애플리케이션 레벨 인가 (객체·기능 수준, CORS 명시) | SECURITY-08 |
| NFR-SEC-09 | 보안 하드닝 (기본 자격증명 제거, 에러에 스택 트레이스 노출 금지) | SECURITY-09 |
| NFR-SEC-10 | 의존성 핀(lock file) + 취약점 스캐너 + SBOM + 사내 레지스트리 | SECURITY-10 |
| NFR-SEC-11 | 보안 핵심 로직 모듈화 + Rate Limiting | SECURITY-11 |
| NFR-SEC-12 | 인증 정책(adaptive 해시, 세션 만료, 무차별 대입 차단, 시크릿 매니저) | SECURITY-12 |
| NFR-SEC-13 | 무결성 검증(safe deserialization, SRI, 감사 가능한 데이터 변경) | SECURITY-13 |
| NFR-SEC-14 | 보안 알림 + append-only 로그 + 90일 이상 보존 | SECURITY-14 |
| NFR-SEC-15 | 예외 처리 fail-closed, 전역 에러 핸들러, 사용자 메시지 일반화 | SECURITY-15 |

### 2.4 운영성 (Observability) — Q32 우려 해소

| ID | 요구사항 |
|---|---|
| NFR-OBS-01 | Prometheus + Grafana로 시스템 메트릭/대시보드 |
| NFR-OBS-02 | 중앙 집중 로깅 (Loki 또는 ELK) |
| NFR-OBS-03 | 분산 추적 (OpenTelemetry) — Phase 2 |
| NFR-OBS-04 | 헬스 체크 엔드포인트 (`/healthz`, `/readyz`) |
| NFR-OBS-05 | 장애 대응 Runbook (자주 발생하는 오류별 복구 절차) |
| NFR-OBS-06 | 자동 백업(메타데이터 DB, 사용자 워크스페이스 일 1회 이상) + 복구 절차 검증 |

### 2.5 호환성 (Compatibility)

| ID | 요구사항 |
|---|---|
| NFR-COMPAT-01 | 지원 브라우저: Chrome 최신 2버전, Edge 최신 2버전, Firefox 최신 2버전 — **IE11 미지원** (CQ5 권장 채택) |
| NFR-COMPAT-02 | 서버 OS: Linux (Ubuntu 22.04 LTS 또는 RHEL 8/9) |
| NFR-COMPAT-03 | 클라이언트 최소 해상도: 1280×800 |

### 2.6 배포 (Deployment)

| ID | 요구사항 |
|---|---|
| NFR-DEPLOY-01 | MVP: Docker Compose 단일 VM 또는 2~3 VM 구성 |
| NFR-DEPLOY-02 | Phase 2: Kubernetes 마이그레이션 경로 확보 (Helm Chart 또는 동등) |
| NFR-DEPLOY-03 | 폐쇄망 친화: 사내 컨테이너 레지스트리(Harbor 등), 사내 PyPI/Conda/NPM 미러 사용 |
| NFR-DEPLOY-04 | 화이트리스트 외부망: LLM API 호출, 시간 동기(NTP), 인증서 갱신 등 사전 등록 도메인만 |
| NFR-DEPLOY-05 | IaC(Infrastructure as Code): Docker Compose 파일 + Ansible 또는 Terraform |

### 2.7 테스트 — PBT 확장 적용

| ID | 요구사항 | 매핑 |
|---|---|---|
| NFR-TEST-01 | 모든 단위에서 테스트 가능 속성(invariant/round-trip 등) 식별 (PBT-01) | PBT-01 |
| NFR-TEST-02 | 직렬화·인코딩·파싱 라운드트립 PBT (SQL 파서, 노트북 JSON 직렬화 등) | PBT-02 |
| NFR-TEST-03 | 비즈니스 룰 invariant PBT (예: 권한 검사 후 비공개 데이터 누출 없음) | PBT-03 |
| NFR-TEST-04 | 멱등 작업 PBT (커넥션 등록, 권한 부여 등) | PBT-04 |
| NFR-TEST-05 | Oracle 비교 (예: 마스킹 함수 vs 레퍼런스 정규식) | PBT-05 |
| NFR-TEST-06 | 상태 기반 PBT (워크스페이스 상태 머신, 노트북 세션) | PBT-06 |
| NFR-TEST-07 | 도메인 특화 제너레이터 (User/Connection/Query 등) | PBT-07 |
| NFR-TEST-08 | Shrinking + Seed 로깅 + CI 통합 | PBT-08 |
| NFR-TEST-09 | 프레임워크 선택: Python = Hypothesis, JS/TS = fast-check | PBT-09 |
| NFR-TEST-10 | 예시 기반 테스트 + PBT 병행 (PBT만으로 핵심 비즈니스 경로 커버 금지) | PBT-10 |

### 2.8 컴플라이언스 / 감사

| ID | 요구사항 |
|---|---|
| NFR-AUDIT-01 | 감사 로그 보존: 최소 1년 (SECURITY-14의 90일을 초과 강제) |
| NFR-AUDIT-02 | 감사 로그는 append-only 저장(WORM 또는 권한 분리) |
| NFR-AUDIT-03 | 정기 권한 리뷰: 분기 1회 사용자/역할 감사 보고서 자동 생성 |

---

## 3. 사용자 및 페르소나 요약

> **2026-05-21 갱신**: User Stories Part 1 답변(Q-USR-1=B,D)에 따라 페르소나가 통합·추가되었습니다. Analyst와 Data Scientist는 권한·도구가 동일하므로 단일 `Analyst` 페르소나로 통합, 보안 감사 전담 `Security Auditor`가 신규 추가됨. 상세는 `aidlc-docs/inception/user-stories/personas.md` 참조.

| 페르소나 | 역할 | 주요 활동 |
|---|---|---|
| 관리자 (Admin) | 1~3명 | 사용자/커넥션/PII/감사 관리 |
| 분석가 (Analyst) — SQL + Python/R 통합 | 15~50명 | SQL 작성, 파일 업로드, 차트, Python/R 모델링·통계, 노트북 작성/공유 |
| 비즈니스 사용자 (Viewer) | 5~20명 | 노트북·대시보드 열람, 보고서 다운로드 (Phase 2부터 본격) |
| 보안 감사관 (Security Auditor) — 신규 | 1~2명 | 감사 로그 조회, PII 정책 검토, 권한-사용 매트릭스 분기 리뷰 |

---

## 4. 가정 및 제약 (Assumptions & Constraints)

### 4.1 가정
- 사내 Linux 인프라(가상화 또는 베어메탈)에 Docker 설치 권한이 확보된다.
- 사내 컨테이너 레지스트리, PyPI 미러, 사내 Git 호스팅이 이미 존재하거나 동시 구축 가능하다.
- Keycloak 서버를 신규 호스팅 또는 사내 기존 IdP 활용이 허용된다.
- LLM 외부 API 호출은 보안팀 협의 후 화이트리스트 등록 절차로 가능하다.

### 4.2 제약
- 동시 사용자 최대 50명, 단일 쿼리/파일 최대 10GB/1억 행. 그 이상은 거부 또는 분할.
- 폐쇄망 일부 허용(특정 도메인 화이트리스트). 외부 인터넷 직결 불가.
- IE11 미지원. 그래야 모던 시각화 라이브러리 사용 가능.
- 1~2개월 MVP 일정 — Phase 2 항목은 별도 일정.

---

## 5. 일정 및 단계 (Phasing)

### Phase 1 — MVP (1~2개월, CQ1=A)
**포함**: FR-AUTH-01~05, FR-DS-01·02·05~08, FR-UI-01~06, FR-VIS-01·02·04, FR-VCS-01·02·04, FR-SEC-01·02, FR-ADM-01~05, 모든 MVP-표시 NFR.

**제외(Phase 2 이후)**: 외부 DW/NoSQL 커넥터, 보고서 생성·스케줄링, Superset 임베드, LLM 어시스턴트, 컬럼 단위 권한, 노트북 검색.

### Phase 2 (MVP+3개월)
보고서·스케줄링·LLM 어시스턴트·외부 DW/NoSQL 커넥터·고급 권한·검색·K8s 마이그레이션.

### Phase 3
PPT/Word 자동 생성, 분산 추적, 24/7 HA 검토.

---

## 6. 핵심 요구사항 요약 (Summary)

- **부서 단위(10~50명) 분석가/사이언티스트/비즈니스 사용자**가 사용하는 사내망 데이터 분석 플랫폼.
- **JupyterLab/Hub 기반**, 셀 단위 SQL·Python·R 실행. 인터랙티브 시각화(Plotly/ECharts) + 정적 시각화(Matplotlib).
- **다중 데이터 소스**: RDBMS(MySQL/PG/Oracle/MSSQL), 빅데이터 SQL 엔진(Hive/Impala/Presto/Trino), 파일(CSV/Excel/Parquet/JSON 등). 공용+개인 자격증명.
- **공유**: 사내 Git(GitLab/Gitea) 자동 연동.
- **보안**: Keycloak 인증 + RBAC(Admin/Analyst/Viewer) + 감사 전수 로깅 + PII 자동 마스킹. SECURITY-Baseline 15개 규칙 강제.
- **테스트**: Hypothesis(파이썬) / fast-check(JS) 기반 PBT 10개 규칙 강제 + 예시 기반 테스트 병행.
- **배포**: Docker Compose MVP → Phase 2에 K8s. 사내 폐쇄망 + 화이트리스트 외부망.
- **MVP는 1~2개월**, Phase 2에 보고서·LLM 어시스턴트·고급 권한 통합.

---

## 7. 추적성 (Traceability)

- 사용자 답변 원문: `requirement-verification-questions.md`, `requirement-clarification-questions.md`
- 확장 규칙: `.aidlc-rule-details/extensions/security/baseline/security-baseline.md`, `.aidlc-rule-details/extensions/testing/property-based/property-based-testing.md`
- 감사 로그: `aidlc-docs/audit.md`
