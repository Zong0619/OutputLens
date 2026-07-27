"""Tests for Analysis Model objects — validation, immutability, and serialization."""

import json

import pytest

from outputlens.analysis.document import AnalysisDocument
from outputlens.analysis.model import (
    Claim,
    ClaimGraph,
    ClaimRelationship,
    CoherenceReport,
    Concept,
    ConceptGraph,
    ConceptRelationship,
    ConfidenceMarker,
    EstablishednessAnnotation,
    EvidenceAnnotation,
    EvidenceGapReport,
    NoveltyAnnotation,
    NoveltyIndex,
    OverconfidenceReport,
    PunchlistEntry,
    ResponseNarrative,
    StructuralIntegrityReport,
    TrustProfile,
    VerificationPunchlist,
)
from outputlens.runtime.model import (
    Metadata,
    NormalizedText,
    PositionIndex,
    PositionMapping,
    RawInput,
    Segment,
)


# ---------------------------------------------------------------------------
# Foundation Objects
# ---------------------------------------------------------------------------


class TestConfidenceMarker:
    def test_valid_hedge(self):
        cm = ConfidenceMarker(
            id="cm1", type="hedge", start_char=0, end_char=3, claim_id="c1",
            expression="may", intensity="weak"
        )
        assert cm.type == "hedge"

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            ConfidenceMarker(id="cm1", type="invalid", start_char=0, end_char=3, claim_id="c1")


class TestClaim:
    def test_valid_claim(self):
        c = Claim(
            id="c1", text="Water freezes at 0 degrees Celsius.",
            start_char=0, end_char=35, segment_id="seg_1",
            claim_type="factual_assertion",
        )
        assert c.id == "c1"
        assert c.claim_type == "factual_assertion"

    def test_empty_text_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            Claim(id="c1", text="  ", start_char=0, end_char=1, segment_id="s1",
                  claim_type="factual_assertion")

    def test_invalid_claim_type_raises(self):
        with pytest.raises(ValueError, match="claim_type must be one of"):
            Claim(id="c1", text="test", start_char=0, end_char=4, segment_id="s1",
                  claim_type="invalid_type")

    def test_all_claim_types_valid(self):
        for ct in Claim.CLAIM_TYPES:
            c = Claim(id="c1", text=f"Test {ct}", start_char=0, end_char=10,
                      segment_id="s1", claim_type=ct)
            assert c.claim_type == ct


class TestConcept:
    def test_valid_concept(self):
        c = Concept(id="con1", canonical_name="Quantum Entanglement",
                     concept_type="domain_concept")
        assert c.canonical_name == "Quantum Entanglement"

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            Concept(id="con1", canonical_name="test", concept_type="invalid")


# ---------------------------------------------------------------------------
# Classification Annotations
# ---------------------------------------------------------------------------


class TestAnnotations:
    def test_establishedness_requires_reasoning(self):
        with pytest.raises(ValueError, match="Reasoning must be at least 20"):
            EstablishednessAnnotation(claim_id="c1", level="E1", reasoning="Too short")

    def test_establishedness_valid(self):
        ann = EstablishednessAnnotation(
            claim_id="c1", level="E2",
            reasoning="This claim is standard textbook material in quantum mechanics."
        )
        assert ann.level == "E2"

    def test_invalid_establishedness_level_raises(self):
        with pytest.raises(ValueError):
            EstablishednessAnnotation(claim_id="c1", level="E10",
                                      reasoning="x" * 30)

    def test_evidence_annotation_valid(self):
        ann = EvidenceAnnotation(
            claim_id="c1", level="R4",
            reasoning="This statistical claim provides no source or citation."
        )
        assert ann.level == "R4"

    def test_novelty_annotation_valid(self):
        ann = NoveltyAnnotation(
            claim_id="c1", level="N3",
            reasoning="This claim proposes a connection not found in standard treatments."
        )
        assert ann.level == "N3"


# ---------------------------------------------------------------------------
# Structure Objects
# ---------------------------------------------------------------------------


class TestClaimRelationship:
    def test_valid_relationship(self):
        rel = ClaimRelationship(
            source_claim_id="c1", target_claim_id="c2",
            relationship_type="supports", strength="explicit",
        )
        assert rel.source_claim_id == "c1"

    def test_self_relationship_raises(self):
        with pytest.raises(ValueError, match="cannot have a relationship with itself"):
            ClaimRelationship(source_claim_id="c1", target_claim_id="c1",
                              relationship_type="supports")

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            ClaimRelationship(source_claim_id="c1", target_claim_id="c2",
                              relationship_type="invalid_type")


