"""Tests for A5: Evidence Requirement Analyzer -- Phase 3.1."""

from __future__ import annotations

import pytest

from outputlens.analysis.model import Claim, EvidenceAnnotation
from outputlens.analyzers.a5_evidence_requirement import (
    EvidenceRequirementAnalyzer,
    _classify_evidence,
    _detect_r1_signals,
    _detect_r2_signals,
    _detect_r3_signals,
    _detect_r4_signals,
    classify_evidence,
)
from outputlens.orchestration.analyzer import AnalysisContext, AnalyzerError


def _c(cid: str, text: str, ctype: str = "factual_assertion") -> Claim:
    return Claim(id=cid, text=text, start_char=0, end_char=len(text),
                 segment_id="s1", claim_type=ctype)


# ---------------------------------------------------------------------------
# R2: Evidence Provided
# ---------------------------------------------------------------------------


class TestR2EvidenceProvided:
    def test_according_to(self):
        claim = _c("c1", "According to Smith et al. (2023), the model achieves 95% accuracy.")
        level, signals, reasoning = _classify_evidence(claim)
        assert level == "R2"
        assert "explicit_citation" in signals

    def test_et_al_citation(self):
        claim = _c("c1", "Brown et al. (2022) demonstrated that the approach is effective.")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R2"

    def test_published_in(self):
        claim = _c("c1", "The results were published in Nature last year.")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R2"

    def test_researchers_at_institution(self):
        claim = _c("c1", "Researchers at Stanford University found similar results "
                   "and published the findings in Science.")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R2"

    def test_bracket_citation(self):
        claim = _c("c1", "The method outperforms baselines [1, 2, 3].")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R2"

    def test_parenthetical_citation(self):
        claim = _c("c1", "The technique was first described (Johnson 2021).")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R2"


# ---------------------------------------------------------------------------
# R3: Evidence Expected (Gesture)
# ---------------------------------------------------------------------------


class TestR3EvidenceGesture:
    def test_studies_show(self):
        claim = _c("c1", "Studies show that this approach is effective.")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R3"
        assert "evidence_gesture" in signals

    def test_research_indicates(self):
        claim = _c("c1", "Research indicates that sleep improves memory.")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R3"

    def test_it_is_known_that(self):
        claim = _c("c1", "It is known that exercise reduces stress.")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R3"

    def test_evidence_suggests(self):
        claim = _c("c1", "Evidence suggests that the treatment is effective.")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R3"

    def test_experts_agree(self):
        claim = _c("c1", "Experts agree that climate change is accelerating.")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R3"

    def test_gesture_with_specific_stat_escalates_to_r4(self):
        claim = _c("c1", "Studies show that 73% of patients recover fully.")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R4"
        assert "evidence_gesture" in signals
        assert "specific_statistic" in signals


# ---------------------------------------------------------------------------
# R1: Self-Evident / Definitional
# ---------------------------------------------------------------------------


class TestR1SelfEvident:
    def test_is_a_definition(self):
        claim = _c("c1", "A compiler is a program that translates source code.",
                   ctype="conceptual_definition")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R1"

    def test_refers_to(self):
        claim = _c("c1", "Entropy refers to the measure of disorder in a system.")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R1"

    def test_meta_claim(self):
        claim = _c("c1", "I cannot provide medical advice.", ctype="meta_claim")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R1"

    def test_normative_claim_r1(self):
        claim = _c("c1", "Governments should regulate AI development.",
                   ctype="normative_claim")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R1"
        assert "normative_or_subjective" in signals


# ---------------------------------------------------------------------------
# R4: Evidence Essential (Missing)
# ---------------------------------------------------------------------------


class TestR4EvidenceMissing:
    def test_statistic_without_source(self):
        claim = _c("c1", "The model achieves 94.7% accuracy on the benchmark.")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R4"
        assert "specific_statistic" in signals

    def test_causal_claim_without_evidence(self):
        claim = _c("c1", "Rising CO2 levels cause ocean acidification.")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R4"
        assert "causal_claim" in signals

    def test_attribution_without_reference(self):
        claim = _c("c1", "The technique was first developed by researchers at MIT.")
        level, signals, _ = _classify_evidence(claim)
        assert level == "R4"

    def test_default_factual_no_evidence(self):
        claim = _c("c1", "The Earth revolves around the Sun.")
        level, signals, _ = _classify_evidence(claim)
        # Common knowledge but no evidence provided → R4 by default
        assert level in ("R1", "R4")

    def test_reasoning_is_meaningful(self):
        claim = _c("c1", "The algorithm improves performance by 30%.")
        level, signals, reasoning = _classify_evidence(claim)
        assert len(reasoning) >= 20
        # Reasoning should mention what was detected, not just the level
        assert "R4" not in reasoning or "specific" in reasoning.lower()


