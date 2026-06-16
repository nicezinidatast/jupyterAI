# Story Generation Plan — 내부망 데이터 분석 플랫폼

**작성일**: 2026-05-21
**기반 문서**: `aidlc-docs/inception/requirements/requirements.md`
**평가**: `aidlc-docs/inception/plans/user-stories-assessment.md` (Execute = Yes)

---

## A. 방법론 (Methodology)

### A.1 Story 형식
- **표준 템플릿**:
  ```
  US-<도메인>-<번호>: <짧은 제목>
    As a <persona>,
    I want <capability>,
    so that <business value>.

  Acceptance Criteria (Given/When/Then):
    - GIVEN ...
    - WHEN  ...
    - THEN  ...

  Related FR/NFR: FR-XX-NN, NFR-XX-NN
  Priority: MVP | Phase 2 | Phase 3
  Persona(s): Admin | Analyst | Data Scientist | Viewer
  ```

### A.2 INVEST 준수
- **Independent**: 다른 스토리 완료에 의존하지 않게 분할
- **Negotiable**: 구현 방식은 후속 단계로 위임
- **Valuable**: 페르소나의 실제 가치 명시 (so that 절)
- **Estimable**: 1~3일 작업 단위로 분해
- **Small**: 한 스토리 당 1~3개 acceptance criteria 정도 (필요 시 분할)
- **Testable**: GWT 또는 체크리스트로 검증 가능

### A.3 추적성
- 모든 스토리는 requirements.md의 FR/NFR ID와 양방향 매핑
- stories.md 말미에 traceability matrix 첨부

---

## B. 산출물 체크리스트 (Mandatory Artifacts)

- [x] `aidlc-docs/inception/user-stories/personas.md` — 4개 페르소나(Admin/Analyst/Viewer/Security Auditor)의 목표·페인포인트·일상 시나리오
- [x] `aidlc-docs/inception/user-stories/stories.md` — INVEST 준수 사용자 스토리 (MVP/Phase 2/Phase 3 마킹)
- [x] Acceptance Criteria — 모든 스토리에 포함 (G/W/T + 부정 케이스 + NFR 측정값)
- [x] Persona ↔ Story 매핑 — stories.md G5 섹션
- [x] FR/NFR ↔ Story 추적성 매트릭스 — stories.md G5 섹션

---

## C. 실행 단계 (Plan Execution Checkboxes)

### Part 2 (생성) 단계
- [x] **Step G1**: personas.md 작성 — 4개 페르소나의 골/페인/일상
- [x] **Step G2**: 도메인 단위로 epic 정의 (Auth, Data Source, Notebook, Visualization, Sharing, Security/Audit, Admin, LLM, Reporting)
- [x] **Step G3**: epic 별 MVP 스토리 작성 (INVEST + AC) — 40 stories
- [x] **Step G4**: Phase 2 / Phase 3 스토리 작성 (마킹) — 12 outlines
- [x] **Step G5**: Traceability matrix 생성 (Story ↔ FR/NFR ↔ Persona)
- [x] **Step G6**: Security Baseline 15 규칙 cross-check (10·11·13은 빌드/인프라 단계 위임)
- [x] **Step G7**: PBT 적용 가능 스토리 표시(13개 식별)
- [x] **Step G8**: INVEST 자체 점검 통과

---

## D. 스토리 분류 접근법 옵션 (Story Breakdown Approaches)

다음 5가지 중 어떤 방식으로 분류·정리할지 골라주세요. (선택지에 대한 trade-off는 옆에 적었습니다.)

