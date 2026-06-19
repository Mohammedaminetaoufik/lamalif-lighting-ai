"""Commissioning completeness rules for a single lampadaire."""
from __future__ import annotations

from typing import Any

from .schemas import Recommendation, make_recommendation


def evaluate(data: dict[str, Any]) -> list[Recommendation]:
    details = data.get("details") or {}
    ref = details.get("reference")
    lamp_id = details.get("id")
    status = details.get("commissioning_status")

    if status in (None, "commissioned"):
        return []

    # Optional finer test status (present when ai_commissioning_status is provided)
    test_comm = details.get("test_comm_status")
    test_dim = details.get("test_dimming_status")
    failed_tests = [name for name, val in
                    (("communication", test_comm), ("dimming", test_dim))
                    if val == "failed"]

    if failed_tests:
        priority = "high" if "communication" in failed_tests else "medium"
        reason = f"Tests de mise en service échoués : {', '.join(failed_tests)}."
    else:
        priority = "medium"
        reason = f"Lampadaire non finalisé (statut : {status}) — il ne doit pas être considéré opérationnel."

    return [make_recommendation(
        rule_id="commissioning_incomplete",
        title="Mise en service incomplète",
        reason=reason,
        action="Finaliser les tests communication/dimming, la localisation GPS et l'association LCU avant mise en production.",
        priority=priority, category="commissioning",
        entity_type="lampadaire", entity_id=lamp_id, entity_reference=ref,
        evidence={"commissioning_status": status, "failed_tests": failed_tests},
    )]
