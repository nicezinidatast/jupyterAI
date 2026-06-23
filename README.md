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
| RAM | 최소 ~8 GB 권장 (사용자 1인당 1.5 GB × 동시 3명 + 백엔드/포털/허브 ~2.5 GB; `.env`로 조정 — §7) |
| 디스크 여유 | 약 3~4 GB |
| Anthropic API 키 | 클라우드 LLM(기본) 사용 시. 폐쇄망이면 사내 vLLM(`INTERNAL_NETWORK=True`) 또는 Ollama로 대체(§6) |

> `git clone` 후 **이 저장소 루트**에서 모든 명령을 실행합니다.

---

## 3. 환경변수 (`backend/.env`)

아래 내용을 `backend/.env` 로 저장합니다.

```dotenv
# 내부망(폐쇄망) LLM 토글
#   True  → 사내 vLLM(Keycloak 인증) 사용 → INTERNAL_LLM_MODEL 로 모델 선택
#   False → 아래 LLM_PROVIDER 설정대로(클라우드 Claude / Ollama)
INTERNAL_NETWORK=False
INTERNAL_LLM_MODEL=gemma4          # gemma4 | gptoss120b

# INTERNAL_NETWORK=False 일 때의 코파일럿 LLM: anthropic | ollama
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...       # anthropic 사용 시
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

기동 서비스: `portal(정적) · backend · redis · jupyterhub · jupyter-gc`. (로그인 시 JupyterHub가 사용자별 노트북 컨테이너를 추가로 스폰 — §7.)
> **외부 노출 포트는 portal 단 하나**(호스트 `5500` → 컨테이너 `80`). backend·jupyter·redis 는 도커 내부 전용이라 따로 열 필요가 없습니다(브라우저는 5500의 portal만 보고, portal이 `/api`·`/jupyter` 를 내부로 프록시). 서버가 다른 포트를 열어줬다면 `PORTAL_PORT=<포트> docker compose -f infra/docker-compose/compose.prod.yml up -d --build` 로 띄우세요.
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

> URL 포트: **운영 배포(A)는 `5500`**(서버 주소로 접속, 예 `http://<서버IP>:5500/`), **개발(B)은 `5180`**(`localhost`). 아래 표는 개발 기준이며, 운영은 `5180`→`5500`, `localhost`→서버 주소로 바꿔 보세요.

| 화면 | URL | 설명 |
|---|---|---|
| 로그인 / 회원가입 | http://localhost:5180/ | 첫 진입(→ `/login/`). 로그인 성공 시 분석가 화면으로 |
| 분석가 워크스페이스 | http://localhost:5180/analyst/ | **JupyterLab + 다분석할Zini** (핵심 화면) |
| 관리자 콘솔 | http://localhost:5180/admin/ | 사용자/감사 등 운영 |
| 감사자 콘솔 | http://localhost:5180/auditor/ | 감사 로그 조회 |

- **관리자 계정**: `admin` / `admin` (최초 부팅 시 자동 생성).
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

### (C) 내부망 vLLM — 사내 모델(Keycloak 인증)
사내망에서 제공하는 vLLM 모델(Gemma-4 / GPT-OSS-120B)을 그대로 씁니다. 별도 키 발급 없이
`backend/.env` 한 줄만 바꾸면 됩니다.
```dotenv
INTERNAL_NETWORK=True
INTERNAL_LLM_MODEL=gemma4      # 또는 gptoss120b
```
- Keycloak 토큰 발급 → OpenAI 호환 `/v1/chat/completions` 스트리밍 호출까지 자동입니다(토큰은
  만료 직전까지 재사용). 엔드포인트/계정 기본값이 코드에 내장돼 있어 보통 추가 설정이 필요 없습니다.
- 계정·모델 id·SSL 검증을 바꿔야 하면 `INTERNAL_LLM_USERNAME` / `INTERNAL_LLM_PASSWORD` /
  `INTERNAL_LLM_MODEL_ID` / `INTERNAL_LLM_VERIFY_SSL` 로 덮어쓸 수 있습니다.
- `INTERNAL_NETWORK=True` 이면 `LLM_PROVIDER` 값은 무시됩니다(내부망 우선).
- 바꾼 뒤 백엔드 재시작: `docker compose -f infra/docker-compose/compose.yml restart backend`

---

## 7. 사용자 격리 (JupyterHub — 사용자별 컨테이너)

