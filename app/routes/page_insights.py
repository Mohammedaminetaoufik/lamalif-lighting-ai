import json
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db import execute_select
from app.llm_client import generate_page_insight
from app.rag import build_rag_context

router = APIRouter(prefix="/ai", tags=["Page Insights"])

# ── In-memory cache { page → {payload, _ts} } ───────────────────────────────
_CACHE: dict[str, dict] = {}
_CACHE_TTL = 300       # 5 minutes for successful responses
_CACHE_TTL_429 = 120   # 2 minutes when Groq rate-limited (avoid hammering)


class PageInsightResponse(BaseModel):
    page: str
    summary: str
    analysis: str
    recommendations: list[str]
    priority: str
    kpis: dict[str, Any]
    confidence: float
    generated_at: str
    cached: bool


# ── Predefined read-only queries per page ────────────────────────────────────
# Each entry: (result_key, sql)
_PAGE_QUERIES: dict[str, list[tuple[str, str]]] = {
    "dashboard": [
        (
            "global_kpis",
            "SELECT * FROM ai_global_kpis LIMIT 1",
        ),
        (
            "top_zones",
            "SELECT zone, offline_count, critical_alerts_count, open_workorders_count, total_lampadaires "
            "FROM ai_zone_health ORDER BY offline_count DESC, critical_alerts_count DESC LIMIT 5",
        ),
        (
            "critical_lcus",
            "SELECT reference, zone, health_score, offline_count, critical_alerts_count "
            "FROM ai_lcu_health ORDER BY health_score ASC LIMIT 5",
        ),
        (
            "oldest_workorders",
            "SELECT title, status, priority, zone, ROUND(age_hours::numeric, 1) AS age_hours "
            "FROM ai_workorder_age "
            "WHERE status IN ('created','assigned','accepted','in_progress') "
            "ORDER BY age_hours DESC LIMIT 5",
        ),
    ],
    "lampadaires": [
        (
            "status_distribution",
            "SELECT etat, COUNT(*) AS count FROM ai_lampadaire_status GROUP BY etat ORDER BY count DESC",
        ),
        (
            "offline_by_zone",
            "SELECT zone, COUNT(*) AS offline_count FROM ai_lampadaire_status "
            "WHERE etat = 'offline' GROUP BY zone ORDER BY offline_count DESC LIMIT 10",
        ),
        (
            "top_diagnostics",
            "SELECT reference, zone, etat, fault_status, open_alerts_count, critical_alerts_count "
            "FROM ai_lampadaire_diagnostics "
            "ORDER BY critical_alerts_count DESC, open_alerts_count DESC LIMIT 10",
        ),
    ],
    "lcus": [
        (
            "lcu_health",
            "SELECT reference, name, zone, status, health_score, offline_count, critical_alerts_count "
            "FROM ai_lcu_health ORDER BY health_score ASC LIMIT 10",
        ),
        (
            "lcu_status",
            "SELECT reference, zone, offline_count, maintenance_count, lampadaires_count "
            "FROM ai_lcu_status ORDER BY offline_count DESC LIMIT 10",
        ),
    ],
    "alerts": [
        (
            "alert_summary",
            "SELECT zone, lcu_reference, severity, total_alerts, latest_alert_at "
            "FROM ai_alert_summary ORDER BY total_alerts DESC LIMIT 10",
        ),
        (
            "recent_critical",
            "SELECT severity, status, message, lampadaire_reference, zone, created_at "
            "FROM ai_open_alerts ORDER BY created_at DESC LIMIT 10",
        ),
    ],
    "workorders": [
        (
            "oldest_open",
            "SELECT title, status, priority, zone, ROUND(age_hours::numeric, 1) AS age_hours, assigned_to_name "
            "FROM ai_workorder_age ORDER BY age_hours DESC LIMIT 10",
        ),
        (
            "status_distribution",
            "SELECT status, COUNT(*) AS count FROM ai_workorders GROUP BY status ORDER BY count DESC",
        ),
    ],
    "energy": [
        (
            "energy_by_zone",
            "SELECT zone, lampadaires_count, total_energy_kwh, avg_energy_kwh, total_operating_hours "
            "FROM ai_energy_summary ORDER BY total_energy_kwh DESC LIMIT 10",
        ),
    ],
    "commissioning": [
        (
            "pending_commissioning",
            "SELECT reference, zone, commissioning_status, commissioning_step, "
            "test_comm_status, test_dimming_status, test_metering_status "
            "FROM ai_commissioning_status WHERE commissioning_status <> 'commissioned' LIMIT 20",
        ),
    ],
    "map": [
        (
            "missing_gps",
            "SELECT asset_type, reference, zone, status FROM ai_map_assets WHERE has_location = false LIMIT 20",
        ),
        (
            "assets_by_zone",
            "SELECT zone, COUNT(*) AS count FROM ai_map_assets GROUP BY zone ORDER BY count DESC LIMIT 10",
        ),
    ],
}

