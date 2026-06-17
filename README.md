# 내부망 데이터 분석 플랫폼 (JupyterAI)

JupyterLab 임베드 + **자연어 분석 어시스턴트 "다분석할Zini"** 를 한 화면에서 쓰는 사내 데이터 분석 플랫폼.
회원가입/로그인 → 내 전용 워크스페이스에서 파일을 올리고, 자연어로 물어보면 코드가 셀로 꽂힙니다.

> 핵심 가치는 **자연어 분석 어시스턴트** 입니다. 로그인·격리·감사는 이를 사내에서 안전하게 쓰기 위한 토대입니다.

---

## 1. 사용 흐름 (한 사이클)

```mermaid
flowchart LR
    A[회원가입 / 로그인] --> B[내 워크스페이스<br/>work/&lt;아이디&gt;]
    B --> C[데이터 파일 업로드<br/>CSV·Excel 등]
    C --> D[자연어로 질문<br/>다분석할Zini]
    D --> E[코드 셀 자동 생성/삽입]
    E --> F[▶ 실행 · 결과 확인]
    F -->|셀별 ✨AI 로 수정| E
```

1. **회원가입/로그인** — 아이디(3~20자)·비밀번호(4자 이상)만으로 자유 가입, 가입 즉시 로그인됩니다. (메일 인증 없음)
2. **내 워크스페이스** — 로그인하면 본인 폴더 `work/<아이디>` 에서 JupyterLab이 열립니다. 기본 화면엔 내 파일만 보입니다.
3. **데이터 업로드** — JupyterLab 파일 브라우저에 CSV/Excel 등을 끌어다 놓습니다. (내부망이라 외부 DB 연결은 쓰지 않습니다 — 파일 기반)
4. **자연어 질문** — 우측 **다분석할Zini** 패널에 질문(예: *"방금 올린 csv에서 도시별 매출 합계 막대그래프 그려줘"*)을 입력합니다.
5. **셀 자동 삽입** — 답변의 코드 블록을 셀에 넣어줍니다(삽입 의도가 있을 때 자동, 평소엔 "📥 셀에 삽입" 버튼).
6. **셀별 ✨AI 편집** — 각 코드 셀 툴바의 **✨** 버튼으로 그 셀만 자연어로 즉시 수정(코랩/커서 스타일, 새로고침 없음).

모든 코파일럿 호출은 `audit_log` 에 `copilot_chat` / `copilot_cell_inserted` 로 기록됩니다.

---

## 2. 사전 요건

| 항목 | 필요 버전 / 비고 |
|---|---|
| Docker + Docker Compose | Docker Desktop 4.x 이상 (Windows/macOS/Linux) |
| RAM | 최소 ~8 GB 권장 (Jupyter 컨테이너 상한 4 GB + 백엔드/포털) |
| 디스크 여유 | 약 3~4 GB |
| Anthropic API 키 | 클라우드 LLM(기본) 사용 시. 폐쇄망이면 Ollama로 대체 가능(§6) |

> `git clone` 후 **이 저장소 루트**에서 모든 명령을 실행합니다.

---

## 3. 환경변수 (`backend/.env`)

아래 내용을 `backend/.env` 로 저장합니다.

```dotenv
# 코파일럿 LLM 선택: anthropic | ollama
LLM_PROVIDER=anthropic

# anthropic 사용 시
ANTHROPIC_API_KEY=sk-ant-...
```

