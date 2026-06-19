"""Work-order ageing / SLA rules for an entity's open work orders."""
from __future__ import annotations

from typing import Any

from .schemas import Recommendation, make_recommendation
from .utils import WO_CRITICAL_HOURS, WO_OLD_HOURS, hours_since, num


def evaluate_wo_rows(rows: list[dict] | None) -> list[Recommendation]:
    """Page-level: evaluate ai_workorder_age rows (age_hours precomputed)."""
    recs: list[Recommendation] = []
    for wo in rows or []:
        if (wo or {}).get("status") in ("resolved", "closed", "cancelled"):
            continue
        age = num(wo.get("age_hours"), default=-1)
        if age < 0:
            continue
        is_critical = (wo.get("priority") == "critical")
        if is_critical and age > WO_CRITICAL_HOURS:
            recs.append(make_recommendation(
                rule_id="wo_critical_overdue",
                title="Bon de travail critique en retard",
                reason=f"« {wo.get('title')} » critique, ouvert depuis {age:.0f} h (> {WO_CRITICAL_HOURS:.0f} h).",
                action="Escalader immédiatement : relancer ou réassigner l'intervention.",
                priority="critical", category="maintenance",
                entity_type="workorder", entity_id=wo.get("id"),
                entity_reference=wo.get("lampadaire_reference") or wo.get("title"),
                evidence={"title": wo.get("title"), "age_hours": round(age, 1), "priority": "critical"},
            ))
        elif age > WO_OLD_HOURS:
            recs.append(make_recommendation(
                rule_id="wo_overdue",
                title="Bon de travail ancien non résolu",
                reason=f"« {wo.get('title')} » ouvert depuis {age:.0f} h (> {WO_OLD_HOURS:.0f} h).",
                action="Replanifier ou relancer le technicien pour respecter le délai d'intervention.",
                priority="high", category="maintenance",
                entity_type="workorder", entity_id=wo.get("id"),
                entity_reference=wo.get("lampadaire_reference") or wo.get("title"),
                evidence={"title": wo.get("title"), "age_hours": round(age, 1)},
            ))
    return recs


def evaluate(data: dict[str, Any]) -> list[Recommendation]:
    details = data.get("details") or {}
    ref = details.get("reference")
    entity_id = details.get("id")
    entity_type = "lampadaire" if "etat" in details else "lcu"

    recs: list[Recommendation] = []
    for wo in data.get("workorders") or []:
        status = (wo or {}).get("status")
        if status in ("resolved", "closed", "cancelled"):
            continue
        age = hours_since(wo.get("created_at"))
        if age is None:
            continue
        is_critical_wo = (wo.get("priority") == "critical")

        if is_critical_wo and age > WO_CRITICAL_HOURS:
            recs.append(make_recommendation(
                rule_id="wo_critical_overdue",
                title="Bon de travail critique en retard",
                reason=f"Le bon « {wo.get('title')} » est critique et ouvert depuis {age:.0f} h (> {WO_CRITICAL_HOURS:.0f} h).",
                action="Escalader immédiatement : relancer le technicien ou réassigner l'intervention.",
                priority="critical", category="maintenance",
                entity_type=entity_type, entity_id=entity_id, entity_reference=ref,
                evidence={"title": wo.get("title"), "age_hours": round(age, 1), "priority": wo.get("priority")},
            ))
        elif age > WO_OLD_HOURS:
            recs.append(make_recommendation(
                rule_id="wo_overdue",
                title="Bon de travail ancien non résolu",
                reason=f"Le bon « {wo.get('title')} » est ouvert depuis {age:.0f} h (> {WO_OLD_HOURS:.0f} h).",
                action="Replanifier ou relancer le technicien pour éviter un dépassement de délai d'intervention.",
                priority="high", category="maintenance",
                entity_type=entity_type, entity_id=entity_id, entity_reference=ref,
                evidence={"title": wo.get("title"), "age_hours": round(age, 1)},
            ))
    return recs