# ---------------------------------------------------------------------------
# Signal Detection Unit Tests
# ---------------------------------------------------------------------------


class TestSignalDetection:
    def test_detect_r2_citation(self):
        assert len(_detect_r2_signals("According to Smith (2023), X is Y.")) >= 1

    def test_detect_r2_none(self):
        assert _detect_r2_signals("The sky is blue.") == []

    def test_detect_r3_gesture(self):
        assert len(_detect_r3_signals("Studies show that X is Y.")) >= 1

    def test_detect_r3_none(self):
        assert _detect_r3_signals("The sky is blue.") == []

    def test_detect_r1_definitional(self):
        assert len(_detect_r1_signals("X is a type of Y.")) >= 1

    def test_detect_r4_statistic(self):
        assert len(_detect_r4_signals("The model achieves 95% accuracy.")) >= 1


# ---------------------------------------------------------------------------
# Orchestration Integration
# ---------------------------------------------------------------------------


class TestEvidenceRequirementAnalyzer:
    def test_declaration(self):
        analyzer = EvidenceRequirementAnalyzer()
        decl = analyzer.declaration
        assert decl.id == "a5"
        assert decl.layer == "classification"
        assert len(decl.inputs) == 1
        assert decl.inputs[0].analyzer_id == "a2"

    def test_analyze_with_valid_context(self):
        claims = [_c("c1", "According to Smith (2023), the model works.")]
        ctx = AnalysisContext()
        ctx.set_output("a2", "a2", {"claims": claims})

        analyzer = EvidenceRequirementAnalyzer()
        result = analyzer.analyze(ctx)

        assert "evidence_annotations" in result
        anns = result["evidence_annotations"]
        assert len(anns) == 1
        assert anns[0].level == "R2"

    def test_analyze_missing_a2_raises(self):
        ctx = AnalysisContext()
        analyzer = EvidenceRequirementAnalyzer()
        with pytest.raises(AnalyzerError, match="requires A2"):
            analyzer.analyze(ctx)

    def test_analyze_empty_claims(self):
        ctx = AnalysisContext()
        ctx.set_output("a2", "a2", {"claims": []})
        analyzer = EvidenceRequirementAnalyzer()
        result = analyzer.analyze(ctx)
        assert result["evidence_annotations"] == []

    def test_every_claim_gets_annotation(self):
        claims = [
            _c("c1", "Studies show X."),
            _c("c2", "Y is a Z.", ctype="conceptual_definition"),
            _c("c3", "The rate is 73%."),
        ]
        ctx = AnalysisContext()
        ctx.set_output("a2", "a2", {"claims": claims})
        analyzer = EvidenceRequirementAnalyzer()
        result = analyzer.analyze(ctx)
        assert len(result["evidence_annotations"]) == 3

    def test_all_annotations_have_reasoning(self):
        claims = [_c("c1", "Some claim without evidence.")]
        ctx = AnalysisContext()
        ctx.set_output("a2", "a2", {"claims": claims})
        analyzer = EvidenceRequirementAnalyzer()
        result = analyzer.analyze(ctx)
        for ann in result["evidence_annotations"]:
            assert len(ann.reasoning) >= 20
            assert isinstance(ann.level, str)
            assert ann.level in EvidenceAnnotation.LEVELS


# ---------------------------------------------------------------------------
# Pipeline Integration
# ---------------------------------------------------------------------------


