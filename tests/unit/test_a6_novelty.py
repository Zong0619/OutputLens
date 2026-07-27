"""Tests for A6: Novelty Analyzer -- Phase 4.1."""

from __future__ import annotations

import pytest

from outputlens.analysis.model import Claim, Concept, ConceptSurfaceForm, NoveltyAnnotation
from outputlens.analyzers.a6_novelty import (
    NoveltyAnalyzer,
    _classify_novelty,
    _detect_established_framing,
    _has_novel_construct,
    classify_novelty,
)
from outputlens.orchestration.analyzer import AnalysisContext, AnalyzerError


def _c(cid: str, text: str, ctype: str = "factual_assertion") -> Claim:
    return Claim(id=cid, text=text, start_char=0, end_char=len(text),
                 segment_id="s1", claim_type=ctype)


def _concept(cid: str, name: str, ctype: str = "domain_concept",
             claim_ids: tuple = ("c1",)) -> Concept:
    return Concept(id=cid, canonical_name=name, concept_type=ctype,
                   surface_forms=(ConceptSurfaceForm(text=name, start_char=0, end_char=len(name)),),
                   referencing_claim_ids=claim_ids)


# ---------------------------------------------------------------------------
# N1-N5 Classification
# ---------------------------------------------------------------------------

class TestN1Canonical:
    def test_definition_is_n1(self):
        claim = _c("c1", "Entropy is a measure of disorder.",
                   ctype="conceptual_definition")
        level, _, _ = _classify_novelty(claim, [])
        assert level == "N1"

    def test_established_framing_is_n1(self):
        claim = _c("c1", "This is a well known phenomenon in standard theory.")
        level, _, _ = _classify_novelty(claim, [])
        assert level == "N1"

    def test_methodological_is_n1(self):
        claim = _c("c1", "The standard approach uses gradient descent.",
                   ctype="methodological_claim")
        level, _, _ = _classify_novelty(claim, [])
        assert level == "N1"


class TestN3PotentiallyNovel:
    def test_predictive_is_n3(self):
        claim = _c("c1", "AI will transform healthcare by 2030.",
                   ctype="predictive_claim")
        level, _, _ = _classify_novelty(claim, [])
        assert level == "N3"

    def test_novel_construct_is_n3(self):
        claim = _c("c1", "The zylonic resonance framework enables new computations.")
        concepts = [_concept("con1", "zylonic resonance framework", "novel_construct")]
        level, _, _ = _classify_novelty(claim, concepts)
        assert level == "N3"

    def test_specific_without_framing_is_n3(self):
        claim = _c("c1", "The model achieves 97.3% accuracy on this specific task.")
        level, _, _ = _classify_novelty(claim, [])
        assert level == "N3"


class TestN4ApparentlyOriginal:
    def test_novel_construct_plus_specifics_is_n4(self):
        claim = _c("c1", "The zylonic framework achieves 432 Hz resonance at 20C.")
        concepts = [_concept("con1", "zylonic framework", "novel_construct")]
        level, signals, _ = _classify_novelty(claim, concepts)
        assert level == "N4"


class TestN5Uncertain:
    def test_default_is_n5(self):
        claim = _c("c1", "The approach has some advantages.")
        level, _, _ = _classify_novelty(claim, [])
        assert level == "N5"

    def test_meta_claim_is_n5(self):
        claim = _c("c1", "I cannot provide specific advice.",
                   ctype="meta_claim")
        level, _, _ = _classify_novelty(claim, [])
        assert level == "N5"


# ---------------------------------------------------------------------------
# Signal Detection
# ---------------------------------------------------------------------------

class TestNovelConstructDetection:
    def test_has_novel_construct(self):
        claim = _c("c1", "The zylonic framework is new.")
        concepts = [_concept("con1", "zylonic framework", "novel_construct")]
        assert _has_novel_construct(concepts, claim)

    def test_no_novel_construct(self):
        claim = _c("c1", "Quantum entanglement is well studied.")
        concepts = [_concept("con1", "quantum entanglement", "domain_concept")]
        assert not _has_novel_construct(concepts, claim)


class TestEstablishedFraming:
    def test_detected(self):
        assert _detect_established_framing("It is widely known that X is Y.")

    def test_not_detected(self):
        assert not _detect_established_framing("The sky appears blue today.")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

