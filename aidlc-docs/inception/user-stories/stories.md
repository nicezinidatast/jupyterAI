# User Stories — 내부망 데이터 분석 플랫폼

**작성일**: 2026-05-21
**기반**: `aidlc-docs/inception/requirements/requirements.md` + `aidlc-docs/inception/plans/story-generation-plan.md`
**분류 방식**: Domain/Feature-Based (Q-PLAN-1=A)
**AC 형식**: Given/When/Then + 모든 스토리에 최소 1개 부정 케이스 + NFR 측정값 포함

---

## 0. 표기 규약

- **Priority**: `MVP` | `Phase 2` | `Phase 3`
- **Personas**: `Admin` | `Analyst` | `Viewer` | `Auditor`
- **PBT**: 해당 스토리에 Property-Based Test가 적용 가능하면 표기 (`✅ <기법>`)
  - 기법: `Round-trip` / `Invariant` / `Idempotent` / `Oracle` / `State-Machine` / `Domain-Generator`
- **FR/NFR**: requirements.md의 식별자

---

# 🔵 MVP Stories (Phase 1)

---

## Epic AUTH — Authentication & Session

### US-AUTH-01: SSO 로그인
- **As a** Analyst (또는 Admin/Viewer/Auditor),
- **I want** Keycloak SSO 로 로그인할 수 있고,
- **so that** 사내 단일 자격증명으로 플랫폼에 접근할 수 있다.

**AC**:
- **GIVEN** 사용자가 Keycloak에 등록된 활성 계정 보유
- **WHEN** 플랫폼 URL 접속 → IdP 리다이렉트 후 자격증명 입력
- **THEN** 페이지 로딩 완료까지 **3초 이내**, JupyterLab 워크스페이스 진입 + `Secure;HttpOnly;SameSite=Lax` 세션 쿠키 발급
- **부정**: **GIVEN** 비활성/잠긴 계정 **WHEN** 로그인 시도 **THEN** 일반화된 에러 메시지("로그인 실패")만 표시, 로그인 실패 5회 시 IdP 정책에 따라 잠금

**Related**: FR-AUTH-01, FR-AUTH-03, NFR-SEC-04, NFR-SEC-09, NFR-SEC-12
**Priority**: MVP
**Personas**: All
**PBT**: ✅ State-Machine (로그인/로그아웃/만료 상태 전이 invariant)

---

### US-AUTH-02: 역할 할당 및 가시성 제어
- **As an** Admin,
- **I want** 사용자에게 Admin/Analyst/Viewer/Auditor 역할을 부여하고,
- **so that** 역할별 메뉴·기능 가시성이 자동으로 제어된다.

**AC**:
- **GIVEN** Admin이 콘솔에서 사용자 검색
- **WHEN** 역할 변경 저장
- **THEN** 변경 즉시 적용, 해당 사용자의 다음 요청부터 새 권한 반영, 감사 로그에 `actor/target/old/new/timestamp` 기록
- **부정**: 자기 자신을 Admin에서 박탈 시도 → **차단**(최소 1명의 활성 Admin 유지)

**Related**: FR-AUTH-02, FR-SEC-01, NFR-SEC-06, NFR-SEC-08
**Priority**: MVP
**Personas**: Admin
**PBT**: ✅ Invariant (시스템에 활성 Admin 항상 ≥1)

---

### US-AUTH-03: 세션 만료와 작업 보호
- **As an** Analyst,
- **I want** 세션 만료 시 자동 로그아웃되면서 **노트북 변경분은 손실되지 않기를**,
- **so that** 보안 정책을 만족하면서 작업이 보호된다.

**AC**:
- **GIVEN** 분석가가 노트북에서 미저장 셀 편집 중
- **WHEN** 세션 TTL 도달
- **THEN** 자동 저장(분 단위) 데이터까지 보존, 재로그인 시 마지막 자동 저장 시점부터 복구 가능, 만료 알림 모달 표시
- **부정**: 만료된 세션 쿠키로 API 호출 → `401`, 백엔드 로그에 만료 사유 기록

**Related**: FR-AUTH-03, FR-UI-06, NFR-SEC-12
**Priority**: MVP
**Personas**: Analyst, Admin, Auditor

---

### US-AUTH-04: Admin MFA 옵션
- **As an** Admin,
- **I want** Admin 계정에 MFA(TOTP)를 강제 적용할 수 있고,
- **so that** 권한이 큰 계정의 도용 위험을 낮춘다.

**AC**:
- **GIVEN** Admin 정책에서 MFA=enabled
- **WHEN** Admin 사용자가 신규 디바이스로 로그인
- **THEN** Keycloak에서 TOTP 입력 단계 발생, 통과 시 정상 진입
- **부정**: TOTP 코드 3회 오류 → 30분 잠금 + 감사 로그 기록

**Related**: FR-AUTH-04, NFR-SEC-12
**Priority**: MVP
**Personas**: Admin

---

### US-AUTH-05: 비밀번호 정책(자체 가입 시)
- **As an** Admin,
- **I want** 사내 IdP 미연동 사용자에 대해 8자+ / 침해 비밀번호 차단 / adaptive 해시 정책을 적용하고,
- **so that** 자체 가입 경로의 보안 기준선을 유지한다.

**AC**:
- **GIVEN** 사용자가 자체 가입 페이지에서 비밀번호 설정
- **WHEN** 비밀번호 입력
- **THEN** 8자 미만 또는 HIBP 리스트 포함 시 즉시 거절, 저장 시 argon2id/PBKDF2 등 adaptive 해시 사용
- **부정**: `password123` 같은 침해 후보 → 거절 + 일반화 에러("정책 위반")

**Related**: FR-AUTH-05, NFR-SEC-12
**Priority**: MVP
**Personas**: Admin (정책 설정), All (적용 대상)
**PBT**: ✅ Domain-Generator (Password 제너레이터: 길이/문자 분포)

---

