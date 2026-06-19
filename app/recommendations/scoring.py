"""Industrial scores (0–100) computed in code from ai_* view data.

All scores are deterministic and explainable. The LLM never computes a score.
Input dicts follow the shape produced by entity_insights data collectors:
  lampadaire: {details, diagnostics, telemetry, alerts, workorders, [lcu_status]}
  lcu:        {details, health, lamps, alerts, workorders}
"""
from __future__ import annotations

from typing import Any

from .utils import (
    DRIVER_TEMP_CRITICAL, DRIVER_TEMP_HIGH, TELEMETRY_STALE_HOURS,
    WO_OLD_HOURS, has_critical_alert, hours_since, num,
)


def _clamp(v: float) -> int:
    return int(max(0, min(100, round(v))))


def _oldest_open_wo_hours(workorders: list[dict] | None) -> float | None:
    ages = []
    for wo in workorders or []:
        if (wo or {}).get("status") in ("resolved", "closed", "cancelled"):
            continue
        h = hours_since(wo.get("created_at"))
        if h is not None:
            ages.append(h)
    return max(ages) if ages else None


def compute_lampadaire_risk_score(data: dict[str, Any]) -> int:
    details = data.get("details") or {}
    diag = data.get("diagnostics") or {}
    alerts = data.get("alerts") or []
    lcu_status = (data.get("lcu_status") or {}).get("status")

    score = 0.0
    if details.get("etat") == "offline":
        score += 30
    if has_critical_alert(alerts) or num(diag.get("critical_alerts_count")) > 0:
        score += 25
    if lcu_status == "offline":
        score += 20
    wo_age = _oldest_open_wo_hours(data.get("workorders"))
    if wo_age is not None and wo_age > WO_OLD_HOURS:
        score += 15

    driver_temp = num(diag.get("driver_temperature"), default=-1)
    if driver_temp >= DRIVER_TEMP_CRITICAL:
        score += 25
    elif driver_temp >= DRIVER_TEMP_HIGH:
        score += 15

    last_tel = diag.get("last_measure_at") or (data.get("telemetry") or {}).get("measured_at")
    tel_age = hours_since(last_tel)
    if tel_age is None or tel_age > TELEMETRY_STALE_HOURS:
        score += 10

    if details.get("commissioning_status") not in (None, "commissioned"):
        score += 10

    return _clamp(score)


def compute_lampadaire_maintainability_score(data: dict[str, Any]) -> int:
    details = data.get("details") or {}
    diag = data.get("diagnostics") or {}

    score = 100.0
    if details.get("latitude") is None or details.get("longitude") is None:
        score -= 15
    if details.get("lcu_id") is None and not details.get("lcu_reference"):
        score -= 20
    last_tel = diag.get("last_measure_at") or (data.get("telemetry") or {}).get("measured_at")
    tel_age = hours_since(last_tel)
    if tel_age is None or tel_age > TELEMETRY_STALE_HOURS:
        score -= 15
    wo_age = _oldest_open_wo_hours(data.get("workorders"))
    if wo_age is not None and wo_age > WO_OLD_HOURS:
        score -= 20
    if not details.get("zone"):
        score -= 10
    if details.get("commissioning_status") not in (None, "commissioned"):
        score -= 10
    return _clamp(score)


def compute_communication_health_score(data: dict[str, Any]) -> int:
    """For a lampadaire or LCU: penalize stale last_seen, offline LCU, weak signal."""
    details = data.get("details") or {}
    score = 100.0

    last_seen = details.get("last_seen_at")
    seen_age = hours_since(last_seen)
    if seen_age is None:
        score -= 30
    elif seen_age > 24:
        score -= 30
    elif seen_age > 6:
        score -= 15

    lcu_status = details.get("status") or (data.get("lcu_status") or {}).get("status")
    if lcu_status == "offline":
        score -= 40
    elif lcu_status == "unknown":
        score -= 20

    signal = details.get("controller_signal_quality")
    if signal is not None:
        s = num(signal)
        if s < 30:
            score -= 25
        elif s < 60:
            score -= 10
    return _clamp(score)


def compute_lcu_risk_score(data: dict[str, Any]) -> int:
    details = data.get("details") or {}
    health = data.get("health") or {}
    lamps = data.get("lamps") or []
    alerts = data.get("alerts") or []

    score = 0.0
    if details.get("status") == "offline":
        score += 40
    health_score = health.get("health_score")
    if health_score is not None:
        hs = num(health_score)
        if hs < 30:
            score += 30
        elif hs < 60:
            score += 15
    if has_critical_alert(alerts) or num(health.get("critical_alerts_count")) > 0:
        score += 20

    total = len(lamps) or num(details.get("lampadaires_count"))
    offline = num(details.get("offline_count"))
    if total and offline / total > 0.3:
        score += 15
    return _clamp(score)


def compute_zone_risk_score(row: dict[str, Any]) -> int:
    total = num(row.get("total_lampadaires"))
    offline = num(row.get("offline_count"))
    critical = num(row.get("critical_alerts_count"))

    score = 0.0
    if total:
        ratio = offline / total
        if ratio >= 0.8:
            score += 60
        elif ratio >= 0.4:
            score += 40
        elif ratio > 0:
            score += 20
    score += min(30, critical * 10)
    if num(row.get("open_workorders_count")) > 0:
        score += 10
    return _clamp(score)


def compute_energy_efficiency_score(row: dict[str, Any]) -> int:
    """Zone-level efficiency from ai_energy_summary. Lower dimming + high power → lower score."""
    score = 100.0
    avg_intensity = row.get("avg_intensity")
    if avg_intensity is not None and num(avg_intensity) >= 90:
        # No effective dimming applied
        score -= 25

    nominal = num(row.get("total_nominal_power_w"))
    measured = num(row.get("avg_measured_power_w"))
    if nominal and measured:
        # Heuristic: high measured power relative to nominal per-lamp average
        lamps = num(row.get("lampadaires_count")) or 1
        nominal_avg = nominal / lamps
        if nominal_avg and measured > nominal_avg * 0.9:
            score -= 20
    return _clamp(score)
