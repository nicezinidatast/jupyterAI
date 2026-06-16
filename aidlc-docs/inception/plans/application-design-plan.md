# Application Design Plan — 내부망 데이터 분석 플랫폼

**작성일**: 2026-05-21
**기반 입력**: `requirements.md`, `stories.md`, `personas.md`, `execution-plan.md`
**목표**: 고수준 컴포넌트 식별 + 서비스 레이어 설계 (상세 비즈니스 룰은 Functional Design 단계로 위임)

---

## A. 방법론 (Methodology)

- **컴포넌트 단위**: 단일 책임. 한 컴포넌트는 한 도메인 책임만 가짐
- **서비스 레이어**: 여러 컴포넌트를 오케스트레이션하는 얇은 레이어. 트랜잭션·인증·감사 횡단 관심사 처리
- **의존성 방향**: acyclic. 상위 → 하위 단방향
- **통신 패턴**: 동기(HTTP/JSON, gRPC 후보) vs 비동기(이벤트 큐) 둘 다 사용. AC에 명시
- **횡단 관심사(Cross-Cutting)**: Auth/Audit/Telemetry는 모든 컴포넌트에서 공통 라이브러리로 흡수
- **Plan now / Build later**: 본 단계에서는 컴포넌트의 *책임*과 *인터페이스 형태*만 정한다. 메서드 시그니처 수준까지만 작성. 비즈니스 룰 디테일은 Functional Design

---

## B. 산출물 체크리스트 (Mandatory Artifacts)

- [x] `aidlc-docs/inception/application-design/components.md` — 컴포넌트 정의 + 책임 + 인터페이스 (30 모듈)
- [x] `aidlc-docs/inception/application-design/component-methods.md` — 메서드 시그니처 (high-level)
- [x] `aidlc-docs/inception/application-design/services.md` — 서비스 레이어 정의 + 오케스트레이션 (6 서비스)
- [x] `aidlc-docs/inception/application-design/component-dependency.md` — 의존성 매트릭스 + 통신 패턴 + 데이터 흐름
- [x] `aidlc-docs/inception/application-design/application-design.md` — 통합 마스터 문서
- [x] 설계 일관성 + 완전성 검증 (acyclic ✓, 40 스토리 모두 매핑 ✓, 횡단 관심사 누락 없음 ✓, 보안/PBT 위치 식별 ✓)

---

## C. 실행 단계 (Plan Execution Checkboxes)

### Part 2 (생성) 단계
- [x] **Step D1**: 컴포넌트 식별 — 23 도메인 + 3 UI + 4 SL = 30 모듈
- [x] **Step D2**: components.md + component-methods.md 작성
- [x] **Step D3**: services.md — 6 서비스
- [x] **Step D4**: component-dependency.md — 매트릭스 + 동기/비동기 패턴 + Mermaid 데이터 흐름
- [x] **Step D5**: application-design.md 통합 마스터
- [x] **Step D6**: 검증 — acyclic ✓ / 40 MVP 스토리 모두 매핑 ✓ / 횡단 관심사 누락 없음 ✓ / SECURITY 15 + PBT 13 위치 식별 ✓

---

## D. Clarification Questions (사용자 입력 필요)

> 형식: 각 질문에 `[Answer]:` 뒤에 답을 적어주세요. 객관식은 알파벳(A/B/C…) 또는 복수 선택 가능. "권장"이라고 답하면 권장 옵션으로 진행합니다.

---

### 1. 컴포넌트 식별 (Component Identification)

#### Q-AD-1: 컴포넌트 입자 크기 (Granularity)
한 도메인 안에서 컴포넌트를 어디까지 세분할지 결정합니다.

- A) **유닛 = 컴포넌트** (1:1, 굵은 입자 7~10개) — 빠르게 진행, 후속 세분은 Functional Design에서
- B) **유닛 안에 2~4개 컴포넌트** (중간 입자, 15~25개) — 권장. 책임 명확 + 테스트 용이
- C) **세밀한 입자 30개+** — DDD 스타일, 작성·리뷰 비용↑

**[Answer]**: B

#### Q-AD-2: 횡단 관심사(Cross-Cutting) 처리
인증 토큰 검증, 감사 로그 발행, 트레이스 ID 전파 등 모든 컴포넌트에 공통으로 필요.