## Epic DS — Data Source & Connections

### US-DS-01: 공용 RDBMS 커넥션 등록 (Admin)
- **As an** Admin,
- **I want** PostgreSQL/MySQL/Oracle/MSSQL 커넥션을 등록하고,
- **so that** 분석가들이 사내 표준 커넥션으로 접속할 수 있다.

**AC**:
- **GIVEN** Admin 콘솔의 커넥션 등록 폼
- **WHEN** host/port/db/user/password + 드라이버 타입 입력 후 "테스트 연결" 클릭
- **THEN** 5초 내 결과 표시(성공/실패 사유), 자격증명은 Vault에 암호화 저장, 평문은 로그·메모리에 남지 않음
- **부정**: 동일 이름의 커넥션 재등록 → 거절 + 충돌 메시지

**Related**: FR-DS-01, FR-DS-07, NFR-SEC-01, NFR-SEC-12
**Priority**: MVP
**Personas**: Admin
**PBT**: ✅ Idempotent (동일 입력 두 번 등록 시 결과 동일/거절)

---

### US-DS-02: 빅데이터 SQL 엔진 커넥션 (Hive/Impala/Presto/Trino)
- **As an** Admin,
- **I want** Hive/Impala/Presto/Trino 커넥션을 Kerberos 인증 옵션과 함께 등록하고,
- **so that** 사내 데이터레이크에 분석가들이 접근할 수 있다.

**AC**:
- **GIVEN** 커넥션 등록 폼에서 엔진 = Hive/Impala/Presto/Trino 선택
- **WHEN** 표준 + Kerberos(keytab) 정보 입력
- **THEN** 테스트 연결 성공 시 등록 완료, keytab은 Vault 저장
- **부정**: 잘못된 principal/keytab → 일반화된 에러("인증 실패") + 상세는 Auditor용 감사 로그에만

**Related**: FR-DS-02, NFR-SEC-09, NFR-SEC-12
**Priority**: MVP
**Personas**: Admin

---

### US-DS-03: 커넥션 권한 부여 (RBAC 확장)
- **As an** Admin,
- **I want** 커넥션 단위로 어떤 역할/사용자에게 접근 권한을 줄지 정하고,
- **so that** 모든 커넥션이 자동 공개되지 않는다(최소 권한 원칙).

**AC**:
- **GIVEN** 등록된 커넥션 + 사용자/역할 목록
- **WHEN** Admin이 권한 부여/회수 후 저장
- **THEN** 권한 변경 즉시 적용, 감사 로그 기록, 회수 후 해당 사용자의 다음 쿼리부터 거절
- **부정**: 권한 없는 사용자의 커넥션 선택 시도 → 사이드 패널에 해당 커넥션이 **표시 자체가 안 됨**(존재 노출 금지)

**Related**: FR-DS-08, NFR-SEC-06, NFR-SEC-08
**Priority**: MVP
**Personas**: Admin, Analyst, Auditor
**PBT**: ✅ Invariant (권한 없는 사용자는 해당 커넥션의 어떤 객체도 보지 못함)

---

### US-DS-04: 개인 자격증명 등록 (Analyst)
- **As an** Analyst,
- **I want** 공용 자격증명이 아닌 내 개인 DB 자격증명을 등록하고 회전·삭제할 수 있고,
- **so that** 내 권한으로 데이터를 조회할 수 있다.

**AC**:
- **GIVEN** Analyst가 본인 설정 화면
- **WHEN** 개인 자격증명 등록/변경/삭제
- **THEN** Vault에 사용자별 namespace로 저장, 동일 사용자의 동일 커넥션에 대해 마지막 입력값으로 덮어쓰기, 변경 이력은 감사 로그에 기록(값 자체는 기록 금지)
- **부정**: 타인의 자격증명 조회 시도 → 403, API 응답에 자격증명 ID 노출 안 함

**Related**: FR-DS-07, NFR-SEC-01, NFR-SEC-06, NFR-SEC-12
**Priority**: MVP
**Personas**: Analyst, Admin
**PBT**: ✅ Idempotent (재등록 멱등) + State-Machine (등록 → 회전 → 삭제)

---

### US-DS-05: 스키마 사이드 패널 탐색
- **As an** Analyst,
- **I want** 허용된 커넥션의 데이터베이스/스키마/테이블/컬럼을 트리로 탐색하고,
- **so that** 쿼리 작성 전 데이터 구조를 파악한다.

**AC**:
- **GIVEN** Analyst가 커넥션 선택
- **WHEN** 사이드 패널에서 트리 펼침
- **THEN** 1000개 이하 객체는 3초 내 표시, 1000+ 는 lazy load 페이지네이션, 컬럼 클릭 시 데이터 타입·PII 마스킹 여부 표기
- **부정**: 권한 없는 스키마 → 트리에서 노출 안 됨

**Related**: FR-UI-03, FR-DS-08, NFR-SEC-06, NFR-PERF-01
**Priority**: MVP
**Personas**: Analyst

---

### US-DS-06: 파일 업로드 (로컬)
- **As an** Analyst,
- **I want** CSV/TSV/Excel/Parquet/JSON/Feather 파일을 로컬에서 업로드하고,
- **so that** 사내망 안에서 즉시 분석할 수 있다.

**AC**:
- **GIVEN** 업로드 모달
- **WHEN** 단일 파일 ≤ **1GB** 선택 후 업로드
- **THEN** 진행률 표시, 업로드 완료 후 노트북 셀에서 즉시 사용 가능, 업로드 이벤트 감사 로그 기록(파일명/크기/MIME)
- **부정**: 1GB 초과 → 클라이언트에서 즉시 거절(서버 부담 없음) + 안내 메시지

**Related**: FR-DS-05, FR-DS-06, NFR-PERF-04, FR-SEC-01
**Priority**: MVP
**Personas**: Analyst
**PBT**: ✅ Round-trip (CSV/Parquet 라운드트립: 업로드 → 읽기 → 직렬화 결과 동일성)

