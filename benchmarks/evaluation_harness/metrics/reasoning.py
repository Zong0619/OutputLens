"""Reasoning quality metrics -- specificity, traceability, non-circularity.

Evaluates the reasoning field on classification annotations (A4, A5, A6).
Per M6-001: Measures explainability, not correctness of the classification.
"""

from __future__ import annotations

from typing import Any


def compute_reasoning_specificity(
    annotations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute reasoning specificity metrics.

    Measures:
    - avg_length: Average character length of reasoning strings.
    - min_length: Shortest reasoning (should be >= 20 per spec).
    - circular_count: Number of reasoning strings that are likely circular
      (restate the classification without explaining why).
    - signal_mention_rate: Fraction of reasoning strings that mention
      specific signals (evidence markers, concepts, patterns).

    Returns dict with all metrics.
    """
    if not annotations:
        return {"avg_length": 0, "min_length": 0, "circular_count": 0,
                "signal_mention_rate": 0.0, "total": 0}

    total = len(annotations)
    lengths = [len(a.get("reasoning", "")) for a in annotations]
    avg_length = sum(lengths) / total
    min_length = min(lengths) if lengths else 0

    # Circular detection: reasoning that just restates the level
    circular_patterns = [
        "classified as", "assigned", "this claim is", "level is",
    ]
    circular = 0
    for a in annotations:
        reasoning = a.get("reasoning", "")
        level = a.get("level", "")
        # Circular if reasoning is short AND contains the level label
        if len(reasoning) < 50 and level and level in reasoning:
            # Check if reasoning is just restating
            words = reasoning.lower().split()
            if len(words) < 15:
                circular += 1

    # Signal mention rate: does the reasoning reference specific observations?
    signal_terms = [
        "detected", "citation", "source", "evidence", "hedging",
        "definition", "pattern", "signal", "marker", "domain",
        "concept", "textbook", "standard", "statistic", "specific",
    ]
    signal_count = 0
    for a in annotations:
        reasoning = a.get("reasoning", "").lower()
        if any(term in reasoning for term in signal_terms):
            signal_count += 1

    return {
        "avg_length": round(avg_length, 1),
        "min_length": min_length,
        "circular_count": circular,
        "circular_rate": round(circular / total, 3),
        "signal_mention_rate": round(signal_count / total, 3),
        "total": total,
    }
