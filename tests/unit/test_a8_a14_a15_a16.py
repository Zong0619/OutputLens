"""Tests for A8, A14, A15, A16 -- final analyzers."""

from __future__ import annotations

import pytest

from outputlens.analysis.model import (
    Claim, ClaimGraph, ClaimRelationship, CoherenceReport, Concept, ConceptGraph,
    ConceptRelationship, ConceptSurfaceForm, EstablishednessAnnotation,
    EvidenceAnnotation, NoveltyAnnotation, OverconfidenceReport,
    PunchlistEntry, ResponseNarrative, StructuralIntegrityReport,
    TrustProfile, VerificationPunchlist,
)
from outputlens.analyzers.a8_concept_relationships import (
    ConceptRelationshipMapper, build_concept_graph,
)
from outputlens.analyzers.a14_a15_a16_terminal import (
    ConceptualCoherenceAnalyzer, ResponseNarrativeGenerator,
    VerificationPunchlistGenerator,
    compute_coherence, generate_narrative, generate_punchlist,
)
from outputlens.orchestration.analyzer import AnalysisContext, AnalyzerError


def _c(cid: str, text: str = "x", start: int = 0, end: int = 50,
       seg: str = "s1", ctype: str = "factual_assertion") -> Claim:
    return Claim(id=cid, text=text, start_char=start, end_char=end,
                 segment_id=seg, claim_type=ctype)

def _concept(cid: str, name: str = "x", ctype: str = "domain_concept",
             claim_ids: tuple = ("c1",)) -> Concept:
    return Concept(id=cid, canonical_name=name, concept_type=ctype,
                   surface_forms=(ConceptSurfaceForm(text=name, start_char=0, end_char=1),),
                   referencing_claim_ids=claim_ids)

def _ea(cid: str, level: str) -> EstablishednessAnnotation:
    return EstablishednessAnnotation(claim_id=cid, level=level, reasoning="x" * 20)

def _eva(cid: str, level: str) -> EvidenceAnnotation:
    return EvidenceAnnotation(claim_id=cid, level=level, reasoning="x" * 20)

def _na(cid: str, level: str) -> NoveltyAnnotation:
    return NoveltyAnnotation(claim_id=cid, level=level, reasoning="x" * 20)


# ---------------------------------------------------------------------------
# A8: Concept Relationship Mapper
# ---------------------------------------------------------------------------

class TestA8ConceptRelationships:
    def test_infers_from_claim_relationships(self):
        concepts = [_concept("con1", "X", claim_ids=("c1",)),
                    _concept("con2", "Y", claim_ids=("c2",))]
        claim_graph = ClaimGraph(relationships=(
            ClaimRelationship("c1", "c2", "supports", "explicit"),
        ))
        graph = build_concept_graph(concepts, claim_graph)
        assert len(graph.relationships) >= 1
        assert graph.relationships[0].evidence == "claim_inferred"

    def test_empty_inputs(self):
        graph = build_concept_graph([], ClaimGraph())
        assert len(graph.relationships) == 0

    def test_orchestration(self):
        ctx = AnalysisContext()
        ctx.set_output("a3", "a3", {"concepts": [_concept("con1")]})
        ctx.set_output("a7", "a7", {"claim_graph": ClaimGraph()})
        result = ConceptRelationshipMapper().analyze(ctx)
        assert result["concept_graph"] is not None


# ---------------------------------------------------------------------------
# A14: Conceptual Coherence
# ---------------------------------------------------------------------------

class TestA14Coherence:
    def test_fully_connected(self):
        graph = ConceptGraph(relationships=(
            ConceptRelationship("con1", "con2", "related_to"),
        ))
        report = compute_coherence(graph, 2)
        assert report.graph_connectivity == 1.0

    def test_fragmented(self):
        graph = ConceptGraph(relationships=())
        report = compute_coherence(graph, 5)
        assert report.graph_connectivity == 0.0
        assert report.fragmentation_flag


# ---------------------------------------------------------------------------
# A15: Response Narrative (rendering layer per A15-001)
# ---------------------------------------------------------------------------

