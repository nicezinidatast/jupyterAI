# 요구사항 명확화 질문 (Requirement Verification Questions)

**프로젝트**: 내부망 데이터 분석 플랫폼

각 질문에 대해 알맞은 보기의 알파벳을 `[Answer]:` 태그 뒤에 적어주세요.
어느 보기도 맞지 않다면 마지막 옵션(`Other`)을 선택하고 직접 설명을 적어주세요.
모두 작성한 후 "완료" 또는 "done"이라고 알려주세요.

---

## 1부: 프로젝트 비전 및 사용자

### Question 1
이 플랫폼의 주요 사용자 규모는 어느 정도인가요?

A) 소규모 팀 (5명 이하)
B) 부서 단위 (10~50명)
C) 전사 (수백 명)
D) 대규모 (1,000명 이상)
E) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 2
플랫폼을 사용할 주요 사용자 유형은 누구인가요? (가장 가까운 것 하나)

A) 데이터 분석가만 (SQL/시각화 중심)
B) 데이터 분석가 + 데이터 사이언티스트 (Python/ML 포함)
C) 데이터 분석가 + 비즈니스 사용자 (리포트 소비자 포함)
D) 데이터 분석가 + 사이언티스트 + 비즈니스 사용자 (모두 포함)
E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

### Question 3
사용자별 권한 분리가 필요한가요?

A) 필요 — 역할 기반 권한(RBAC): 관리자/분석가/뷰어 등 구분
B) 필요 — 데이터 소스 단위로 권한 분리 (예: A 분석가는 DB1만)
C) 필요 — 행/열 단위 권한 (Row/Column Level Security)
D) 불필요 — 모든 사용자가 동일 권한
E) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 4
인증 방식은 무엇을 사용하나요?

A) 사내 SSO/LDAP/AD 연동
B) OAuth2 / OpenID Connect (Keycloak 등 자체 호스팅 IdP)
C) 자체 ID/PW 회원가입
D) 아직 미정 — 추천 부탁
E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## 2부: 데이터 소스 및 연결

### Question 5
어떤 종류의 데이터베이스를 연결해야 하나요? (해당하는 것 모두 적어주세요, 콤마 구분)

A) PostgreSQL / MySQL / Oracle / MS SQL Server 등 RDBMS
B) Hive / Impala / Presto / Trino 등 빅데이터 SQL 엔진
C) ClickHouse / Snowflake / BigQuery 등 분석 DW
D) MongoDB / Elasticsearch 등 NoSQL
E) Other (please describe after [Answer]: tag below)

[Answer]: A,B,C,D

---

### Question 6
파일 데이터 소스는 무엇을 지원해야 하나요?

A) CSV / Excel 위주
B) CSV / Excel + Parquet / Feather (대용량 분석 포맷)
C) JSON / XML 포함
D) 모든 일반 포맷 (CSV/Excel/Parquet/JSON/TSV 등)
E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

### Question 7
파일 업로드/저장 방식은 어떻게 처리하나요?

A) 사용자가 로컬에서 업로드 (서버 디스크에 저장)
B) 사내 공유 스토리지 마운트 (NAS, S3 호환 MinIO 등)
C) 둘 다 지원
D) 아직 미정
E) Other (please describe after [Answer]: tag below)

[Answer]: C

---

### Question 8
데이터 소스 연결 정보(접속 정보, 비밀번호 등)는 어떻게 관리하나요?

A) 사용자 개인이 본인 자격증명 입력하여 사용
B) 관리자가 공용 커넥션을 등록, 사용자는 권한 받아 사용
C) 둘 다 지원 (공용 + 개인)
D) 아직 미정 — 추천 부탁
E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

### Question 9
처리 가능해야 하는 데이터 규모는 대략 어느 정도인가요? (가장 큰 케이스 기준)

A) 작음 (단일 쿼리/파일 < 100MB, 행 수 < 1백만)
B) 중간 (단일 쿼리/파일 < 10GB, 행 수 < 1억)
C) 큼 (단일 쿼리/파일 > 10GB, 행 수 > 1억) — 분산 처리 필요할 수 있음
D) 아직 모름
E) Other (please describe after [Answer]: tag below)

[Answer]: B 

---

## 3부: 분석 인터페이스 (Jupyter류)

### Question 10
"주피터랩처럼"이라고 하셨는데, 어떤 형태가 가장 가까운가요?