---

### US-DS-07: 공유 스토리지 마운트
- **As an** Analyst,
- **I want** NAS/MinIO 공유 폴더의 파일을 업로드 없이 노트북에서 직접 참조하고,
- **so that** 같은 데이터를 여러 분석가가 중복 업로드하지 않는다.

**AC**:
- **GIVEN** Admin이 공유 폴더를 마운트 등록 + 권한 부여
- **WHEN** Analyst가 노트북에서 마운트 경로 접근
- **THEN** 읽기 가능, 1GB 미만 파일 메타데이터는 3초 내 응답
- **부정**: 마운트 외 경로 접근 시도 → 격리된 컨테이너 sandbox로 차단(IO 거절)

**Related**: FR-DS-06, NFR-SEC-06, NFR-SEC-07
**Priority**: MVP
**Personas**: Analyst, Admin

---

## Epic NB — Notebook & SQL

### US-NB-01: JupyterHub 멀티유저 환경 진입
- **As an** Analyst,
- **I want** SSO 로그인 후 내 전용 JupyterLab 워크스페이스로 진입하고,
- **so that** 다른 사용자의 환경과 격리된 상태에서 분석한다.

**AC**:
- **GIVEN** 활성 사용자 ≤ **50명** (NFR-PERF-03)
- **WHEN** 로그인 후 워크스페이스 진입
- **THEN** 각 사용자별 별도 컨테이너(JupyterHub spawner), 진입까지 평균 **3초 이내**
- **부정**: 동시 활성 51번째 사용자 → 대기 큐 또는 안내 메시지(시스템 다운 아님)

**Related**: FR-UI-01, NFR-PERF-02, NFR-PERF-03
**Priority**: MVP
**Personas**: Analyst

---

### US-NB-02: 셀 단위 SQL 실행
- **As an** Analyst,
- **I want** 노트북 셀에 SQL을 작성하고 실행 결과를 표 형태로 받고,
- **so that** SQL-Centric 흐름을 끝낼 수 있다.

**AC**:
- **GIVEN** 권한 있는 커넥션 선택 상태
- **WHEN** `%%sql` 또는 SQL 셀에 쿼리 작성 후 실행
- **THEN** 결과 행 100/페이지 페이지네이션, **5초 이상 걸리면** "백그라운드 실행" 옵션 제공(NFR-PERF-01), PII 컬럼은 자동 마스킹된 채 표시
- **부정**: SQL 인젝션 패턴(쿼리 내 placeholder를 string format 으로 우회) → 파라미터화 강제, 막힘

**Related**: FR-UI-02, FR-UI-04, FR-SEC-02, NFR-SEC-05, NFR-PERF-01
**Priority**: MVP
**Personas**: Analyst
**PBT**: ✅ Oracle (마스킹 결과 vs 레퍼런스 정규식 비교)

---

### US-NB-03: 셀 단위 Python/R 실행
- **As an** Analyst,
- **I want** 같은 노트북에서 Python과 R 셀을 모두 실행하고,
- **so that** 모델링/통계 분석을 끊김 없이 진행한다.

**AC**:
- **GIVEN** 노트북에서 커널 선택(Python 3 또는 R)
- **WHEN** 코드 셀 실행
- **THEN** 커널 메모리/CPU 제한 내 실행, 결과/에러는 셀 출력에 표시, 셀 실행 큐 대기 평균 **< 3초**
- **부정**: 메모리 한도 초과 → 셀 강제 종료 + 안내 메시지("리소스 한도 초과")

**Related**: FR-UI-02, NFR-PERF-02
**Priority**: MVP
**Personas**: Analyst

---

### US-NB-04: SQL 자동완성·구문 강조
- **As an** Analyst,
- **I want** SQL 작성 시 키워드·테이블·컬럼 자동완성과 구문 강조를 받고,
- **so that** 실수 없이 빠르게 쿼리를 만든다.

**AC**:
- **GIVEN** 커넥션 선택 + 스키마 캐시 로드 완료
- **WHEN** SQL 입력 중 `Ctrl+Space`
- **THEN** 200ms 내 후보 제안(테이블/컬럼/키워드)
- **부정**: 권한 없는 객체 → 후보에 노출 안 됨

**Related**: FR-UI-04
**Priority**: MVP
**Personas**: Analyst

---

### US-NB-05: 노트북 자동 저장
- **As an** Analyst,
- **I want** 노트북을 작성 중 분 단위로 자동 저장되고,
- **so that** 브라우저 사고 시에도 작업이 보존된다.

**AC**:
- **GIVEN** 노트북에 변경분 존재
- **WHEN** 마지막 변경 후 60초 경과 또는 셀 실행 시
- **THEN** 서버에 자동 저장, UI에 "저장됨 HH:MM" 표시
- **부정**: 디스크 용량 부족 → 사용자에게 명확한 메시지 + 변경분 일시 보존(읽기 전용 모드)

**Related**: FR-UI-06
**Priority**: MVP
**Personas**: Analyst

---

### US-NB-06: 백그라운드 셀 실행
- **As an** Analyst,
- **I want** 5초 이상 걸릴 만한 셀을 백그라운드로 실행하고 결과 도착 시 알림을 받고,
- **so that** 다른 작업을 막지 않으면서 무거운 쿼리/계산을 돌린다.

**AC**:
- **GIVEN** 셀에 "백그라운드 실행" 토글 활성
- **WHEN** 실행 시작
- **THEN** 셀 상태가 "실행 중"으로 비동기 처리, 완료 시 UI 인디케이터 + 알림
- **부정**: 백그라운드 잡 누적 한도 초과 → 신규 잡 큐잉 + 사용자에게 안내

**Related**: FR-UI-02, NFR-PERF-01
**Priority**: MVP
**Personas**: Analyst

---

## Epic VIS — Visualization

