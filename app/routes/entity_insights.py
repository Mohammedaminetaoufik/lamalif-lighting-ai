import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db import execute_select_params
from app.llm_client import generate_entity_insight
from app.rag import build_rag_context

router = APIRouter(prefix="/ai", tags=["Entity Insights"])

_CACHE: dict[str, dict] = {}
_CACHE_TTL = 300  # 5 minutes

SUPPORTED_TYPES = ("lampadaire", "lcu")


class EntityInsightResponse(BaseModel):
    entity_type: str
    entity_id: int
    technical_details: dict[str, Any]
    related_data: dict[str, Any]
    summary: str
    analysis: str
    recommendation: str
    priority: str
    suggested_actions: list[str]
    confidence: float
    generated_at: str
    cached: bool


# ── Data collection ──────────────────────────────────────────────────────────

def _safe_first(rows: list) -> dict:
    return rows[0] if rows else {}


def _safe_query(sql: str, params: dict) -> list[dict]:
    try:
        return execute_select_params(sql, params)["rows"]
    except Exception:
        return []


def get_lampadaire_insight_data(lamp_id: int) -> dict:
    p = {"id": lamp_id}
    details     = _safe_first(_safe_query("SELECT * FROM ai_lampadaire_status WHERE id = :id LIMIT 1", p))
    diagnostics = _safe_first(_safe_query("SELECT * FROM ai_lampadaire_diagnostics WHERE lampadaire_id = :id LIMIT 1", p))
    telemetry   = _safe_first(_safe_query("SELECT * FROM ai_telemetry_latest WHERE lampadaire_id = :id LIMIT 1", p))
    alerts      = _safe_query(
        "SELECT severity, status, message, created_at FROM ai_open_alerts WHERE lampadaire_id = :id ORDER BY created_at DESC LIMIT 10",
        p,
    )
    workorders  = _safe_query(
        "SELECT title, status, priority, created_at FROM ai_workorders WHERE lampadaire_id = :id ORDER BY created_at DESC LIMIT 10",
        p,
    )
    return {
        "details":     details,
        "diagnostics": diagnostics,
        "telemetry":   telemetry,
        "alerts":      alerts,
        "workorders":  workorders,
    }


def get_lcu_insight_data(lcu_id: int) -> dict:
    p = {"id": lcu_id}
    details    = _safe_first(_safe_query("SELECT * FROM ai_lcu_status WHERE id = :id LIMIT 1", p))
    health     = _safe_first(_safe_query("SELECT * FROM ai_lcu_health WHERE lcu_id = :id LIMIT 1", p))
    lamps      = _safe_query(
        "SELECT reference, etat, zone, intensite, has_critical_alert FROM ai_lampadaire_status WHERE lcu_id = :id ORDER BY etat DESC LIMIT 50",
        p,
    )
    # Alerts and workorders keyed by LCU reference
    ref = details.get("reference", "")
    pr = {"ref": ref}
    alerts     = _safe_query(
        "SELECT severity, status, message, created_at FROM ai_open_alerts WHERE lcu_reference = :ref ORDER BY created_at DESC LIMIT 20",
        pr,
    )
    workorders = _safe_query(
        "SELECT title, status, priority, created_at FROM ai_workorders WHERE lcu_reference = :ref ORDER BY created_at DESC LIMIT 20",
        pr,
    )
    return {
        "details":    details,
        "health":     health,
        "lamps":      lamps,
        "alerts":     alerts,
        "workorders": workorders,
    }


# ── Rule-based priority fallback ─────────────────────────────────────────────

def _rule_priority_lampadaire(data: dict) -> str:
    details    = data.get("details") or {}
    diagnostics = data.get("diagnostics") or {}
    alerts     = data.get("alerts") or []
    telemetry  = data.get("telemetry") or {}

    etat = details.get("etat", "")
    critical_alerts = diagnostics.get("critical_alerts_count") or 0
    open_alerts     = diagnostics.get("open_alerts_count") or 0
    driver_temp     = diagnostics.get("driver_temperature")
    has_critical    = any(a.get("severity") == "critical" for a in alerts)

    if etat == "offline" or has_critical or (critical_alerts > 0) or not telemetry:
        return "critical"
    if (open_alerts > 0) or (driver_temp and float(driver_temp) > 70):
        return "high"
    if etat == "maintenance":
        return "medium"
    return "low"


