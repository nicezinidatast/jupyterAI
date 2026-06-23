"""data-unit 공개 API — 연결 목록, 스키마 조회, 쿼리 실행, 파일 업로드.

실제 드라이버 경로는 ``open_runtime_connector``를 통한 asyncpg / aiomysql이다.
모든 결과 행은 서버를 떠나기 전에 PII(개인식별정보) 마스킹을 거친다 — 이
규칙이 깨지면 원본 개인정보가 클라이언트로 새어 나가므로 절대 우회 경로를
만들지 않는다.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from credential.adapters.vault import VaultAdapter
from credential.models import Credential
from dataplatform_shared.result import Err

from data.connectors.factory import open_runtime_connector
from data.models import Connection, PiiPattern
from data.schemas import ConnectionSpec, ParamQuery
from data.services.pii_masking import mask_row

router = APIRouter(prefix="/api", tags=["data"])
Session = Annotated[AsyncSession, Depends(get_session)]


def _vault(request: Request) -> VaultAdapter:
    # 비밀 보관소(vault) 어댑터를 앱 상태에서 꺼내는 의존성. 아직 초기화 전이면
    # 자격증명 복호화가 불가능하므로 503으로 분명히 막는다(조용한 실패 금지).
    adapter = getattr(request.app.state, "vault_adapter", None)
    if adapter is None:
        raise HTTPException(status_code=503, detail="vault not initialized")
    return adapter


VaultDep = Annotated[VaultAdapter, Depends(_vault)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _spec_from(conn: Connection) -> ConnectionSpec:
    return ConnectionSpec(
        name=conn.name,
        engine=conn.engine,
        host=conn.host,
        port=conn.port,
        database=conn.database,
        credential_id=str(conn.credential_id),
        options=conn.options or {},
    )


async def _resolve_credentials(
    conn: Connection, session: AsyncSession, vault: VaultAdapter
) -> tuple[str, str]:
    """(username, password)를 반환한다. 비밀번호는 vault 어댑터로 복호화한다.

    사용자명은 비밀이 아닌 운영 메타데이터라 Connection.options에 평문으로 둔다.
    비밀번호는 ``Credential.vault_path`` 위치의 SecretsStorage에 암호화돼 있다.
    자격증명이 없거나 삭제됐거나 복호화에 실패하면 빈 비밀번호("")를 돌려준다.
    호출부는 username이 비었는지로 "자격증명 미구성"을 판단한다.
    """
    username = (conn.options or {}).get("username", "")
    cred = await session.get(Credential, conn.credential_id)
    if cred is None or cred.deleted_at is not None:
        return username, ""
    result = await vault.read(cred.vault_path)
    if not result.ok:
        return username, ""
    return username, result.value.reveal()


def _classify_column_kinds(columns: list[str]) -> dict[str, str | None]:
    # 컬럼명을 보고 PII 종류를 추정한다. 흔한 컬럼명을 종류에 매핑하고,
    # 매칭이 없으면 None으로 둬 값 기반 자동 탐지(detect_kind)에 맡긴다.
    # 비교는 소문자로 정규화해 대소문자 표기 차이를 흡수한다.
    column_kinds: dict[str, str | None] = {}
    for col in columns:
        name = col.lower()
        if name in ("name", "customer_name", "lead_name", "display_name"):
            column_kinds[col] = "name"
        elif name == "email":
            column_kinds[col] = "email"
        elif name in ("phone", "mobile"):
            column_kinds[col] = "phone"
        elif name in ("rrn", "ssn"):
            column_kinds[col] = "rrn"
        else:
            column_kinds[col] = None
    return column_kinds


# ---------------------------------------------------------------------------
# 연결 목록 (분석가에게는 읽기 전용)
# ---------------------------------------------------------------------------
@router.get("/connections")
async def list_connections(session: Session) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(Connection).where(Connection.is_active.is_(True)).order_by(Connection.name)
        )
    ).scalars().all()
    return [
        {
            "connection_id": str(c.connection_id),
            "name": c.name,
            "engine": c.engine,
            "host": c.host,
            "port": c.port,
            "database": c.database,
        }
        for c in rows
    ]


# ---------------------------------------------------------------------------
# 스키마 조회 — 실제 information_schema 질의
# ---------------------------------------------------------------------------
@router.get("/connections/{connection_id}/schema")
async def connection_schema(connection_id: UUID, session: Session, vault: VaultDep) -> dict[str, Any]:
    conn = await session.get(Connection, connection_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="connection not found")

    spec = _spec_from(conn)
    username, password = await _resolve_credentials(conn, session, vault)
    if not username:
        # 자격증명이 연결되지 않은 엔진(예: warehouse_hive 자리표시자)은 이번
        # 라운드에서 조회 불가다. 오류 대신 빈 stub과 안내 노트로 부드럽게 반환한다.
        return {
            "connection_id": str(connection_id),
            "name": conn.name,
            "tables": [],
            "note": "credentials not configured (Phase 2 engine)",
        }
    factory_result = open_runtime_connector(spec, username=username, password=password)
    if isinstance(factory_result, Err):
        raise HTTPException(status_code=400, detail="engine not supported in this build")
    connector = factory_result.value

    active_patterns = (
        await session.execute(select(PiiPattern).where(PiiPattern.is_active.is_(True)))
    ).scalars().all()

    try:
        introspection = await connector.introspect()
    except Exception as exc:  # noqa: BLE001
        # 외부 DB 조회 실패는 우리 서버 잘못이 아니므로 502(상류 게이트웨이 오류)로 알린다.
        raise HTTPException(status_code=502, detail=f"introspection failed: {exc!s}") from None

    # 활성 PII 패턴 종류에서 "컬럼명 → PII 종류" 조회표를 만들어, 각 컬럼에
    # pii_kind 힌트를 달아준다(프런트가 어떤 컬럼이 가려질지 미리 표시).
    pii_lookup = _build_pii_column_lookup({p.kind for p in active_patterns})
    enriched_tables: list[dict[str, Any]] = []
    for table in introspection.get("tables", []):
        cols = [
            {
                "name": col["name"],
                "type": col["type"],
                "pii_kind": pii_lookup.get(col["name"].lower()),
            }
            for col in table["columns"]
        ]
        enriched_tables.append(
            {
                "schema": table.get("schema"),
                "name": table["name"],
                "columns": cols,
            }
        )

    return {
        "connection_id": str(connection_id),
        "name": conn.name,
        "engine": conn.engine,
        "tables": enriched_tables,
    }


def _build_pii_column_lookup(active_kinds: set[str]) -> dict[str, str]:
    # 활성화된 PII 종류만 조회표에 넣는다. 관리자가 끈 종류는 빠지므로,
    # 비활성 패턴의 컬럼에는 pii_kind 힌트가 달리지 않는다.
    lookup: dict[str, str] = {}
    if "name" in active_kinds:
        for n in ("name", "customer_name", "lead_name", "display_name"):
            lookup[n] = "name"
    if "email" in active_kinds:
        lookup["email"] = "email"
    if "phone" in active_kinds:
        lookup["phone"] = "phone"
        lookup["mobile"] = "phone"
    if "rrn" in active_kinds:
        lookup["rrn"] = "rrn"
        lookup["ssn"] = "rrn"
    return lookup


# ---------------------------------------------------------------------------
# 쿼리 실행 — 실제 드라이버, PII 마스킹, 소요 시간 측정
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    connection_id: str
    sql: str = Field(min_length=1, max_length=100_000)
    params: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


_MAX_ROWS = 10_000  # SPA가 폭주 응답에 압사하지 않도록 행 수 상한
_DEFAULT_TIMEOUT = 5.0


@router.post("/queries/execute")
async def execute_query(body: QueryRequest, session: Session, vault: VaultDep) -> dict[str, Any]:
    try:
        conn_uuid = UUID(body.connection_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid connection id") from None

    conn = await session.get(Connection, conn_uuid)
    if conn is None:
        raise HTTPException(status_code=404, detail="connection not found")

    spec = _spec_from(conn)
    username, password = await _resolve_credentials(conn, session, vault)
    if not username:
        raise HTTPException(
            status_code=503,
            detail="connection has no credentials configured for this build",
        )

    factory_result = open_runtime_connector(spec, username=username, password=password)
    if isinstance(factory_result, Err):
        raise HTTPException(status_code=400, detail="engine not supported in this build")
    connector = factory_result.value

    try:
        query = ParamQuery(sql=body.sql, params=body.params)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from None

    # 벽시계 기준 소요 시간을 잰다(perf_counter는 단조 증가라 시계 보정에 영향 없음).
    started = time.perf_counter()
    try:
        stream = await connector.execute(query, timeout=_DEFAULT_TIMEOUT)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="query exceeded 5s timeout") from None
    except Exception as exc:  # noqa: BLE001
        # 일반화된 오류만 노출하고, 상세는 로거를 통해 서버 측에만 남긴다(정보 누설 방지).
        raise HTTPException(status_code=502, detail=f"query failed: {exc!s}") from None
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    # 커넥터가 to_list를 제공하면 빠른 경로로 한 번에 받고, 아니면 비동기 순회한다.
    rows = stream.to_list() if hasattr(stream, "to_list") else [r async for r in stream]
    if len(rows) > _MAX_ROWS:
        rows = rows[:_MAX_ROWS]  # 상한 초과분은 잘라 응답 크기를 제한

    if not rows:
        columns: list[str] = []
        masked_rows: list[dict[str, Any]] = []
    else:
        # 첫 행의 키를 컬럼 목록으로 삼는다. 컬럼명으로 PII 종류를 분류한 뒤,
        # JSON 직렬화 가능한 형태로 정규화하고 행마다 마스킹을 적용한다.
        columns = list(rows[0].keys())
        column_kinds = _classify_column_kinds(columns)
        masked_rows = [mask_row(_normalise_row(r), column_kinds) for r in rows]

    active_patterns = (
        await session.execute(select(PiiPattern).where(PiiPattern.is_active.is_(True)))
    ).scalars().all()

    return {
        "connection": conn.name,
        "engine": conn.engine,
        "sql": body.sql,
        "columns": columns,
        "rows": masked_rows,
        "row_count": len(masked_rows),
        "elapsed_ms": elapsed_ms,
        "active_pii_patterns": [p.name for p in active_patterns],
        "executed_at": datetime.utcnow().isoformat() + "Z",
    }


def _normalise_row(row: dict[str, Any]) -> dict[str, Any]:
    """JSON 기본형이 아닌 값을 JSON 친화적 형태로 강제 변환한다.

    DB 드라이버는 datetime·date·bytes·Decimal 등 JSON으로 바로 못 싣는 타입을
    돌려줄 수 있다. 날짜류는 isoformat 문자열로, 바이트는 UTF-8(깨진 바이트는
    치환)로, 그 외 미지의 타입은 str()로 떨어뜨려 직렬화 실패를 막는다.
    """
    out: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif hasattr(v, "isoformat"):  # date·time 등 isoformat을 가진 다른 타입도 포괄
            out[k] = v.isoformat()
        elif isinstance(v, (bytes, bytearray)):
            out[k] = v.decode("utf-8", errors="replace")
        elif isinstance(v, (int, float, str, bool)) or v is None:
            out[k] = v  # 이미 JSON 기본형이면 그대로 둔다
        else:
            out[k] = str(v)  # Decimal 등 알 수 없는 타입은 문자열로 안전 변환
    return out


# ---------------------------------------------------------------------------
# 파일 업로드 — CSV/TSV/JSON/Parquet/Excel/Feather, 최대 1 GiB.
# ---------------------------------------------------------------------------
# 업로드 처리에만 필요한 의존성을 이 위치에서 늦게 import 한다(모듈 상단을
# 가볍게 유지하고, 업로드 관련 코드를 한 곳에 모으기 위함).
from datetime import datetime as _dt
from fastapi import UploadFile, File
from uuid import uuid4 as _uuid4

from audit.models import AuditLog
from data.models import FileUpload
from data.services.file_ingest import IngestError, ingest_upload
from auth.api.oidc_dependency import actor_from_request


@router.post("/files/upload")
async def upload_file(
    session: Session, request: Request, upload: UploadFile = File(...)
) -> dict[str, Any]:
    if not upload.filename:
        raise HTTPException(status_code=422, detail="missing filename")
    actor = await actor_from_request(request)
    try:
        result = await ingest_upload(upload.filename, upload)
    except IngestError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from None

    file_id = _uuid4()
    # 아직 사용자 식별이 배선되지 않은 단계라, 0으로 채운 센티넬 UUID를 소유자로
    # 쓴다(인증 연동 시 실제 user_id로 교체될 자리).
    sentinel_user = UUID("00000000-0000-0000-0000-000000000000")
    session.add(
        FileUpload(
            file_id=file_id,
            user_id=sentinel_user,
            filename=result.safe_name,
            size_bytes=result.size_bytes,
            mime=result.mime,
            storage_path=str(result.storage_path),
        )
    )
    # FR-SEC-01: 모든 파일 업로드는 기록 대상 이벤트다. FileUpload 삽입과 같은
    # 트랜잭션에서 감사 로그 행을 함께 넣어, 둘이 원자적으로(atomically) 커밋되게
    # 한다. 한쪽만 남아 업로드는 됐는데 감사 기록이 없는 상태를 방지하기 위함이다.
    session.add(
        AuditLog(
            event_type="file_uploaded",
            actor_id=actor,
            resource=f"file:{result.safe_name}",
            result="success",
            occurred_at=_dt.utcnow(),
            corr_id=f"upload-{file_id}",
            payload={
                "file_id": str(file_id),
                "safe_name": result.safe_name,
                "size_bytes": result.size_bytes,
                "mime": result.mime,
                "kind": result.kind,
            },
        )
    )
    await session.commit()
    return {
        "file_id": str(file_id),
        "safe_name": result.safe_name,
        "size_bytes": result.size_bytes,
        "kind": result.kind,
        "mime": result.mime,
        "jupyter_path": result.jupyter_path,
        # 분석가가 JupyterLab에서 바로 붙여 쓸 수 있는 pandas 읽기 코드 힌트.
        # xlsx만 pd.read_excel로 매핑되고 나머지는 read_<kind> 규칙을 따른다.
        "hint": f"pd.read_{result.kind if result.kind != 'xlsx' else 'excel'}('{result.jupyter_path}')",
    }


# ---------------------------------------------------------------------------
# 단순 핑 — 플랫폼 스모크(smoke) 점검 엔드포인트용으로 유지
# ---------------------------------------------------------------------------
@router.get("/queries/ping")
async def ping_queries() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/connections/ping")
async def ping_connections() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/files/ping")
async def ping_files() -> dict[str, str]:
    return {"status": "ok"}
