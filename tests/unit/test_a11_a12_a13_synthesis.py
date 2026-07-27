"""Tests for A11, A12, A13 synthesis analyzers."""

from __future__ import annotations

import pytest

from outputlens.analysis.model import (
    Claim, ClaimGraph, ConfidenceMarker, EstablishednessAnnotation,
    NoveltyAnnotation, NoveltyIndex, OverconfidenceReport, StructuralIntegrityReport,
)
from outputlens.analyzers.a11_a12_a13_synthesis import (
    NoveltyIndexCalculator, OverconfidenceDetector, StructuralIntegrityAnalyzer,
    compute_novelty_index, detect_overconfidence, compute_structural_integrity,
)
from outputlens.orchestration.analyzer import AnalysisContext, AnalyzerError


def _na(cid: str, level: str) -> NoveltyAnnotation:
    return NoveltyAnnotation(claim_id=cid, level=level, reasoning="Test. " * 10)

def _ea(cid: str, level: str) -> EstablishednessAnnotation:
    return EstablishednessAnnotation(claim_id=cid, level=level, reasoning="Test. " * 10)

def _claim(cid: str, markers: tuple = ()) -> Claim:
    return Claim(id=cid, text="Claim text.", start_char=0, end_char=11,
                 segment_id="s1", claim_type="factual_assertion",
                 confidence_markers=markers)


class TestA11NoveltyIndex:
    def test_mixed(self):
        anns = [_na("c1", "N1"), _na("c2", "N3"), _na("c3", "N5")]
        ni = compute_novelty_index(anns)
        assert ni.novelty_proportion == pytest.approx(2/3, abs=0.01)
        assert ni.n3_count == 1
        assert ni.n5_count == 1

    def test_caveat_present(self):
        assert "not inherently good or bad" in NoveltyIndex.CAVEAT.lower()

    def test_orchestration(self):
        ctx = AnalysisContext()
        ctx.set_output("a6", "a6", {"novelty_annotations": [_na("c1", "N1")]})
        result = NoveltyIndexCalculator().analyze(ctx)
        assert result["novelty_index"].novelty_proportion == 0.0


class TestA12Overconfidence:
    def test_detected(self):
        cm = ConfidenceMarker(id="cm1", type="certainty", start_char=0, end_char=10,
                              claim_id="c1", expression="definitely", intensity="strong")
        claims = [_claim("c1", markers=(cm,))]
        e_anns = [_ea("c1", "E3")]
        report = detect_overconfidence(claims, e_anns)
        assert len(report.overconfident_claims) == 1

    def test_not_detected_when_established(self):
        cm = ConfidenceMarker(id="cm1", type="certainty", start_char=0, end_char=10,
                              claim_id="c1", expression="clearly")
        claims = [_claim("c1", markers=(cm,))]
        e_anns = [_ea("c1", "E2")]
        report = detect_overconfidence(claims, e_anns)
        assert len(report.overconfident_claims) == 0

    def test_no_markers_no_detection(self):
        claims = [_claim("c1")]
        e_anns = [_ea("c1", "E4")]
        report = detect_overconfidence(claims, e_anns)
        assert len(report.overconfident_claims) == 0


class TestA13StructuralIntegrity:
    def test_all_healthy(self):
        graph = ClaimGraph(
            foundational_claim_ids=("c1",),
            orphan_claim_ids=(),
            contradiction_clusters=(),
            cascading_uncertainty_chains=(),
        )
        e_anns = [_ea("c1", "E2")]
        report = compute_structural_integrity(graph, e_anns, 1)
        assert report.foundation_health == 1.0

    def test_orphan_proportion(self):
        graph = ClaimGraph(orphan_claim_ids=("c3",))
        e_anns = [_ea("c1", "E2"), _ea("c2", "E2"), _ea("c3", "E3")]
        report = compute_structural_integrity(graph, e_anns, 3)
        assert report.orphan_proportion == pytest.approx(1/3, abs=0.01)

    def test_orchestration(self):
        graph = ClaimGraph()
        ctx = AnalysisContext()
        ctx.set_output("a7", "a7", {"claim_graph": graph})
        ctx.set_output("a2", "a2", {"claims": []})
        ctx.set_output("a4", "a4", {"establishedness_annotations": []})
        result = StructuralIntegrityAnalyzer().analyze(ctx)
        assert isinstance(result["structural_integrity_report"], StructuralIntegrityReport)
