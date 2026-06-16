# 내부망 데이터 분석 플랫폼

JupyterLab 임베드 + **자연어 분석 코파일럿**을 한 화면에서 쓰는 사내 데이터 분석 플랫폼.
Docker Compose 한 번으로 전체 스택(백엔드 / 4개 SPA / Postgres / Redis / JupyterLab / 데모 데이터 DB)이 뜹니다.

---

## 1. 사전 요건

| 항목 | 필요 버전 / 비고 |
|---|---|
| Docker Desktop | 4.x 이상 (Windows / macOS / Linux 모두 OK) |
| 디스크 여유 | 약 4 GB (이미지 + 데모 DB), Ollama 추가 시 +5 GB |
| Anthropic API 키 *(선택)* | 클라우드 LLM을 쓰려는 경우만 |

> `git clone` 후 **이 저장소 루트**에서 모든 명령을 실행합니다.

---

## 2. 환경변수 (`backend/.env`)

`backend/.env.example` 같은 파일은 따로 두지 않습니다 — 아래 내용을 `backend/.env` 로 그대로 저장하면 됩니다.

```dotenv
# 코파일럿 LLM 선택: anthropic | ollama
LLM_PROVIDER=anthropic

# anthropic 사용 시
ANTHROPIC_API_KEY=sk-ant-...

# (선택) 사내 SSO 켜기
BACKEND_OIDC_ENABLED=false
```

> `.env` 는 `.gitignore` 처리되어 있습니다. **키를 평문으로 커밋하지 마세요.**
> 실수로 노출했다면 즉시 [Anthropic 콘솔](https://console.anthropic.com/)에서 revoke 하고 새 키를 발급받으세요.

---

## 3. 한 번에 띄우기

```powershell
docker compose -f infra/docker-compose/compose.yml up -d
```

처음 한 번은 SPA 이미지의 `npm install` 때문에 2–5 분 걸립니다. 이후 재시작은 수 초.

상태 확인:

```powershell
docker compose -f infra/docker-compose/compose.yml ps
```

모든 서비스가 `Up (healthy)` 가 되면 준비 끝.

---

## 4. 접속 URL

| 화면 | URL | 설명 |
|---|---|---|
| 페르소나 선택 | http://localhost:5180/ | 시작 페이지 |
| 분석가 워크스페이스 | http://localhost:5180/analyst/ | **JupyterLab + 자연어 코파일럿** (핵심 화면) |
| 빠른 SQL | http://localhost:5180/analyst/sql | SQL 직접 실행 + 차트 + 노트북 저장 |
| 관리자 콘솔 | http://localhost:5180/admin/ | 커넥션 / 자격증명 / 권한 |
| 감사자 콘솔 | http://localhost:5180/auditor/ | 감사 로그 조회 |
| 조회자 포털 | http://localhost:5180/viewer/ | 읽기 전용 노트북 뷰어 |
| JupyterLab 직통 | http://localhost:5180/jupyter/lab?token=dataplatform | 토큰: `dataplatform` |
| 백엔드 API | http://localhost:8081/api | 직접 호출용 |

### 자연어 → 셀 자동 삽입

`/analyst/` 진입 시 좌측에 `copilot.ipynb` 가 자동으로 열립니다.
우측 코파일럿 패널에 자연어 질문(예: *"sales.customers 상위 5명 보여줘"*)을 입력하면

1. AI가 SQL/Python 코드 블록을 포함한 답변을 스트리밍
2. 코드 블록이 `copilot.ipynb` 에 **자동으로 셀 추가**
3. 좌측 JupyterLab UI에 새 셀이 즉시 표시됨 → ▶ 실행

모든 호출은 `audit_log` 에 `copilot_chat` / `copilot_cell_inserted` 로 기록됩니다.

---

## 5. 코파일럿 LLM 모드

### (A) Anthropic (기본)

`backend/.env` 에 `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` 설정 후 위 명령으로 `up -d` 만 하면 됩니다.

### (B) Ollama — 폐쇄망

```powershell
# 1) 7 B 코드 모델(qwen2.5-coder:7b, ~4.7 GB) 한 번만 pull
docker compose -f infra/docker-compose/compose.yml --profile llm up -d ollama ollama-init
# ollama-init 가 exit 0 되면 모델 준비 완료

# 2) backend/.env 에서 LLM_PROVIDER=ollama 로 바꾼 뒤 백엔드 재시작
docker compose -f infra/docker-compose/compose.yml restart backend
```

다른 모델: `OLLAMA_MODEL=llama3.1:8b docker compose ... --profile llm up -d`

---

## 6. 운영 명령 모음

```powershell
# 로그 확인
docker compose -f infra/docker-compose/compose.yml logs -f backend

# 특정 서비스만 재시작 (코드 수정 반영)
docker compose -f infra/docker-compose/compose.yml restart backend

# 전체 종료 (볼륨 유지 — 데이터 보존)
docker compose -f infra/docker-compose/compose.yml down

# 전체 초기화 (볼륨까지 삭제 — 데모 데이터/노트북 전부 날아감)
docker compose -f infra/docker-compose/compose.yml down -v
```

코드 수정은 호스트의 `units/*/src` / `backend/src` 가 컨테이너에 bind-mount 되어 있어
백엔드는 `docker compose restart backend`, SPA는 Vite HMR 로 자동 반영됩니다.

---

## 7. 동작 검증 (e2e)

```powershell
# Python 의존성 (한 번만)
uv sync
uv run playwright install chromium

# 핵심 e2e — 자연어 → 셀 자동 삽입 → JupyterLab UI 표시까지 검증
uv run pytest tests/e2e/test_jupyter_visible_cell.py -v

# 전체 코파일럿 통합 (PUT + audit + UI)
uv run pytest tests/e2e -m copilot -v
```

테스트가 끝나면 `tests/e2e/.last-*.png` 에 스크린샷이 남습니다.

---

## 8. 트러블슈팅

| 증상 | 원인 / 대응 |
|---|---|
| `:5180` 접속 안 됨 | 다른 프로세스가 포트 점유. `compose.yml` 의 portal 포트 변경 또는 점유 프로세스 종료. |
| 코파일럿 응답에 코드가 없음 ("스키마를 알려달라") | 우측 상단 **커넥션 컨텍스트** 미선택. `sales_db` 등을 고르면 AI가 스키마를 받아 SQL 생성. |
| `GET /api/copilot/provider` → 503 | `ANTHROPIC_API_KEY` 미설정 또는 `LLM_PROVIDER=ollama` 인데 ollama 컨테이너 미기동. |
| 새 셀이 JupyterLab UI 에 안 보임 | 페이지 새로고침. iframe 은 PUT 후 자동 reload 되지만 네트워크 지연 시 1–2 초 걸림. |
| `docker compose up` 도중 SPA 가 OOM | `compose.yml` 의 `NODE_OPTIONS=--max-old-space-size=4096` 더 키우거나 Docker Desktop 메모리 할당 증가. |

---

## 9. 저장소 구조 (요약)

```
units/                   # 7+1 application units (shared-lib / gateway / auth / audit / credential / data / notebook / admin / copilot)
backend/                 # FastAPI 통합 진입점
infra/docker-compose/    # compose.yml (전체 스택)
infra/portal/            # nginx 단일 진입 (5180)
infra/demo-data/         # 데모 Postgres/MySQL 시드 (≥1000 행)
tests/e2e/               # Playwright e2e
aidlc-docs/              # 전체 설계 문서 (Inception + Construction)
```

상세 설계는 `aidlc-docs/` 참고.

---

## 라이선스

내부 사용 전용.