### US-VIS-01: 결과 셀 원클릭 차트 변환
- **As an** Analyst,
- **I want** SQL/DataFrame 결과 셀에 "차트 변환" 버튼을 누르면 즉시 인터랙티브 차트가 나오고,
- **so that** 별도 코드 없이도 시각화한다.

**AC**:
- **GIVEN** 결과 행 ≤ **10만 행**
- **WHEN** 차트 변환 클릭 → 차트 종류 선택(line/bar/pie/scatter/heatmap/box/area)
- **THEN** Plotly로 줌·호버·필터 가능한 차트 렌더 (1초 내 시작)
- **부정**: 10만 행 초과 → 샘플링/집계 옵션 제안

**Related**: FR-UI-05, FR-VIS-01, FR-VIS-04
**Priority**: MVP
**Personas**: Analyst

---

### US-VIS-02: 인터랙티브 차트(Plotly/ECharts)
- **As an** Analyst,
- **I want** Plotly/ECharts로 줌/호버/필터 가능한 차트를 만들고,
- **so that** Viewer가 자가 탐색할 수 있도록 한다.

**AC**:
- **GIVEN** 노트북 셀에서 Plotly figure 생성
- **WHEN** 셀 실행
- **THEN** 브라우저에서 인터랙션 가능, 노트북 저장 시 차트 JSON이 함께 저장됨
- **부정**: 차트 데이터에 PII 컬럼 포함 → 자동 마스킹 적용 후 렌더

**Related**: FR-VIS-01, FR-VIS-04, FR-SEC-02
**Priority**: MVP
**Personas**: Analyst, Viewer

---

### US-VIS-03: 정적 이미지 차트(Matplotlib/Seaborn)
- **As an** Analyst,
- **I want** Python 셀에서 matplotlib/seaborn 차트를 PNG로 임베드하고,
- **so that** 보고서·문서에 그대로 활용한다.

**AC**:
- **GIVEN** Python 셀에 plt 코드
- **WHEN** 실행
- **THEN** PNG 이미지가 셀 출력에 임베드, 노트북 저장 시 base64 포함
- **부정**: figure 크기 초과(예: 50MB+) → 자동 리사이즈 + 경고

**Related**: FR-VIS-02
**Priority**: MVP
**Personas**: Analyst

---

### US-VIS-04: 차트 표준 셋
- **As an** Analyst,
- **I want** line/bar/pie/scatter/heatmap/box/area 7종 차트 빌더가 UI로 제공되고,
- **so that** 코드 없이도 표준 시각화를 만든다.

**AC**:
- **GIVEN** 차트 변환 모달
- **WHEN** 차트 종류 + 축 매핑 선택
- **THEN** 미리보기 즉시 렌더, "노트북에 코드로 삽입" 옵션 제공
- **부정**: 축 매핑이 데이터 타입과 안 맞음(예: 문자열 컬럼을 scatter Y축) → 명확한 오류 + 권장 옵션

**Related**: FR-VIS-04
**Priority**: MVP
**Personas**: Analyst

---

## Epic SHARE — Sharing & Version Control

### US-SHARE-01: Git 자동 커밋 (백그라운드)
- **As an** Analyst,
- **I want** 노트북 저장 시 사내 GitLab/Gitea로 백그라운드 자동 커밋되고,
- **so that** 모든 변경 이력이 보존된다.

**AC**:
- **GIVEN** 사용자 워크스페이스에 Git 저장소 연결
- **WHEN** 노트북 자동 저장 직후 또는 사용자가 명시적 커밋 메시지 작성
- **THEN** 메시지 미입력 시 "auto: <노트북명> @ <timestamp>"로 커밋, 30초 내 push, 실패 시 재시도(최대 3회) 후 UI 알림
- **부정**: Git 서버 다운 → 로컬 변경분은 유지, 다음 가용 시 푸시

**Related**: FR-VCS-01, FR-VCS-02
**Priority**: MVP
**Personas**: Analyst
**PBT**: ✅ Idempotent (동일 콘텐츠 재커밋 시 no-op)

---

### US-SHARE-02: 개인/팀 워크스페이스 분리
- **As an** Analyst,
- **I want** 개인 Git 저장소와 팀 공유 저장소를 구분해서 사용하고,
- **so that** 실험 코드와 공식 산출물을 섞지 않는다.

**AC**:
- **GIVEN** 사용자에게 개인 저장소 + 0~N개 팀 저장소 권한
- **WHEN** 노트북 생성 시 저장 위치 선택
- **THEN** 선택한 저장소로 커밋, 사이드바에 저장소별 색상/배지 구분
- **부정**: 팀 저장소 권한 없는 사용자가 push 시도 → 403 + 명확한 사유

**Related**: FR-VCS-02
**Priority**: MVP
**Personas**: Analyst, Admin

---

### US-SHARE-03: 노트북 링크 공유 + 권한
- **As an** Analyst,
- **I want** 노트북에 읽기/실행/편집 권한을 부여한 링크를 동료에게 공유하고,
- **so that** 협업 가능 범위를 명시적으로 제어한다.

**AC**:
- **GIVEN** Analyst가 노트북 공유 모달 열기
- **WHEN** 대상 사용자 + 권한 레벨(읽기/실행/편집) 지정
- **THEN** SSO 인증된 사용자만 접근 가능한 링크 생성, 권한 범위에 따라 UI 동작 제한(읽기는 셀 실행 버튼 비활성)
- **부정**: 링크 도용(인증되지 않은 사용자) → 401 + 감사 로그

**Related**: FR-VCS-04
**Priority**: MVP
**Personas**: Analyst, Viewer
**PBT**: ✅ Invariant (권한 < 요구권한 → 항상 거절)

---

### US-SHARE-04: 공유 노트북 실행(권한 = 실행)
- **As a** Viewer (또는 Analyst),
- **I want** 공유받은 노트북을 권한 = 실행으로 받았을 때 셀을 실행해 최신 데이터로 결과를 다시 보고,
- **so that** 시점이 어긋난 정적 자료가 아니라 최신 데이터로 의사결정한다.