def _rule_priority_lcu(data: dict) -> str:
    details = data.get("details") or {}
    health  = data.get("health") or {}
    lamps   = data.get("lamps") or []
    alerts  = data.get("alerts") or []

    status       = details.get("status", "")
    offline_cnt  = details.get("offline_count") or 0
    health_score = health.get("health_score")
    has_critical = any(a.get("severity") == "critical" for a in alerts)

    if status == "offline" or has_critical or (health_score is not None and float(health_score) < 30):
        return "critical"
    total = len(lamps) or 1
    if offline_cnt > total * 0.3 or (health_score is not None and float(health_score) < 60):
        return "high"
    if offline_cnt > 0 or len(alerts) > 0:
        return "medium"
    return "low"


def _build_technical_details(entity_type: str, data: dict) -> dict:
    if entity_type == "lampadaire":
        d = data.get("details") or {}
        t = data.get("telemetry") or {}
        diag = data.get("diagnostics") or {}
        return {
            "reference":     d.get("reference"),
            "zone":          d.get("zone"),
            "etat":          d.get("etat"),
            "intensite":     d.get("intensite"),
            "puissance":     d.get("puissance"),
            "lcu_reference": d.get("lcu_reference"),
            "commissioning": d.get("commissioning_status"),
            "latitude":      d.get("latitude"),
            "longitude":     d.get("longitude"),
            "last_seen_at":  d.get("last_seen_at"),
            "temperature":   t.get("temperature"),
            "measured_power":t.get("puissance"),
            "courant":       t.get("courant"),
            "tension":       t.get("tension"),
            "luminosite":    t.get("luminosite"),
            "driver_brand":  diag.get("driver_brand"),
            "driver_model":  diag.get("driver_model"),
            "fault_status":  diag.get("fault_status"),
        }
    # lcu
    d = data.get("details") or {}
    h = data.get("health") or {}
    return {
        "reference":       d.get("reference"),
        "name":            d.get("name"),
        "ip_address":      d.get("ip_address"),
        "port":            d.get("port"),
        "protocol":        d.get("protocol"),
        "zone":            d.get("zone"),
        "status":          d.get("status"),
        "last_seen_at":    d.get("last_seen_at"),
        "last_sync_at":    d.get("last_sync_at"),
        "lampadaires_count": d.get("lampadaires_count"),
        "online_count":    d.get("online_count"),
        "offline_count":   d.get("offline_count"),
        "maintenance_count": d.get("maintenance_count"),
        "health_score":    h.get("health_score"),
    }


def _build_related_data(entity_type: str, data: dict) -> dict:
    alerts    = data.get("alerts") or []
    workorders = data.get("workorders") or []
    if entity_type == "lampadaire":
        return {
            "alerts_count":    len(alerts),
            "workorders_count": len(workorders),
            "critical_alerts": sum(1 for a in alerts if a.get("severity") == "critical"),
        }
    lamps = data.get("lamps") or []
    return {
        "lampadaires_count": len(lamps),
        "offline_lamps":     sum(1 for l in lamps if l.get("etat") == "offline"),
        "alerts_count":      len(alerts),
        "workorders_count":  len(workorders),
        "critical_alerts":   sum(1 for a in alerts if a.get("severity") == "critical"),
    }


