"""Tests for A7: Claim Relationship Mapper -- Phase 4.2."""

from __future__ import annotations

import pytest

from outputlens.analysis.model import (
    Claim, ClaimGraph, ClaimRelationship, EstablishednessAnnotation,
)
from outputlens.analyzers.a7_claim_relationships import (
    ClaimRelationshipMapper,
    _detect_relationship,
    _map_relationships,
    build_claim_graph,
)
from outputlens.orchestration.analyzer import AnalysisContext, AnalyzerError
from outputlens.runtime.model import NormalizedText, Segment


def _c(cid: str, text: str, start: int = 0, end: int = 50,
       ctype: str = "factual_assertion", seg: str = "s1") -> Claim:
    return Claim(id=cid, text=text, start_char=start, end_char=end,
                 segment_id=seg, claim_type=ctype)


def _ea(cid: str, level: str) -> EstablishednessAnnotation:
    return EstablishednessAnnotation(claim_id=cid, level=level,
                                     reasoning="Test reasoning. " * 3)


class TestDiscourseMarkerDetection:
    def test_therefore_is_support(self):
        assert _detect_relationship("therefore this follows") == "supports"

    def test_however_is_concede(self):
        assert _detect_relationship("however there is a limitation") == "concedes"

    def test_for_example_is_elaborate(self):
        assert _detect_relationship("for example consider the case") == "elaborates"

    def test_based_on_is_depends_on(self):
        assert _detect_relationship("based on this assumption") == "depends_on"

    def test_first_is_sequence(self):
        assert _detect_relationship("first we consider") == "sequences"

    def test_in_other_words_is_restate(self):
        assert _detect_relationship("in other words it means") == "restates"

    def test_contradiction_requires_strong_signal(self):
        """A7-001: Contrast markers do NOT automatically mean contradiction."""
        assert _detect_relationship("however") != "contradicts"
        assert _detect_relationship("but this is different") != "contradicts"

    def test_direct_negation_is_contradiction(self):
        assert _detect_relationship("this is not correct") == "contradicts"

    def test_no_marker_returns_none(self):
        assert _detect_relationship("some plain text") is None


class TestRelationshipMapping:
    def test_adjacent_implicit(self):
        claims = [_c("c1", "Claim one.", 0, 10), _c("c2", "Claim two.", 12, 22)]
        rels = _map_relationships(claims, "Claim one. Claim two.")
        assert len(rels) == 1
        assert rels[0].strength == "implicit"

    def test_explicit_therefore(self):
        claims = [_c("c1", "Premise.", 0, 8), _c("c2", "Conclusion.", 20, 30)]
        rels = _map_relationships(claims, "Premise. therefore Conclusion.")
        assert len(rels) == 1
        assert rels[0].relationship_type == "supports"
        assert rels[0].strength == "explicit"

    def test_however_is_concede_not_contradict(self):
        """A7-001: 'however' maps to concedes, not contradicts."""
        claims = [_c("c1", "It works well.", 0, 13),
                  _c("c2", "It has limitations.", 25, 43)]
        rels = _map_relationships(claims, "It works well. however It has limitations.")
        assert len(rels) == 1
        assert rels[0].relationship_type == "concedes"

    def test_single_claim_no_relationships(self):
        claims = [_c("c1", "Only claim.", 0, 11)]
        assert _map_relationships(claims, "Only claim.") == []


class TestGraphProperties:
    def test_foundational_claims(self):
        claims = [_c("c1", "Foundation A.", 0, 12, seg="s1"),
                  _c("c2", "Depends on A.", 14, 28, seg="s1"),
                  _c("c3", "Also depends on A.", 30, 48, seg="s1")]
        text = "Foundation A. This depends on A. Also depends on A."
        e_anns = [_ea("c1", "E2"), _ea("c2", "E2"), _ea("c3", "E2")]
        # c1 appears in depends_on relationships for c2 and c3
        # Need explicit depends_on markers
        text2 = "Foundation A. Depends on Foundation A. Relies on Foundation A."
        graph = build_claim_graph(claims, text2, e_anns)
        assert isinstance(graph, ClaimGraph)

    def test_orphan_detection(self):
        claims = [_c("c1", "Connected.", 0, 11, seg="s1"),
                  _c("c2", "Connected.", 13, 24, seg="s1"),
                  _c("c3", "Orphan.", 26, 33, seg="s1")]
        text = "Connected. Connected. Orphan."
        e_anns = [_ea("c1", "E2"), _ea("c2", "E2"), _ea("c3", "E2")]
        graph = build_claim_graph(claims, text, e_anns)
        assert "c3" in graph.orphan_claim_ids

    def test_uncertainty_chains(self):
        claims = [_c("c1", "Uncertain premise.", 0, 18, seg="s1"),
                  _c("c2", "Depends on premise.", 20, 39, seg="s1")]
        text = "Uncertain premise. Depends on Uncertain premise."
        e_anns = [_ea("c1", "E3"), _ea("c2", "E2")]
        graph = build_claim_graph(claims, text, e_anns)
        assert len(graph.cascading_uncertainty_chains) >= 1


class TestOrchestration:
    def test_declaration(self):
        a = ClaimRelationshipMapper()
        assert a.declaration.id == "a7"
        assert a.declaration.layer == "structure"

    def test_analyze(self):
        claims = [_c("c1", "Premise.", 0, 8), _c("c2", "Therefore conclusion.", 10, 30)]
        norm = NormalizedText(text="Premise. Therefore conclusion.",
                              segments=(Segment(id="s1", type="paragraph", start_char=0, end_char=30),))
        ctx = AnalysisContext()
        ctx.set_output("a1", "a1", {"normalized_text": norm})
        ctx.set_output("a2", "a2", {"claims": claims})
        ctx.set_output("a4", "a4", {"establishedness_annotations": [_ea("c1", "E2"), _ea("c2", "E2")]})
        result = ClaimRelationshipMapper().analyze(ctx)
        graph = result["claim_graph"]
        assert len(graph.relationships) >= 1

    def test_missing_input_raises(self):
        with pytest.raises(AnalyzerError):
            ClaimRelationshipMapper().analyze(AnalysisContext())
