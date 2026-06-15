import time
from fastapi import APIRouter
from app.db import execute_select

router = APIRouter(prefix="/ai", tags=["AI Suggestions"])

_CACHE = {
    "suggestions": [],
    "generated_at": 0,
}
_CACHE_TTL = 180  # 3 minutes


@router.get("/suggestions")
def get_ai_suggestions():
    now = time.monotonic()
    if _CACHE["suggestions"] and (now - _CACHE["generated_at"]) < _CACHE_TTL:
        return {
            "suggestions": _CACHE["suggestions"],
            "generated_at": _CACHE["generated_at"],
            "cached": True
        }

    suggestions = []

    # 1. Zone la plus critique (plus de lampadaires offline)
    try:
        res = execute_select("SELECT zone, offline_count FROM ai_zone_health ORDER BY offline_count DESC LIMIT 1")
        if res["rows"] and res["rows"][0]["offline_count"] > 0:
            zone = res["rows"][0]["zone"]
            count = res["rows"][0]["offline_count"]
            suggestions.append(f"Pourquoi la zone {zone} contient {count} lampadaires offline ?")
            suggestions.append(f"Quelle zone est la plus critique actuellement ?")
    except Exception:
        pass

    # 2. Alertes critiques récentes
    try:
        res = execute_select("SELECT COUNT(*) as count FROM ai_open_alerts WHERE severity = 'critical'")
        if res["rows"] and res["rows"][0]["count"] > 0:
            count = res["rows"][0]["count"]
            suggestions.append(f"Détaille les {count} alertes critiques en cours.")
    except Exception:
        pass

    # 3. Bons de travail anciens (> 48h)
    try:
        res = execute_select("SELECT COUNT(*) as count FROM ai_workorder_age WHERE age_hours > 48 AND status NOT IN ('resolved', 'closed')")
        if res["rows"] and res["rows"][0]["count"] > 0:
            suggestions.append("Quels bons de travail dépassent 48 heures ?")
    except Exception:
        pass

    # 4. Commissioning restant
    try:
        res = execute_select("SELECT SUM(discovered_count) as total FROM ai_zone_health")
        if res["rows"] and res["rows"][0]["total"] and res["rows"][0]["total"] > 0:
            suggestions.append("Quels équipements restent à commissionner ?")
    except Exception:
        pass

    # 5. Pire LCU (santé la plus faible)
    try:
        res = execute_select("SELECT reference, health_score FROM ai_lcu_health ORDER BY health_score ASC LIMIT 1")
        if res["rows"] and res["rows"][0]["health_score"] < 80:
            ref = res["rows"][0]["reference"]
            suggestions.append(f"Quelle LCU a le score de santé le plus faible ?")
            suggestions.append(f"Pourquoi la LCU {ref} a un score de santé de {res['rows'][0]['health_score']}% ?")
    except Exception:
        pass

    # Fallback / Complétion si peu de suggestions
    defaults = [
        "Donne-moi la situation globale du réseau.",
        "Quelle est la zone qui consomme le plus d'énergie ?",
        "Affiche un résumé de la maintenance en cours."
    ]
    
    for d in defaults:
        if d not in suggestions:
            suggestions.append(d)
        if len(suggestions) >= 6:
            break

    # Unique suggestions
    unique_suggestions = []
    for s in suggestions:
        if s not in unique_suggestions:
            unique_suggestions.append(s)
            
    _CACHE["suggestions"] = unique_suggestions[:6]
    _CACHE["generated_at"] = now

    return {
        "suggestions": _CACHE["suggestions"],
        "generated_at": now,
        "cached": False
    }