**AC**:
- **GIVEN** 권한 = 실행 링크
- **WHEN** 사용자가 "전체 셀 실행"
- **THEN** 노트북 원작성자의 자격증명이 아닌 **현재 사용자**의 자격증명·권한 기준으로 쿼리 실행 (보안 격리)
- **부정**: 현재 사용자에게 권한 없는 데이터 셀 → 해당 셀 실패, 다른 셀은 계속

**Related**: FR-VCS-04, NFR-SEC-06, NFR-SEC-08
**Priority**: MVP
**Personas**: Analyst, Viewer

---

## Epic SEC — Security & Audit

### US-SEC-01: 활동 감사 로그 전수 기록
- **As an** Auditor,
- **I want** 로그인/쿼리 실행/파일 업로드·다운로드/권한 변경 이벤트가 빠짐없이 감사 로그에 기록되기를,
- **so that** 사후 추적이 가능하다.

**AC**:
- **GIVEN** 시스템 정상 운영 상태
- **WHEN** 사용자가 위 이벤트 중 하나라도 발생시킴
- **THEN** append-only 저장소에 `actor, action, resource, timestamp, correlation-id` 기록, **유실률 0**, 보존 ≥ **1년**(NFR-AUDIT-01)
- **부정**: 감사 로그 저장소가 일시 불가 → 어플리케이션은 fail-closed (이벤트 수행 거절) 또는 로컬 큐잉 후 재전송

**Related**: FR-SEC-01, NFR-SEC-14, NFR-AUDIT-01, NFR-AUDIT-02
**Priority**: MVP
**Personas**: Admin, Auditor
**PBT**: ✅ Invariant (이벤트 발생 횟수 ≤ 감사 로그 레코드 수)

---

### US-SEC-02: PII 자동 마스킹
- **As an** Admin,
- **I want** 결과 테이블 렌더링 시 이름·주민번호·전화·이메일 등 표준 PII 패턴을 자동 마스킹하고,
- **so that** 분석가의 의도와 무관하게 PII가 노출되지 않는다.

**AC**:
- **GIVEN** 컬럼 메타데이터에 PII 표기 또는 표준 정규식 매칭
- **WHEN** 결과 셀 렌더링
- **THEN** 마스킹 적용 후 표시(예: `홍*동`, `010-****-1234`), 원본 데이터는 클라이언트로 송신되지 않음
- **부정**: 화이트리스트(예: 공개 가능 컬럼) → 마스킹 제외, 단 감사 로그에 화이트리스트 적용 사실 기록

**Related**: FR-SEC-02, NFR-AUDIT-02
**Priority**: MVP
**Personas**: Admin, Analyst, Auditor
**PBT**: ✅ Oracle (마스킹 함수 vs 레퍼런스 정규식 비교) + Idempotent (이미 마스킹된 값에 재적용 시 동일)

---

### US-SEC-03: 감사 로그 검색 콘솔 (Auditor)
- **As an** Auditor,
- **I want** 사용자 ID / 기간 / 액션 종류 / 리소스로 감사 로그를 검색하고,
- **so that** 인시던트 대응과 분기 권한 리뷰를 신속히 수행한다.

**AC**:
- **GIVEN** Auditor 권한
- **WHEN** 검색 조건 입력
- **THEN** 페이지네이션 결과 표시, CSV/JSON 내보내기 가능(감사 로그 자체도 다운로드 이벤트로 기록)
- **부정**: Analyst가 감사 로그 콘솔 URL 접근 시도 → 403

**Related**: FR-ADM-03, FR-SEC-01, NFR-SEC-08
**Priority**: MVP
**Personas**: Auditor, Admin

---

### US-SEC-04: 보안 헤더 + 입력 검증
- **As an** Admin,
- **I want** 모든 응답에 CSP/HSTS/X-Content-Type-Options/X-Frame-Options/Referrer-Policy를 적용하고 API 입력값을 검증하고,
- **so that** 일반적 웹 취약점을 차단한다.

**AC**:
- **GIVEN** 어떤 엔드포인트에 요청
- **WHEN** HTTP 응답 헤더 확인
- **THEN** 5종 헤더 모두 포함, API 본문은 schema 검증 후만 처리, SQL은 파라미터화
- **부정**: 잘못된 schema 본문 → 400 + 일반화 메시지(스택 트레이스 노출 없음)

**Related**: NFR-SEC-04, NFR-SEC-05, NFR-SEC-09, NFR-SEC-15
**Priority**: MVP
**Personas**: Admin

---

### US-SEC-05: TLS 1.2+ 및 at-rest 암호화
- **As an** Admin,
- **I want** 모든 외부 트래픽은 TLS 1.2+, 저장 데이터(메타DB, Vault, 백업)는 at-rest 암호화되도록,
- **so that** SECURITY-01 베이스라인을 만족한다.

**AC**:
- **GIVEN** 배포된 시스템
- **WHEN** 외부에서 HTTP/HTTPS 요청
- **THEN** HTTP → HTTPS 리다이렉트, TLS < 1.2 거절
- **부정**: 백업 디스크가 평문 → 배포 단계에서 차단(IaC에 강제 적용)

**Related**: NFR-SEC-01
**Priority**: MVP
**Personas**: Admin

---

## Epic ADM — Administration

### US-ADM-01: 사용자/역할 관리 콘솔
- **As an** Admin,
- **I want** 사용자 목록/검색/역할 변경/비활성 처리를 콘솔에서 수행하고,
- **so that** 온/오프보딩을 일원화한다.

**AC**:
- **GIVEN** 1000명 이하 사용자
- **WHEN** 검색/필터/페이지네이션
- **THEN** 검색은 200ms 내 응답, 모든 변경은 감사 로그
- **부정**: 권한 없는 사용자 → 콘솔 진입 자체 차단