def _fallback_insight(entity_type: str, data: dict, priority: str) -> dict:
    details = (data.get("details") or {})
    ref = details.get("reference", f"{entity_type.upper()}-?")

    if entity_type == "lampadaire":
        etat = details.get("etat", "inconnu")
        return {
            "summary": f"Lampadaire {ref} — état : {etat}.",
            "analysis": "Analyse IA indisponible. Vérifiez les données de télémétrie et les alertes ouvertes.",
            "recommendation": "Consultez les alertes associées et l'historique des interventions.",
            "priority": priority,
            "suggested_actions": [
                "Vérifier la connectivité de la LCU associée.",
                "Contrôler la dernière télémétrie disponible.",
                "Créer un bon de travail si l'anomalie persiste.",
            ],
            "confidence": 0.0,
        }
    # lcu
    offline = details.get("offline_count", 0)
    return {
        "summary": f"LCU {ref} — {offline} lampadaire(s) hors ligne.",
        "analysis": "Analyse IA indisponible. Vérifiez l'état réseau de la LCU.",
        "recommendation": "Testez la connectivité IP de la LCU et synchronisez les lampadaires associés.",
        "priority": priority,
        "suggested_actions": [
            "Lancer un test de connectivité depuis la page LCUs.",
            "Synchroniser la LCU pour rafraîchir les données.",
            "Vérifier les alertes ouvertes liées à cette passerelle.",
        ],
        "confidence": 0.0,
    }


# ── Cache helpers ────────────────────────────────────────────────────────────

def _cache_key(entity_type: str, entity_id: int) -> str:
    return f"{entity_type}:{entity_id}"


def _cache_valid(key: str) -> bool:
    entry = _CACHE.get(key)
    return bool(entry and (time.monotonic() - entry["_ts"]) < _CACHE_TTL)


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.get("/entity-insights/{entity_type}/{entity_id}", response_model=EntityInsightResponse)
def get_entity_insights(
    entity_type: str,
    entity_id: int,
    refresh: bool = Query(default=False),
):
    # TODO: add JWT / internal-token auth before exposing to production
    entity_type = entity_type.lower().strip()

    if entity_type not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=404,
            detail=f"Type '{entity_type}' non supporté. Types disponibles : {', '.join(SUPPORTED_TYPES)}",
        )

    key = _cache_key(entity_type, entity_id)
    if not refresh and _cache_valid(key):
        return EntityInsightResponse(**_CACHE[key]["payload"], cached=True)

    # Collect data from PostgreSQL (predefined parameterized queries)
    if entity_type == "lampadaire":
        data = get_lampadaire_insight_data(entity_id)
    else:
        data = get_lcu_insight_data(entity_id)

    # Check entity exists
    if not data.get("details"):
        raise HTTPException(status_code=404, detail=f"{entity_type} with id={entity_id} not found")

    priority = (_rule_priority_lampadaire(data) if entity_type == "lampadaire" else _rule_priority_lcu(data))
    tech     = _build_technical_details(entity_type, data)
    related  = _build_related_data(entity_type, data)

    # Build RAG context (non-blocking, never raises)
    rag_query = f"diagnostic {entity_type} éclairage public recommandations"
    rag = build_rag_context(rag_query, extra_context=entity_type)

    # Generate AI text
    try:
        insight = generate_entity_insight(entity_type, entity_id, data, rag=rag)
    except Exception as exc:
        err = str(exc)
        if "429" in err or "rate_limit" in err.lower():
            raise HTTPException(status_code=429, detail="Limite de tokens IA atteinte. Réessayez dans quelques minutes.")
        insight = _fallback_insight(entity_type, data, priority)

    generated_at = datetime.now(tz=timezone.utc).isoformat()

    payload: dict[str, Any] = {
        "entity_type":      entity_type,
        "entity_id":        entity_id,
        "technical_details": tech,
        "related_data":     related,
        "summary":          insight.get("summary", ""),
        "analysis":         insight.get("analysis", ""),
        "recommendation":   insight.get("recommendation", ""),
        "priority":         insight.get("priority", priority),
        "suggested_actions": insight.get("suggested_actions", []),
        "confidence":       float(insight.get("confidence", 0.7)),
        "generated_at":     generated_at,
    }

    _CACHE[key] = {"payload": payload, "_ts": time.monotonic()}
    return EntityInsightResponse(**payload, cached=False)
