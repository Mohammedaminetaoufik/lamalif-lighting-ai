"""Decision Center — compact AI summary for the dashboard widget + AI Center page.

Rule-based only (0 token). LLM enrichment is NOT triggered here — this endpoint
must always respond fast and never incur token costs.
"""
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.db import execute_select
from app.recommendations import evaluate_daily, global_priority, serialize
from app.routes.daily_digest import _collect_kpis, _collect_views

router = APIRouter(prefix="/ai", tags=["AI Decision Center"])

_CACHE: dict = {"data": None, "ts": 0.0}
_CACHE_TTL = 300  # 5 minutes


# ── Score & status ────────────────────────────────────────────────────────────

def _offline_count(kpis: dict) -> int:
    return int(kpis.get("offline_lampadaires", kpis.get("offline_count", 0)))


def _compute_network_score(kpis: dict, lcu_health: list) -> int:
    total = max(int(kpis.get("total_lampadaires", 1)), 1)
    offline = _offline_count(kpis)
    score = 100
    score -= int((offline / total) * 60)                                       # offline (0-60)
    critical = int(kpis.get("critical_alerts_24h", kpis.get("critical_alerts", 0)))
    score -= min(20, critical * 3)                                             # critiques (0-20)
    lcu_offline = sum(
        1 for r in lcu_health
        if r.get("status") == "offline"
        or (r.get("health_score") is not None and float(r.get("health_score", 100)) < 30)
    )
    lcu_total = max(len(lcu_health), 1)
    score -= int((lcu_offline / lcu_total) * 20)                               # LCU (0-20)
    return max(0, score)


def _status(score: int) -> str:
    if score >= 71:
        return "normal"
    if score >= 41:
        return "warning"
    return "critical"


# ── Probable causes ───────────────────────────────────────────────────────────

def _probable_causes(kpis: dict, lcu_health: list) -> list[dict]:
    total = max(int(kpis.get("total_lampadaires", 1)), 1)
    offline = _offline_count(kpis)
    offline_ratio = offline / total
    lcu_offline = sum(
        1 for r in lcu_health
        if r.get("status") == "offline"
        or (r.get("health_score") is not None and float(r.get("health_score", 100)) < 30)
    )
    critical = int(kpis.get("critical_alerts_24h", kpis.get("critical_alerts", 0)))

    causes: list[dict] = []

    if offline_ratio > 0.05 or lcu_offline > 0:
        p = min(0.95, 0.40 + offline_ratio * 0.50 + lcu_offline * 0.08)
        causes.append({"label": "Problème communication LCU/gateway", "probability": round(p, 2)})

    if offline_ratio > 0.15 or critical > 2:
        p = min(0.90, 0.40 + offline_ratio * 0.30 + min(critical, 5) * 0.04)
        causes.append({"label": "Problème alimentation réseau", "probability": round(p, 2)})

    if lcu_offline > 1:
        causes.append({"label": "Problème gateway / backhaul", "probability": round(min(0.85, 0.40 + lcu_offline * 0.10), 2)})
    elif offline_ratio > 0.25:
        causes.append({"label": "Problème gateway / backhaul", "probability": 0.55})

    causes.append({"label": "Problème driver LED", "probability": 0.25})
    return sorted(causes, key=lambda x: x["probability"], reverse=True)


# ── Summary (rule-based, no LLM) ─────────────────────────────────────────────

def _summary(kpis: dict, status: str, causes: list) -> str:
    offline = _offline_count(kpis)
    total   = int(kpis.get("total_lampadaires", 0))
    alerts  = int(kpis.get("open_alerts", 0))

    if offline == 0 and alerts == 0:
        return "Le réseau fonctionne normalement. Aucune anomalie détectée."

    sev = (
        "une panne critique"        if status == "critical" else
        "des anomalies importantes" if status == "warning"  else
        "des anomalies mineures"
    )
    parts: list[str] = []
    if offline > 0:
        pct = int(offline / max(total, 1) * 100)
        parts.append(f"{offline} lampadaire(s) hors ligne ({pct}%)")
    if alerts > 0:
        parts.append(f"{alerts} alerte(s) ouvertes")

    text = f"Le réseau présente {sev}. " + " et ".join(parts) + "."
    if causes:
        text += f" Cause probable : {causes[0]['label']}."
    return text