A) JupyterLab/JupyterHub를 그대로 호스팅하고 기능을 확장
B) 노트북 UX를 모방한 자체 웹 IDE (셀 단위 실행, 마크다운 등)
C) 노트북이 아닌 대시보드형 워크벤치 (쿼리 에디터 + 시각화 패널)
D) 노트북 + 대시보드 둘 다 (탭이나 모드 전환)
E) Other (please describe after [Answer]: tag below)

[Answer]: 주피터랩, 허브가 무료로 상업에 사용할 수 있으면 A, 그렇지 않으면 B

---

### Question 11
분석가가 작성/실행할 수 있는 언어는 어떤 것을 지원해야 하나요?

A) SQL만
B) SQL + Python
C) SQL + Python + R
D) SQL + Python + 노코드 GUI (드래그앤드롭)
E) Other (please describe after [Answer]: tag below)

[Answer]: C

---

### Question 12
사용자가 작성한 노트북/쿼리/대시보드를 다른 사용자와 공유하는 기능이 필요한가요?

A) 필요 — 워크스페이스/폴더 단위 공유 + 권한 제어
B) 필요 — 단순 링크 공유만
C) 필요 — Git 연동(버전 관리 포함)
D) 불필요 — 개인 작업 위주
E) Other (please describe after [Answer]: tag below)

[Answer]: C

---

### Question 13
사용자가 작성한 결과물의 저장/버전 관리는?

A) DB에 메타데이터 + 파일로 저장 (자체 관리)
B) 사내 Git (GitLab/Gitea 등)에 자동 연동
C) 단순 자동 저장, 버전 관리 없음
D) 아직 미정
E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## 4부: 시각화 및 리포트

### Question 14
차트/그래프 라이브러리는 어떤 것이 선호되나요?

A) Plotly / ECharts 등 인터랙티브 차트 (줌, 호버 등)
B) Matplotlib / Seaborn 같은 정적 이미지 차트
C) Apache Superset 또는 Metabase 임베드
D) 모두 지원
E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

### Question 15
"보고서"는 어떤 형태인가요?

A) PDF 다운로드 (정적 리포트)
B) 웹 대시보드 형태 (URL 공유, 인터랙티브)
C) PPT / Word 자동 생성
D) A + B 모두 (PDF + 웹 대시보드)
E) Other (please describe after [Answer]: tag below)

[Answer]: A,B,C

---

### Question 16
리포트를 스케줄링 발송(예: 매주 월요일 9시 메일 발송)할 필요가 있나요?

A) 필요 — 사내 메일/메신저로 정기 발송
B) 필요 — URL/대시보드 갱신만, 발송은 없음
C) 불필요 — 사용자가 직접 실행
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 17
리포트 템플릿 기능이 필요한가요?

A) 필요 — 관리자가 템플릿 만들고 분석가들이 재사용
B) 필요 — 분석가 본인이 자기 템플릿 저장/재사용
C) 둘 다
D) 불필요 — 매번 새로 작성
E) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## 5부: 배포 환경 및 인프라

### Question 18
"내부망"이라고 하셨는데, 인터넷 연결 정책은?

A) 완전 폐쇄망 (외부 인터넷 불가, 패키지/도커 이미지도 사내 미러로만)
B) 제한적 외부망 (특정 도메인 화이트리스트만 허용)
C) 사내망이지만 외부 인터넷 가능
D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 19
배포 인프라는 무엇인가요?

A) Kubernetes 클러스터 (온프레미스)
B) Docker Compose / Docker Swarm
C) 일반 VM (k8s 없음)
D) 베어메탈 서버 직접 배포
E) Other (please describe after [Answer]: tag below)

[Answer]: 아직 모르겠어

---

### Question 20
운영체제 환경은?

A) Linux (RHEL/CentOS/Ubuntu 등) — 권장
B) Windows Server
C) 혼합
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 21
주된 사용자 클라이언트 환경은?

A) 사내 웹 브라우저 (Chrome/Edge 최신)
B) 사내 웹 브라우저 (IE11 또는 구형 포함)
C) 데스크톱 앱 형태 (Electron 등) 도 검토
D) Other (please describe after [Answer]: tag below)

[Answer]: A,B

---

## 6부: 비기능 요구사항 (NFR)

### Question 22
동시 활성 사용자는 최대 몇 명까지 가정하나요?

