"""Zone-level rules — operate on a single ai_zone_health row."""
from __future__ import annotations

from typing import Any

from .schemas import Recommendation, make_recommendation
from .utils import num


def evaluate_row(row: dict[str, Any]) -> list[Recommendation]:
    zone = row.get("zone") or "Inconnue"
    total = num(row.get("total_lampadaires"))
    offline = num(row.get("offline_count"))
    if total <= 0 or offline <= 0:
        return []

    ratio = offline / total
    if ratio >= 0.8:
        priority = "critical"
    elif ratio >= 0.4:
        priority = "high"
    else:
        priority = "medium"

    return [make_recommendation(
        rule_id="zone_grouped_outage",
        title=f"Panne groupée dans la zone {zone}",
        reason=(f"{offline:.0f}/{total:.0f} lampadaires hors ligne ({ratio*100:.0f} %). "
                "Une panne groupée indique souvent un problème LCU, réseau ou alimentation, pas des pannes individuelles."),
        action="Contrôler les LCUs de la zone, gateway, alimentation et communication AVANT d'envoyer plusieurs techniciens.",
        priority=priority, category="communication",
        entity_type="zone", entity_reference=zone,
        evidence={
            "offline_count": offline, "total_lampadaires": total,
            "offline_ratio": round(ratio, 2),
            "critical_alerts_count": num(row.get("critical_alerts_count")),
        },
    )]


def evaluate(rows: list[dict[str, Any]] | None) -> list[Recommendation]:
    recs: list[Recommendation] = []
    for row in rows or []:
        recs.extend(evaluate_row(row))
    return recs