# ── DB helpers (non-critical — fail silently) ─────────────────────────────────

def _alert_summary() -> dict:
    try:
        rows = execute_select(
            "SELECT severity, COUNT(*) AS count FROM alerts WHERE status = 'open' GROUP BY severity"
        )["rows"]
        out: dict = {"critical": 0, "warning": 0, "info": 0}
        for r in rows:
            sev = str(r.get("severity", "info"))
            out[sev] = out.get(sev, 0) + int(r.get("count", 0))
        return out
    except Exception:
        return {"critical": 0, "warning": 0, "info": 0}


def _timeline_events() -> list[dict]:
    try:
        rows = execute_select(
            "SELECT message, severity, created_at FROM alerts ORDER BY created_at DESC LIMIT 8"
        )["rows"]
        events: list[dict] = []
        for r in rows:
            raw = r.get("created_at")
            if raw is None:
                t = "--:--"
            elif isinstance(raw, str):
                t = datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%H:%M")
            else:
                t = raw.strftime("%H:%M")
            events.append({
                "time": t,
                "event": str(r.get("message", "Événement inconnu")),
                "severity": str(r.get("severity", "info")),
            })
        return events
    except Exception:
        return []


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("/decision-center")
def get_decision_center(refresh: bool = Query(default=False)):
    now = time.monotonic()

    if not refresh and _CACHE["data"] and (now - _CACHE["ts"]) < _CACHE_TTL:
        return {**_CACHE["data"], "cached": True}

    kpis       = _collect_kpis()
    views      = _collect_views()
    zone_health = views.get("zone_health", [])
    lcu_health  = views.get("lcu_health", [])

    # Rule engine
    recs     = evaluate_daily(kpis, views)
    all_recs = serialize(recs)
    top_actions = all_recs[:3]

    # Scores & analysis
    net_score  = _compute_network_score(kpis, lcu_health)
    status     = _status(net_score)
    causes     = _probable_causes(kpis, lcu_health)
    network_summary = _summary(kpis, status, causes)

    # Overall priority (highest of all recommendations)
    priority   = global_priority(recs) if recs else "low"

    # Confidence: higher when we have good coverage data
    total_lamps = max(int(kpis.get("total_lampadaires", 1)), 1)
    coverage    = min(1.0, (len(zone_health) * 8 + len(lcu_health) * 4) / total_lamps)
    confidence  = round(min(0.95, 0.72 + coverage * 0.23), 2)

    # Zone status (sorted by offline count desc)
    zone_status = sorted(
        [
            {
                "zone":            r.get("zone", "—"),
                "total":           int(r.get("total_lampadaires", 0)),
                "offline_count":   int(r.get("offline_count", 0)),
                "critical_alerts": int(r.get("critical_alerts_count", 0)),
                "open_workorders": int(r.get("open_workorders_count", 0)),
                "offline_pct":     round(
                    int(r.get("offline_count", 0)) / max(int(r.get("total_lampadaires", 1)), 1) * 100
                ),
            }
            for r in zone_health
        ],
        key=lambda x: x["offline_count"],
        reverse=True,
    )

    # LCU status
    lcu_status = [
        {
            "ref":             r.get("reference", "—"),
            "zone":            r.get("zone", "—"),
            "status":          r.get("status", "unknown"),
            "health_score":    int(float(r.get("health_score", 100))),
            "offline_lamps":   int(r.get("offline_count", 0)),
            "critical_alerts": int(r.get("critical_alerts_count", 0)),
        }
        for r in lcu_health
    ]

    data = {
        "network_score":      net_score,
        "confidence":         confidence,
        "status":             status,
        "priority":           priority,
        "summary":            network_summary,
        "top_actions":        top_actions,
        "all_recommendations": all_recs,
        "probable_causes":    causes,
        "kpis":               kpis,
        "zone_status":        zone_status,
        "lcu_status":         lcu_status,
        "alert_summary":      _alert_summary(),
        "timeline_events":    _timeline_events(),
        "generated_at":       datetime.now(tz=timezone.utc).isoformat(),
        "llm_available":      False,
        "cached":             False,
    }

    _CACHE["data"] = data
    _CACHE["ts"]   = now
    return data