# ---------------------------------------------------------------------------
# Synthesis Objects
# ---------------------------------------------------------------------------


class TestTrustProfile:
    def test_valid_profile(self):
        tp = TrustProfile(established_pct=65.0, plausible_pct=25.0, needs_verification_pct=10.0)
        assert tp.established_pct == 65.0

    def test_percentages_must_sum_to_100(self):
        with pytest.raises(ValueError):
            TrustProfile(established_pct=50.0, plausible_pct=25.0, needs_verification_pct=10.0)


class TestPunchlistEntry:
    def test_valid_entry(self):
        entry = PunchlistEntry(
            rank=1, claim_id="c1", attention_trigger="no_evidence",
            structural_importance="structural", risk_if_wrong="Argument collapses",
            suggested_verification="Search for primary source",
        )
        assert entry.rank == 1

    def test_invalid_trigger_raises(self):
        with pytest.raises(ValueError):
            PunchlistEntry(
                rank=1, claim_id="c1", attention_trigger="invalid",
                structural_importance="structural", risk_if_wrong="x",
                suggested_verification="x",
            )


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


class TestImmutability:
    def test_claim_is_frozen(self):
        c = Claim(id="c1", text="test", start_char=0, end_char=4, segment_id="s1",
                  claim_type="factual_assertion")
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            c.text = "modified"  # type: ignore[misc]

    def test_trust_profile_is_frozen(self):
        tp = TrustProfile(established_pct=65.0, plausible_pct=25.0, needs_verification_pct=10.0)
        with pytest.raises(Exception):
            tp.established_pct = 70.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AnalysisDocument
# ---------------------------------------------------------------------------


