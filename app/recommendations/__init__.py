"""Lamalif decision engine — rule-based recommendations & industrial scores.

Source of truth: PostgreSQL ai_* views. The engine computes priorities, scores
and recommendations in code (deterministic, explainable). The LLM may rephrase
the output but never decides.
"""
from .rule_engine import (
    evaluate_daily, evaluate_lampadaire, evaluate_lcu, evaluate_page,
    global_priority, serialize,
)
from .schemas import PRIORITY_RANK, Recommendation

__all__ = [
    "evaluate_lampadaire", "evaluate_lcu", "evaluate_page", "evaluate_daily",
    "serialize", "global_priority", "Recommendation", "PRIORITY_RANK",
]
