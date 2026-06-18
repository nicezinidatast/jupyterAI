"""커널 부팅 시 자동으로 SQL 커넥션을 등록하고 분석용 매직 명령을 설정한다.

커널이 시작될 때 한 번만 실행된다. 이 스크립트가 노출하는 것들:

    sales_engine  — 판매 DB(Postgres 데모)용 SQLAlchemy 엔진
    crm_engine    — CRM MySQL 데모용 SQLAlchemy 엔진
    %sql / %%sql  — 기본적으로 sales_engine에 바인딩됨 (jupysql)

덕분에 코파일럿이 생성한 다음과 같은 셀이 별도 설정 없이 바로 동작한다:

    %%sql
    SELECT name, city FROM sales.customers LIMIT 10

한 노트북 안에서 DB를 전환하려면:

    %sql crm_engine
    %%sql
    SELECT * FROM leads LIMIT 5

DSN 문자열은 docker-compose가 주입하는 환경변수에서 읽어온다.
자격증명을 이미지에 하드코딩하지 않기 위해 이 방식을 택했다.
"""

from __future__ import annotations

import os

# sqlalchemy가 설치되지 않은 환경에서도 스크립트 자체가 죽지 않도록
# ImportError를 조용히 처리한다. 엔진 생성 함수가 None으로 대체되므로
# 이후 로직에서 None 체크로 분기한다.
try:
    from sqlalchemy import create_engine
except Exception as exc:  # pragma: no cover
    print(f"[platform-startup] sqlalchemy unavailable: {exc}")
    create_engine = None  # type: ignore[assignment]


def _maybe_engine(env_var: str, *, name: str):
    """환경변수에서 DSN을 읽어 SQLAlchemy 엔진을 생성하고, 연결 가능 여부를 즉시 검증한다.

    환경변수가 없거나 연결에 실패하면 None을 반환하고 에러를 출력한다.
    반환값이 None이어도 스크립트 전체가 중단되지 않아, 일부 DB가 없는
    개발 환경에서도 커널이 정상 시작된다.
    """
    if create_engine is None:
        return None
    dsn = os.environ.get(env_var)
    if not dsn:
        print(f"[platform-startup] {name}: {env_var} not set, skipping")
        return None
    try:
        eng = create_engine(dsn, pool_pre_ping=True)
        # 부팅 시점에 연결을 즉시 smoke-test한다.
        # DSN이 잘못되었을 때 "3번째 셀을 실행하다가 조용히 실패"하는 대신
        # 커널 시작 직후에 명확하게 오류를 드러내기 위해서다.
        with eng.connect() as c:
            c.exec_driver_sql("SELECT 1")
        print(f"[platform-startup] {name} ready  ({dsn.split('@')[-1]})")
        return eng
    except Exception as exc:  # noqa: BLE001
        print(f"[platform-startup] {name} unavailable: {exc}")
        return None


# 각 DB 엔진을 커널 네임스페이스(globals)에 직접 노출한다.
# 노트북 셀에서 `sales_engine`을 import 없이 바로 쓸 수 있게 하기 위함이다.
sales_engine = _maybe_engine("DATAPLATFORM_SALES_DSN", name="sales_engine")
crm_engine = _maybe_engine("DATAPLATFORM_CRM_DSN", name="crm_engine")

# jupysql(%sql / %%sql)을 로드하고 기본 엔진을 sales_engine으로 지정한다.
# 코파일럿의 샘플 쿼리가 sales.customers를 대상으로 하기 때문에
# 분석가가 boilerplate 없이 %%sql 셀을 바로 실행할 수 있도록 이 DB를 기본값으로 삼는다.
try:
    from IPython import get_ipython

    ip = get_ipython()
    if ip is not None:
        ip.run_line_magic("load_ext", "sql")
        # jupysql은 SQLAlchemy URL 문자열이나 라이브 엔진 변수 이름을 받는다.
        # %sql <변수명> 형태(따옴표 없이)로 바인딩하는 것이 공식 문서 권장 방식이다.
        # autopandas=True: 결과를 DataFrame으로 자동 변환해 판다스 체이닝을 바로 쓸 수 있게 한다.
        # feedback·displaycon을 끄면 %%sql 실행 시 불필요한 메타정보 출력이 사라진다.
        ip.run_line_magic("config", "SqlMagic.autopandas = True")
        ip.run_line_magic("config", "SqlMagic.feedback = False")
        ip.run_line_magic("config", "SqlMagic.displaycon = False")
        if sales_engine is not None:
            # `%sql sales_engine` 은 이후 `%%sql ...` 셀이 자동으로 이 커넥션을 재사용하게 한다.
            # 커넥션을 마지막으로 바인딩한 엔진이 기본값이 되는 jupysql의 동작 방식을 이용한 것이다.
            ip.run_line_magic("sql", "sales_engine")
            print("[platform-startup] %%sql bound to sales_engine")
        else:
            print("[platform-startup] %%sql loaded; no default engine bound")
except Exception as exc:  # noqa: BLE001
    print(f"[platform-startup] could not configure %sql: {exc}")
