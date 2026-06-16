# notebook-unit — NFR Design

## 1. JupyterHub 통합

```python
# Spawner — backend가 JupyterHub Authenticator 백엔드 역할
class PlatformAuthenticator(Authenticator):
    async def authenticate(self, handler, data):
        # gateway-unit이 이미 SSO 했음. JupyterHub 진입은 gateway 패스스루
        # JupyterHub는 platform JWT를 받고 검증
        token = data.get('platform_token')
        result = await auth_client.verify(token)
        if isinstance(result, Err): return None
        return {"name": result.value.user_id, "auth_state": {...}}
```

- JupyterHub config: DockerSpawner + 사용자별 분리 컨테이너
- Resource quota: 메모리 4GB, CPU 2 cores, idle timeout 30분 (구성 변수)

## 2. AutoCommitOrchestrator

```python
async def commit_loop():
    redis = await aioredis.from_url(REDIS_URL)
    while True:
        try:
            async with asyncio.timeout(5):
                await redis.subscribe("git:notify")
        except TimeoutError: pass

        async with AsyncSessionLocal() as session, session.begin():
            rows = await session.execute(
                select(GitCommitOutbox)
                .where(GitCommitOutbox.state == 'queued')
                .order_by(GitCommitOutbox.created_at)
                .limit(50)
                .with_for_update(skip_locked=True)
            )
            for row in rows.scalars():
                await process_one(session, row)

async def process_one(session, row):
    version = await session.get(NotebookVersion, row.notebook_version_id)
    workspace = await session.get(Workspace, version.notebook.workspace_id)
    msg = row.commit_message or f"auto: {version.notebook.path} @ {version.saved_at:%Y-%m-%dT%H:%M:%SZ}"
    try:
        sha = await git.commit_and_push(workspace, version, msg)
        version.git_commit_sha = sha
        row.state = 'committed'
        await emit_audit(session, "git_committed", version.saved_by, ...)
    except NetworkError as e:
        row.attempts += 1
        if row.attempts >= 3:
            row.state = 'failed'
            row.last_error = str(e)
            await emit_audit(session, "git_commit_failed", version.saved_by, ...)
        else:
            row.last_error = str(e)
            # state는 queued 유지, 다음 라운드 재시도
            await asyncio.sleep(2 ** row.attempts)
```

## 3. ShareLink (Invariant 강제)

```python
async def resolve(link_id: UUID, requester: UserContext) -> Result[NotebookAccess, _]:
    link = await session.get(ShareLink, link_id)
    if not link or link.revoked_at: return Err(NOT_FOUND)
    # audience 매칭
    matched = await session.scalar(
        select(literal(True))
        .where(ShareAudience.link_id == link_id,
               or_(ShareAudience.subject_user_id == requester.user_id,
                   ShareAudience.subject_role.in_(requester.roles)))
        .limit(1)
    )
    if not matched: return Err(FORBIDDEN)
    return Ok(NotebookAccess(
        notebook_id=link.notebook_id,
        permission=link.permission,
        use_current_user_credentials=True,
    ))
```

- PBT: 임의로 permission/audience 조합 생성 → 매칭 안 되면 항상 FORBIDDEN

## 4. ChartBuilder

```python
def build(df: DataFrame, chart_type: ChartType, mapping: AxisMapping) -> Result[ChartSpec, _]:
    if len(df) > 100_000:
        return Err(DomainError.VALIDATION)  # 샘플링 권장
    err = validate_mapping(df.dtypes, mapping)
    if isinstance(err, Err): return err
    if chart_type == 'line':
        spec = {"data": [{"x": df[mapping.x].tolist(), "y": df[mapping.y].tolist(), "type": "scatter", "mode": "lines"}]}
    elif chart_type == 'bar': ...
    # 7종 분기
    return Ok({"engine": "plotly", "spec": spec})
```

## 5. KernelManager — SQL cell 분기

```python
async def execute_cell(ctx, args):
    if args.kernel == 'sql':
        # data-unit으로 위임
        result = await data_access.run_query(
            ctx, args.conn_id, ParamQuery(sql=args.code, params={}), opts
        )
        return result
    # python/r — JupyterHub kernel API
    ...
```

## 6. 메트릭

```
notebook_saves_total{auto}
notebook_save_latency_seconds
git_commits_total{result}
git_commit_latency_seconds
git_outbox_depth          (gauge)
share_links_created_total{permission}
share_link_resolutions_total{result}
kernel_executions_total{kernel,result}
kernel_active             (gauge)
background_jobs_pending   (gauge)
chart_builds_total{type,result}
```

## 7. 에러 매핑

| DomainError | HTTP |
|---|---|
| ShareLink not found | 404 |
| permission insufficient | 403 |
| 10만 행 초과 차트 | 422 |
| Git network error | 502 (consumer 측은 retry, API는 즉시 응답) |