class TestAnalysisDocument:
    def _make_doc(self) -> AnalysisDocument:
        """Create a minimal valid AnalysisDocument."""
        doc = AnalysisDocument()
        doc.metadata = Metadata.create(engine_version="0.1.0")
        doc.raw_input = RawInput(text="Test text.")
        norm_text = NormalizedText(text="Test text.\n")
        doc.normalized_text = norm_text
        doc.position_index = PositionIndex(mappings=())
        doc.set_claim(Claim(
            id="c1", text="Test claim.", start_char=0, end_char=11,
            segment_id="seg_1", claim_type="factual_assertion",
        ))
        return doc

    def test_incremental_construction(self):
        doc = self._make_doc()
        assert len(doc.claims) == 1
        assert not doc.is_finalized

    def test_finalization(self):
        doc = self._make_doc()
        doc.finalize()
        assert doc.is_finalized

    def test_mutation_after_finalization_raises(self):
        doc = self._make_doc()
        doc.finalize()
        with pytest.raises(RuntimeError, match="has been finalized"):
            doc.set_claim(Claim(
                id="c2", text="Another claim.", start_char=12, end_char=26,
                segment_id="seg_1", claim_type="factual_assertion",
            ))

    def test_validation_catches_missing_metadata(self):
        doc = AnalysisDocument()
        errors = doc.validate()
        assert any("metadata" in e for e in errors)

    def test_validation_catches_missing_claims(self):
        doc = AnalysisDocument()
        doc.metadata = Metadata.create(engine_version="0.1.0")
        errors = doc.validate()
        assert any("claim" in e for e in errors)

    def test_validation_catches_bad_references(self):
        doc = self._make_doc()
        doc.set_establishedness_annotations([
            EstablishednessAnnotation(
                claim_id="c_nonexistent", level="E1",
                reasoning="This is common knowledge in general science education."
            )
        ])
        errors = doc.validate()
        assert any("unknown claim" in e for e in errors)

    def test_valid_document_passes_validation(self):
        doc = self._make_doc()
        doc.set_establishedness_annotations([
            EstablishednessAnnotation(
                claim_id="c1", level="E1",
                reasoning="This is common knowledge in general science education."
            )
        ])
        errors = doc.validate()
        assert len(errors) == 0

    def test_to_dict_produces_valid_structure(self):
        doc = self._make_doc()
        doc.set_establishedness_annotations([
            EstablishednessAnnotation(
                claim_id="c1", level="E1",
                reasoning="This is common knowledge in general science education."
            )
        ])
        doc.set_trust_profile(TrustProfile(
            established_pct=100.0, plausible_pct=0.0, needs_verification_pct=0.0
        ))
        doc.finalize()

        result = doc.to_dict()
        assert result["schema_version"] == "1.0.0"
        assert "metadata" in result
        assert "runtime_objects" in result
        assert "analysis_objects" in result
        assert len(result["analysis_objects"]["claims"]) == 1

    def test_to_dict_json_serializable(self):
        doc = self._make_doc()
        doc.finalize()
        result = doc.to_dict()
        # Should serialize without errors
        json_str = json.dumps(result, indent=2, default=str)
        assert len(json_str) > 0

    def test_full_pipeline_document_roundtrip(self):
        """Build a complete AnalysisDocument, serialize, and verify structure."""
        doc = AnalysisDocument()
        doc.metadata = Metadata.create(engine_version="0.1.0",
                                        model_identifier="claude-opus-4-8")
        doc.raw_input = RawInput(text="AI is transforming society.")
        doc.normalized_text = NormalizedText(text="AI is transforming society.\n")
        doc.position_index = PositionIndex(mappings=(
            PositionMapping(normalized_start=0, normalized_end=1, raw_start=0, raw_end=1),
        ))

        # Foundation
        doc.set_claim(Claim(id="c1", text="AI is transforming society.",
                            start_char=0, end_char=27, segment_id="seg_1",
                            claim_type="factual_assertion"))

        # Classifications
        doc.set_establishedness_annotations([
            EstablishednessAnnotation(claim_id="c1", level="E3",
                                      reasoning="Broad claim about societal transformation "
                                                "that is plausible but lacks specifics.")
        ])
        doc.set_evidence_annotations([
            EvidenceAnnotation(claim_id="c1", level="R4",
                               reasoning="No specific evidence or examples provided.")
        ])
        doc.set_novelty_annotations([
            NoveltyAnnotation(claim_id="c1", level="N1",
                              reasoning="This is a very general, commonly stated observation.")
        ])

        # Synthesis
        doc.set_trust_profile(TrustProfile(
            established_pct=0.0, plausible_pct=100.0, needs_verification_pct=0.0
        ))
        doc.set_evidence_gap_report(EvidenceGapReport(
            gap_ratio=1.0, r3_count=0, r4_count=1
        ))
        doc.set_novelty_index(NoveltyIndex(novelty_proportion=0.0))
        doc.set_overconfidence_report(OverconfidenceReport(
            overconfident_claims=()
        ))
        doc.set_structural_integrity_report(StructuralIntegrityReport(
            foundation_health=1.0, contradiction_count=0, orphan_proportion=0.0
        ))
        doc.set_coherence_report(CoherenceReport(
            graph_connectivity=1.0, cluster_count=1
        ))
        doc.set_response_narrative(ResponseNarrative(
            narrative_text="This single-claim response makes a broad assertion "
                           "about AI transforming society. The claim is plausible "
                           "but presented without specific evidence. Readers should "
                           "seek concrete examples before relying on this as more "
                           "than a general observation."
        ))

        # Punchlist
        doc.set_verification_punchlist(VerificationPunchlist(
            entries=(
                PunchlistEntry(
                    rank=1, claim_id="c1",
                    attention_trigger="no_evidence",
                    structural_importance="structural",
                    risk_if_wrong="Misleading generalization",
                    suggested_verification="Search for recent studies on AI "
                                           "impact on specific societal domains",
                    claim_text="AI is transforming society.",
                    suggested_query="AI impact on society evidence 2025 2026",
                ),
            ),
            overall_severity="minor_flags",
            prioritization_rationale="Single claim flagged for missing evidence.",
        ))

        doc.finalize()

        # Validate
        errors = doc.validate()
        assert len(errors) == 0, f"Validation errors: {errors}"

        # Serialize
        result = doc.to_dict()
        json_str = json.dumps(result, indent=2, default=str)

        # Verify key structures present
        assert result["schema_version"] == "1.0.0"
        ao = result["analysis_objects"]
        assert len(ao["claims"]) == 1
        assert ao["trust_profile"]["established_pct"] == 0.0
        assert len(ao["verification_punchlist"]["entries"]) == 1
        assert ao["verification_punchlist"]["overall_severity"] == "minor_flags"

        # Roundtrip: parse back and check
        parsed = json.loads(json_str)
        assert parsed["schema_version"] == "1.0.0"
