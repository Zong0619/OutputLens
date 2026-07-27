"""Synthesis evaluation metrics -- trust profile correlation, punchlist quality.

Evaluates A9-A16 synthesis outputs. Per M6-001 and A16-001: measures
agreement and usefulness, not correctness.
"""

from __future__ import annotations

from typing import Any


def compute_trust_profile_correlation(
    doc: dict[str, Any],
    gold_trust: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Extract trust profile from document. If gold provided, compute correlation.

    Without gold data, returns the trust profile values for documentation.
    """
    tp = doc.get("analysis_objects", {}).get("trust_profile", {})
    result: dict[str, Any] = {
        "established_pct": tp.get("established_pct", 0),
        "plausible_pct": tp.get("plausible_pct", 0),
        "needs_verification_pct": tp.get("needs_verification_pct", 0),
    }

    if gold_trust:
        # Simple absolute difference correlation
        diffs = {
            "established_diff": abs(result["established_pct"] - gold_trust.get("established_pct", 0)),
            "plausible_diff": abs(result["plausible_pct"] - gold_trust.get("plausible_pct", 0)),
            "needs_verification_diff": abs(result["needs_verification_pct"] - gold_trust.get("needs_verification_pct", 0)),
        }
        avg_diff = sum(diffs.values()) / 3
        result["gold_trust"] = gold_trust
        result["diffs"] = diffs
        result["avg_absolute_diff"] = round(avg_diff, 1)
        result["correlation"] = round(max(0.0, 1.0 - avg_diff / 100), 3)

    return result


def compute_punchlist_precision_recall(
    punchlist: dict[str, Any],
    gold_annotations: dict[str, Any],
) -> dict[str, Any]:
    """Compute punchlist precision and recall against gold annotations.

    Precision: fraction of punchlist entries the annotator would verify.
    Recall: fraction of gold "should_verify" claims that appear in the punchlist.

    Per A16-001: Measures usefulness of investigation priorities, not
    whether claims are actually false.
    """
    entries = punchlist.get("entries", [])
    gold_rankings = gold_annotations.get("rankings", [])
    missing = gold_annotations.get("missing_claims", [])

    if not gold_rankings:
        return {"precision": 0.0, "recall": 0.0, "total_entries": len(entries),
                "gold_should_verify": 0, "usefulness": gold_annotations.get("overall_usefulness", 0)}

    punchlist_claim_ids = {e.get("claim_id", "") for e in entries}
    should_verify_ids = {
        r.get("claim_id", "") or f"{r.get('claim_text','')}:{r.get('start_char',0)}"
        for r in gold_rankings if r.get("should_verify", False)
    }

    # Precision: how many punchlist entries are marked "should verify"
    verified_entries = sum(
        1 for e in entries
        if any(
            r.get("should_verify", False) and
            (r.get("claim_id") == e.get("claim_id") or
             r.get("claim_text") == e.get("claim_text"))
            for r in gold_rankings
        )
    )
    precision = verified_entries / len(entries) if entries else 0.0

    # Recall: how many "should verify" claims are in the punchlist
    if should_verify_ids:
        recall = len(punchlist_claim_ids & should_verify_ids) / len(should_verify_ids)
    else:
        recall = 0.0

    usefulness = gold_annotations.get("overall_usefulness", 0)

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "total_entries": len(entries),
        "gold_should_verify": len(should_verify_ids),
        "missing_claims_count": len(missing),
        "usefulness": usefulness,
    }
