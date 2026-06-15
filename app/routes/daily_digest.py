import time
from fastapi import APIRouter, Query
from app.db import execute_select
from app.llm_client import generate_daily_digest
from app.rag.retriever import build_rag_context

router = APIRouter(prefix="/ai", tags=["AI Daily Digest"])

_CACHE = {
    "digest": None,
    "generated_at": 0,
}
_CACHE_TTL = 3600 * 6  # 6 hours
_CACHE_TTL_429 = 300   # 5 minutes if rate limited


def _collect_kpis() -> dict:
    """Collect dashboard KPIs from PostgreSQL — cheap, no LLM tokens."""
    kpis: dict = {}
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
        kpis = {
            "total_lampadaires": 0, "offline_lampadaires": 0, "open_alerts": 0,
            "critical_alerts": 0, "open_workorders": 0, "total_energy_kwh": 0,
            "new_alerts_24h": 0, "critical_alerts_24h": 0, "new_workorders_24h": 0,
            "resolved_workorders_24h": 0
        }
    return kpis


@router.get("/daily-digest")
def get_daily_digest(refresh: bool = Query(default=False)):
    now = time.monotonic()

    # Serve last generated digest; NEVER call the LLM unless explicitly refreshed.
    # A page load/refresh costs zero tokens — KPI chips still show (DB only).
    if not refresh:
        if _CACHE["digest"]:
            return {**_CACHE["digest"], "cached": True, "generated_at": _CACHE["generated_at"]}
        # Not generated yet — return KPIs only, no LLM call
        return {
            "summary": "",
            "analysis": "",
            "recommendations": [],
            "priority": "medium",
            "confidence": 0.0,
            "kpis": _collect_kpis(),
            "cached": False,
            "generated_at": 0,
        }

    # 1. Collect KPIs
    kpis = _collect_kpis()

    # 2. Generate LLM Digest
    try:
        rag = build_rag_context("synthèse quotidienne réseau éclairage public dernières 24 heures")
        digest = generate_daily_digest(kpis, rag=rag)
        
        # Merge KPIs into digest for the UI chips
        result = {**digest, "kpis": kpis}
        
        _CACHE["digest"] = result
        _CACHE["generated_at"] = now
        
        return {**result, "cached": False, "generated_at": now}
        
    except Exception as e:
        print(f"Error generating daily digest: {e}")
        
        # Fallback result with raw KPIs
        fallback = {
            "summary": "Synthèse indisponible (service IA). Voici les indicateurs bruts du réseau.",
            "analysis": "Les indicateurs de performance du réseau sont disponibles ci-dessous.",
            "recommendations": ["Veuillez vérifier manuellement les alertes critiques.", "Consultez la liste des lampadaires hors ligne."],
            "priority": "medium",
            "confidence": 0.0,
            "kpis": kpis,
            "error": str(e)
        }
        
        # If it's a 429, don't retry too often
        if "429" in str(e):
            _CACHE["digest"] = fallback
            _CACHE["generated_at"] = now - (_CACHE_TTL - _CACHE_TTL_429)
            
        return {**fallback, "cached": False, "generated_at": now}
