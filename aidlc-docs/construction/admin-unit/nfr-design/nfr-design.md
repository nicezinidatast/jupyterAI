# admin-unit — NFR Design

## 1. SPA 빌드

```
units/admin-unit/admin-console/
├── package.json
├── vite.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Users.tsx
│   │   ├── Connections.tsx
│   │   ├── PiiPatterns.tsx
│   │   └── Backups.tsx
│   ├── api/ (생성된 OpenAPI 클라이언트)
│   ├── hooks/
│   └── components/
```

- Vite 빌드: `npm run build` → `dist/` (static)
- gateway-unit이 `/` 라우트에서 정적 서빙
- 환경별 `VITE_API_BASE_URL`

## 2. AuditorConsole

```
units/admin-unit/auditor-console/
```
- 별도 SPA, 별도 라우트 (`/auditor`)
- RBAC: gateway-unit이 진입 시 role=Auditor|Admin 강제

## 3. Backup Service 흐름

```python
async def run_meta_db_backup(target: str) -> Result[BackupId, _]:
    backup_id = uuid4()
    async with session.begin():
        await session.execute(insert(Backup).values(
            backup_id=backup_id, target=target, state='running'
        ))
    try:
        # subprocess for pg_dump
        proc = await asyncio.create_subprocess_exec(
            "pg_dump", "--format=custom",
            f"--file=/var/backups/{backup_id}.dump",
            env={**os.environ, "PGPASSWORD": "***"},  # 마스킹
        )
        await proc.communicate()
        if proc.returncode != 0:
            raise BackupError(...)
        size = os.path.getsize(f"/var/backups/{backup_id}.dump")
        await update_backup_row(backup_id, 'success', size, f"/var/backups/{backup_id}.dump")
    except Exception as e:
        await update_backup_row(backup_id, 'failed', error=str(e))
        await alert(e)
        return Err(...)
    return Ok(backup_id)
```

## 4. RestoreVerifier

```text
monthlyRehearsal:
  1. latest_backup = SELECT WHERE state='success' ORDER BY started_at DESC LIMIT 1
  2. docker compose -f infra/restore-test/compose.yml up -d  # 격리 env
  3. restore meta_db from backup
  4. sanity tests:
     - SELECT count(*) FROM users
     - SELECT count(*) FROM connections
     - 마이그레이션 버전 검증
  5. INSERT INTO restore_rehearsals (..., report=jsonb)
  6. docker compose down -v
  7. emit audit
```

## 5. Quarterly Access Review

```python
async def generate_quarterly_report(quarter: str):
    # 사용자별 권한 + 최근 90일 활동
    rows = await session.execute(text("""
        SELECT u.user_id, u.email,
               array_agg(DISTINCT ur.role) AS roles,
               count(DISTINCT al.id) AS event_count_90d,
               max(al.occurred_at) AS last_activity
        FROM users u
        LEFT JOIN user_roles ur ON u.user_id = ur.user_id
        LEFT JOIN audit_log al ON al.actor_id = u.user_id
            AND al.occurred_at > NOW() - INTERVAL '90 days'
        GROUP BY u.user_id, u.email
    """))
    # markdown 또는 PDF 생성
    path = f"/var/reports/access-review-{quarter}.md"
    await write_markdown(path, rows)
    await send_to_security_team(path)
    INSERT INTO quarterly_access_reviews(...)
```

## 6. JupyterExtensionsBundle 빌드

```
units/admin-unit/jupyter-extensions/
├── package.json   ← @jupyterlab/builder
├── src/
│   ├── plugins/
│   │   ├── connection-panel.tsx
│   │   ├── sql-editor.tsx
│   │   └── chart-button.tsx
│   └── index.ts
├── tsconfig.json
└── style/
```

- `jupyter labextension build` → wheel 산출물
- user-image Dockerfile 빌드 시 설치

## 7. 메트릭

```
admin_user_searches_total
backup_runs_total{target,result}
backup_duration_seconds{target}
restore_rehearsals_total{result}
quarterly_reviews_generated_total
```
