"""Availability rules for a single lampadaire."""
from __future__ import annotations

from typing import Any

from .schemas import Recommendation, make_recommendation
from .utils import has_critical_alert, num


def evaluate(data: dict[str, Any]) -> list[Recommendation]:
    details = data.get("details") or {}
    diag = data.get("diagnostics") or {}
    alerts = data.get("alerts") or []
    lcu_status = (data.get("lcu_status") or {}).get("status")

    ref = details.get("reference")
    lamp_id = details.get("id") or diag.get("lampadaire_id")
    etat = details.get("etat")
    critical = has_critical_alert(alerts) or num(diag.get("critical_alerts_count")) > 0

    recs: list[Recommendation] = []
    if etat != "offline":
        return recs

    if lcu_status == "offline":
        recs.append(make_recommendation(
            rule_id="lamp_offline_lcu_offline",
            title="Lampadaire hors ligne — LCU associée hors ligne",
            reason="Le lampadaire et sa LCU sont tous deux hors ligne : la panne vient probablement de la LCU, du réseau ou de l'alimentation, pas du lampadaire seul.",
            action="Contrôler en priorité la LCU (alimentation, gateway/backhaul, antenne) avant toute intervention sur le lampadaire.",
            priority="critical", category="communication",
            entity_type="lampadaire", entity_id=lamp_id, entity_reference=ref,
            evidence={"etat": etat, "lcu_status": lcu_status},
        ))
    elif critical:
        recs.append(make_recommendation(
            rule_id="lamp_offline_critical_alert",
            title="Lampadaire hors ligne avec alerte critique",
            reason="Un lampadaire hors ligne cumulant une alerte critique présente un risque opérationnel élevé.",
            action="Vérifier alimentation locale, driver et connectivité ; créer/escalader un bon de travail.",
            priority="critical", category="availability",
            entity_type="lampadaire", entity_id=lamp_id, entity_reference=ref,
            evidence={"etat": etat, "critical_alerts_count": num(diag.get("critical_alerts_count"))},
        ))
    else:
        recs.append(make_recommendation(
            rule_id="lamp_offline",
            title="Lampadaire hors ligne",
            reason="Le lampadaire ne communique plus ; cause possible : alimentation, driver, LCU ou connectivité.",
            action="Vérifier alimentation locale, driver, LCU associée et dernière télémétrie.",
            priority="high", category="availability",
            entity_type="lampadaire", entity_id=lamp_id, entity_reference=ref,
            evidence={"etat": etat},
        ))
    return recs
