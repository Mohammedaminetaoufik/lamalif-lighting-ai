"""Shared helpers for the rule engine — pure functions, no DB, no LLM."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def hours_since(ts: Any) -> float | None:
    """Hours elapsed since an ISO timestamp string (as serialized by app.db).

    Returns None when the timestamp is missing or unparseable — callers treat
    None as "no recent data" rather than crashing.
    """
    if not ts:
        return None
    if isinstance(ts, (int, float)):
        # epoch seconds
        try:
            dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
        except (ValueError, OSError):
            return None
    else:
        try:
            dt = datetime.fromisoformat(str(ts))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(tz=timezone.utc) - dt
    return delta.total_seconds() / 3600.0


def num(value: Any, default: float = 0.0) -> float:
    """Coerce a possibly-None numeric to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def has_critical_alert(alerts: list[dict] | None) -> bool:
    return any((a or {}).get("severity") == "critical" for a in (alerts or []))


# Telemetry older than this is considered "stale" / no recent data.
TELEMETRY_STALE_HOURS = 6.0
# Work order age thresholds (hours).
WO_OLD_HOURS = 48.0
WO_CRITICAL_HOURS = 24.0
# Driver temperature thresholds (°C).
DRIVER_TEMP_CRITICAL = 80.0
DRIVER_TEMP_HIGH = 70.0