| 옵션 | 설명 | 장점 | 단점 |
|---|---|---|---|
| **A. Feature/Domain-Based** | 도메인별로 묶음 (Auth, Data Source, Notebook…) — Epic = 도메인 | 요구사항 매핑이 단순, 팀 분할 쉬움 | 사용자 여정 단절 가능 |
| **B. User Journey-Based** | 분석가의 "로그인 → 커넥션 선택 → 쿼리 → 차트 → 공유" 흐름 따라 정렬 | UX 일관성 ↑, 데모 시연 자연스러움 | 횡단 관심사(보안, 감사) 분산 |
| **C. Persona-Based** | 각 페르소나(Admin/Analyst/DS/Viewer) 별로 묶음 | 페르소나별 가치 명확 | 동일 기능이 여러 페르소나에 중복 출현 |
| **D. Epic-Based (계층형)** | Epic → Feature → Story 3단 계층, MVP/Phase 2 별로 분리 | 로드맵 관리 용이 | 문서가 길어짐 |
| **E. Hybrid (도메인 + 페르소나 그리드)** | 1차 도메인 정렬 + 2차 페르소나 매핑 표 | A의 장점 + 페르소나 가시성 | 작성 비용 ↑ |

### Q-PLAN-1: 스토리 분류 방식
**[Answer]**: A<!-- A/B/C/D/E 중 하나, 또는 조합. 권장: E (Hybrid: 도메인 1차 + 페르소나 매핑) -->

---

## E. Clarification Questions (사용자 입력 필요)

> 형식: 각 질문에 `[Answer]:` 뒤에 답을 적어주세요. 객관식은 알파벳(A/B/C…) 또는 복수 선택 가능.

---

### 1. 페르소나 (Personas)

#### Q-USR-1: 페르소나 4종(Admin / Analyst / Data Scientist / Viewer)이면 충분한가요? 추가/통합할 페르소나가 있나요?
- A) 4종 그대로 유지
- B) Analyst와 Data Scientist를 하나로 통합 (도구·권한이 거의 같으므로)
- C) "데이터 엔지니어"(커넥션·ETL 관리 담당) 페르소나 추가
- D) "보안 감사관"(감사 로그 조회 전용) 페르소나 추가
- E) 기타 (직접 기재)

**[Answer]**: B, D

#### Q-USR-2: 각 페르소나의 1차 페인포인트는 무엇인가요? (현재 가장 큰 불편) — 알고 계신 것만 적어주세요. 모르면 "AI가 합리적 추정으로 작성" 적어주세요.
- Admin: **[Answer]**:
- Analyst: **[Answer]**:
- Data Scientist: **[Answer]**:
- Viewer: **[Answer]**:

#### Q-USR-3: 페르소나별 사용 빈도/시간 — 일과 중 이 플랫폼에서 보내는 비중을 알 수 있나요?
- A) 모름 — AI가 합리적 가정으로 작성
- B) 알고 있음 (직접 기재)

**[Answer]**: A

---

### 2. 스토리 세분화 (Granularity)

#### Q-STR-1: 스토리 크기(estimable) 기준을 어떻게 잡을까요?
- A) 1~3일 작업 단위 (권장 — INVEST의 Small 적용)
- B) 1주 작업 단위 (큰 단위, 빠른 작성)
- C) 0.5~2일 작업 단위 (매우 세분, 스토리 수 증가)

**[Answer]**: A

#### Q-STR-2: MVP 스토리는 대략 몇 개를 목표로 할까요? (작성 깊이 결정)
- A) ~20개 (도메인 별 핵심만)
- B) **~30~40개 (도메인 별 핵심 + 부가 흐름) — 권장**
- C) ~50개+ (모든 흐름 망라, 작성·리뷰 비용 ↑)

**[Answer]**: B

#### Q-STR-3: Phase 2/3 스토리도 같은 깊이로 작성할까요?
- A) MVP와 동일 깊이
- B) **Phase 2는 개요만 (간략 제목 + 의도), 상세는 해당 단계 도래 시 — 권장**
- C) Phase 2/3는 이번 단계에서 스킵 (요구사항 문서로만 추적)

**[Answer]**: B

---

### 3. Acceptance Criteria 형식

#### Q-AC-1: AC 형식 선호
- A) **Given/When/Then (Gherkin 스타일) — 권장 (PBT/예시 테스트로 변환 용이)**
- B) 체크리스트(불릿) 형식 (간결, 비기술자 가독성 ↑)
- C) 두 형식 혼용 (기능 스토리 = G/W/T, 비기능 스토리 = 체크리스트)

**[Answer]**: A