class TestA1A2A3A5Pipeline:
    def test_full_classification_pipeline(self):
        from outputlens.analyzers.a1_normalizer import TextNormalizerAnalyzer
        from outputlens.analyzers.a2_claim_extractor import ClaimExtractorAnalyzer
        from outputlens.analyzers.a3_concept_extractor import ConceptExtractorAnalyzer
        from outputlens.orchestration.engine import OrchestrationEngine, AnalyzerRegistry
        from outputlens.runtime.model import RawInput

        registry = AnalyzerRegistry()
        registry.register(TextNormalizerAnalyzer.declaration, lambda: TextNormalizerAnalyzer())
        registry.register(ClaimExtractorAnalyzer.declaration, lambda: ClaimExtractorAnalyzer())
        registry.register(ConceptExtractorAnalyzer.declaration, lambda: ConceptExtractorAnalyzer())
        registry.register(EvidenceRequirementAnalyzer.declaration,
                          lambda: EvidenceRequirementAnalyzer())

        engine = OrchestrationEngine(registry)
        context = AnalysisContext()
        context.set_output("_bootstrap", "raw_input",
                           RawInput(text="Studies show that AI is improving. "
                                   "According to Smith (2023), accuracy reached 95%.\n"))

        engine.execute(frozenset({"a1", "a2", "a3", "a5"}), context)

        assert context.has_output("a5", "a5")
        annotations = context.get_output("a5", "a5")["evidence_annotations"]
        assert len(annotations) >= 2
        levels = {a.level for a in annotations}
        assert "R2" in levels or "R3" in levels


# ===================================================================
# Evaluation Summary
# ===================================================================


class TestEvaluationSummary:
    """Representative examples evaluating classification quality."""

    def test_eval_1_explicit_citation(self):
        """Claim with explicit citation → R2."""
        claim = _c("c1", "According to a 2023 study published in Nature, "
                   "the new treatment reduced symptoms by 45%.")
        level, signals, reasoning = _classify_evidence(claim)
        assert level == "R2", f"Expected R2, got {level}. Reasoning: {reasoning}"
        # PASS: explicit citation correctly detected

    def test_eval_2_gesture_without_source(self):
        """Gesture at evidence without specific source → R3."""
        claim = _c("c1", "Research shows that regular exercise improves "
                   "cardiovascular health significantly.")
        level, signals, reasoning = _classify_evidence(claim)
        assert level == "R3", f"Expected R3, got {level}. Reasoning: {reasoning}"
        # PASS: evidence gesture detected, no citation present

    def test_eval_3_specific_statistic_no_source(self):
        """Specific statistic without source → R4."""
        claim = _c("c1", "The model achieves 97.3% accuracy on ImageNet "
                   "and processes 500 images per second.")
        level, signals, reasoning = _classify_evidence(claim)
        assert level == "R4", f"Expected R4, got {level}. Reasoning: {reasoning}"
        # PASS: specific statistics detected without evidence

    def test_eval_4_definitional_structure(self):
        """Definitional claim → R1."""
        claim = _c("c1", "A transformer is a neural network architecture "
                   "that uses self-attention mechanisms.",
                   ctype="conceptual_definition")
        level, signals, reasoning = _classify_evidence(claim)
        assert level == "R1", f"Expected R1, got {level}. Reasoning: {reasoning}"
        # PASS: definitional structure correctly detected

    def test_eval_5_gesture_with_specific_stats(self):
        """Gesture at evidence BUT with specific stats → R4 (escalated)."""
        claim = _c("c1", "Studies show that 82% of users prefer the new "
                   "interface, and satisfaction improved by 35%.")
        level, signals, reasoning = _classify_evidence(claim)
        assert level == "R4", f"Expected R4, got {level}. Reasoning: {reasoning}"
        # PASS: gesture + specific statistics correctly escalates to R4

    def test_eval_6_normative_opinion(self):
        """Normative claim → R1 (unverifiable by design)."""
        claim = _c("c1", "Governments should invest more in renewable energy "
                   "to combat climate change.",
                   ctype="normative_claim")
        level, signals, reasoning = _classify_evidence(claim)
        assert level == "R1", f"Expected R1, got {level}. Reasoning: {reasoning}"
        # PASS: normative claim correctly classified as unverifiable

    def test_eval_7_common_knowledge_no_citation(self):
        """Common knowledge without citation → R4 by default (PARTIAL)."""
        claim = _c("c1", "Water freezes at 0 degrees Celsius at sea level.")
        level, signals, reasoning = _classify_evidence(claim)
        # Without A4's establishedness context, A5 classifies as R4
        # This is a known limitation -- A4 will enrich this classification
        assert level in ("R1", "R4"), f"Got {level}. Reasoning: {reasoning}"
        # PARTIAL: correct by A5 rules (no evidence detected) but ideally R1
        # for truly common knowledge. A4/A9 integration will address this.