- A) **공통 라이브러리(공유 패키지)** — 모든 컴포넌트가 import. 권장 (폐쇄망 + 통일된 동작)
- B) 사이드카(sidecar) 컨테이너 패턴 — k8s 마이그레이션 시 유리
- C) API Gateway에만 두고 컴포넌트는 신뢰 — 단순하나 보안 책임이 게이트웨이 단일점에 집중

**[Answer]**:A

#### Q-AD-3: UI 컴포넌트 처리
JupyterLab은 외부 OSS. 자체 UI는 어떻게 다룰까요?

- A) **JupyterLab Extension(들) + 분리된 Admin/Audit UI(SPA)** — 권장. 분석가는 JupyterLab 안, 관리자는 별도 페이지
- B) 모든 UI를 단일 SPA로 통합 (JupyterLab을 iframe 임베드)
- C) JupyterLab을 그대로 두고 Admin/Audit는 GitLab/Keycloak UI 위임

**[Answer]**: A

---

### 2. 컴포넌트 메서드 (Component Methods)

#### Q-AD-4: 메서드 시그니처 표기 언어
컴포넌트 인터페이스를 어떻게 표기할까요? (이번 단계에서는 시그니처만, 구현 언어 결정은 NFR Requirements 단계)

- A) **언어 중립 의사 시그니처** (TypeScript-ish, e.g. `register(conn: Connection): Result<ConnectionId>`) — 권장
- B) OpenAPI 3.0 스니펫 (HTTP REST 가정)
- C) gRPC `.proto` (gRPC 가정)

**[Answer]**: A

#### Q-AD-5: 에러 표현 방식
모든 메서드의 실패 표현을 어떻게 통일할까요?

- A) **Result/Either 패턴**: 성공·실패를 값으로 (검증 친화) — 권장
- B) 예외 throw (전통적)
- C) 두 가지 혼용 (도메인 오류=값, 시스템 오류=예외)

**[Answer]**: A

---

### 3. 서비스 레이어 (Service Layer)

#### Q-AD-6: 서비스 오케스트레이션 패턴
여러 컴포넌트를 묶어 한 사용자 동작을 처리합니다 (예: 쿼리 실행 = 권한 검사 → 커넥션 획득 → 쿼리 → 마스킹 → 감사).

- A) **얇은 서비스 + 컴포넌트가 일을 함** (Domain-Driven, 권장) — 서비스는 트랜잭션·감사만, 도메인 로직은 컴포넌트
- B) 두꺼운 서비스 + 빈약한 컴포넌트 (Transaction Script 스타일) — 단순하나 도메인 응집도↓
- C) 사가(Saga) 패턴 — 비동기 다단계 처리에만 한정

**[Answer]**: A

#### Q-AD-7: 서비스 경계의 단위
"서비스"의 정의를 어떻게 잡을까요?

- A) **도메인 단위 서비스** (예: NotebookService, ConnectionService) — 권장
- B) 기능 단위 서비스 (예: ShareNotebookService, RunQueryService) — UseCase 패턴
- C) Bounded Context 단위 서비스 — Aggregate 단위 일치

**[Answer]**:A

---

### 4. 컴포넌트 의존성 & 통신 (Dependencies & Communication)

#### Q-AD-8: 컴포넌트 간 동기/비동기 기본값
- A) **기본 동기(HTTP/JSON 또는 in-process call)**, 명시적으로 비동기인 것만 큐 사용 (감사 발행, Git push, LLM 호출) — 권장
- B) 기본 비동기(이벤트 기반) — 일관성·확장성↑, MVP에 과한 복잡도
- C) 사람 친화: in-process 모놀리스 + 일부만 큐 — 가장 단순

**[Answer]**: A

#### Q-AD-9: 이벤트 버스/큐 기술 후보
비동기 흐름에 어떤 메시지 백엔드를 가정할까요? (확정은 NFR Design 단계, 본 단계는 가정)

- A) **Redis Streams 또는 RabbitMQ** (가벼움, 사내 친화) — 권장
- B) Kafka — 처리량↑, 운영 부담↑
- C) DB 폴링 (outbox 패턴) — 최소 의존성

**[Answer]**: A

