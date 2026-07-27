"""Classification metrics -- agreement, confusion, and distribution analysis.

Evaluates A4 (Establishedness), A5 (Evidence Requirement), and A6 (Novelty).
Per M6-001: Measures agreement, not correctness.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


def compute_agreement(
    annotations: list[dict[str, Any]],
    gold_classifications: list[dict[str, Any]],
    level_key: str = "level",
) -> dict[str, Any]:
    """Compute exact and adjacent agreement between analyzer and gold.

    Aligns by claim_text + position span. Adjacent agreement counts
    classifications that are within 1 level (e.g., E2 vs E3).

    Returns: exact_agreement, adjacent_agreement, total_aligned, total_gold.
    """
    # Build lookup from gold by (text, start_char)
    gold_map: dict[tuple[str, int], dict[str, Any]] = {}
    for gc in gold_classifications:
        key = (gc.get("claim_text", ""), gc.get("start_char", 0))
        gold_map[key] = gc

    exact = 0
    adjacent = 0
    aligned = 0

    for ann in annotations:
        key = (ann.get("claim_text", ""), ann.get("start_char", 0))
        gold = gold_map.get(key)
        if gold is None:
            continue
        aligned += 1

        ann_level = ann.get(level_key, "")
        gold_level = gold.get(level_key, "")

        if ann_level == gold_level:
            exact += 1
            adjacent += 1
        elif _levels_adjacent(ann_level, gold_level):
            adjacent += 1

    total_gold = len(gold_classifications)

    return {
        "exact_agreement": round(exact / total_gold, 3) if total_gold > 0 else 0.0,
        "adjacent_agreement": round(adjacent / total_gold, 3) if total_gold > 0 else 0.0,
        "total_aligned": aligned,
        "total_gold": total_gold,
    }


def _levels_adjacent(a: str, b: str) -> bool:
    """Check if two classification levels are adjacent (differ by 1)."""
    if not a or not b or a[0] != b[0]:
        return False
    try:
        return abs(int(a[1:]) - int(b[1:])) == 1
    except ValueError:
        return False


def compute_kappa(
    annotations: list[dict[str, Any]],
    gold_classifications: list[dict[str, Any]],
    level_key: str = "level",
) -> float:
    """Compute Cohen's kappa for classification agreement.

    Simple implementation for ordinal classification scales.
    """
    gold_map: dict[tuple[str, int], dict[str, Any]] = {}
    for gc in gold_classifications:
        key = (gc.get("claim_text", ""), gc.get("start_char", 0))
        gold_map[key] = gc

    pairs: list[tuple[str, str]] = []
    for ann in annotations:
        key = (ann.get("claim_text", ""), ann.get("start_char", 0))
        gold = gold_map.get(key)
        if gold is not None:
            pairs.append((ann.get(level_key, ""), gold.get(level_key, "")))

    if not pairs:
        return 0.0

    n = len(pairs)
    ann_counts = Counter(a for a, _ in pairs)
    gold_counts = Counter(g for _, g in pairs)

    po = sum(1 for a, g in pairs if a == g) / n
    pe = sum(
        (ann_counts.get(level, 0) / n) * (gold_counts.get(level, 0) / n)
        for level in set(ann_counts) | set(gold_counts)
    )

    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0

    return round((po - pe) / (1 - pe), 3)


def compute_confusion(
    annotations: list[dict[str, Any]],
    gold_classifications: list[dict[str, Any]],
    level_key: str = "level",
) -> dict[str, dict[str, int]]:
    """Build confusion matrix between analyzer and gold levels."""
    gold_map: dict[tuple[str, int], dict[str, Any]] = {}
    for gc in gold_classifications:
        key = (gc.get("claim_text", ""), gc.get("start_char", 0))
        gold_map[key] = gc

    matrix: dict[str, dict[str, int]] = {}
    for ann in annotations:
        key = (ann.get("claim_text", ""), ann.get("start_char", 0))
        gold = gold_map.get(key)
        if gold is None:
            continue
        ann_level = ann.get(level_key, "")
        gold_level = gold.get(level_key, "")
        matrix.setdefault(gold_level, {}).setdefault(ann_level, 0)
        matrix[gold_level][ann_level] += 1

    return matrix


def compute_distribution(
    annotations: list[dict[str, Any]],
    level_key: str = "level",
) -> dict[str, float]:
    """Compute the distribution of classification levels."""
    total = len(annotations)
    if total == 0:
        return {}
    counts = Counter(a.get(level_key, "") for a in annotations)
    return {level: round(count / total, 3) for level, count in counts.items()}
