# notebook-unit — Code Generation Plan

**실제 코드 위치**: `units/notebook-unit/` (백엔드 모듈 + JupyterHub config + JupyterLab Extension)

## Plan — Backend
- [ ] `pyproject.toml`
- [ ] `requirements.lock`
- [ ] `migrations/0001_workspaces.py`
- [ ] `migrations/0002_notebooks_versions.py`
- [ ] `migrations/0003_share_jobs_outbox.py`
- [ ] `src/notebook/models.py`
- [ ] `src/notebook/schemas.py`
- [ ] `src/notebook/repositories/notebooks.py`
- [ ] `src/notebook/repositories/share.py`
- [ ] `src/notebook/repositories/jobs.py`
- [ ] `src/notebook/services/notebook_service.py`
- [ ] `src/notebook/services/share_link.py`
- [ ] `src/notebook/services/chart_builder.py`
- [ ] `src/notebook/services/kernel_manager.py`
- [ ] `src/notebook/adapters/git.py` (GitLab/Gitea)
- [ ] `src/notebook/adapters/jupyterhub.py`
- [ ] `src/notebook/orchestrators/auto_commit.py`
- [ ] `src/notebook/api/router.py` (`/api/notebooks`, `/api/share`, `/api/charts`)
- [ ] `src/notebook/main.py`

## Plan — JupyterHub
- [ ] `infra/jupyterhub/jupyterhub_config.py`
- [ ] `infra/jupyterhub/platform_authenticator.py` (Authenticator subclass)
- [ ] `infra/jupyterhub/Dockerfile`
- [ ] `infra/jupyterhub/user-image/Dockerfile`
- [ ] `infra/jupyterhub/user-image/requirements.txt`

## Plan — JupyterLab Extension
- [ ] `units/admin-unit/jupyter-extensions/package.json` (모듈 위치는 admin-unit이지만 사용자 워크플로는 notebook-unit과 결합 — 실제 코드는 admin-unit 산출물에서)

## Plan — Tests
- [ ] `tests/test_auto_commit_idempotent.py` (PBT)
- [ ] `tests/test_share_link_invariant.py` (PBT)
- [ ] `tests/test_notebook_roundtrip.py` (PBT)
- [ ] `tests/test_job_state_machine.py` (PBT)
- [ ] `tests/test_chart_builder.py`
- [ ] `tests/integration/test_save_to_git.py` (실제 Gitea 컨테이너 fixture)
- [ ] `tests/integration/test_shared_execute.py`
- [ ] `.gitlab-ci.yml`

## Definition of Done
- coverage ≥ 80%
- PBT 4종 통과
- Git push 재시도 3회 검증 (Gitea 의도적 다운 시나리오)
- ShareLink 무인증 접근 → 401, 권한 부족 → 403
- 10만 행 차트 → 422 + 샘플링 안내

## 비고
- 가장 다양한 도메인 — 내부 모듈 6개 (services/)로 분리
- JupyterHub config 코드는 `infra/` 폴더에 위치 (배포 산출물)
