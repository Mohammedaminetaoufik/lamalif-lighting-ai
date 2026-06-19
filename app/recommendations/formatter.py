"""Sorting, dedup, global priority and serialization of recommendations."""
from __future__ import annotations

from typing import Any

from .schemas import PRIORITY_RANK, Recommendation


def sort_recommendations(recs: list[Recommendation]) -> list[Recommendation]:
    return sorted(
        recs,
        key=lambda r: (PRIORITY_RANK.get(r.priority, 0), r.confidence),
        reverse=True,
    )


def dedupe(recs: list[Recommendation]) -> list[Recommendation]:
    seen: set[str] = set()
    out: list[Recommendation] = []
    for r in recs:
        if r.id in seen:
            continue
        seen.add(r.id)
        out.append(r)
    return out


def global_priority(recs: list[Recommendation]) -> str:
    if not recs:
        return "low"
    return max(recs, key=lambda r: PRIORITY_RANK.get(r.priority, 0)).priority


def finalize(recs: list[Recommendation], limit: int | None = None) -> list[Recommendation]:
    out = sort_recommendations(dedupe(recs))
    return out[:limit] if limit else out


def serialize(recs: list[Recommendation]) -> list[dict[str, Any]]:
    return [r.model_dump() for r in recs]


def priority_from_score(score: int) -> str:
    """Map a 0–100 risk-style score to a priority bucket."""
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"
