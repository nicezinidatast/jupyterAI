# notebook-unit — Infrastructure Design

## 배포
- **컨테이너 B (backend)**: NotebookStore, ShareLinkManager, AutoCommitOrchestrator, ChartBuilder, NotebookService — 모듈 동거
- **컨테이너 C (JupyterHub)**: JupyterHub + DockerSpawner. 분석가 진입 시 사용자별 ephemeral 컨테이너 spawn
- AutoCommitOrchestrator는 backend lifespan에 task (Phase 2에 별도 worker)

## JupyterHub 컨테이너
```dockerfile
FROM jupyterhub/jupyterhub:4.0
RUN pip install --index-url ${INTERNAL_PYPI} dockerspawner jupyterhub-idle-culler
COPY infra/jupyterhub/jupyterhub_config.py /srv/jupyterhub/
ENV JUPYTERHUB_AUTHENTICATOR=platform_authenticator.PlatformAuthenticator
USER 1000
EXPOSE 8000
CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]
```

## DockerSpawner 사용자 이미지
```dockerfile
# units/notebook-unit/user-image/Dockerfile
FROM jupyter/datascience-notebook:python-3.11
RUN pip install --index-url ${INTERNAL_PYPI} \
    pandas pyarrow plotly \
    psycopg pymysql oracledb pymssql pyhive impyla \
    dataplatform-shared dataplatform-jupyter-ext
# JupyterLab Extensions 설치
RUN jupyter labextension install dataplatform-jupyter-ext
```

- Memory: 4GB / CPU: 2 cores / idle: 30분 자동 정리

## 환경 변수
- `JUPYTERHUB_API_TOKEN` (backend ↔ JupyterHub 통신)
- `GITLAB_BASE_URL` (https://git.internal)
- `GIT_TOKEN_PROVIDER=vault://...` (사용자별 토큰)
- `AUTO_COMMIT_MAX_ATTEMPTS=3`
- `BG_JOB_TTL_SECONDS=3600`

## DB 마이그레이션
- workspaces, workspace_members, notebooks, notebook_versions, git_commit_outbox, share_links, share_audience, background_jobs

## 외부 의존
- JupyterHub (사내 또는 본 플랫폼이 host)
- GitLab/Gitea (사내)
- Docker socket (DockerSpawner) — 보안 위험. Phase 2 K8s + KubeSpawner로 격리

## Docker socket 보안 (MVP)
- backend는 socket 접근 권한 없음. JupyterHub 컨테이너만 socket mount (`/var/run/docker.sock:/var/run/docker.sock:ro`)
- JupyterHub 컨테이너는 격리된 서비스 user

## 백업
- 모든 notebook 테이블 일 1회
- Git 저장소 자체는 GitLab/Gitea가 자체 백업 (이중 안전망)

## 네트워크
- backend → GitLab (HTTPS)
- JupyterHub → backend (HTTPS)
- 사용자 컨테이너 → backend (HTTPS, 토큰 인증)
- 사용자 컨테이너 → 사내 DB (data-unit이 중계 — 직접 X)
