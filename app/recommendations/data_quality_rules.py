"""Data-quality rules for a single lampadaire (impacts supervision & maintenance)."""
from __future__ import annotations

from typing import Any

from .schemas import Recommendation, make_recommendation
from .utils import TELEMETRY_STALE_HOURS, hours_since


def evaluate(data: dict[str, Any]) -> list[Recommendation]:
    details = data.get("details") or {}
    diag = data.get("diagnostics") or {}
    ref = details.get("reference")
    lamp_id = details.get("id") or diag.get("lampadaire_id")
    recs: list[Recommendation] = []

    if details.get("lcu_id") is None and not details.get("lcu_reference"):
        recs.append(make_recommendation(
            rule_id="dq_no_lcu",
            title="Aucune LCU associée",
            reason="Sans LCU associée, le lampadaire ne peut être supervisé ni piloté à distance.",
            action="Associer le lampadaire à sa passerelle LCU.",
            priority="high", category="data_quality",
            entity_type="lampadaire", entity_id=lamp_id, entity_reference=ref,
            evidence={"lcu_id": details.get("lcu_id")},
        ))

    if details.get("latitude") is None or details.get("longitude") is None:
        recs.append(make_recommendation(
            rule_id="dq_no_gps",
            title="Localisation GPS manquante",
            reason="Sans coordonnées GPS, le lampadaire n'apparaît pas sur la carte et complique l'intervention terrain.",
            action="Renseigner la position GPS depuis l'application technicien ou la carte.",
            priority="medium", category="data_quality",
            entity_type="lampadaire", entity_id=lamp_id, entity_reference=ref,
            evidence={"latitude": details.get("latitude"), "longitude": details.get("longitude")},
        ))

    if not details.get("zone"):
        recs.append(make_recommendation(
            rule_id="dq_no_zone",
            title="Zone non renseignée",
            reason="L'absence de zone empêche les agrégations et le pilotage par secteur.",
            action="Affecter le lampadaire à une zone.",
            priority="low", category="data_quality",
            entity_type="lampadaire", entity_id=lamp_id, entity_reference=ref,
            evidence={"zone": details.get("zone")},
        ))

    last_tel = diag.get("last_measure_at") or (data.get("telemetry") or {}).get("measured_at")
    tel_age = hours_since(last_tel)
    if tel_age is None or tel_age > TELEMETRY_STALE_HOURS:
        recs.append(make_recommendation(
            rule_id="dq_no_recent_telemetry",
            title="Pas de télémétrie récente",
            reason="Aucune mesure récente : supervision et maintenance prédictive dégradées.",
            action="Vérifier la communication LCU et l'état des capteurs.",
            priority="medium", category="communication",
            entity_type="lampadaire", entity_id=lamp_id, entity_reference=ref,
            evidence={"last_measure_at": last_tel, "telemetry_age_hours": round(tel_age, 1) if tel_age is not None else None},
        ))
    return recs
