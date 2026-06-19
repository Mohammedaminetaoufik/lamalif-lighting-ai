"""Mobile AI endpoints — field diagnostic for the technician app.

Rule-based only (0 token). Returns structured diagnosis with checklist, tools
and expected result so the technician has clear field guidance.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.db import execute_select_params
from app.recommendations import evaluate_daily, evaluate_lampadaire, evaluate_lcu, serialize
from app.routes.entity_insights import get_lampadaire_insight_data, get_lcu_insight_data
from app.routes.daily_digest import _collect_kpis, _collect_views

router = APIRouter(prefix="/ai/mobile", tags=["AI Mobile"])

# ── Checklists & tools by category ───────────────────────────────────────────

_CHECKLISTS: dict[str, list[str]] = {
    "communication": [
        "Vérifier l'alimentation du coffret LCU",
        "Vérifier l'état physique du LCU (diodes, display)",
        "Tester la connectivité réseau du LCU (ping IP)",
        "Vérifier l'antenne / signal gateway",
        "Contrôler le câble backhaul (fibre ou 4G)",
        "Tester la communication avec les lampadaires",
        "Prendre photo du coffret",
        "Ajouter note terrain",
    ],
    "availability": [
        "Vérifier l'alimentation du coffret",
        "Tester la connexion LCU associée",
        "Contrôler l'état physique du lampadaire",
        "Mesurer la tension d'alimentation",
        "Vérifier le câblage depuis le coffret",
        "Prendre photo du lampadaire",
        "Ajouter note terrain",
    ],
    "driver": [
        "Mesurer la température du driver (thermomètre IR)",
        "Vérifier la ventilation du luminaire",
        "Contrôler la tension d'alimentation du driver",
        "Vérifier les connexions électriques du driver",
        "Inspecter visuellement le module LED",
        "Prendre photo du luminaire et du driver",
        "Ajouter note terrain",
    ],
    "maintenance": [
        "Vérifier l'état général du luminaire",
        "Contrôler les fixations mécaniques",
        "Inspecter le câblage et les protections",
        "Nettoyer le luminaire si nécessaire",
        "Vérifier la connexion avec la LCU",
        "Prendre photo de l'état actuel",
        "Ajouter note terrain",
    ],
    "energy": [
        "Mesurer la consommation réelle (pince ampèremétrique)",
        "Comparer avec la consommation nominale",
        "Vérifier le profil d'éclairage appliqué",
        "Contrôler le dimming actif",
        "Vérifier les réglages du driver",
        "Prendre photo du tableau de bord",
        "Ajouter note terrain",
    ],
    "commissioning": [
        "Vérifier les paramètres de commissioning",
        "Tester la communication (test comm)",
        "Tester le dimming (test dimming)",
        "Vérifier la position GPS",
        "Vérifier l'association avec la LCU",
        "Valider les tests dans l'application",
        "Prendre photo de l'installation",
        "Ajouter note terrain",
    ],
    "default": [
        "Vérifier l'état général de l'équipement",
        "Contrôler la connectivité",
        "Vérifier les alertes actives",
        "Prendre photo de l'état",
        "Ajouter note terrain",
    ],
}

_TOOLS: dict[str, list[str]] = {
    "communication": ["Multimètre", "Testeur réseau/LAN", "Smartphone GPS", "EPI complet"],
    "availability":  ["Multimètre", "Testeur réseau/LAN", "Smartphone GPS", "EPI complet"],
    "driver":        ["Multimètre", "Thermomètre infrarouge", "Tournevis isolé", "EPI électrique"],
    "maintenance":   ["Multimètre", "Clé à molette", "Smartphone GPS", "EPI complet"],
    "energy":        ["Multimètre", "Pince ampèremétrique", "Analyseur de réseau", "EPI électrique"],
    "commissioning": ["Ordinateur portable", "Câble réseau", "Smartphone GPS", "EPI complet"],
    "default":       ["Multimètre", "Smartphone GPS", "EPI complet"],
}


def _checklist_for(recs: list[dict]) -> list[str]:
    cat = recs[0].get("category", "default") if recs else "default"
    return _CHECKLISTS.get(cat, _CHECKLISTS["default"])


def _tools_for(recs: list[dict]) -> list[str]:
    cat = recs[0].get("category", "default") if recs else "default"
    return _TOOLS.get(cat, _TOOLS["default"])


def _expected_result(recs: list[dict], entity_type: str) -> str:
    if not recs:
        return f"{entity_type.capitalize()} opérationnel(le) après vérification."
    action = recs[0].get("action", "")
    return action if action else f"Anomalie résolue sur {entity_type}."


# ── Engine runner (local, avoids importing private _run_engine) ───────────────

def _run(entity_type: str, data: dict) -> dict:
    if entity_type == "lampadaire":
        result = evaluate_lampadaire(data)
    else:
        result = evaluate_lcu(data)
    scores = result["scores"]
    return {
        "risk_score":   scores.get("risk_score"),
        "recommendations": serialize(result["recommendations"]),
        "priority":     result["priority"],
    }


def _mobile_response(entity_type: str, engine: dict, data: dict, extra: dict | None = None) -> dict:
    recs     = engine.get("recommendations", [])
    priority = engine.get("priority", "low")

    if entity_type == "lampadaire":
        det = data.get("details", {})
        als = data.get("alerts", [])
        impact = {
            "etat":        det.get("etat", "inconnu"),
            "alerts_open": len(als),
            "zone":        det.get("zone"),
        }
        probable_cause = recs[0].get("reason", "Anomalie détectée") if recs else "Aucune anomalie détectée"
    else:
        det   = data.get("details", {})
        lamps = data.get("lamps", [])
        als   = data.get("alerts", [])
        impact = {
            "lampadaires_offline": sum(1 for l in lamps if l.get("etat") == "offline"),
            "alerts_open":         len(als),
            "zone":                det.get("zone"),
            "lcu_status":          det.get("status", "inconnu"),
        }
        probable_cause = recs[0].get("reason", "Anomalie LCU détectée") if recs else "LCU opérationnel"

    confidence = float(recs[0].get("confidence", 0.85)) if recs else 0.85

    result = {
        "priority":        priority,
        "probable_cause":  probable_cause,
        "confidence":      confidence,
        "impact":          impact,
        "checklist":       _checklist_for(recs),
        "tools_required":  _tools_for(recs),
        "expected_result": _expected_result(recs, entity_type),
        "recommendations": recs,
        "risk_score":      engine.get("risk_score"),
        "generated_at":    datetime.now(tz=timezone.utc).isoformat(),
    }
    if extra:
        result.update(extra)
    return result


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/lampadaires/{lamp_id}/diagnostic")
def get_lampadaire_diagnostic(lamp_id: int):
    data = get_lampadaire_insight_data(lamp_id)
    if not data.get("details"):
        raise HTTPException(status_code=404, detail=f"Lampadaire {lamp_id} introuvable")
    engine = _run("lampadaire", data)
    return _mobile_response("lampadaire", engine, data)


@router.get("/lcus/{lcu_id}/diagnostic")
def get_lcu_diagnostic(lcu_id: int):
    data = get_lcu_insight_data(lcu_id)
    if not data.get("details"):
        raise HTTPException(status_code=404, detail=f"LCU {lcu_id} introuvable")
    engine = _run("lcu", data)
    return _mobile_response("lcu", engine, data)


@router.get("/workorders/{wo_id}/diagnostic")
def get_workorder_diagnostic(wo_id: int):
    try:
        rows = execute_select_params(
            """
            SELECT id, title, status, priority, description, lampadaire_id
            FROM work_orders
            WHERE id = :id
            LIMIT 1
            """,
            {"id": wo_id},
        )["rows"]
    except Exception:
        rows = []

    if not rows:
        raise HTTPException(status_code=404, detail=f"WorkOrder {wo_id} introuvable")

    wo       = rows[0]
    lamp_id  = wo.get("lampadaire_id")
    wo_meta  = {
        "workorder": {
            "id":       wo.get("id"),
            "title":    wo.get("title"),
            "status":   wo.get("status"),
            "priority": wo.get("priority"),
        }
    }

    if lamp_id:
        data = get_lampadaire_insight_data(int(lamp_id))
        if data.get("details"):
            engine = _run("lampadaire", data)
            return _mobile_response("lampadaire", engine, data, extra=wo_meta)

    # Fallback — no associated lampadaire with known data
    wo_priority = wo.get("priority", "medium")
    return {
        "priority":        wo_priority,
        "probable_cause":  "Inspection manuelle requise.",
        "confidence":      0.50,
        "impact":          {"workorder_status": wo.get("status", "open")},
        "checklist":       _CHECKLISTS["default"],
        "tools_required":  _TOOLS["default"],
        "expected_result": "Bon de travail résolu après inspection terrain.",
        "recommendations": [],
        "risk_score":      None,
        "generated_at":    datetime.now(tz=timezone.utc).isoformat(),
        **wo_meta,
    }


@router.get("/missions")
def get_missions():
    """Top AI missions — global priority queue for the technician dashboard."""
    kpis  = _collect_kpis()
    views = _collect_views()
    recs  = serialize(evaluate_daily(kpis, views))

    missions = [
        {
            "id":               rec.get("id", f"mission-{i}"),
            "title":            rec.get("title", "Mission IA"),
            "priority":         rec.get("priority", "medium"),
            "category":         rec.get("category", "maintenance"),
            "reason":           rec.get("reason", ""),
            "action":           rec.get("action", ""),
            "entity_type":      rec.get("entity_type", "global"),
            "entity_id":        rec.get("entity_id"),
            "entity_reference": rec.get("entity_reference"),
            "confidence":       rec.get("confidence", 0.80),
        }
        for i, rec in enumerate(recs[:10])
    ]

    return {
        "missions":     missions,
        "total":        len(missions),
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
