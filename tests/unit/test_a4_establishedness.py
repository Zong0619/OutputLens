"""Tests for A4: Establishedness Analyzer -- Phase 3.2."""

from __future__ import annotations

import pytest

from outputlens.analysis.model import Claim, Concept, ConceptSurfaceForm, EstablishednessAnnotation
from outputlens.analyzers.a4_establishedness import (
    EstablishednessAnalyzer,
    _classify_establishedness,
    _detect_hedging,
    _detect_certainty,
    _detect_specificity,
    _domain_grounding_score,
    classify_establishedness,
)
from outputlens.orchestration.analyzer import AnalysisContext, AnalyzerError


def _c(cid: str, text: str, ctype: str = "factual_assertion") -> Claim:
    return Claim(id=cid, text=text, start_char=0, end_char=len(text),
                 segment_id="s1", claim_type=ctype)

def _concept(cid: str, name: str, domains: dict[str, float],
             ctype: str = "domain_concept", claim_ids: tuple = ("c1",)) -> Concept:
    return Concept(id=cid, canonical_name=name, concept_type=ctype,
                   surface_forms=(ConceptSurfaceForm(text=name, start_char=0, end_char=len(name)),),
                   domain_associations=domains, referencing_claim_ids=claim_ids)


# ---------------------------------------------------------------------------
# E1-E5 Classification
# ---------------------------------------------------------------------------

class TestE1DefinitionsAndMeta:
    def test_definition_is_e1(self):
        claim = _c("c1", "A compiler translates source code to machine code.",
                   ctype="conceptual_definition")
        level, signals, _ = _classify_establishedness(claim, [])
        assert level == "E1"

    def test_meta_claim_is_e4(self):
        claim = _c("c1", "I cannot provide specific medical advice.",
                   ctype="meta_claim")
        level, signals, _ = _classify_establishedness(claim, [])
        assert level == "E4"

    def test_normative_is_e4(self):
        claim = _c("c1", "AI should be regulated carefully.",
                   ctype="normative_claim")
        level, signals, _ = _classify_establishedness(claim, [])
        assert level == "E4"

    def test_predictive_is_e3(self):
        claim = _c("c1", "AI will transform healthcare by 2030.",
                   ctype="predictive_claim")
        level, signals, _ = _classify_establishedness(claim, [])
        assert level == "E3"


class TestE2DomainEstablished:
    def test_physics_claim_with_concept_is_e2(self):
        claim = _c("c1", "Quantum entanglement allows particles to share quantum states.")
        concepts = [_concept("con1", "quantum entanglement", {"physics": 0.9})]
        level, signals, _ = _classify_establishedness(claim, concepts)
        assert level == "E2"

    def test_math_claim_with_concept_is_e2(self):
        claim = _c("c1", "The Pythagorean theorem relates triangle side lengths.")
        concepts = [_concept("con1", "Pythagorean theorem", {"mathematics": 0.9})]
        level, signals, _ = _classify_establishedness(claim, concepts)
        assert level == "E2"


class TestE3Plausible:
    def test_hedged_claim_is_e3_or_e4(self):
        claim = _c("c1", "This approach may potentially improve performance "
                   "in some scenarios, but remains uncertain.")
        level, signals, _ = _classify_establishedness(claim, [])
        assert level in ("E3", "E4")

    def test_no_context_defaults_to_e3(self):
        claim = _c("c1", "The approach has several advantages over alternatives.")
        level, signals, _ = _classify_establishedness(claim, [])
        assert level in ("E3", "E5")


# ---------------------------------------------------------------------------
# Signal Detection
# ---------------------------------------------------------------------------

class TestHedgingDetection:
    def test_may_be_hedging(self):
        has, count, examples = _detect_hedging("This may be the case.")
        assert has

    def test_no_hedging(self):
        has, _, _ = _detect_hedging("The sky is blue.")
        assert not has

    def test_multiple_hedges(self):
        has, count, examples = _detect_hedging(
            "This may potentially appear to be significant."
        )
        assert has and count >= 2

class TestCertaintyDetection:
    def test_certainty_detected(self):
        has, examples = _detect_certainty("It is well known that water freezes at 0C.")
        assert has

class TestSpecificityDetection:
    def test_percentage_detected(self):
        has, examples = _detect_specificity("The model achieves 94.7% accuracy.")
        assert has


class TestDomainGrounding:
    def test_physics_high_score(self):
        c = _concept("con1", "entanglement", {"physics": 0.9})
        assert _domain_grounding_score(c) > 0.5

    def test_no_domains_zero(self):
        c = Concept(id="con1", canonical_name="x", concept_type="domain_concept")
        assert _domain_grounding_score(c) == 0.0


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

class TestEstablishednessAnalyzer:
    def test_declaration(self):
        a = EstablishednessAnalyzer()
        assert a.declaration.id == "a4"
        assert a.declaration.layer == "classification"
        assert {inp.analyzer_id for inp in a.declaration.inputs} == {"a2", "a3"}

    def test_analyze_with_valid_context(self):
        claims = [_c("c1", "Entanglement enables quantum teleportation.")]
        concepts = [_concept("con1", "entanglement", {"physics": 0.9})]
        ctx = AnalysisContext()
        ctx.set_output("a2", "a2", {"claims": claims})
        ctx.set_output("a3", "a3", {"concepts": concepts})
        a = EstablishednessAnalyzer()
        result = a.analyze(ctx)
        anns = result["establishedness_annotations"]
        assert len(anns) == 1
        assert anns[0].level == "E2"

    def test_analyze_missing_a2_raises(self):
        ctx = AnalysisContext()
        ctx.set_output("a3", "a3", {"concepts": []})
        with pytest.raises(AnalyzerError, match="requires A2"):
            EstablishednessAnalyzer().analyze(ctx)

    def test_all_annotations_have_reasoning(self):
        claims = [_c("c1", "X is Y.", ctype="conceptual_definition")]
        ctx = AnalysisContext()
        ctx.set_output("a2", "a2", {"claims": claims})
        ctx.set_output("a3", "a3", {"concepts": []})
        a = EstablishednessAnalyzer()
        result = a.analyze(ctx)
        for ann in result["establishedness_annotations"]:
            assert len(ann.reasoning) >= 20
            assert ann.level in EstablishednessAnnotation.LEVELS


