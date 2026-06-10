import datetime
import decimal
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from app.config import settings


def _serialize_value(v):
    """Convert PostgreSQL types to JSON-safe primitives."""
    if v is None:
        return None
    if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, datetime.timedelta):
        return v.total_seconds()
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    return v

# Read-only engine — SELECT on ai_* views only
engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Write engine — INSERT/SELECT on ai_query_logs only
log_engine: Engine = create_engine(
    settings.effective_log_database_url,
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=5,
)


def test_connection() -> dict:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 AS ok"))
        row = result.fetchone()
    return {
        "database": "connected",
        "ok": row[0] == 1,
    }


def execute_select(sql: str) -> dict:
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = result.fetchall()
        columns = list(result.keys())
    return {
        "columns": columns,
        "rows": [{k: _serialize_value(v) for k, v in zip(columns, row)} for row in rows],
        "row_count": len(rows),
    }


def execute_select_params(sql: str, params: dict) -> dict:
    """Parameterized SELECT — safe for user-supplied IDs."""
    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = result.fetchall()
        columns = list(result.keys())
    return {
        "columns": columns,
        "rows": [{k: _serialize_value(v) for k, v in zip(columns, row)} for row in rows],
        "row_count": len(rows),
    }


def log_ai_query(
    question: str,
    generated_sql: str | None,
    status: str,
    row_count: int = 0,
    error_message: str | None = None,
    duration_ms: int | None = None,
    user_id: int | None = None,
) -> None:
    sql = text("""
        INSERT INTO ai_query_logs
            (user_id, question, generated_sql, status, row_count, error_message, duration_ms)
        VALUES
            (:user_id, :question, :generated_sql, :status, :row_count, :error_message, :duration_ms)
    """)
    with log_engine.begin() as conn:
        conn.execute(sql, {
            "user_id": user_id,
            "question": question,
            "generated_sql": generated_sql,
            "status": status,
            "row_count": row_count,
            "error_message": error_message,
            "duration_ms": duration_ms,
        })


def get_ai_query_history(limit: int = 20) -> dict:
    sql = text("""
        SELECT id, user_id, question, generated_sql, status,
               row_count, error_message, duration_ms, created_at
        FROM ai_query_logs
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    with log_engine.connect() as conn:
        result = conn.execute(sql, {"limit": limit})
        rows = result.fetchall()
        columns = list(result.keys())
    return {
        "columns": columns,
        "rows": [{k: _serialize_value(v) for k, v in zip(columns, row)} for row in rows],
        "row_count": len(rows),
    }
