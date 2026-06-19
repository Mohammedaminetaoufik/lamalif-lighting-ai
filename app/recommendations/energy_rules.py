"""Energy rules — operate on ai_energy_summary rows (per zone)."""
from __future__ import annotations

from typing import Any

from .schemas import Recommendation, make_recommendation
from .scoring import compute_energy_efficiency_score
from .utils import num


def evaluate_row(row: dict[str, Any]) -> list[Recommendation]:
    zone = row.get("zone") or "Inconnue"
    avg_intensity = row.get("avg_intensity")
    total_kwh = num(row.get("total_energy_kwh"))
    recs: list[Recommendation] = []

    if avg_intensity is not None and num(avg_intensity) >= 90 and total_kwh > 0:
        recs.append(make_recommendation(
            rule_id="energy_no_dimming",
            title=f"Dimming inactif sur la zone {zone}",
            reason=(f"Intensité moyenne {num(avg_intensity):.0f} % avec {total_kwh:.0f} kWh consommés : "
                    "aucune réduction nocturne effective n'est appliquée."),
            action="Appliquer un profil de dimming nocturne (toute modification de profil doit être validée par un humain).",
            priority="medium", category="energy",
            entity_type="zone", entity_reference=zone,
            evidence={"avg_intensity": num(avg_intensity), "total_energy_kwh": total_kwh,
                      "energy_efficiency_score": compute_energy_efficiency_score(row)},
        ))
    return recs


def evaluate(rows: list[dict[str, Any]] | None) -> list[Recommendation]:
    recs: list[Recommendation] = []
    for row in rows or []:
        recs.extend(evaluate_row(row))
    return recs
