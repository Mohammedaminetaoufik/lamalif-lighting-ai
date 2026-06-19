"""Driver thermal rules for a single lampadaire."""
from __future__ import annotations

from typing import Any

from .schemas import Recommendation, make_recommendation
from .utils import DRIVER_TEMP_CRITICAL, DRIVER_TEMP_HIGH, num


def evaluate(data: dict[str, Any]) -> list[Recommendation]:
    details = data.get("details") or {}
    diag = data.get("diagnostics") or {}
    ref = details.get("reference")
    lamp_id = details.get("id") or diag.get("lampadaire_id")

    temp = diag.get("driver_temperature")
    if temp is None:
        return []
    t = num(temp)

    if t >= DRIVER_TEMP_CRITICAL:
        priority = "critical"
    elif t >= DRIVER_TEMP_HIGH:
        priority = "high"
    else:
        return []

    return [make_recommendation(
        rule_id="driver_overheat",
        title=f"Driver LED en surchauffe ({t:.0f} °C)",
        reason=f"Une température driver de {t:.0f} °C accélère le vieillissement et risque une défaillance prématurée (seuil {DRIVER_TEMP_HIGH:.0f}/{DRIVER_TEMP_CRITICAL:.0f} °C).",
        action="Vérifier dissipation thermique, MCPCB, ventilation de l'armoire, surcharge, et adapter le profil de dimming.",
        priority=priority, category="driver",
        entity_type="lampadaire", entity_id=lamp_id, entity_reference=ref,
        evidence={"driver_temperature": t, "led_module_temperature": diag.get("led_module_temperature")},
    )]