A) 10명 이하
B) 10~50명
C) 50~200명
D) 200명 이상
E) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 23
쿼리/실행 결과의 응답 시간 목표는?

A) 일반 쿼리 1~3초, 큰 쿼리는 백그라운드 처리
B) 일반 쿼리 5초 이내면 OK, 큰 쿼리도 동기 가능
C) 최선 노력 (SLA 없음)
D) Other (please describe after [Answer]: tag below)

[Answer]: C

---

### Question 24
사용자 작업의 가용성(고가용성)이 필요한가요?

A) 필요 — 24/7, 단일 장애점 없음 (HA 구성, 페일오버)
B) 업무 시간(예: 평일 9~18시) 안정 운영이면 충분
C) 베스트 에포트
D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 25
데이터 감사(audit) / 사용자 활동 로깅 요구가 있나요?

A) 필요 — 누가 언제 어떤 쿼리/데이터에 접근했는지 전수 기록 (감사/컴플라이언스)
B) 필요 — 단순 접근 로그만
C) 불필요
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 26
개인정보/민감정보 마스킹 또는 보호 요구가 있나요?

A) 필요 — 자동 마스킹(이름/주민번호 등 PII)
B) 필요 — 권한 없는 사용자에게는 컬럼 숨김
C) 불필요
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## 7부: 일정 및 우선순위

### Question 27
원하시는 MVP(최소 기능 제품) 출시 시기는?

A) 1~2개월 내 (필수 기능만)
B) 3~6개월 내 (표준 구성)
C) 6개월 이상 (완성도 우선)
D) 미정 — 점진 출시
E) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 28
MVP에 반드시 포함되어야 하는 핵심 기능 우선순위를 매겨주세요. (가장 중요한 것부터 콤마로)

보기:
1) DB 커넥션 관리 + SQL 에디터
2) 파일 업로드 후 분석
3) 차트/시각화
4) 보고서(PDF/대시보드)
5) 사용자 인증/권한
6) 노트북(Python 등) 실행
7) 공유/협업
8) 스케줄링

예) `[Answer]: 1, 3, 5, 4, 6, 2, 7, 8`

[Answer]: 1,2,3,6

---

## 8부: 확장 모듈 (Extensions)

### Question 29: Security Extensions
이 프로젝트에 보안 확장 규칙을 적용할까요?

A) 적용 — 모든 SECURITY 규칙을 차단 제약(blocking)으로 강제 (운영 등급 권장)
B) 적용 안 함 — 모든 SECURITY 규칙 스킵 (PoC/프로토타입에 적합)
X) Other (please describe after [Answer]: tag below)

[Answer]: 1

---

### Question 30: Property-Based Testing Extension
이 프로젝트에 PBT(속성 기반 테스트) 규칙을 적용할까요?

A) 적용 — 모든 PBT 규칙을 차단 제약으로 강제 (비즈니스 로직, 데이터 변환, 직렬화, 상태 컴포넌트가 있는 프로젝트에 권장)
B) 부분 적용 — 순수 함수와 직렬화 라운드트립에만 PBT 규칙 적용 (제한적 알고리즘 복잡도)
C) 적용 안 함 — 모든 PBT 규칙 스킵 (단순 CRUD, UI 전용, 얇은 통합 레이어에 적합)
X) Other (please describe after [Answer]: tag below)

[Answer]: 1

---

## 9부: 자유 입력

### Question 31
이 외에 꼭 알려주고 싶거나, 참고했으면 하는 기존 도구/사례가 있나요?
(예: "Redash와 Superset의 좋은 점을 합쳤으면 좋겠다", "사내에 이미 X 시스템이 있어서 연동 필요" 등)

[Answer]: fabi.ai 가 온프레미스로 가는 느낌이면 좋겠음. 내부망은 api에서, 모델은 외부에 띄우는 방식으로 하면 보안과 속도를 다 잡을 수 있지 않을까.

---

### Question 32
이번 단계에서 본인이 우려하는 가장 큰 리스크나 제약 조건이 있다면 자유롭게 적어주세요.

[Answer]: 이렇게 만들어서 오류가 발생하면 어떻게 수정해야할지 모르겠음.

---

**작성을 모두 마치셨다면 "완료" 또는 "done"이라고 알려주세요.** 답변에 모순이나 모호한 점이 있으면 추가 질문지를 만들 수 있고, 명확하다면 요구사항 문서(`requirements.md`) 작성으로 진행하겠습니다.
