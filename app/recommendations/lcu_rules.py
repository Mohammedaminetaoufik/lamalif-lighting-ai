"""Rules for a single LCU (gateway)."""
from __future__ import annotations

from typing import Any

from .schemas import Recommendation, make_recommendation
from .utils import num


def evaluate_row(row: dict[str, Any]) -> list[Recommendation]:
    """Page-level: evaluate a single ai_lcu_health row (reference, zone, health_score, offline_count...)."""
    ref = row.get("reference")
    lcu_id = row.get("lcu_id") or row.get("id")
    recs: list[Recommendation] = []
    action = ("Vérifier alimentation, gateway/backhaul, antenne et dernière communication "
              "avant d'intervenir sur les lampadaires associés.")

    if row.get("status") == "offline":
        recs.append(make_recommendation(
            rule_id="lcu_offline",
            title=f"LCU {ref} hors ligne",
            reason="Une LCU hors ligne coupe la supervision de tous ses lampadaires — panne groupée probable.",
            action=action, priority="critical", category="communication",
            entity_type="lcu", entity_id=lcu_id, entity_reference=ref,
            evidence={"status": "offline", "offline_count": num(row.get("offline_count"))},
        ))
        return recs

    hs = row.get("health_score")
    if hs is not None:
        h = num(hs)
        if h < 30:
            recs.append(make_recommendation(
                rule_id="lcu_health_critical",
                title=f"Score de santé LCU critique — {ref} ({h:.0f}/100)",
                reason=f"Le score de santé {h:.0f} indique une dégradation sévère de la passerelle.",
                action=action, priority="critical", category="communication",
                entity_type="lcu", entity_id=lcu_id, entity_reference=ref,
                evidence={"health_score": h, "offline_count": num(row.get("offline_count"))},
            ))
        elif h < 60:
            recs.append(make_recommendation(
                rule_id="lcu_health_low",
                title=f"Score de santé LCU faible — {ref} ({h:.0f}/100)",
                reason=f"Le score de santé {h:.0f} signale une fiabilité réduite de la passerelle.",
                action=action, priority="high", category="communication",
                entity_type="lcu", entity_id=lcu_id, entity_reference=ref,
                evidence={"health_score": h},
            ))
    return recs


def evaluate(data: dict[str, Any]) -> list[Recommendation]:
    details = data.get("details") or {}
    health = data.get("health") or {}
    lamps = data.get("lamps") or []
    ref = details.get("reference")
    lcu_id = details.get("id") or health.get("lcu_id")
    recs: list[Recommendation] = []

    action = ("Vérifier alimentation, gateway/backhaul, antenne, dernière communication "
              "et le contrôleur avant d'intervenir sur les lampadaires associés.")

    if details.get("status") == "offline":
        recs.append(make_recommendation(
            rule_id="lcu_offline",
            title="LCU hors ligne",
            reason="Une LCU hors ligne coupe la supervision de tous ses lampadaires — panne groupée probable.",
            action=action,
            priority="critical", category="communication",
            entity_type="lcu", entity_id=lcu_id, entity_reference=ref,
            evidence={"status": details.get("status"), "lampadaires_count": details.get("lampadaires_count")},
        ))

    hs = health.get("health_score")
    if hs is not None:
        h = num(hs)
        if h < 30:
            recs.append(make_recommendation(
                rule_id="lcu_health_critical",
                title=f"Score de santé LCU critique ({h:.0f}/100)",
                reason=f"Le score de santé {h:.0f} indique une dégradation sévère (offline, alertes critiques).",
                action=action,
                priority="critical", category="communication",
                entity_type="lcu", entity_id=lcu_id, entity_reference=ref,
                evidence={"health_score": h},
            ))
        elif h < 60:
            recs.append(make_recommendation(
                rule_id="lcu_health_low",
                title=f"Score de santé LCU faible ({h:.0f}/100)",
                reason=f"Le score de santé {h:.0f} signale une fiabilité réduite de la passerelle.",
                action=action,
                priority="high", category="communication",
                entity_type="lcu", entity_id=lcu_id, entity_reference=ref,
                evidence={"health_score": h},
            ))

    total = len(lamps) or num(details.get("lampadaires_count"))
    offline = num(details.get("offline_count"))
    if total and offline / total > 0.3 and details.get("status") != "offline":
        recs.append(make_recommendation(
            rule_id="lcu_many_offline",
            title="Forte proportion de lampadaires hors ligne sous cette LCU",
            reason=f"{offline:.0f}/{total:.0f} lampadaires hors ligne ({offline/total*100:.0f} %) — défaut probable côté LCU/réseau.",
            action=action,
            priority="high", category="communication",
            entity_type="lcu", entity_id=lcu_id, entity_reference=ref,
            evidence={"offline_count": offline, "total": total, "offline_ratio": round(offline/total, 2)},
        ))
    return recs