> `.env` 는 `.gitignore` 처리되어 있습니다. **키를 평문으로 커밋하지 마세요.**
> 실수로 노출했다면 즉시 [Anthropic 콘솔](https://console.anthropic.com/)에서 revoke 후 재발급하세요.

---

## 4. 실행 방법

배포 형태가 두 가지입니다.

### (A) 운영/시범 배포 — 권장 (`compose.prod.yml`)

SPA를 **정적 빌드**해 nginx가 서빙합니다. 개발용 Vite 서버(노드 컨테이너 4개·런타임 npm)가 없어 **가볍고**(작은 서버에 적합) 런타임에 인터넷이 필요 없습니다.

```bash
docker compose -f infra/docker-compose/compose.prod.yml up -d --build
```

기동 서비스: `portal(정적) · backend · jupyter · redis`.
> 빌드 단계의 SPA 번들링이 순간 **~4 GB** 메모리를 씁니다. 서버 RAM이 빠듯하면 프록시 되는 다른 PC에서 빌드 후 `docker save`/`load` 로 이미지를 옮기세요.

### (B) 개발 (`compose.yml`)

SPA가 Vite 개발 서버로 떠서 **소스 수정 시 HMR 즉시 반영**됩니다.

```bash
docker compose -f infra/docker-compose/compose.yml up -d
# 데모용 DB/keycloak 까지 전부 띄우려면:
docker compose -f infra/docker-compose/compose.yml --profile full up -d
```

처음 한 번은 SPA `npm install` 때문에 2~5분 걸립니다. 상태 확인:

```bash
docker compose -f infra/docker-compose/compose.yml ps
```

---

## 5. 접속 & 계정

| 화면 | URL | 설명 |
|---|---|---|
| 로그인 / 회원가입 | http://localhost:5180/ | 첫 진입(→ `/login/`). 로그인 성공 시 분석가 화면으로 |
| 분석가 워크스페이스 | http://localhost:5180/analyst/ | **JupyterLab + 다분석할Zini** (핵심 화면) |
| 관리자 콘솔 | http://localhost:5180/admin/ | 사용자/감사 등 운영 |
| 감사자 콘솔 | http://localhost:5180/auditor/ | 감사 로그 조회 |

- **관리자 계정**: `admin` / `admin_st` (최초 부팅 시 자동 생성).
- 일반 사용자는 로그인 화면에서 **자유롭게 회원가입**합니다.
- `/platform` 은 예전 페르소나 선택 페이지로, URL로만 접근됩니다(메뉴에 노출 안 됨).

---

## 6. 코파일럿 LLM 모드

### (A) Anthropic (기본)
`backend/.env` 에 `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` 설정. 대화는 `claude-sonnet-4-6`, 셀별 단발 수정은 가벼운 `claude-haiku-4-5` 를 씁니다(`COPILOT_EDIT_MODEL` 로 변경).

### (B) Ollama — 완전 폐쇄망
```bash
# 7B 코드 모델(qwen2.5-coder:7b, ~4.7GB) 한 번 pull
docker compose -f infra/docker-compose/compose.yml --profile llm up -d ollama ollama-init
# backend/.env 에서 LLM_PROVIDER=ollama 로 바꾼 뒤 백엔드 재시작
docker compose -f infra/docker-compose/compose.yml restart backend
```

---

## 7. 사용자 격리 (현재: 소프트)

- 각 사용자는 본인 폴더 `work/<아이디>/` 에서 시작하고, 코파일럿 노트북도 `work/<아이디>/copilot-<아이디>.ipynb` 입니다.
- 폴더는 영구 볼륨(`jupyter-data`)에 있어 **컨테이너 재생성에도 보존**됩니다.
- ⚠️ 공유 단일 JupyterLab 서버라 **완전 격리는 아닙니다** — 기본 화면은 내 폴더지만, 파일 브라우저에서 상위로 올라가면 다른 폴더가 보일 수 있습니다.
- Jupyter 컨테이너에 메모리 상한(`mem_limit: 4g`)을 둬, 한 사용자의 큰 작업이 전체 스택을 OOM으로 내리는 걸 막습니다.
- 동시 20~30명이 무거운 분석을 돌리는 규모라면 **사용자별 JupyterLab 환경(JupyterHub) + RAM 32GB+ 서버** 가 필요합니다(현 구조에서 `work/<id>` 관례가 그대로 이전됩니다).

---

## 8. 운영 명령 모음

```bash
# 로그 확인 (프로덕션 예시)
docker compose -f infra/docker-compose/compose.prod.yml logs -f backend

# 전체 종료 (볼륨 유지 — 데이터 보존)
docker compose -f infra/docker-compose/compose.prod.yml down

# 전체 초기화 (볼륨까지 삭제 — 노트북/사용자 폴더/DB 전부 삭제)
docker compose -f infra/docker-compose/compose.prod.yml down -v
```

데이터 저장 위치: 앱 DB는 SQLite(`/uploads/appdb/app.db`), 사용자 노트북/파일은 `work/` 볼륨.

---

## 9. 트러블슈팅

| 증상 | 원인 / 대응 |
|---|---|
| `:5180` 접속 안 됨 | 포트 점유. 점유 프로세스 종료 또는 portal 포트 변경. |
| `GET /api/copilot/provider` → 503 | `ANTHROPIC_API_KEY` 미설정, 또는 `LLM_PROVIDER=ollama` 인데 ollama 미기동. |
| 로그인 후 흰 화면 | 브라우저 새로고침. 그래도면 백엔드 로그 확인. |
| 빌드 중 SPA OOM | 빌드 머신 RAM 부족. `infra/portal/Dockerfile` 의 `NODE_OPTIONS` 상향 또는 RAM 더 큰 머신에서 빌드. |
| 사용자가 큰 데이터로 느려짐/죽음 | 공유 서버 한계. Jupyter `mem_limit` 조정, 또는 §7의 JupyterHub 전환 검토. |

---

## 10. 저장소 구조 (요약)

```
units/                      # 애플리케이션 유닛 (shared-lib / gateway / auth / audit / credential / data / notebook / admin / copilot)
backend/                    # FastAPI 통합 진입점 (SQLite)
infra/docker-compose/
  ├─ compose.yml            # 개발 스택 (Vite HMR, --profile full 로 데모DB/keycloak)
  └─ compose.prod.yml       # 운영 린 스택 (정적 portal + backend + jupyter + redis)
infra/portal/
  ├─ Dockerfile             # SPA 4개 정적 빌드 → nginx (운영용)
  ├─ nginx.prod.conf        # 운영 라우팅 (정적 SPA + /api·/jupyter 프록시)
  └─ nginx.conf             # 개발 라우팅 (Vite 프록시)
infra/jupyter/              # JupyterLab 커스텀 이미지 + 커널 시작 스크립트
tests/                      # 통합/e2e 테스트
aidlc-docs/                 # 설계 문서
```

---

## 라이선스

내부 사용 전용.
