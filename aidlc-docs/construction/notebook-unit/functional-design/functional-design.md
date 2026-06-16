# notebook-unit — Functional Design

**모듈**: NotebookStore, JupyterHubSpawner, KernelManager, ChartBuilder, ShareLinkManager, GitAdapter, AutoCommitOrchestrator, NotebookService

---

## 1. 데이터 모델

```sql
CREATE TABLE workspaces (
    workspace_id UUID PRIMARY KEY,
    owner_user_id UUID NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('personal','team')),
    name TEXT NOT NULL,
    git_repo_url TEXT NOT NULL,           -- GitLab/Gitea 저장소 URL
    git_branch TEXT NOT NULL DEFAULT 'main',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE workspace_members (
    workspace_id UUID NOT NULL REFERENCES workspaces(workspace_id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner','editor','viewer')),
    PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE notebooks (
    notebook_id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(workspace_id),
    path TEXT NOT NULL,                   -- workspace 안의 상대 경로
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (workspace_id, path)
);

CREATE TABLE notebook_versions (
    version_id UUID PRIMARY KEY,
    notebook_id UUID NOT NULL REFERENCES notebooks(notebook_id) ON DELETE CASCADE,
    content_sha256 TEXT NOT NULL,
    content JSONB NOT NULL,               -- nbformat
    saved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    saved_by UUID NOT NULL,
    is_autosave BOOLEAN NOT NULL DEFAULT false,
    git_commit_sha TEXT
);
CREATE INDEX idx_nv_notebook_time ON notebook_versions(notebook_id, saved_at DESC);

CREATE TABLE git_commit_outbox (
    id BIGSERIAL PRIMARY KEY,
    notebook_version_id UUID NOT NULL REFERENCES notebook_versions(version_id),
    commit_message TEXT,
    attempts INT NOT NULL DEFAULT 0,
    state TEXT NOT NULL DEFAULT 'queued' CHECK (state IN ('queued','committed','failed')),
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE share_links (
    link_id UUID PRIMARY KEY,
    notebook_id UUID NOT NULL REFERENCES notebooks(notebook_id) ON DELETE CASCADE,
    permission TEXT NOT NULL CHECK (permission IN ('read','execute','edit')),
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);

CREATE TABLE share_audience (
    link_id UUID NOT NULL REFERENCES share_links(link_id) ON DELETE CASCADE,
    subject_user_id UUID,
    subject_role TEXT,
    CHECK ((subject_user_id IS NULL) <> (subject_role IS NULL)),
    PRIMARY KEY (link_id, COALESCE(subject_user_id::text, subject_role))
);

CREATE TABLE background_jobs (
    job_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    notebook_id UUID,
    cell_id TEXT,
    kind TEXT NOT NULL,                   -- 'cell_execute', 'export', ...
    state TEXT NOT NULL DEFAULT 'queued' CHECK (state IN ('queued','running','completed','failed','cancelled')),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    result JSONB,
    error TEXT
);
```

## 2. 핵심 비즈니스 룰

### 2.1 자동 저장 (US-NB-05)
- 60초 무변경 또는 셀 실행 시 트리거
- content_sha256으로 중복 저장 회피 (no-op)
- 자동저장 row는 `is_autosave=true`, retention 30일

### 2.2 노트북 저장 + outbox (US-SHARE-01)
```text
saveAndCommit(ctx, notebook, opts):
  BEGIN TX
    INSERT INTO notebook_versions (..., is_autosave=opts.auto)
    INSERT INTO git_commit_outbox (notebook_version_id, message)
    INSERT INTO audit_outbox (...)        -- audit-unit
  COMMIT
  XADD git:notify * id <outbox_id>        -- best-effort
```

AutoCommitOrchestrator consumer:
```text
loop:
  rows = SELECT ... FROM git_commit_outbox WHERE state='queued' ... LIMIT 50 FOR UPDATE SKIP LOCKED
  for row in rows:
    notebook_version = SELECT ... WHERE version_id = row.notebook_version_id
    workspace = SELECT git_repo_url, git_branch FROM workspaces ...
    msg = row.commit_message or f"auto: {notebook.path} @ {iso8601(ts)}"
    try:
      sha = GitAdapter.commit(workspace, notebook.content, msg, author=created_by)
      GitAdapter.push(workspace, branch)
      UPDATE notebook_versions SET git_commit_sha = sha
      UPDATE git_commit_outbox SET state='committed'
    except NetworkError:
      attempts += 1
      if attempts >= 3:
        UPDATE git_commit_outbox SET state='failed', last_error = ...
        emit audit('git_commit_failed')
      else:
        sleep exponential backoff
        retry next iteration
```

### 2.3 권한 = execute 공유 노트북 실행 (US-SHARE-04)
- ShareLinkManager.resolve(link_id, ctx) → NotebookAccess(permission)
- permission ≥ 'execute' 필요
- 셀 실행 시 **현재 사용자 ctx**로 인가/자격증명 — 원작성자의 자격증명 사용 X (보안 격리)
- 권한 없는 데이터 셀은 그 셀만 실패, 나머지는 계속

### 2.4 ShareLink (US-SHARE-03)
- SSO 인증된 사용자만 접근
- audience(user 또는 role) 매칭 확인
- 권한 < 요구권한 → 항상 거절 (Invariant)
- 비인증 접근 → 401 + 감사

### 2.5 KernelManager (US-NB-02·03·06)
- JupyterHubSpawner.spawn(user) → kernel endpoint
- 셀 실행:
  - SQL: data-unit.DataAccessService.runQuery 호출
  - Python/R: 직접 Jupyter kernel API
- 5초 임계: data-unit이 자체적으로 background 승격, KernelManager는 job_id 전달
- 큐: 사용자당 동시 활성 잡 ≤ 10

### 2.6 ChartBuilder (US-VIS-01·04)
- 입력: DataFrame (pandas) + chartType + AxisMapping
- 검증: 축 타입 데이터 타입 정합 (예: scatter의 Y에 문자열 거절)
- 10만 행 초과: 거절 + 샘플링 권장 응답
- 출력: ChartSpec (engine='plotly', spec=JSON)
- PII 가정: ChartBuilder에 들어오는 데이터는 이미 마스킹 통과 가정 (data-unit에서 보장)

### 2.7 GitAdapter
- GitLab/Gitea API (httpx)
- Token: 사용자 personal access token (Vault에 저장) 또는 워크스페이스별 deploy token
- 동일 콘텐츠 재커밋 = no-op (Git diff 검사) — PBT (Idempotent)

## 3. PBT
| 함수 | 기법 | 검증 |
|---|---|---|
| AutoCommit 동일 콘텐츠 재발행 | Idempotent | 두 번째 호출은 no-op |
| ShareLink 권한 거부 | Invariant | requested_perm > granted_perm → 항상 거절 |
| NotebookVersion content roundtrip | Round-trip | nbformat → json → nbformat 동일 |
| BackgroundJob lifecycle | State-Machine | queued → running → completed/failed/cancelled |

## 4. 외부 의존
- JupyterHub (spawner)
- GitLab/Gitea
- data-unit (SQL 셀)
- auth-unit (verify)
- Redis (jobs)
- Postgres

## 5. Story 매핑
US-NB-01~06, US-VIS-01~04, US-SHARE-01~04 (16 스토리)