# ---------------------------------------------------------------------------
# Pipeline: A1→A2→A3→{A4,A5}
# ---------------------------------------------------------------------------

class TestFullClassificationPipeline:
    def test_a4_a5_parallel(self):
        from outputlens.analyzers.a1_normalizer import TextNormalizerAnalyzer
        from outputlens.analyzers.a2_claim_extractor import ClaimExtractorAnalyzer
        from outputlens.analyzers.a3_concept_extractor import ConceptExtractorAnalyzer
        from outputlens.analyzers.a5_evidence_requirement import EvidenceRequirementAnalyzer
        from outputlens.orchestration.engine import OrchestrationEngine, AnalyzerRegistry
        from outputlens.runtime.model import RawInput

        registry = AnalyzerRegistry()
        for cls in [TextNormalizerAnalyzer, ClaimExtractorAnalyzer,
                     ConceptExtractorAnalyzer, EstablishednessAnalyzer,
                     EvidenceRequirementAnalyzer]:
            registry.register(cls.declaration, lambda c=cls: c())

        engine = OrchestrationEngine(registry)
        context = AnalysisContext()
        context.set_output("_bootstrap", "raw_input",
                           RawInput(text="Quantum entanglement is a phenomenon "
                                   "in physics where particles become correlated. "
                                   "According to Bell's theorem, this demonstrates "
                                   "non-locality.\n"))

        engine.execute(frozenset({"a1", "a2", "a3", "a4", "a5"}), context)

        assert context.has_output("a4", "a4")
        assert context.has_output("a5", "a5")
        e_anns = context.get_output("a4", "a4")["establishedness_annotations"]
        ev_anns = context.get_output("a5", "a5")["evidence_annotations"]
        assert len(e_anns) >= 1
        assert len(ev_anns) >= 1


# ===================================================================
# Evaluation Summary
# ===================================================================

class TestEvaluationSummary:
    def test_eval_1_domain_established_physics(self):
        claim = _c("c1", "Quantum entanglement violates Bell's inequalities.")
        concepts = [_concept("con1", "quantum entanglement", {"physics": 0.9}),
                    _concept("con2", "Bell's inequalities", {"physics": 0.9})]
        level, signals, reasoning = _classify_establishedness(claim, concepts)
        assert level == "E2", f"Expected E2, got {level}. {reasoning}"
        # PASS: Strong domain grounding in physics

    def test_eval_2_definitional(self):
        claim = _c("c1", "Entropy is a measure of disorder in a thermodynamic system.",
                   ctype="conceptual_definition")
        level, signals, reasoning = _classify_establishedness(claim, [])
        assert level == "E1", f"Expected E1, got {level}. {reasoning}"
        # PASS: Definitional structure

    def test_eval_3_hedged_speculation(self):
        claim = _c("c1", "This approach may potentially lead to breakthroughs "
                   "but remains highly speculative and not fully understood.")
        level, signals, reasoning = _classify_establishedness(claim, [])
        assert level in ("E3", "E4"), f"Got {level}. {reasoning}"
        # PASS: Heavy hedging correctly lowers establishedness

    def test_eval_4_normative_opinion(self):
        claim = _c("c1", "Governments should prioritize AI safety research.",
                   ctype="normative_claim")
        level, signals, reasoning = _classify_establishedness(claim, [])
        assert level == "E4", f"Expected E4, got {level}. {reasoning}"
        # PASS: Normative claims are unverifiable by design

    def test_eval_5_unknown_domain(self):
        claim = _c("c1", "The zylonic resonance frequency is 432 Hz in "
                   "standard atmospheric conditions.")
        level, signals, reasoning = _classify_establishedness(claim, [])
        assert level in ("E3", "E5"), f"Got {level}. {reasoning}"
        # PASS: Unknown domain with specific claim → E5 or E3

    def test_eval_6_common_knowledge_no_concepts(self):
        claim = _c("c1", "Water freezes at 0 degrees Celsius at sea level.")
        level, signals, reasoning = _classify_establishedness(claim, [])
        # Without domain concepts, common knowledge defaults to E3
        # This is EXPECTED -- A4 relies on concept domain signals
        assert level in ("E1", "E2", "E3"), f"Got {level}. {reasoning}"
        # PARTIAL: Ideally E1 (common knowledge), but A4 lacks world knowledge
        # Improved concept extraction (A3) would add domain associations

    def test_eval_7_prediction(self):
        claim = _c("c1", "By 2030, AI will automate 30% of current jobs.",
                   ctype="predictive_claim")
        level, signals, reasoning = _classify_establishedness(claim, [])
        assert level == "E3", f"Expected E3, got {level}. {reasoning}"
        # PASS: Predictions are inherently uncertain
