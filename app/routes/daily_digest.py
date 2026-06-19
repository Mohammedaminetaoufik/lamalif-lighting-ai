import time
from fastapi import APIRouter, Query
from app.db import execute_select
from app.llm_client import generate_daily_digest
from app.rag.retriever import build_rag_context
from app.recommendations import evaluate_daily, global_priority, serialize

router = APIRouter(prefix="/ai", tags=["AI Daily Digest"])

_CACHE = {
    "digest": None,
    "generated_at": 0,
    "cooldown_until": 0.0,   # monotonic time until which we must not call Groq (429 cooldown)
}
_CACHE_TTL = 3600 * 6  # 6 hours
_CACHE_TTL_429 = 300   # 5 minutes if rate limited

_EMPTY_KPIS = {
    "total_lampadaires": 0, "offline_lampadaires": 0, "open_alerts": 0,
    "critical_alerts": 0, "open_workorders": 0, "total_energy_kwh": 0,
    "new_alerts_24h": 0, "critical_alerts_24h": 0, "new_workorders_24h": 0,
    "resolved_workorders_24h": 0,
}


def _collect_kpis() -> dict:
    """KPIs from the ai_daily_operations_kpis view (source of truth, 0 token).

    Falls back to per-query collection if the 24h view is not yet installed.
    """
    try:
        res = execute_select("SELECT * FROM ai_daily_operations_kpis")
        if res["rows"]:
            return {**_EMPTY_KPIS, **res["rows"][0]}
    except Exception:
        pass

    # Fallback (view not migrated yet) — global KPIs + inline 24h deltas
    kpis = dict(_EMPTY_KPIS)
    try:
        res = execute_select("SELECT total_lampadaires, offline_lampadaires, open_alerts, critical_alerts, open_workorders, total_energy_kwh FROM ai_global_kpis")
        if res["rows"]:
            kpis.update(res["rows"][0])
        res = execute_select("SELECT COUNT(*) as count FROM alerts WHERE created_at > NOW() - INTERVAL '24 hours'")
        kpis["new_alerts_24h"] = res["rows"][0]["count"] if res["rows"] else 0
        res = execute_select("SELECT COUNT(*) as count FROM alerts WHERE severity = 'critical' AND created_at > NOW() - INTERVAL '24 hours'")
        kpis["critical_alerts_24h"] = res["rows"][0]["count"] if res["rows"] else 0
        res = execute_select("SELECT COUNT(*) as count FROM work_orders WHERE created_at > NOW() - INTERVAL '24 hours'")
        kpis["new_workorders_24h"] = res["rows"][0]["count"] if res["rows"] else 0
        res = execute_select("SELECT COUNT(*) as count FROM work_orders WHERE status IN ('resolved', 'closed') AND resolved_at > NOW() - INTERVAL '24 hours'")
        kpis["resolved_workorders_24h"] = res["rows"][0]["count"] if res["rows"] else 0
    except Exception as e:
        print(f"Error collecting KPIs for digest: {e}")
    return kpis


def _collect_views() -> dict:
    """Zone/LCU rows feeding the rule engine — read-only ai_* views, 0 token."""
    views: dict = {}
    try:
        views["zone_health"] = execute_select(
            "SELECT zone, total_lampadaires, offline_count, critical_alerts_count, open_workorders_count "
            "FROM ai_zone_health"
        )["rows"]
    except Exception:
        views["zone_health"] = []
    try:
        views["lcu_health"] = execute_select(
            "SELECT reference, zone, status, health_score, offline_count, critical_alerts_count "
            "FROM ai_lcu_health ORDER BY health_score ASC LIMIT 10"
        )["rows"]
    except Exception:
        views["lcu_health"] = []
    return views


def _rule_based(kpis: dict) -> list[dict]:
    return serialize(evaluate_daily(kpis, _collect_views()))


@router.get("/daily-digest")
def get_daily_digest(refresh: bool = Query(default=False)):
    now = time.monotonic()

    # Serve last generated digest; NEVER call the LLM unless explicitly refreshed.
    if not refresh:
        if _CACHE["digest"]:
            return {**_CACHE["digest"], "cached": True, "generated_at": _CACHE["generated_at"]}
        kpis = _collect_kpis()
        recs = _rule_based(kpis)
        return {
            "summary": "",
            "analysis": "",
            "recommendations": [],
            "rule_based_recommendations": recs,
            "priority": global_priority(evaluate_daily(kpis, _collect_views())) if recs else "low",
            "confidence": 0.0,
            "kpis": kpis,
            "llm_available": False,
            "cached": False,
            "generated_at": 0,
            "retry_after_seconds": 0,
        }

    kpis = _collect_kpis()
    rule_recs = _rule_based(kpis)

    # Respect the 429 cooldown — don't hammer Groq.
    if now < _CACHE["cooldown_until"]:
        retry_after = int(_CACHE["cooldown_until"] - now)
        return {
            "summary": "Analyse avancée temporairement indisponible. Les recommandations opérationnelles restent disponibles.",
            "analysis": "",
            "recommendations": [],
            "rule_based_recommendations": rule_recs,
            "priority": "medium",
            "confidence": 0.0,
            "kpis": kpis,
            "llm_available": False,
            "cached": False,
            "generated_at": now,
            "retry_after_seconds": retry_after,
        }

    try:
        rag = build_rag_context("synthèse quotidienne réseau éclairage public dernières 24 heures")
        digest = generate_daily_digest(kpis, rag=rag)
        result = {
            **digest,
            "kpis": kpis,
            "rule_based_recommendations": rule_recs,
            "llm_available": True,
            "retry_after_seconds": 0,
        }
        _CACHE["digest"] = result
        _CACHE["generated_at"] = now
        return {**result, "cached": False, "generated_at": now}

    except Exception as e:
        print(f"Error generating daily digest: {e}")
        is_429 = "429" in str(e) or "rate_limit" in str(e).lower()
        if is_429:
            _CACHE["cooldown_until"] = now + _CACHE_TTL_429
        fallback = {
            "summary": "Analyse avancée temporairement indisponible. Les recommandations opérationnelles restent disponibles.",
            "analysis": "Les indicateurs et recommandations rule-based ci-dessous restent valides.",
            "recommendations": [],
            "rule_based_recommendations": rule_recs,
            "priority": "medium",
            "confidence": 0.0,
            "kpis": kpis,
            "llm_available": False,
            "retry_after_seconds": _CACHE_TTL_429 if is_429 else 0,
        }
        return {**fallback, "cached": False, "generated_at": now}
