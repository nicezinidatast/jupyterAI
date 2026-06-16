"""Auto-registered SQL connections + helpful imports for analyst notebooks.

Runs once per kernel boot. Exposes:

    sales_engine  — SQLAlchemy engine for the sales_db (Postgres demo)
    crm_engine    — SQLAlchemy engine for the crm_mysql demo
    %sql / %%sql  — bound to sales_engine by default (jupysql)

So a copilot-generated cell like

    %%sql
    SELECT name, city FROM sales.customers LIMIT 10

just works. To switch databases inside one notebook:

    %sql crm_engine
    %%sql
    SELECT * FROM leads LIMIT 5

DSN strings are pulled from env vars set by docker-compose so we don't bake
credentials into the image.
"""

from __future__ import annotations

import os

try:
    from sqlalchemy import create_engine
except Exception as exc:  # pragma: no cover
    print(f"[platform-startup] sqlalchemy unavailable: {exc}")
    create_engine = None  # type: ignore[assignment]


def _maybe_engine(env_var: str, *, name: str):
    if create_engine is None:
        return None
    dsn = os.environ.get(env_var)
    if not dsn:
        print(f"[platform-startup] {name}: {env_var} not set, skipping")
        return None
    try:
        eng = create_engine(dsn, pool_pre_ping=True)
        # Smoke-test the connection so a broken DSN fails loudly at boot,
        # not silently three cells later.
        with eng.connect() as c:
            c.exec_driver_sql("SELECT 1")
        print(f"[platform-startup] {name} ready  ({dsn.split('@')[-1]})")
        return eng
    except Exception as exc:  # noqa: BLE001
        print(f"[platform-startup] {name} unavailable: {exc}")
        return None


sales_engine = _maybe_engine("DATAPLATFORM_SALES_DSN", name="sales_engine")
crm_engine = _maybe_engine("DATAPLATFORM_CRM_DSN", name="crm_engine")

# Wire jupysql so `%%sql` resolves without boilerplate. Default to sales_engine
# because the copilot's sample queries target sales.customers.
try:
    from IPython import get_ipython

    ip = get_ipython()
    if ip is not None:
        ip.run_line_magic("load_ext", "sql")
        # jupysql prefers SQLAlchemy URLs OR a live engine variable. Passing
        # the engine variable name (without quotes in %sql) is the documented
        # path; here we set the default via the configurable.
        ip.run_line_magic("config", "SqlMagic.autopandas = True")
        ip.run_line_magic("config", "SqlMagic.feedback = False")
        ip.run_line_magic("config", "SqlMagic.displaycon = False")
        if sales_engine is not None:
            # `%sql sales_engine` binds the magic to that engine. Subsequent
            # `%%sql ...` cells reuse the last-bound connection.
            ip.run_line_magic("sql", "sales_engine")
            print("[platform-startup] %%sql bound to sales_engine")
        else:
            print("[platform-startup] %%sql loaded; no default engine bound")
except Exception as exc:  # noqa: BLE001
    print(f"[platform-startup] could not configure %sql: {exc}")