#### Q-AD-10: 외부 시스템 어댑터 (Anti-Corruption Layer)
Keycloak/Vault/GitLab/사내 DB/LLM 등 외부 시스템과의 결합을 어떻게 다룰까요?

- A) **모든 외부 시스템마다 어댑터(Adapter) 컴포넌트** — 권장. 도메인은 인터페이스로만 의존
- B) 도메인이 외부 SDK를 직접 import — 단순하나 결합도↑
- C) 핵심 시스템(Auth/Vault)만 어댑터, 나머지는 직접

**[Answer]**: A

---

### 5. 설계 패턴 / 아키텍처 스타일 (Design Patterns)

#### Q-AD-11: 전체 아키텍처 스타일
- A) **모듈러 모놀리스(Modular Monolith) → Phase 2에 마이크로서비스 후보 추출** — 권장 (MVP 일정에 적합)
- B) MVP부터 마이크로서비스 (4~7개) — k8s 직접
- C) 단일 모놀리스 (분리 없음) — 작성 빠름, 유지보수↓

**[Answer]**: A

#### Q-AD-12: 도메인 모델 스타일
- A) **Anemic Model + Service** (DTO + 서비스에 로직) — 권장 (학습 곡선 낮음)
- B) Rich Domain Model + Aggregate (DDD)
- C) Functional Core / Imperative Shell — 함수형 강함

**[Answer]**: A

#### Q-AD-13: 보안 정책 적용 지점
보안 베이스라인 15규칙 + RBAC 등 보안 정책의 강제 지점을 어디에?

- A) **모든 컴포넌트 진입점**(공통 라이브러리로 자동) + 게이트웨이 이중 — 권장 (Defense in Depth)
- B) 게이트웨이 단일 지점만 — 단순, 단일 실패점
- C) 도메인 컴포넌트마다 수동 — 누락 위험

**[Answer]**: A

---

### 6. 일관성 / 트랜잭션 (Consistency)

#### Q-AD-14: 트랜잭션 경계
사용자 한 동작(예: 노트북 저장 + Git 커밋 + 감사 로그)의 일관성 모델

- A) **메타 DB는 트랜잭션, Git push·감사 발행은 outbox 비동기** — 권장 (eventual consistency, fail-safe)
- B) 모든 단계 동기 강일관성 — 단순하나 외부 시스템 다운에 취약
- C) 사가 패턴으로 보상 트랜잭션 정의 — Phase 2

**[Answer]**: A

---

### 7. 데이터 흐름 (Data Flow)

#### Q-AD-15: PII 마스킹 적용 지점
- A) **결과가 사용자에게 응답되기 직전(렌더링 직전) + 사전 컬럼 메타 기반 차단(가능 시)** — 권장 (이중)
- B) DB 쿼리 단계에서 마스킹 (커넥터 레벨)
- C) UI에서만 마스킹 — 가장 위험, 비추

**[Answer]**: A

---

## E. 사용자 답변 종합 후 절차

1. 위 [Answer]:를 모두 채워 다시 보내주세요. (또는 일부 또는 전체에 "권장"이라고 답하면 권장값으로 진행)
2. AI가 답변에서 모호함을 분석합니다(Step 8·9).
3. 모호함이 없으면 본 plan 승인 후 Part 2(생성) — 5개 산출물 작성에 착수합니다.

---

## F. 예상 산출물 미리보기 (Sample — 최종이 아님)

> Q-AD-1=B(중간 입자) + Q-AD-11=A(모듈러 모놀리스) 가정 시 예시.

**Domain: Auth & Session**
- `AuthGateway` — Keycloak OIDC 콜백 처리, 토큰 검증
- `SessionStore` — 세션 TTL·만료·무효화
- `RoleResolver` — 사용자 ↔ 역할 매핑, 권한 확인 API

**Domain: Connectors**
- `ConnectionRegistry` — 등록·조회·삭제
- `CredentialVaultAdapter` — Vault 어댑터 (Q-AD-10=A 적용)
- `KerberosTicketCache` — Hive/Impala 등에 사용
- `QueryExecutor` — 파라미터화 쿼리 실행 + 결과 페이지네이션
- `PiiMaskingFilter` — 결과 렌더 직전 마스킹

…(이런 식으로 도메인별로 정렬)

---

**다음 단계**: 위 [Answer]:들을 채우거나 "권장 전체 수용" 이라고 답해주세요.