- 로그인하면 **JupyterHub(DockerSpawner)** 가 그 사용자만의 노트북 컨테이너를 띄웁니다. 작업 폴더는 사용자별 전용 볼륨(`jupyterhub-user-<아이디>`)의 `work/` 에 영속 — **남의 폴더는 보이지도 접근되지도 않습니다**(파일시스템 완전 분리). 컨테이너 재생성·재로그인에도 내 파일은 보존됩니다.
- **1인당 자원 상한**: 기본 RAM `1.5G` · CPU `2.0코어` · 동시 접속 `3명`. 전부 `infra/docker-compose/.env`의 환경변수(`JUPYTERHUB_USER_MEM_LIMIT` · `JUPYTERHUB_USER_CPU_LIMIT` · `JUPYTERHUB_ACTIVE_SERVER_LIMIT`)로 조정합니다. 동시 인원 상한에 도달하면 새 사용자는 누군가 내릴 때까지 **대기(큐잉)** 합니다. 박스 RAM별 `(1인당RAM ↔ 동시인원)` 가이드는 `.env.example`의 표를 참고하세요.
- **자동 회수(자원 절약)**: 유휴 30분 서버 종료 + 활동 중이어도 1일 하드캡 종료 + 로그아웃 시 즉시 회수. 1일 지난 사용자 볼륨은 `jupyter-gc` 가 삭제합니다(사용 중 볼륨은 미접근).
- **OOM 안내**: 한 사용자가 자기 메모리 상한을 넘겨 커널이 죽어도 **다른 사용자에겐 영향이 없고**, 그 사용자 화면의 "Kernel Restarting" 다이얼로그에 *"메모리 부족일 수 있음 — 관리자에게 메모리 증설 요청"* 안내가 함께 표시됩니다.
- 동시 인원을 더 받으려면 1인당 RAM을 줄이거나(예: `500M` → 8 GB에서 ~11명) 서버 RAM을 키웁니다.

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
| `:5500`(운영) / `:5180`(개발) 접속 안 됨 | ① 서버 방화벽/보안그룹에서 해당 포트 인바운드 허용 확인 ② 호스트 포트 점유 시 점유 프로세스 종료 또는 `PORTAL_PORT=<다른포트>` 로 변경. |
| `GET /api/copilot/provider` → 503 | `ANTHROPIC_API_KEY` 미설정, `LLM_PROVIDER=ollama` 인데 ollama 미기동, 또는 `INTERNAL_NETWORK=True` 인데 `INTERNAL_LLM_MODEL` 값이 `gemma4`/`gptoss120b` 가 아님. |
| 로그인 후 흰 화면 | 브라우저 새로고침. 그래도면 백엔드 로그 확인. |
| 빌드 중 SPA OOM | 빌드 머신 RAM 부족. `infra/portal/Dockerfile` 의 `NODE_OPTIONS` 상향 또는 RAM 더 큰 머신에서 빌드. |
| 사용자가 큰 데이터로 느려짐/죽음 | 1인당 자원 상한 초과(OOM). 화면에 "메모리 증설 요청" 안내가 뜸. `JUPYTERHUB_USER_MEM_LIMIT` 상향 또는 동시 인원(`JUPYTERHUB_ACTIVE_SERVER_LIMIT`) 하향 — §7. |

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
infra/jupyterhub/           # JupyterHub 설정 + 사용자 노트북 이미지(user-image/) + 볼륨 GC(volume_gc.py)
tests/                      # 통합/e2e 테스트
aidlc-docs/                 # 설계 문서
```

---

## 11. 변경 이력 · 개발 메모

- 변경 이력: [`CHANGELOG.md`](CHANGELOG.md)
- 개발자 회상 / 구조·의사결정 메모: [`FOR_DEVELOPER.md`](FOR_DEVELOPER.md)
- 설계 문서: `aidlc-docs/`

---

## 라이선스

이 저장소의 자체 코드는 **내부 사용 전용**입니다.

이 플랫폼에 임베드된 주피터 스택은 전부 **Project Jupyter 공식 오픈소스**이며, 모두 **BSD 3-Clause(Modified/Revised BSD) 라이선스**입니다. 베이스 이미지·패키지를 그대로 사용하며 포크·소스 벤더링은 없습니다.

| 구성 요소 | 저장소 내 근거 | 공식 출처 | 라이선스 |
|---|---|---|---|
| JupyterHub 4.0 (멀티유저 허브) | `infra/jupyterhub/Dockerfile` (`FROM jupyterhub/jupyterhub:4.0`) | [github.com/jupyterhub/jupyterhub](https://github.com/jupyterhub/jupyterhub) (Docker Hub `jupyterhub/jupyterhub`) | BSD 3-Clause |
| JupyterLab (사용자 노트북 서버) | `infra/jupyterhub/user-image/Dockerfile`, `infra/jupyter/Dockerfile` (`FROM quay.io/jupyter/scipy-notebook`) | [github.com/jupyter/docker-stacks](https://github.com/jupyter/docker-stacks) (`quay.io/jupyter/scipy-notebook`) | BSD 3-Clause |
| JupyterLab 확장 SDK | `units/admin-unit/jupyter-extensions/package.json` (`@jupyterlab/*`, `@lumino/widgets`) | [github.com/jupyterlab/jupyterlab](https://github.com/jupyterlab/jupyterlab) | BSD 3-Clause |
| DockerSpawner / jupyterhub-idle-culler | `infra/jupyterhub/Dockerfile` (pip) | [github.com/jupyterhub/dockerspawner](https://github.com/jupyterhub/dockerspawner) · [github.com/jupyterhub/jupyterhub-idle-culler](https://github.com/jupyterhub/jupyterhub-idle-culler) | BSD 3-Clause |

> 참고: Jupyter Docker Stacks 이미지는 2023-10-20부터 Docker Hub가 아닌 `quay.io/jupyter/` 네임스페이스로만 게시됩니다. 각 컴포넌트의 라이선스 전문은 위 공식 저장소의 `LICENSE` 파일에서 확인할 수 있습니다.
