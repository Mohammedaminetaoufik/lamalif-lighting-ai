"""Orchestrator — turns ai_* data into structured recommendations + scores.

Pure Python over dicts: no DB access, no LLM. Testable in isolation.
"""
from __future__ import annotations

from typing import Any

from . import (
    commissioning_rules, data_quality_rules, driver_rules, energy_rules,
    lampadaire_rules, lcu_rules, maintenance_rules, zone_rules,
)
from .formatter import finalize, global_priority, priority_from_score, serialize
from .schemas import PRIORITY_RANK, Recommendation
from .scoring import (
    compute_communication_health_score, compute_lampadaire_maintainability_score,
    compute_lampadaire_risk_score, compute_lcu_risk_score,
)


def _max_priority(*priorities: str) -> str:
    valid = [p for p in priorities if p]
    if not valid:
        return "low"
    return max(valid, key=lambda p: PRIORITY_RANK.get(p, 0))


def evaluate_lampadaire(data: dict[str, Any]) -> dict[str, Any]:
    recs: list[Recommendation] = []
    recs += lampadaire_rules.evaluate(data)
    recs += driver_rules.evaluate(data)
    recs += maintenance_rules.evaluate(data)
    recs += commissioning_rules.evaluate(data)
    recs += data_quality_rules.evaluate(data)
    recs = finalize(recs)

    scores = {
        "risk_score": compute_lampadaire_risk_score(data),
        "maintainability_score": compute_lampadaire_maintainability_score(data),
        "communication_health_score": compute_communication_health_score(data),
    }
    priority = _max_priority(global_priority(recs), priority_from_score(scores["risk_score"]))
    return {"recommendations": recs, "scores": scores, "priority": priority}


def evaluate_lcu(data: dict[str, Any]) -> dict[str, Any]:
    recs = finalize(lcu_rules.evaluate(data))
    scores = {
        "risk_score": compute_lcu_risk_score(data),
        "communication_health_score": compute_communication_health_score(data),
    }
    priority = _max_priority(global_priority(recs), priority_from_score(scores["risk_score"]))
    return {"recommendations": recs, "scores": scores, "priority": priority}


# ── Page-level dispatch ───────────────────────────────────────────────────────

def _lamp_rows_recs(rows: list[dict] | None) -> list[Recommendation]:
    """Recommendations from ai_lampadaire_diagnostics-style rows (page-level)."""
    from .schemas import make_recommendation
    from .utils import num
    out: list[Recommendation] = []
    for r in rows or []:
        crit = num(r.get("critical_alerts_count"))
        if r.get("etat") == "offline" and crit > 0:
            out.append(make_recommendation(
                rule_id="lamp_offline_critical_alert",
                title=f"Lampadaire {r.get('reference')} hors ligne + alerte critique",
                reason="Lampadaire hors ligne cumulant une alerte critique — risque élevé.",
                action="Vérifier alimentation, driver, LCU ; escalader un bon de travail.",
                priority="critical", category="availability",
                entity_type="lampadaire", entity_reference=r.get("reference"),
                evidence={"etat": r.get("etat"), "critical_alerts_count": crit},
            ))
    return out


def _map_missing_gps_recs(rows: list[dict] | None) -> list[Recommendation]:
    from .schemas import make_recommendation
    rows = rows or []
    if not rows:
        return []
    from .schemas import Recommendation as _R  # noqa
    refs = [r.get("reference") for r in rows][:10]
    return [make_recommendation(
        rule_id="map_missing_gps",
        title=f"{len(rows)} équipement(s) sans localisation GPS",
        reason="Des équipements sans coordonnées n'apparaissent pas sur la carte et compliquent l'intervention terrain.",
        action="Renseigner la position GPS depuis l'application technicien.",
        priority="medium", category="data_quality",
        entity_type="map", entity_reference="carte",
        evidence={"missing_count": len(rows), "sample": refs},
    )]


def evaluate_page(page: str, page_data: dict[str, Any]) -> list[Recommendation]:
    recs: list[Recommendation] = []
    g = page_data.get

    if page == "dashboard":
        recs += zone_rules.evaluate(g("top_zones"))
        for row in g("critical_lcus") or []:
            recs += lcu_rules.evaluate_row(row)
        recs += maintenance_rules.evaluate_wo_rows(g("oldest_workorders"))
    elif page == "lampadaires":
        recs += _lamp_rows_recs(g("top_diagnostics"))
        recs += zone_rules.evaluate(g("offline_by_zone"))
    elif page == "lcus":
        for row in g("lcu_health") or []:
            recs += lcu_rules.evaluate_row(row)
    elif page == "alerts":
        recs += zone_rules.evaluate(g("alert_summary"))
    elif page == "workorders":
        recs += maintenance_rules.evaluate_wo_rows(g("oldest_open"))
    elif page == "energy":
        recs += energy_rules.evaluate(g("energy_by_zone"))
    elif page == "commissioning":
        from .schemas import make_recommendation
        pending = g("pending_commissioning") or []
        if pending:
            recs.append(make_recommendation(
                rule_id="commissioning_pending_batch",
                title=f"{len(pending)} équipement(s) non finalisés",
                reason="Des équipements ne sont pas commissionnés et ne doivent pas être considérés opérationnels.",
                action="Finaliser tests communication/dimming, localisation GPS et association LCU.",
                priority="medium", category="commissioning",
                entity_type="page", entity_reference="commissioning",
                evidence={"pending_count": len(pending)},
            ))
    elif page == "map":
        recs += _map_missing_gps_recs(g("missing_gps"))

    return finalize(recs, limit=10)


def evaluate_daily(kpis: dict[str, Any], views: dict[str, Any] | None = None) -> list[Recommendation]:
    """Network-wide daily recommendations from KPIs + optional view rows."""
    from .schemas import make_recommendation
    from .utils import num
    views = views or {}
    recs: list[Recommendation] = []

    recs += zone_rules.evaluate(views.get("zone_health"))
    for row in views.get("lcu_health") or []:
        recs += lcu_rules.evaluate_row(row)

    critical = num(kpis.get("critical_alerts"))
    if critical > 0:
        recs.append(make_recommendation(
            rule_id="daily_critical_alerts",
            title=f"{critical:.0f} alerte(s) critique(s) ouverte(s)",
            reason="Des alertes critiques non traitées exposent le réseau à des pannes prolongées.",
            action="Traiter en priorité les alertes critiques et créer les bons de travail correspondants.",
            priority="critical", category="availability",
            entity_type="global", entity_reference="réseau",
            evidence={"critical_alerts": critical},
        ))

    offline = num(kpis.get("offline_lampadaires"))
    total = num(kpis.get("total_lampadaires"))
    if total and offline / total > 0.1:
        recs.append(make_recommendation(
            rule_id="daily_high_offline",
            title=f"{offline:.0f} lampadaires hors ligne sur le réseau",
            reason=f"{offline/total*100:.0f} % du parc est hors ligne — vérifier d'éventuelles pannes groupées (LCU/réseau).",
            action="Identifier les zones et LCUs concentrant les pannes avant interventions individuelles.",
            priority="high", category="availability",
            entity_type="global", entity_reference="réseau",
            evidence={"offline": offline, "total": total, "offline_ratio": round(offline/total, 2)},
        ))
    return finalize(recs, limit=10)


__all__ = [
    "evaluate_lampadaire", "evaluate_lcu", "evaluate_page", "evaluate_daily",
    "serialize", "global_priority",
]