**Related**: FR-ADM-01, FR-AUTH-02
**Priority**: MVP
**Personas**: Admin

---

### US-ADM-02: 커넥션 관리 콘솔
- **As an** Admin,
- **I want** 등록된 커넥션을 한 화면에서 보고 편집/비활성/삭제할 수 있고,
- **so that** 데이터 액세스 정책을 빠르게 적용한다.

**AC**:
- **GIVEN** 등록된 커넥션 목록
- **WHEN** 편집/비활성/삭제
- **THEN** 활성 사용자 세션에는 다음 쿼리부터 영향 반영, Vault 자격증명 함께 회수
- **부정**: 실행 중 쿼리가 있는 커넥션 삭제 시도 → 경고 + 강제 종료 옵션

**Related**: FR-ADM-02, FR-DS-01~08
**Priority**: MVP
**Personas**: Admin

---

### US-ADM-03: PII 마스킹 패턴 관리
- **As an** Admin,
- **I want** PII 마스킹 표준 패턴(이름/주민번호/전화/이메일)을 추가·수정·비활성화하고,
- **so that** 정책 변경을 즉시 반영한다.

**AC**:
- **GIVEN** 패턴 관리 화면
- **WHEN** 신규 정규식 패턴 등록 → "테스트" 입력으로 매칭 확인
- **THEN** 저장 시 유효성 검증(정규식 컴파일 + 무한 루프 방지: 길이 한도), 즉시 마스킹 엔진에 반영
- **부정**: 악성 정규식(예: catastrophic backtracking) → 거절

**Related**: FR-ADM-04, FR-SEC-02
**Priority**: MVP
**Personas**: Admin
**PBT**: ✅ Domain-Generator (PII 후보 문자열 생성기 + 마스킹 결과 검증)

---

### US-ADM-04: 시스템 헬스 대시보드
- **As an** Admin,
- **I want** 서비스 상태/리소스/오류율을 Prometheus/Grafana 대시보드에서 보고,
- **so that** 장애를 사전에 감지한다.

**AC**:
- **GIVEN** Prometheus + Grafana 운영 중
- **WHEN** 대시보드 진입
- **THEN** 컴포넌트별 up/down, CPU/메모리/디스크/네트워크, 최근 5xx 비율, 알림 룰 상태 표시, 15초 단위 갱신
- **부정**: Prometheus 다운 → Grafana는 명확히 "데이터 없음" 표기

**Related**: FR-ADM-05, NFR-OBS-01, NFR-OBS-04, NFR-OBS-05
**Priority**: MVP
**Personas**: Admin

---

### US-ADM-05: 자동 백업 & 복구 검증
- **As an** Admin,
- **I want** 메타DB/사용자 워크스페이스가 일 1회 이상 자동 백업되고 복구 절차가 정기적으로 검증되고,
- **so that** 재해 시 복원 가능성을 보장한다.

**AC**:
- **GIVEN** 백업 스케줄 = 매일 02:00
- **WHEN** 백업 작업 실행
- **THEN** 성공/실패 결과 Prometheus 메트릭 + Grafana 알림, 월 1회 복구 리허설 자동 보고서
- **부정**: 백업 실패 3회 연속 → Admin/Auditor에 경보

**Related**: NFR-OBS-06, NFR-AUDIT-02
**Priority**: MVP
**Personas**: Admin, Auditor

---

# 🟠 Phase 2 Stories (Outline — 제목 + 의도만)

> Q-STR-3=B: Phase 2/3는 상세 AC를 해당 단계 도래 시 작성.

## Epic LLM — LLM 어시스턴트 (Phase 2)

- **US-LLM-01: Text-to-SQL** — 자연어 입력 → SQL 초안 생성. 사용자 검토 후 실행. (FR-LLM-01)
- **US-LLM-02: 데이터 요약/인사이트** — 결과 테이블을 한 줄로 요약·해석 코멘트 생성. (FR-LLM-02)
- **US-LLM-03: 코드 어시스턴트** — Python/R 셀 자동 완성·제안. (FR-LLM-03)
- **US-LLM-04: 사내 프록시 + 화이트리스트** — 모든 LLM 호출은 사내 프록시 경유, 허용 도메인 외 차단. (FR-LLM-04, NFR-SEC-07)
- **US-LLM-05: 송신 데이터 정책** — 초기엔 메타데이터(스키마)만 송신, 실데이터 송신은 보안팀 승인 후 활성화. 송신 페이로드 전수 로깅(Auditor 가시화). (FR-LLM-05, NFR-AUDIT-01)

## Epic RPT — Reporting (Phase 2)

- **US-RPT-01: 노트북 → PDF 다운로드** — (FR-RPT-01)
- **US-RPT-02: 노트북 → 웹 URL 공유(읽기 전용)** — (FR-RPT-02)
- **US-RPT-04: 보고서 템플릿 관리** — Admin이 템플릿 등록, Analyst가 데이터 매핑. (FR-RPT-04)
- **US-RPT-05: 정기 발송 스케줄** — 사내 메일/메신저로 PDF·링크 정기 전송. (FR-RPT-05)
- **US-VIS-Phase2: Superset 임베드** — 대시보드 임베드 패널. (FR-VIS-03)

## Epic ADV — Advanced (Phase 2)

- **US-DS-Phase2-DW**: 외부 DW 커넥터 — ClickHouse/Snowflake/BigQuery (화이트리스트 + 보안 검토). (FR-DS-03)
- **US-DS-Phase2-NoSQL**: NoSQL 커넥터 — MongoDB/Elasticsearch. (FR-DS-04)
- **US-SEC-Phase2-Column**: 컬럼 단위 권한 — 권한 없는 컬럼 자체를 결과에서 숨김. (FR-SEC-03)
- **US-SEC-Phase2-QueryReview**: 위험 쿼리 검토 — `SELECT *` 등 경고. (FR-SEC-04)
- **US-NB-Phase2-Search**: 노트북 검색 — 파일명/내용/태그. (FR-UI-07)
- **US-OBS-Phase2-Trace**: 분산 추적 — OpenTelemetry. (NFR-OBS-03)
- **US-DEPLOY-Phase2-K8s**: Kubernetes 마이그레이션 + Helm Chart. (NFR-DEPLOY-02)

