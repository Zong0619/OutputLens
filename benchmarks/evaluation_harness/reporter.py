"""Evaluation report generation from metric results.

Aggregates metric outputs across all items in a golden dataset and produces
a structured evaluation report.
"""

from __future__ import annotations

from typing import Any


def aggregate_metrics(all_item_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-item metric dicts into summary statistics.

    Args:
        all_item_metrics: List of per-item metric dicts from evaluate_item().

    Returns:
        Aggregated metrics dict with averages, totals, and per-item detail.
    """
    if not all_item_metrics:
        return {"error": "No items to aggregate", "item_count": 0}

    # Aggregate extraction metrics
    extraction_f1s = [
        m.get("extraction", {}).get("f1", 0.0)
        for m in all_item_metrics if "extraction" in m
    ]
    extraction_precisions = [
        m.get("extraction", {}).get("precision", 0.0)
        for m in all_item_metrics if "extraction" in m
    ]
    extraction_recalls = [
        m.get("extraction", {}).get("recall", 0.0)
        for m in all_item_metrics if "extraction" in m
    ]

    # Aggregate classification metrics
    e_agreements = [
        m.get("classification", {}).get("establishedness", {}).get("exact_agreement", 0.0)
        for m in all_item_metrics if "classification" in m
    ]
    ev_agreements = [
        m.get("classification", {}).get("evidence", {}).get("exact_agreement", 0.0)
        for m in all_item_metrics if "classification" in m
    ]
    n_agreements = [
        m.get("classification", {}).get("novelty", {}).get("exact_agreement", 0.0)
        for m in all_item_metrics if "classification" in m
    ]

    # Aggregate reasoning metrics
    signal_rates = [
        m.get("reasoning", {}).get("signal_mention_rate", 0.0)
        for m in all_item_metrics if "reasoning" in m
    ]
    circular_rates = [
        m.get("reasoning", {}).get("circular_rate", 0.0)
        for m in all_item_metrics if "reasoning" in m
    ]

    return {
        "item_count": len(all_item_metrics),
        "extraction": {
            "avg_f1": round(_mean(extraction_f1s), 3),
            "avg_precision": round(_mean(extraction_precisions), 3),
            "avg_recall": round(_mean(extraction_recalls), 3),
        },
        "classification": {
            "establishedness_avg_agreement": round(_mean(e_agreements), 3),
            "evidence_avg_agreement": round(_mean(ev_agreements), 3),
            "novelty_avg_agreement": round(_mean(n_agreements), 3),
        },
        "reasoning": {
            "avg_signal_mention_rate": round(_mean(signal_rates), 3),
            "avg_circular_rate": round(_mean(circular_rates), 3),
        },
        "per_item": all_item_metrics,
    }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def evaluate_item(
    doc: dict[str, Any],
    gold_item: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate a single AnalysisDocument against one golden dataset item.

    Args:
        doc: The AnalysisDocument dict.
        gold_item: One item from a golden dataset, containing annotations.

    Returns:
        Dict of metrics for this item.
    """
    from benchmarks.evaluation_harness.loader import (
        get_annotations,
        get_claims,
    )
    from benchmarks.evaluation_harness.metrics.extraction import (
        compute_claim_boundary_f1,
        compute_claim_type_accuracy,
    )
    from benchmarks.evaluation_harness.metrics.classification import (
        compute_agreement,
        compute_distribution,
    )
    from benchmarks.evaluation_harness.metrics.reasoning import (
        compute_reasoning_specificity,
    )
    from benchmarks.evaluation_harness.metrics.synthesis import (
        compute_punchlist_precision_recall,
        compute_trust_profile_correlation,
    )

    result: dict[str, Any] = {"item_id": gold_item.get("item_id", "unknown")}

    gold_annotations = gold_item.get("annotations", {})
    claims = get_claims(doc)

    # Extraction metrics (if GOLD-CLAIM annotations present)
    gold_claims = gold_annotations.get("claims", [])
    if gold_claims:
        result["extraction"] = {
            "boundary": compute_claim_boundary_f1(claims, gold_claims),
            "type_accuracy": compute_claim_type_accuracy(claims, gold_claims),
        }

    # Classification metrics
    e_anns = get_annotations(doc, "establishedness_annotations")
    ev_anns = get_annotations(doc, "evidence_annotations")
    n_anns = get_annotations(doc, "novelty_annotations")

    gold_e = gold_annotations.get("establishedness", [])
    gold_ev = gold_annotations.get("evidence", [])
    gold_n = gold_annotations.get("novelty", [])

    class_metrics: dict[str, Any] = {}
    if gold_e:
        class_metrics["establishedness"] = {
            "agreement": compute_agreement(e_anns, gold_e),
            "kappa": _compute_kappa_wrapper(e_anns, gold_e),
            "distribution": compute_distribution(e_anns),
        }
    if gold_ev:
        class_metrics["evidence"] = {
            "agreement": compute_agreement(ev_anns, gold_ev),
            "distribution": compute_distribution(ev_anns),
        }
    if gold_n:
        class_metrics["novelty"] = {
            "agreement": compute_agreement(n_anns, gold_n),
            "distribution": compute_distribution(n_anns),
        }
    if class_metrics:
        result["classification"] = class_metrics

    # Reasoning metrics (on establishedness annotations as representative)
    if e_anns:
        result["reasoning"] = compute_reasoning_specificity(e_anns)

    # Synthesis metrics
    gold_punchlist = gold_annotations.get("punchlist", {})
    punchlist = doc.get("analysis_objects", {}).get("verification_punchlist", {})
    if gold_punchlist and punchlist:
        result["synthesis"] = {
            "punchlist": compute_punchlist_precision_recall(
                punchlist, gold_punchlist,
            ),
        }

    gold_trust = gold_annotations.get("trust_profile")
    if gold_trust:
        synth = result.setdefault("synthesis", {})
        synth["trust_profile"] = compute_trust_profile_correlation(doc, gold_trust)

    return result


def _compute_kappa_wrapper(anns: list, gold: list) -> float:
    from benchmarks.evaluation_harness.metrics.classification import compute_kappa
    return compute_kappa(anns, gold)


def generate_report(
    dataset: dict[str, Any],
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate a complete evaluation report from a dataset and documents.

    Args:
        dataset: Loaded golden dataset dict.
        documents: List of AnalysisDocument dicts, one per dataset item.

    Returns:
        Complete evaluation report dict.
    """
    if len(documents) != len(dataset.get("items", [])):
        raise ValueError(
            f"Document count ({len(documents)}) does not match "
            f"dataset item count ({len(dataset['items'])})"
        )

    item_metrics = []
    for doc, gold_item in zip(documents, dataset["items"]):
        item_metrics.append(evaluate_item(doc, gold_item))

    aggregated = aggregate_metrics(item_metrics)

    return {
        "report_version": "0.1.0",
        "dataset_id": dataset.get("dataset_id"),
        "dataset_version": dataset.get("version"),
        "evaluation_timestamp": "",  # To be filled by caller
        "summary": {
            "extraction_f1": aggregated.get("extraction", {}).get("avg_f1", 0),
            "establishedness_agreement": (
                aggregated.get("classification", {})
                .get("establishedness_avg_agreement", 0)
            ),
            "evidence_agreement": (
                aggregated.get("classification", {})
                .get("evidence_avg_agreement", 0)
            ),
            "reasoning_signal_rate": (
                aggregated.get("reasoning", {}).get("avg_signal_mention_rate", 0)
            ),
        },
        "detail": aggregated,
    }
