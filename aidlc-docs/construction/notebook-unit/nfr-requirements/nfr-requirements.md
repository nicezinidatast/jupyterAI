# notebook-unit — NFR Requirements

| ID | 요구사항 |
|---|---|
| NFR-NB-PERF-01 | spawner spawn 시간 | < 5s (이미 이미지 캐시된 상태) |
| NFR-NB-PERF-02 | 셀 실행 큐 대기 | 평균 < 3s (NFR-PERF-02) |
| NFR-NB-PERF-03 | 자동 저장 → outbox insert | < 100ms |
| NFR-NB-PERF-04 | Git commit (작은 노트북) | < 2s |
| NFR-NB-PERF-05 | Git push 재시도 | 3회 × exp backoff(1s, 2s, 4s) |
| NFR-NB-PERF-06 | ChartBuilder build (10만 행 이내) | < 500ms |
| NFR-NB-SEC-01 | execute 권한 노트북 → 현재 사용자 자격증명 사용 | 격리 보장 |
| NFR-NB-SEC-02 | ShareLink — 비인증 접근 → 401, 권한 부족 → 403 | PBT |
| NFR-NB-SEC-03 | JupyterLab CSP 호환 — 필요 시 nonce 부여 | gateway-unit과 협업 |
| NFR-NB-AUDIT-01 | 저장/공유/실행/Git 모든 이벤트 감사 | shared-lib emitter |
| NFR-NB-OBS-01 | 메트릭: notebooks_saved, git_commits, share_links, kernel_active, chart_builds | Prometheus |

## 기술 스택

| 항목 | 결정 |
|---|---|
| Web Framework | FastAPI |
| ORM | SQLAlchemy 2 + asyncpg |
| JupyterHub | **JupyterHub 4.x** + DockerSpawner (MVP), KubeSpawner (Phase 2) |
| Kernel | ipykernel (Python), IRkernel (R) |
| Notebook format | **nbformat 5.10+** (jsonschema 검증) |
| Plotly | `plotly >= 5.20`, `pandas`, `pyarrow` |
| Git Client | `httpx` (GitLab/Gitea API) — `gitpython` X (느리고 무거움) |
| Job queue | Redis Streams |
| JupyterLab Extension API | `jupyterlab >= 4.0`, TypeScript build |