---

# 🔴 Phase 3 Stories (Outline)

- **US-RPT-Phase3-PPTWord**: 노트북/대시보드 → PPT/Word 자동 생성. (FR-RPT-03)
- **US-AVL-Phase3-HA**: 24/7 HA 구성 검토 — Active/Standby + 데이터 복제. (NFR-AVL-03)

---

# 📊 G5. Traceability Matrix (Story ↔ FR/NFR ↔ Persona)

## FR ↔ Story

| FR ID | Stories |
|---|---|
| FR-AUTH-01 | US-AUTH-01 |
| FR-AUTH-02 | US-AUTH-02, US-ADM-01 |
| FR-AUTH-03 | US-AUTH-01, US-AUTH-03 |
| FR-AUTH-04 | US-AUTH-04 |
| FR-AUTH-05 | US-AUTH-05 |
| FR-DS-01 | US-DS-01, US-ADM-02 |
| FR-DS-02 | US-DS-02 |
| FR-DS-03 | US-DS-Phase2-DW |
| FR-DS-04 | US-DS-Phase2-NoSQL |
| FR-DS-05 | US-DS-06 |
| FR-DS-06 | US-DS-06, US-DS-07 |
| FR-DS-07 | US-DS-01, US-DS-04 |
| FR-DS-08 | US-DS-03, US-DS-05 |
| FR-UI-01 | US-NB-01 |
| FR-UI-02 | US-NB-02, US-NB-03, US-NB-06 |
| FR-UI-03 | US-DS-05 |
| FR-UI-04 | US-NB-02, US-NB-04 |
| FR-UI-05 | US-VIS-01 |
| FR-UI-06 | US-NB-05, US-AUTH-03 |
| FR-UI-07 | US-NB-Phase2-Search |
| FR-VIS-01 | US-VIS-01, US-VIS-02 |
| FR-VIS-02 | US-VIS-03 |
| FR-VIS-03 | US-VIS-Phase2 |
| FR-VIS-04 | US-VIS-01, US-VIS-02, US-VIS-04 |
| FR-RPT-01 | US-RPT-01 |
| FR-RPT-02 | US-RPT-02 |
| FR-RPT-03 | US-RPT-Phase3-PPTWord |
| FR-RPT-04 | US-RPT-04 |
| FR-RPT-05 | US-RPT-05 |
| FR-VCS-01 | US-SHARE-01 |
| FR-VCS-02 | US-SHARE-01, US-SHARE-02 |
| FR-VCS-03 | (Phase 2 — GitLab/Gitea UI 위임) |
| FR-VCS-04 | US-SHARE-03, US-SHARE-04 |
| FR-SEC-01 | US-SEC-01, US-SEC-03 |
| FR-SEC-02 | US-SEC-02, US-ADM-03, US-NB-02, US-VIS-02 |
| FR-SEC-03 | US-SEC-Phase2-Column |
| FR-SEC-04 | US-SEC-Phase2-QueryReview |
| FR-LLM-01 | US-LLM-01 |
| FR-LLM-02 | US-LLM-02 |
| FR-LLM-03 | US-LLM-03 |
| FR-LLM-04 | US-LLM-04 |
| FR-LLM-05 | US-LLM-05 |
| FR-ADM-01 | US-ADM-01 |
| FR-ADM-02 | US-ADM-02 |
| FR-ADM-03 | US-SEC-03 |
| FR-ADM-04 | US-ADM-03 |
| FR-ADM-05 | US-ADM-04 |

## NFR ↔ Story (선별 — 측정값/베이스라인 매핑이 명시된 것만)

| NFR ID | Stories |
|---|---|
| NFR-PERF-01 | US-NB-02, US-DS-05, US-NB-06 |
| NFR-PERF-02 | US-NB-03 |
| NFR-PERF-03 | US-NB-01 |
| NFR-PERF-04 | US-DS-06 |
| NFR-AVL-01 | (운영 SLA — 모든 스토리에 암묵적 적용) |
| NFR-SEC-01 | US-DS-01, US-DS-04, US-SEC-05 |
| NFR-SEC-02 | (인프라 레벨 — US-ADM-04 헬스에 포함) |
| NFR-SEC-03 | (애플리케이션 로깅 — US-SEC-01에 포함) |
| NFR-SEC-04 | US-AUTH-01, US-SEC-04 |
| NFR-SEC-05 | US-NB-02, US-SEC-04 |
| NFR-SEC-06 | US-AUTH-02, US-DS-03, US-DS-04, US-SHARE-04 |
| NFR-SEC-07 | US-DS-07, US-LLM-04 |
| NFR-SEC-08 | US-AUTH-02, US-DS-03, US-SEC-03, US-SHARE-04 |
| NFR-SEC-09 | US-AUTH-01, US-DS-02, US-SEC-04 |
| NFR-SEC-10 | (의존성 핀 — 빌드/배포 단계, 별도 스토리 없음) |
| NFR-SEC-11 | (Rate limiting — 게이트웨이 구성, 별도 스토리 없음 — Build/Test에서 검증) |
| NFR-SEC-12 | US-AUTH-01·03·04·05, US-DS-01·02·04 |
| NFR-SEC-13 | (Safe deserialization — 코드 레벨, Build/Test 검증) |
| NFR-SEC-14 | US-SEC-01, US-AUDIT-* |
| NFR-SEC-15 | US-SEC-04 |
| NFR-OBS-01·04·05·06 | US-ADM-04, US-ADM-05 |
| NFR-AUDIT-01·02 | US-SEC-01, US-ADM-05, US-LLM-05 |