#### Q-AC-2: 각 스토리에 부정 케이스(예: 권한 거부, 잘못된 입력)도 AC에 포함할까요?
- A) **모든 스토리에 1개 이상의 부정 케이스 포함 — 권장 (보안·PBT 관점)**
- B) 보안·인증·권한 관련 스토리에만 포함
- C) 부정 케이스는 별도 스토리로 분리

**[Answer]**: A

#### Q-AC-3: 비기능(NFR) 측정값(예: 응답 5초 이하)을 AC에 명시할까요?
- A) **명시 — 측정 가능한 NFR은 그대로 AC에 — 권장**
- B) 별도 NFR 문서로만 (스토리는 기능 중심)
- C) 핵심 NFR(성능·보안)만 명시

**[Answer]**: A

---

### 4. 비즈니스 컨텍스트 (Business Context)

#### Q-BIZ-1: 이 플랫폼의 성공 지표(Success Metric)는 무엇인가요? (스토리 가치 평가 기준)
- A) 모름 — AI가 합리적 가정으로 작성(예: 활성 사용자 수, 노트북 작성 수, 분석 → 의사결정 전환율)
- B) 알고 있음 (직접 기재)

**[Answer]**:A

#### Q-BIZ-2: MVP 출시 시 가장 먼저 검증하고 싶은 가설은?
- A) "분석가가 외부 도구 없이 사내망 안에서 SQL+시각화를 끝낼 수 있다"
- B) "관리자가 데이터 접근/PII 통제를 일원화할 수 있다"
- C) "비즈니스 사용자(Viewer)가 결과를 자가 열람할 수 있다"
- D) 모두 — 우선순위는 A > B > C
- E) 기타 (직접 기재)

**[Answer]**: D

---

### 5. 기술적 제약 (Technical Constraints)

#### Q-TEC-1: 스토리에 기술 구현 힌트(예: Keycloak, JupyterHub)를 포함할까요?
- A) **포함 — 이미 결정된 기술 스택은 AC에 반영 (예: "Keycloak SSO 사용") — 권장**
- B) 제외 — 스토리는 기술 중립
- C) Epic 수준 메모로만 (스토리 본문은 중립)

**[Answer]**:A

#### Q-TEC-2: 신규 통합 포인트(LLM, 사내 Git, 외부 DW 등)에 대한 스토리는 어떻게 다룰까요?
- A) **각각 별도 스토리 — 권장 (가치 명확)**
- B) "외부 시스템 통합" Epic 하나로 묶음
- C) MVP는 Git/Keycloak/사내 DB만, 나머지는 Phase 2 스토리로

**[Answer]**:A

---

### 6. 사용자 여정 (User Journey) — 분류 옵션 E(Hybrid) 또는 B(Journey) 선택 시에만

#### Q-JRN-1: 분석가의 "Golden Path"(가장 일반적 사용 흐름)는 다음 중 어디서 시작해서 끝나나요? (스토리 정렬 기준)
- A) SSO 로그인 → 커넥션 선택 → SQL → 차트 → 노트북 저장 → Git 커밋
- B) SSO 로그인 → 파일 업로드 → 파이썬 분석 → 시각화 → 보고서
- C) **A와 B 둘 다 — 두 경로 모두 1차 시민으로 — 권장**
- D) 기타 (직접 기재)

**[Answer]**:C

---

## F. 사용자 답변 종합 후 절차

1. 위 [Answer]:를 모두 채워 다시 보내주세요. ✅ (2026-05-21 완료)
2. AI가 답변에서 모호함을 분석합니다(Step 9·10). ✅
3. 모호함이 있으면 별도 `story-generation-clarification.md`로 추가 질문. → 경미한 모호함 2건은 합리적 가정으로 처리(아래 F.1 참조).
4. 모호함이 없으면 본 plan을 **승인 요청**합니다. ⏳ 현재 단계
5. 승인 후 Part 2(생성) — personas.md / stories.md 생성에 착수합니다.

### F.1 확정된 결정사항 (Decisions Summary — 2026-05-21)

