"""Structured recommendation schema for the Lamalif decision engine.

Every recommendation is explainable: it carries the reason, a concrete action,
and the evidence (the real numbers used to derive it). The LLM may later rephrase
a recommendation, but the decision itself comes from the rule engine.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

Priority = Literal["critical", "high", "medium", "low"]
Category = Literal[
    "availability", "maintenance", "energy", "communication",
    "commissioning", "driver", "dimming", "network", "data_quality",
]
Source = Literal["rule_based", "rag_guided", "llm_enriched", "fallback"]

PRIORITY_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class Recommendation(BaseModel):
    id: str
    title: str
    summary: str = ""
    reason: str
    action: str
    priority: Priority = "medium"
    category: Category = "maintenance"
    entity_type: str = "global"
    entity_id: int | None = None
    entity_reference: str | None = None
    confidence: float = 0.8
    evidence: dict[str, Any] = Field(default_factory=dict)
    source: Source = "rule_based"
    created_at: str = Field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())


def make_recommendation(
    *,
    rule_id: str,
    title: str,
    reason: str,
    action: str,
    priority: Priority,
    category: Category,
    evidence: dict[str, Any],
    entity_type: str = "global",
    entity_id: int | None = None,
    entity_reference: str | None = None,
    summary: str = "",
    confidence: float = 0.85,
    source: Source = "rule_based",
) -> Recommendation:
    """Factory that guarantees every recommendation carries reason/action/evidence."""
    return Recommendation(
        id=f"{rule_id}:{entity_type}:{entity_id if entity_id is not None else entity_reference or '_'}",
        title=title,
        summary=summary or title,
        reason=reason,
        action=action,
        priority=priority,
        category=category,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_reference=entity_reference,
        confidence=confidence,
        evidence=evidence,
        source=source,
    )