## Persona ↔ Story (Coverage)

| Persona | MVP Stories |
|---|---|
| Admin | US-AUTH-02·04·05, US-DS-01·02·03·07, US-SEC-02·04·05, US-ADM-01~05 (15+) |
| Analyst | US-AUTH-01·03, US-DS-04·05·06·07, US-NB-01~06, US-VIS-01~04, US-SHARE-01~04 (20+) |
| Viewer | US-AUTH-01·03, US-VIS-02, US-SHARE-03·04 (5) |
| Auditor | US-AUTH-01·03, US-DS-03, US-SEC-01·02·03, US-ADM-05 (7) |

---

# 🔒 G6. Security Baseline 15 규칙 Cross-Check

| Rule | Mapping |
|---|---|
| SECURITY-01 (at-rest + TLS) | US-SEC-05 + US-DS-01·04 (Vault 암호화) |
| SECURITY-02 (액세스 로깅) | US-ADM-04 (헬스/로그 가시화), 인프라 레벨 |
| SECURITY-03 (구조화 로깅) | US-SEC-01 (correlation-id 포함) |
| SECURITY-04 (HTTP 보안 헤더) | US-SEC-04 |
| SECURITY-05 (입력 검증 + 파라미터화) | US-SEC-04 + US-NB-02 |
| SECURITY-06 (최소 권한) | US-AUTH-02 + US-DS-03·04 + US-SHARE-04 |
| SECURITY-07 (deny-by-default 네트워크) | US-DS-07 (sandbox) + US-LLM-04 (Phase 2 화이트리스트) |
| SECURITY-08 (애플리케이션 인가) | US-DS-03 + US-SEC-03 + US-SHARE-04 |
| SECURITY-09 (보안 하드닝) | US-AUTH-01 (일반화 메시지) + US-SEC-04 (스택 미노출) |
| SECURITY-10 (의존성/SBOM) | Build & Test 단계에서 강제 (빌드 인프라) |
| SECURITY-11 (모듈화 + Rate Limiting) | API Gateway 구성 — Construction 단계 |
| SECURITY-12 (인증 정책) | US-AUTH-01·03·04·05 + US-DS-01·02·04 |
| SECURITY-13 (무결성) | US-VIS-02 (차트 JSON 무결성), Safe deserialization — 코드 레벨 |
| SECURITY-14 (보안 알림 + append-only + 90일↑) | US-SEC-01 + US-ADM-05 (90일 → 1년 강화) |
| SECURITY-15 (fail-closed 예외 처리) | US-SEC-04 + US-SEC-01 (감사 저장소 불가 시 fail-closed) |

**결과**: 15개 규칙 모두 최소 1개 이상의 스토리 AC에 반영. 일부 규칙(10·11·13)은 빌드/인프라 레벨이라 별도 스토리 없이 **Construction 단계의 Build/Test 산출물**에서 강제하기로 합의.

---

# 🎲 G7. PBT 적용 가능 스토리 요약

| Story | PBT 기법 | 무엇을 검증 |
|---|---|---|
| US-AUTH-01 | State-Machine | 로그인/로그아웃/만료 상태 전이가 invariant 위반 없음 |
| US-AUTH-02 | Invariant | 활성 Admin ≥ 1 (절대 0 으로 떨어지지 않음) |
| US-AUTH-05 | Domain-Generator | 비밀번호 정책 통과 여부의 무작위 입력 검증 |
| US-DS-01 | Idempotent | 동일 입력 두 번 등록 → 결과 동일 또는 거절 |
| US-DS-03 | Invariant | 권한 없는 사용자에게는 어떤 객체도 노출 안 됨 |
| US-DS-04 | Idempotent + State-Machine | 등록 → 회전 → 삭제 흐름의 일관성 |
| US-DS-06 | Round-trip | CSV/Parquet 업로드-읽기-직렬화 동일성 |
| US-NB-02 | Oracle | PII 마스킹 결과 = 레퍼런스 정규식 결과 |
| US-SEC-01 | Invariant | 이벤트 수 ≤ 감사 로그 레코드 수 (유실 없음) |
| US-SEC-02 | Oracle + Idempotent | 마스킹 함수 vs 레퍼런스 + 재적용 시 동일 |
| US-ADM-03 | Domain-Generator | PII 문자열 생성기로 마스킹 룰 견고성 검증 |
| US-SHARE-01 | Idempotent | 동일 콘텐츠 재커밋 = no-op |
| US-SHARE-03 | Invariant | 권한 < 요구권한 → 항상 거절 |

(예시 기반 테스트 병행 — NFR-TEST-10 준수)

---

# ✅ G8. INVEST 자체 점검

| 기준 | 점검 결과 |
|---|---|
| **Independent** | 모든 스토리가 단일 도메인 안에서 완결. 외부 의존(예: US-NB-* → US-AUTH-01 SSO)은 가정 가능하므로 독립 |
| **Negotiable** | 구현 기술(예: "Plotly")은 명시되었으나 변경 가능(Q-TEC-1=A 반영, 그러나 후속 단계에서 동등 대체 가능) |
| **Valuable** | 모든 스토리에 "so that" 비즈니스 가치 절 포함 |
| **Estimable** | 각 스토리 1~3일 작업 단위로 분해 가능(Q-STR-1=A 준수) |
| **Small** | AC 항목 3~5개 수준, 더 크면 분할 권장(예: US-LLM-* 는 Phase 2 outline만) |
| **Testable** | GWT 형식 + 부정 케이스 + 측정값 → 자동화 가능 |

**결론**: MVP 40개 스토리 + Phase 2/3 outline 약 12개. INVEST 기준 모두 충족.

---

## 📌 변경 이력

- 2026-05-21: 초안 작성 (Q-PLAN-1=A 도메인 기반, F.1·F.2 결정사항 반영)