SUPPORTED_PAGES = list(_PAGE_QUERIES.keys())


def _collect_page_data(page: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key, sql in _PAGE_QUERIES[page]:
        try:
            result = execute_select(sql)
            data[key] = result["rows"]
        except Exception as exc:
            data[key] = {"error": str(exc)}
    return data


def _cache_valid(page: str) -> bool:
    entry = _CACHE.get(page)
    if not entry:
        return False
    ttl = _CACHE_TTL_429 if entry.get("_rate_limited") else _CACHE_TTL
    return (time.monotonic() - entry["_ts"]) < ttl


@router.get("/page-insights/{page}", response_model=PageInsightResponse)
def get_page_insights(
    page: str,
    refresh: bool = Query(default=False, description="Force regeneration, bypass cache"),
):
    # TODO: add JWT / internal-token auth before exposing to production
    page = page.lower().strip()

    if page not in _PAGE_QUERIES:
        raise HTTPException(
            status_code=404,
            detail=f"Page '{page}' non supportée. Pages disponibles : {', '.join(SUPPORTED_PAGES)}",
        )

    # Serve the last generated result; NEVER call the LLM unless explicitly refreshed.
    # This means a page load/refresh costs zero tokens — only the manual refresh button
    # (refresh=true) regenerates the analysis.
    if not refresh:
        entry = _CACHE.get(page)
        if entry:
            return PageInsightResponse(**entry["payload"], cached=True)
        # Not generated yet — return an empty placeholder, no token usage
        return PageInsightResponse(
            page=page,
            summary="",
            analysis="",
            recommendations=[],
            priority="medium",
            kpis={},
            confidence=0.0,
            generated_at="",
            cached=False,
        )

    # Collect data from PostgreSQL (predefined queries only — no LLM SQL generation)
    data = _collect_page_data(page)

    # Build RAG context for this page (non-blocking)
    rag = build_rag_context(f"analyse page {page} télégestion éclairage public")

    # Generate AI insight via Groq / Llama 3
    rate_limited = False
    try:
        insight = generate_page_insight(page, data, rag=rag)
    except Exception as exc:
        err_str = str(exc)
        if "429" in err_str or "rate_limit" in err_str.lower() or "rate limit" in err_str.lower():
            rate_limited = True
            insight = {
                "summary": "Limite de requêtes IA atteinte. L'analyse sera disponible dans quelques minutes.",
                "analysis": "Le service Groq a atteint sa limite de tokens par minute. Aucune action requise — l'analyse se régénérera automatiquement.",
                "recommendations": [
                    "Patientez 1–2 minutes avant de rafraîchir.",
                    "Utilisez le bouton de rafraîchissement manuel si nécessaire.",
                ],
                "priority": "low",
                "confidence": 0.0,
            }
        else:
            insight = {
                "summary": f"Analyse temporairement indisponible pour la page '{page}'.",
                "analysis": "Le service IA n'a pas pu générer une analyse. Vérifiez la connexion Groq.",
                "recommendations": [
                    "Vérifiez la connectivité au service Groq.",
                    "Réessayez dans quelques instants ou forcez le rechargement.",
                ],
                "priority": "medium",
                "confidence": 0.0,
            }

    generated_at = datetime.now(tz=timezone.utc).isoformat()

    # Extract global KPIs for dashboard page
    kpis: dict[str, Any] = {}
    if page == "dashboard":
        rows = data.get("global_kpis", [])
        if isinstance(rows, list) and rows:
            kpis = rows[0]

    payload: dict[str, Any] = {
        "page": page,
        "summary": insight.get("summary", ""),
        "analysis": insight.get("analysis", ""),
        "recommendations": insight.get("recommendations", []),
        "priority": insight.get("priority", "medium"),
        "kpis": kpis,
        "confidence": float(insight.get("confidence", 0.7)),
        "generated_at": generated_at,
    }

    _CACHE[page] = {"payload": payload, "_ts": time.monotonic(), "_rate_limited": rate_limited}

    return PageInsightResponse(**payload, cached=False)
