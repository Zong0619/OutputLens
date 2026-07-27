"""Tests for the evaluation harness -- Phase 6.2."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from benchmarks.evaluation_harness.loader import (
    get_annotations,
    get_claims,
    load_analysis_document,
    load_golden_dataset,
    validate_analysis_document,
)
from benchmarks.evaluation_harness.metrics.extraction import (
    compute_claim_boundary_f1,
    compute_claim_type_accuracy,
)
from benchmarks.evaluation_harness.metrics.classification import (
    compute_agreement,
    compute_confusion,
    compute_distribution,
    compute_kappa,
    _levels_adjacent,
)
from benchmarks.evaluation_harness.metrics.reasoning import (
    compute_reasoning_specificity,
)
from benchmarks.evaluation_harness.metrics.synthesis import (
    compute_punchlist_precision_recall,
    compute_trust_profile_correlation,
)
from benchmarks.evaluation_harness.reporter import (
    aggregate_metrics,
    evaluate_item,
    generate_report,
)


def _make_doc(claims=None, e_anns=None, ev_anns=None, punchlist=None):
    """Build a minimal valid AnalysisDocument dict."""
    doc: dict = {
        "schema_version": "1.0.0",
        "metadata": {"engine_version": "0.1.0", "timestamp": "2026-01-01T00:00:00Z", "analysis_id": "test"},
        "runtime_objects": {"raw_input": {"text": "Test."}},
        "analysis_objects": {"claims": claims or []},
    }
    ao = doc["analysis_objects"]
    if e_anns is not None:
        ao["establishedness_annotations"] = e_anns
    if ev_anns is not None:
        ao["evidence_annotations"] = ev_anns
    if punchlist is not None:
        ao["verification_punchlist"] = punchlist
    return doc


# ---------------------------------------------------------------------------
# Loader Tests
# ---------------------------------------------------------------------------

class TestLoader:
    def test_validate_valid_doc(self):
        doc = _make_doc([{"id": "c1", "text": "Test.", "start_char": 0, "end_char": 5,
                          "segment_id": "s1", "claim_type": "factual_assertion"}])
        assert validate_analysis_document(doc) == []

    def test_validate_missing_schema(self):
        assert len(validate_analysis_document({})) > 0

    def test_validate_wrong_version(self):
        doc = {"schema_version": "0.0.0", "analysis_objects": {"claims": []}}
        errors = validate_analysis_document(doc)
        assert any("version" in e for e in errors)

    def test_validate_missing_claims(self):
        doc = {"schema_version": "1.0.0", "analysis_objects": {}}
        errors = validate_analysis_document(doc)
        assert any("claims" in e for e in errors)

    def test_load_and_validate_roundtrip(self):
        doc = _make_doc([{"id": "c1", "text": "T.", "start_char": 0, "end_char": 2,
                          "segment_id": "s1", "claim_type": "factual_assertion"}])
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(doc, f)
            tmp = f.name
        try:
            loaded = load_analysis_document(tmp)
            assert loaded["schema_version"] == "1.0.0"
        finally:
            Path(tmp).unlink()

    def test_get_claims(self):
        doc = _make_doc([{"id": "c1", "text": "T."}])
        assert len(get_claims(doc)) == 1

    def test_get_annotations(self):
        doc = _make_doc(e_anns=[{"claim_id": "c1", "level": "E2", "reasoning": "Test reasoning " * 5}])
        anns = get_annotations(doc, "establishedness_annotations")
        assert len(anns) == 1


# ---------------------------------------------------------------------------
# Extraction Metrics Tests
# ---------------------------------------------------------------------------

class TestExtractionMetrics:
    def test_perfect_f1(self):
        claims = [{"start_char": 0, "end_char": 10, "claim_type": "factual_assertion"}]
        gold = [{"start_char": 0, "end_char": 10, "claim_type": "factual_assertion"}]
        result = compute_claim_boundary_f1(claims, gold)
        assert result["f1"] == 1.0

    def test_no_match(self):
        claims = [{"start_char": 0, "end_char": 5}]
        gold = [{"start_char": 50, "end_char": 55}]
        result = compute_claim_boundary_f1(claims, gold)
        assert result["f1"] == 0.0

    def test_empty_gold(self):
        result = compute_claim_boundary_f1([{"start_char": 0, "end_char": 5}], [])
        assert result["f1"] == 0.0

    def test_type_accuracy(self):
        claims = [{"start_char": 0, "end_char": 10, "claim_type": "factual_assertion"}]
        gold = [{"start_char": 0, "end_char": 10, "claim_type": "factual_assertion"}]
        result = compute_claim_type_accuracy(claims, gold)
        assert result["accuracy"] == 1.0


# ---------------------------------------------------------------------------
# Classification Metrics Tests
# ---------------------------------------------------------------------------

class TestClassificationMetrics:
    def test_perfect_agreement(self):
        anns = [{"claim_text": "X.", "start_char": 0, "level": "E2", "reasoning": "x" * 20}]
        gold = [{"claim_text": "X.", "start_char": 0, "level": "E2", "reasoning": "x" * 20}]
        result = compute_agreement(anns, gold)
        assert result["exact_agreement"] == 1.0

    def test_adjacent_agreement(self):
        anns = [{"claim_text": "X.", "start_char": 0, "level": "E2", "reasoning": "x" * 20}]
        gold = [{"claim_text": "X.", "start_char": 0, "level": "E3", "reasoning": "x" * 20}]
        result = compute_agreement(anns, gold)
        assert result["exact_agreement"] == 0.0
        assert result["adjacent_agreement"] == 1.0

    def test_levels_adjacent(self):
        assert _levels_adjacent("E2", "E3") is True
        assert _levels_adjacent("E1", "E5") is False
        assert _levels_adjacent("R1", "R2") is True

    def test_kappa_perfect(self):
        anns = [{"claim_text": "X.", "start_char": 0, "level": "E2", "reasoning": "x" * 20}]
        gold = [{"claim_text": "X.", "start_char": 0, "level": "E2", "reasoning": "x" * 20}]
        assert compute_kappa(anns, gold) == 1.0

    def test_distribution(self):
        anns = [
            {"level": "E1", "reasoning": "x" * 20},
            {"level": "E2", "reasoning": "x" * 20},
            {"level": "E2", "reasoning": "x" * 20},
        ]
        dist = compute_distribution(anns)
        assert dist.get("E1") == pytest.approx(1/3, abs=0.01)
        assert dist.get("E2") == pytest.approx(2/3, abs=0.01)

    def test_confusion(self):
        anns = [{"claim_text": "X.", "start_char": 0, "level": "E2", "reasoning": "x" * 20}]
        gold = [{"claim_text": "X.", "start_char": 0, "level": "E3", "reasoning": "x" * 20}]
        matrix = compute_confusion(anns, gold)
        assert "E3" in matrix
        assert "E2" in matrix["E3"]


# ---------------------------------------------------------------------------
# Reasoning Metrics Tests
# ---------------------------------------------------------------------------

class TestReasoningMetrics:
    def test_specificity(self):
        anns = [
            {"level": "E2", "reasoning": "This claim references quantum entanglement which is a well-established domain concept in physics textbooks."},
            {"level": "E1", "reasoning": "E1"},
        ]
        result = compute_reasoning_specificity(anns)
        assert result["total"] == 2
        assert result["avg_length"] > 20
        assert result["circular_count"] >= 1

    def test_empty(self):
        result = compute_reasoning_specificity([])
        assert result["total"] == 0


# ---------------------------------------------------------------------------
# Synthesis Metrics Tests
# ---------------------------------------------------------------------------

class TestSynthesisMetrics:
    def test_trust_profile(self):
        doc = _make_doc()
        doc["analysis_objects"]["trust_profile"] = {
            "established_pct": 60, "plausible_pct": 30, "needs_verification_pct": 10,
        }
        result = compute_trust_profile_correlation(doc)
        assert result["established_pct"] == 60

    def test_punchlist_precision(self):
        punchlist = {"entries": [
            {"claim_id": "c1", "claim_text": "X.", "rank": 1}
        ]}
        gold = {
            "rankings": [
                {"claim_id": "c1", "claim_text": "X.", "should_verify": True, "priority": 1,
                 "reason": "Needs source.", "suggested_verification": "Search."}
            ],
            "overall_usefulness": 4,
        }
        result = compute_punchlist_precision_recall(punchlist, gold)
        assert result["precision"] == 1.0
        assert result["usefulness"] == 4


# ---------------------------------------------------------------------------
# Reporter Tests
# ---------------------------------------------------------------------------

class TestReporter:
    def test_aggregate_empty(self):
        result = aggregate_metrics([])
        assert result["item_count"] == 0

    def test_evaluate_item(self):
        doc = _make_doc(
            claims=[{"id": "c1", "text": "X.", "start_char": 0, "end_char": 2,
                     "segment_id": "s1", "claim_type": "factual_assertion"}],
            e_anns=[{"claim_id": "c1", "level": "E2", "claim_text": "X.", "start_char": 0,
                     "reasoning": "This is standard textbook material in introductory physics courses."}],
        )
        gold_item = {
            "item_id": "001",
            "response_text": "X.",
            "annotations": {
                "claims": [{"claim_text": "X.", "start_char": 0, "end_char": 2,
                           "claim_type": "factual_assertion"}],
                "establishedness": [{"claim_text": "X.", "start_char": 0,
                                    "level": "E2", "reasoning": "Standard."}],
            },
        }
        result = evaluate_item(doc, gold_item)
        assert result["item_id"] == "001"
        assert "extraction" in result

    def test_deterministic(self):
        """Same inputs must produce identical outputs."""
        doc = _make_doc(
            claims=[{"id": "c1", "text": "X.", "start_char": 0, "end_char": 2,
                     "segment_id": "s1", "claim_type": "factual_assertion"}],
        )
        gold_item = {
            "item_id": "001",
            "response_text": "X.",
            "annotations": {
                "claims": [{"claim_text": "X.", "start_char": 0, "end_char": 2,
                           "claim_type": "factual_assertion"}],
            },
        }
        r1 = evaluate_item(doc, gold_item)
        r2 = evaluate_item(doc, gold_item)
        assert r1 == r2

    def test_generate_report(self):
        doc = _make_doc(
            claims=[{"id": "c1", "text": "X.", "start_char": 0, "end_char": 2,
                     "segment_id": "s1", "claim_type": "factual_assertion"}],
            e_anns=[{"claim_id": "c1", "claim_text": "X.", "start_char": 0,
                     "level": "E2", "reasoning": "Standard textbook material in physics."}],
        )
        dataset = {
            "dataset_id": "GOLD-ESTABLISHED",
            "version": "0.1.0",
            "items": [
                {"item_id": "001", "response_text": "X.",
                 "annotations": {
                     "establishedness": [{"claim_text": "X.", "start_char": 0,
                                         "level": "E2", "reasoning": "Standard."}],
                 }},
            ],
        }
        report = generate_report(dataset, [doc])
        assert report["dataset_id"] == "GOLD-ESTABLISHED"
        assert report["dataset_version"] == "0.1.0"
        assert "summary" in report
        assert "detail" in report