class TestA15Narrative:
    def test_generates_text(self):
        trust = TrustProfile(established_pct=60, plausible_pct=30, needs_verification_pct=10)
        ev_gap = __import__('outputlens.analysis.model', fromlist=['EvidenceGapReport']).EvidenceGapReport(0.1, 1, 1)
        from outputlens.analysis.model import EvidenceGapReport as EGR, NoveltyIndex, OverconfidenceReport, StructuralIntegrityReport, CoherenceReport
        ev_gap = EGR(gap_ratio=0.1, r3_count=1, r4_count=1)
        novelty = NoveltyIndex(novelty_proportion=0.2)
        overconf = OverconfidenceReport()
        struct = StructuralIntegrityReport(foundation_health=1.0, contradiction_count=0, orphan_proportion=0.0)
        coh = CoherenceReport(graph_connectivity=1.0, cluster_count=1)

        narrative = generate_narrative(trust, ev_gap, novelty, overconf, struct, coh)
        assert len(narrative.narrative_text) >= 50

    def test_rendering_layer_no_analysis(self):
        """A15-001: Narrative is rendering, not analysis."""
        trust = TrustProfile(50, 30, 20)
        from outputlens.analysis.model import EvidenceGapReport as EGR, NoveltyIndex, OverconfidenceReport, StructuralIntegrityReport, CoherenceReport
        ev_gap = EGR(0, 0, 0)
        novelty = NoveltyIndex(0)
        overconf = OverconfidenceReport()
        struct = StructuralIntegrityReport(1.0, 0, 0.0)
        coh = CoherenceReport(1.0, 0)
        narrative = generate_narrative(trust, ev_gap, novelty, overconf, struct, coh)
        # Must not contain language implying new analysis
        assert "new analysis" not in narrative.narrative_text.lower()


# ---------------------------------------------------------------------------
# A16: Verification Punchlist (investigation priorities per A16-001)
# ---------------------------------------------------------------------------

class TestA16Punchlist:
    def test_high_evidence_gap_ranked_first(self):
        claims = [_c("c1", "Specific stat: 95% accuracy.")]
        e_anns = [_ea("c1", "E3")]
        ev_anns = [_eva("c1", "R4")]
        n_anns = [_na("c1", "N1")]
        punchlist = generate_punchlist(claims, e_anns, ev_anns, n_anns, None, None)
        assert len(punchlist.entries) >= 1
        assert punchlist.entries[0].attention_trigger == "no_evidence"

    def test_no_truth_claims(self):
        """A16-001: Punchlist must not assert truth/falsehood."""
        claims = [_c("c1", "Claim text.")]
        e_anns = [_ea("c1", "E3")]
        ev_anns = [_eva("c1", "R4")]
        n_anns = [_na("c1", "N1")]
        punchlist = generate_punchlist(claims, e_anns, ev_anns, n_anns, None, None)
        for entry in punchlist.entries:
            assert "false" not in entry.risk_if_wrong.lower()
            assert "true" not in entry.suggested_verification.lower()
            assert "correct" not in entry.risk_if_wrong.lower()

    def test_empty_claims(self):
        punchlist = generate_punchlist([], [], [], [], None, None)
        assert len(punchlist.entries) == 0

    def test_foundational_gets_higher_priority(self):
        claims = [_c("c1", "Foundation."), _c("c2", "Peripheral.")]
        e_anns = [_ea("c1", "E3"), _ea("c2", "E3")]
        ev_anns = [_eva("c1", "R4"), _eva("c2", "R4")]
        n_anns = [_na("c1", "N1"), _na("c2", "N1")]
        graph = ClaimGraph(foundational_claim_ids=("c1",))
        punchlist = generate_punchlist(claims, e_anns, ev_anns, n_anns, graph, None)
        if len(punchlist.entries) >= 2:
            assert punchlist.entries[0].structural_importance == "foundational"

    def test_orchestration(self):
        ctx = AnalysisContext()
        ctx.set_output("a2", "a2", {"claims": [_c("c1")]})
        ctx.set_output("a4", "a4", {"establishedness_annotations": [_ea("c1", "E3")]})
        ctx.set_output("a5", "a5", {"evidence_annotations": [_eva("c1", "R4")]})
        ctx.set_output("a6", "a6", {"novelty_annotations": [_na("c1", "N1")]})
        ctx.set_output("a7", "a7", {"claim_graph": ClaimGraph()})
        result = VerificationPunchlistGenerator().analyze(ctx)
        assert len(result["verification_punchlist"].entries) == 1


# ---------------------------------------------------------------------------
# Full 16-Analyzer Pipeline
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_all_sixteen_analyzers_registered(self):
        from outputlens.orchestration.engine import get_default_registry
        from outputlens.analyzers import register_all
        registry = get_default_registry()
        register_all(registry)
        ids = registry.analyzer_ids
        expected = {f"a{i}" for i in [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]}
        assert ids == expected, f"Missing: {expected - ids}, Extra: {ids - expected}"