| 항목 | 결정 | 출처 |
|---|---|---|
| 페르소나 (4종) | Admin / **Analyst (SQL+Python/R 통합)** / Viewer / **Security Auditor (신규)** | Q-USR-1=B,D + 가정 |
| 분류 방식 | **A. Domain/Feature-Based** (Epic = 도메인) | Q-PLAN-1=A |
| 스토리 크기 | 1~3일 작업 단위 | Q-STR-1=A |
| MVP 스토리 수 | ~30~40개 | Q-STR-2=B |
| Phase 2/3 스토리 | 개요만 (제목 + 의도) | Q-STR-3=B |
| AC 형식 | Given/When/Then (Gherkin) | Q-AC-1=A |
| 부정 케이스 | 모든 스토리에 1개 이상 | Q-AC-2=A |
| NFR 값 | 측정 가능한 NFR은 AC에 명시 | Q-AC-3=A |
| 성공 지표 | AI 합리적 추정 (활성사용자·노트북생성수·분석→의사결정 전환율) | Q-BIZ-1=A |
| MVP 가설 우선순위 | A > B > C | Q-BIZ-2=D |
| 기술 힌트 | 결정된 기술스택은 AC에 반영 (Keycloak, JupyterLab 등) | Q-TEC-1=A |
| 통합 포인트 | 각 통합(Git/LLM/외부DW)마다 별도 스토리 | Q-TEC-2=A |
| Golden Path | SQL-Centric + Notebook-Centric 둘 다 1급 | Q-JRN-1=C |
| 페인포인트 | AI 합리적 추정 | Q-USR-2=공란 |
| 사용 빈도 | AI 합리적 추정 | Q-USR-3=A |

### F.2 합리적 가정 (Reasonable Assumptions)

- **A1**: Analyst + Data Scientist 통합 페르소나의 이름 = **"Analyst"**. 본문에서 "SQL 분석가 + Python/R 사이언티스트 둘 다 포함, 권한·도구 동일"로 명시. 권한 분기 필요 시 sub-role로 표기.
- **A2**: Q-JRN-1=C는 Domain-Based 분류 안에서 Notebook/Visualization Epic 내부에 SQL-Centric·Notebook-Centric 두 흐름을 모두 스토리화 하는 것으로 해석.
- **A3**: `requirements.md` Section 3 페르소나 표는 Part 2 시작 시 신규 4종(Admin/Analyst/Viewer/Security Auditor)으로 동기화.

### F.3 산출물 영향

위 결정사항을 반영하여 다음과 같이 작성:
- `personas.md`: 4종(Admin/Analyst/Viewer/Security Auditor), 골/페인포인트(추정)/일과 시나리오/플랫폼 사용 빈도(추정)
- `stories.md`: Epic = 도메인(Auth, Data Source, Notebook & SQL, File & Analysis, Visualization, Sharing & VCS, Security/Audit, Admin, [Phase 2] LLM, [Phase 2] Reporting). 30~40개 MVP 스토리 + Phase 2/3 스토리는 제목/의도만. GWT AC + 부정 케이스 + NFR 측정값 + FR/NFR ID 매핑.

---

## G. 예상 산출물 미리보기 (Sample — 최종이 아님)

> Q-PLAN-1=E(Hybrid) + Q-STR-2=B(~30~40개) 가정 시 예시.

**Epic: Authentication & Session**
- US-AUTH-01: 분석가는 SSO(Keycloak)로 로그인할 수 있다.
- US-AUTH-02: 관리자는 사용자 역할을 변경할 수 있다.
- US-AUTH-03: 세션 만료 시 자동 로그아웃되고 작업이 손실되지 않는다.

**Epic: Data Source**
- US-DS-01: 분석가는 등록된 RDBMS 커넥션 목록을 사이드 패널에서 본다.
- US-DS-02: 분석가는 개인 자격증명을 등록·회전·삭제할 수 있다.
- US-DS-03: 관리자는 부서별로 커넥션 접근 권한을 부여할 수 있다.

…(이런 식으로 도메인별로 정렬)

---

**다음 단계**: 위 [Answer]:들을 채우고 "완료" 라고 답해주세요.
