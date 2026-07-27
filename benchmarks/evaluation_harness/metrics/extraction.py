"""Extraction metrics -- claim boundary alignment and type accuracy.

Evaluates A2 Claim Extractor output against gold-standard annotations.
"""

from __future__ import annotations

from typing import Any


def _span_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    """Compute character overlap between two spans."""
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def compute_claim_boundary_f1(
    claims: list[dict[str, Any]],
    gold_claims: list[dict[str, Any]],
) -> dict[str, float]:
    """Compute claim boundary precision, recall, and F1.

    Aligns extracted claims to gold claims by maximum span overlap.
    A claim matches if its span overlaps a gold claim span by at least 50%.

    Returns dict with precision, recall, f1.
    """
    if not gold_claims:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "gold_count": 0, "extracted_count": len(claims)}

    matched_gold: set[int] = set()
    matched_extracted: set[int] = set()

    for ei, ec in enumerate(claims):
        best_overlap = 0
        best_gi = -1
        for gi, gc in enumerate(gold_claims):
            if gi in matched_gold:
                continue
            overlap = _span_overlap(
                ec.get("start_char", 0), ec.get("end_char", 0),
                gc.get("start_char", 0), gc.get("end_char", 0),
            )
            gc_len = gc.get("end_char", 0) - gc.get("start_char", 1)
            if gc_len > 0 and overlap / gc_len >= 0.5 and overlap > best_overlap:
                best_overlap = overlap
                best_gi = gi

        if best_gi >= 0:
            matched_extracted.add(ei)
            matched_gold.add(best_gi)

    precision = len(matched_extracted) / len(claims) if claims else 0.0
    recall = len(matched_gold) / len(gold_claims) if gold_claims else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "gold_count": len(gold_claims),
        "extracted_count": len(claims),
        "matched_count": len(matched_extracted),
    }


def compute_claim_type_accuracy(
    claims: list[dict[str, Any]],
    gold_claims: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute claim type classification accuracy against gold annotations.

    Aligns claims by span overlap, then compares claim_type fields.
    Returns accuracy and per-type counts.
    """
    if not gold_claims:
        return {"accuracy": 0.0, "total_matched": 0}

    correct = 0
    total_matched = 0
    type_confusion: dict[str, dict[str, int]] = {}

    for ec in claims:
        best_gi = -1
        best_overlap = 0
        for gi, gc in enumerate(gold_claims):
            overlap = _span_overlap(
                ec.get("start_char", 0), ec.get("end_char", 0),
                gc.get("start_char", 0), gc.get("end_char", 0),
            )
            gc_len = gc.get("end_char", 0) - gc.get("start_char", 1)
            if gc_len > 0 and overlap / gc_len >= 0.5 and overlap > best_overlap:
                best_overlap = overlap
                best_gi = gi

        if best_gi >= 0:
            total_matched += 1
            gold_type = gold_claims[best_gi].get("claim_type", "")
            extracted_type = ec.get("claim_type", "")
            if gold_type == extracted_type:
                correct += 1
            type_confusion.setdefault(gold_type, {}).setdefault(extracted_type, 0)
            type_confusion[gold_type][extracted_type] += 1

    accuracy = correct / total_matched if total_matched > 0 else 0.0
    return {
        "accuracy": round(accuracy, 3),
        "correct": correct,
        "total_matched": total_matched,
        "confusion": type_confusion,
    }
