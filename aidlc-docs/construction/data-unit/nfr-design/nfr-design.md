# data-unit — NFR Design

## 1. ParamQuery 검증

```python
class ParamQuery(BaseModel):
    sql: str
    params: dict[str, str | int | float | bool | None]

    @field_validator('sql')
    def no_string_format(cls, v):
        # 단순 검증: f-string 흔적/% 포맷 흔적 없음 — 더 정교한 검사는 lint에서
        # 핵심은 driver에서 paramstyle을 강제하는 것
        return v
```

DB driver 별:
- psycopg3: `cursor.execute(sql, params)` (named/positional)
- pymysql: `%s` (named %(...)s)
- oracledb: `:name`
- pyhive: `%(name)s`

추상 `Connector.execute(ParamQuery)` 내부에서 driver-specific 변환 + 강제 paramstyle 사용.

## 2. 5초 임계 → 백그라운드 승격

```python
async def run(...) -> Result[QueryHandle | JobId, _]:
    handle = uuid4()
    save_execution_row(handle, ...)
    task = asyncio.create_task(execute_sync(handle, ...))
    try:
        result = await asyncio.wait_for(task, timeout=5.0)
        return Ok({"kind": "sync", "handle": handle, "first_page": result.first_page})
    except asyncio.TimeoutError:
        # 5초 초과 → 백그라운드로 승격
        await job_queue.xadd("jobs:query", {"handle": str(handle)})
        return Ok({"kind": "background", "handle": handle})
    # task는 백그라운드 잡 워커가 계속 실행
```

## 3. Result Cache (페이지네이션)

```python
class ResultCache:
    """첫 페이지는 메모리, 큰 결과는 parquet 임시 파일."""
    async def store_first_page(self, handle, rows): ...      # Redis 1MB
    async def store_full(self, handle, dataframe): ...        # /tmp/{handle}.parquet, TTL 15분
    async def fetch_page(self, handle, page_no): ...
```

## 4. PII Masking 함수

```python
# 정규식 사용은 timeout 보호 — `regex` 라이브러리의 timeout
import regex as re

PATTERNS = {
    'name': re.compile(r'^[가-힣]{2,4}$'),
    'rrn': re.compile(r'^\d{6}-?\d{7}$'),
    'phone': re.compile(r'^01[016789]-?\d{3,4}-?\d{4}$'),
    'email': re.compile(r'^[\w.+-]+@[\w-]+\.[\w.-]+$'),
}

def apply_mask(value: str, kind: str) -> str:
    if kind == 'name' and len(value) >= 2:
        return value[0] + '*' * (len(value) - 2) + (value[-1] if len(value) > 1 else '')
    if kind == 'rrn':
        return value[:6] + '-*******'
    if kind == 'phone':
        parts = value.replace('-', '')
        return f"{parts[:3]}-****-{parts[-4:]}"
    if kind == 'email':
        user, _, domain = value.partition('@')
        return user[0] + '***@' + domain
    return '***'  # custom or unknown

def mask_row(row: dict, ctx: MaskContext) -> dict:
    return {col: _maybe_mask(col, val, ctx) for col, val in row.items()}
```

- Idempotent: 마스킹된 값을 한 번 더 마스킹해도 결과 동일 (PBT)
- Oracle: 위 정규식과 동일 결과 (PBT)

## 5. Bad Regex 차단

```python
def validate_regex(pattern: str) -> Result[None, DomainError]:
    if len(pattern) > 256:
        return Err(DomainError.VALIDATION)
    # 위험 패턴 휴리스틱
    if any(bad in pattern for bad in ['(.*)*', '(.+)+', '(.*)+']):
        return Err(DomainError.VALIDATION)
    try:
        # `regex` 라이브러리: 매칭에 timeout 보호 가능
        compiled = re.compile(pattern, timeout=0.1)
        # smoke test: 짧은 문자열 매치
        compiled.fullmatch("test")
        return Ok(None)
    except (re.error, TimeoutError):
        return Err(DomainError.VALIDATION)
```

## 6. File Upload

```python
@router.post("/api/files/upload")
async def upload(req: Request, ctx: UserContext = Depends(current_user)):
    cl = int(req.headers.get("content-length", 0))
    if cl > 1024**3:
        return Err(DomainError.VALIDATION)  # 1GB 한도
    total = 0
    file_id = uuid4()
    storage = await get_storage_writer(ctx, file_id)
    try:
        async for chunk in req.stream():
            total += len(chunk)
            if total > 1024**3:
                await storage.abort()
                return Err(DomainError.VALIDATION)
            await storage.write(chunk)
    finally:
        await storage.close()
    # magic bytes 검증
    if not validate_file_format(storage.path, request.filename):
        await storage.delete()
        return Err(DomainError.VALIDATION)
    # 메타 row insert + audit
    ...
```

## 7. Schema Introspect

```python
async def tree(conn_id, user_ctx, expand: list[str] | None):
    # lazy: expand 경로만 fetch
    # 1000+ 객체: 페이지네이션 50/page
    # column_policies = 'block' 컬럼은 결과에서 제거
```

## 8. 메트릭

```
data_queries_total{engine, result}
data_query_duration_seconds {engine}   (histogram)
data_query_rows_returned {engine}      (histogram)
data_query_background_promotions_total
data_query_active_jobs                 (gauge)
data_files_uploaded_total {mime, result}
data_file_bytes_total
data_pii_mask_total {kind}
data_schema_introspect_latency_seconds
data_connectors_open                   (gauge)
```

## 9. Connection Pool

- Connector 인스턴스는 connection_id 별로 풀링 (사용자 자격증명별로 부풀려지지 않게 sharing)
- Idle timeout 5분, max-per-conn 20개

## 10. 에러 매핑

| DomainError 사유 | HTTP |
|---|---|
| connection NOT_FOUND | 404 |
| no grant | 403 |
| ParamQuery 위반 | 422 |
| Result too large | 422 |
| Connector unreachable | 502 |
| PII regex invalid | 422 |
