"""Tests for A9 (Trust Profile Generator) and A10 (Evidence Gap Analyzer)."""

from __future__ import annotations

import pytest

from outputlens.analysis.model import (
    EstablishednessAnnotation,
    EvidenceAnnotation,
    EvidenceGapReport,
    TrustProfile,
)
from outputlens.analyzers.a9_a10_synthesis import (
    EvidenceGapAnalyzer,
    TrustProfileGenerator,
    compute_evidence_gap,
    compute_trust_profile,
)
from outputlens.orchestration.analyzer import AnalysisContext, AnalyzerError


def _ea(cid: str, level: str) -> EstablishednessAnnotation:
    return EstablishednessAnnotation(claim_id=cid, level=level,
                                     reasoning="Test reasoning for classification " + level + "." * 5)

def _eva(cid: str, level: str) -> EvidenceAnnotation:
    return EvidenceAnnotation(claim_id=cid, level=level,
                              reasoning="Test reasoning for evidence " + level + "." * 5)


class TestTrustProfile:
    def test_all_established(self):
        e_anns = [_ea("c1", "E1"), _ea("c2", "E2")]
        ev_anns = [_eva("c1", "R1"), _eva("c2", "R2")]
        tp = compute_trust_profile(e_anns, ev_anns)
        assert tp.established_pct == 100.0

    def test_mixed_distribution(self):
        e_anns = [_ea("c1", "E1"), _ea("c2", "E3"), _ea("c3", "E4")]
        ev_anns = [_eva("c1", "R1"), _eva("c2", "R3"), _eva("c3", "R4")]
        tp = compute_trust_profile(e_anns, ev_anns)
        assert tp.established_pct + tp.plausible_pct + tp.needs_verification_pct == pytest.approx(100.0)

    def test_r4_overrides_e_level(self):
        e_anns = [_ea("c1", "E2")]  # Domain established
        ev_anns = [_eva("c1", "R4")]  # But no evidence
        tp = compute_trust_profile(e_anns, ev_anns)
        assert tp.needs_verification_pct == 100.0

    def test_empty_claims(self):
        tp = compute_trust_profile([], [])
        assert tp.established_pct == 0.0
        assert tp.needs_verification_pct == 100.0

    def test_caveat_present(self):
        assert "not a reliability score" in TrustProfile.CAVEAT.lower()


class TestEvidenceGap:
    def test_no_gaps(self):
        ev_anns = [_eva("c1", "R1"), _eva("c2", "R2")]
        report = compute_evidence_gap(ev_anns)
        assert report.gap_ratio == 0.0

    def test_all_gaps(self):
        ev_anns = [_eva("c1", "R3"), _eva("c2", "R4")]
        report = compute_evidence_gap(ev_anns)
        assert report.gap_ratio == 1.0
        assert report.r3_count == 1
        assert report.r4_count == 1

    def test_mixed(self):
        ev_anns = [_eva("c1", "R1"), _eva("c2", "R2"), _eva("c3", "R3"), _eva("c4", "R4")]
        report = compute_evidence_gap(ev_anns)
        assert report.gap_ratio == 0.5
        assert report.r3_count == 1
        assert report.r4_count == 1

    def test_empty(self):
        report = compute_evidence_gap([])
        assert report.gap_ratio == 0.0
        assert report.r3_count == 0
        assert report.r4_count == 0


class TestOrchestration:
    def test_a9_declaration(self):
        a = TrustProfileGenerator()
        assert a.declaration.id == "a9"
        assert a.declaration.layer == "synthesis"

    def test_a10_declaration(self):
        a = EvidenceGapAnalyzer()
        assert a.declaration.id == "a10"
        assert a.declaration.layer == "synthesis"

    def test_a9_analyze(self):
        ctx = AnalysisContext()
        ctx.set_output("a4", "a4", {"establishedness_annotations": [_ea("c1", "E2")]})
        ctx.set_output("a5", "a5", {"evidence_annotations": [_eva("c1", "R1")]})
        result = TrustProfileGenerator().analyze(ctx)
        tp = result["trust_profile"]
        assert tp.established_pct == 100.0

    def test_a10_analyze(self):
        ctx = AnalysisContext()
        ctx.set_output("a5", "a5", {"evidence_annotations": [_eva("c1", "R4")]})
        result = EvidenceGapAnalyzer().analyze(ctx)
        report = result["evidence_gap_report"]
        assert report.gap_ratio == 1.0

    def test_a9_missing_input_raises(self):
        with pytest.raises(AnalyzerError):
            TrustProfileGenerator().analyze(AnalysisContext())

    def test_a10_missing_input_raises(self):
        with pytest.raises(AnalyzerError):
            EvidenceGapAnalyzer().analyze(AnalysisContext())