class TestNoveltyAnalyzer:
    def test_declaration(self):
        a = NoveltyAnalyzer()
        assert a.declaration.id == "a6"
        assert a.declaration.layer == "classification"
        assert {inp.analyzer_id for inp in a.declaration.inputs} == {"a2", "a3"}

    def test_analyze(self):
        claims = [_c("c1", "X is a standard Y.", ctype="conceptual_definition")]
        ctx = AnalysisContext()
        ctx.set_output("a2", "a2", {"claims": claims})
        ctx.set_output("a3", "a3", {"concepts": []})
        result = NoveltyAnalyzer().analyze(ctx)
        anns = result["novelty_annotations"]
        assert len(anns) == 1
        assert anns[0].level == "N1"

    def test_missing_a2_raises(self):
        ctx = AnalysisContext()
        ctx.set_output("a3", "a3", {"concepts": []})
        with pytest.raises(AnalyzerError):
            NoveltyAnalyzer().analyze(ctx)

    def test_all_have_reasoning(self):
        claims = [_c("c1", "X.")]
        ctx = AnalysisContext()
        ctx.set_output("a2", "a2", {"claims": claims})
        ctx.set_output("a3", "a3", {"concepts": []})
        result = NoveltyAnalyzer().analyze(ctx)
        for ann in result["novelty_annotations"]:
            assert len(ann.reasoning) >= 20
            assert ann.level in NoveltyAnnotation.LEVELS


# ===================================================================
# Evaluation Summary
# ===================================================================

class TestEvaluationSummary:
    def test_eval_1_definitional_canonical(self):
        claim = _c("c1", "A compiler translates source code to machine code.",
                   ctype="conceptual_definition")
        level, signals, reasoning = _classify_novelty(claim, [])
        assert level == "N1", f"Expected N1, got {level}. {reasoning}"
        # PASS: Definitions present canonical knowledge

    def test_eval_2_established_framing(self):
        claim = _c("c1", "It is well known that exercise improves health outcomes.")
        level, _, reasoning = _classify_novelty(claim, [])
        assert level == "N1", f"Expected N1, got {level}. {reasoning}"
        # PASS: Established framing correctly detected

    def test_eval_3_novel_construct_heuristic(self):
        claim = _c("c1", "The plasmoid resonance theory explains quantum decoherence.")
        concepts = [_concept("con1", "plasmoid resonance theory", "novel_construct")]
        level, signals, reasoning = _classify_novelty(claim, concepts)
        assert level == "N3", f"Expected N3, got {level}. {reasoning}"
        # PASS: Novel construct → N3. Reasoning correctly notes this is heuristic.

    def test_eval_4_novel_with_specifics(self):
        claim = _c("c1", "The zylonic framework achieves 99.7% accuracy at 20C.")
        concepts = [_concept("con1", "zylonic framework", "novel_construct")]
        level, _, reasoning = _classify_novelty(claim, concepts)
        assert level == "N4", f"Expected N4, got {level}. {reasoning}"
        # PASS: Novel construct + specifics → N4

    def test_eval_5_prediction_novelty(self):
        claim = _c("c1", "By 2030, quantum computing will revolutionize drug discovery.",
                   ctype="predictive_claim")
        level, _, reasoning = _classify_novelty(claim, [])
        assert level == "N3", f"Expected N3, got {level}. {reasoning}"
        # PASS: Predictions go beyond established knowledge

    def test_eval_6_common_knowledge_defaults_n5(self):
        claim = _c("c1", "The sky is blue during the day.")
        level, _, reasoning = _classify_novelty(claim, [])
        assert level == "N5", f"Got {level}. {reasoning}"
        # PARTIAL: Ideally N1 (canonical), but A6 lacks world knowledge.
        # Correct per knowledge boundary -- no external knowledge used.
        # The reasoning correctly notes "insufficient signals."

    def test_eval_7_knowledge_boundary_respected(self):
        """Verify A6 reasoning never claims objective novelty."""
        claim = _c("c1", "The zylonic framework is a new approach to computing.")
        concepts = [_concept("con1", "zylonic framework", "novel_construct")]
        level, _, reasoning = _classify_novelty(claim, concepts)
        # Reasoning must contain boundary language
        boundary_terms = ["not external", "heuristic", "based on", "text pattern",
                          "concept typing", "not a verified"]
        assert any(term in reasoning.lower() for term in boundary_terms), (
            f"Reasoning should acknowledge knowledge boundary. Got: {reasoning}"
        )
        # PASS: Reasoning explicitly acknowledges the heuristic limitation
