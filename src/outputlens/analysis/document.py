"""AnalysisDocument — the boundary object between engine and interfaces.

The AnalysisDocument contains Runtime objects needed for rendering and all
Analysis objects produced by requested analyzers. It is assembled incrementally
during analysis and becomes immutable after finalization.

Spec reference: OutputLens Framework Specification Edition 1, Chapter 26.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from outputlens.runtime.model import (
    ExecutionTrace,
    Metadata,
    NormalizedText,
    PositionIndex,
    RawInput,
)
from outputlens.analysis.model import (
    Claim,
    ClaimGraph,
    CoherenceReport,
    Concept,
    ConceptGraph,
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

SCHEMA_VERSION = "1.0.0"


@dataclass
class AnalysisDocument:
    """The complete output of an OutputLens analysis run.

    Assembled incrementally by the orchestration layer as analyzers complete.
    Once finalized, no further modifications are permitted.

    Contains Runtime objects (for rendering) and Analysis objects (for insight).
    """

    schema_version: str = SCHEMA_VERSION
    metadata: Metadata | None = None

    # Runtime objects
    raw_input: RawInput | None = None
    normalized_text: NormalizedText | None = None
    position_index: PositionIndex | None = None
    execution_trace: ExecutionTrace | None = None

    # Analysis objects — Foundation
    claims: list[Claim] = field(default_factory=list)
    concepts: list[Concept] | None = None

    # Analysis objects — Classifications
    establishedness_annotations: list[EstablishednessAnnotation] | None = None
    evidence_annotations: list[EvidenceAnnotation] | None = None
    novelty_annotations: list[NoveltyAnnotation] | None = None

    # Analysis objects — Structure
    claim_graph: ClaimGraph | None = None
    concept_graph: ConceptGraph | None = None

    # Analysis objects — Synthesis
    trust_profile: TrustProfile | None = None
    evidence_gap_report: EvidenceGapReport | None = None
    novelty_index: NoveltyIndex | None = None
    overconfidence_report: OverconfidenceReport | None = None
    structural_integrity_report: StructuralIntegrityReport | None = None
    coherence_report: CoherenceReport | None = None
    response_narrative: ResponseNarrative | None = None

    # Analysis objects — Terminal
    verification_punchlist: VerificationPunchlist | None = None

    # Internal state
    _finalized: bool = field(default=False, init=False, repr=False)

    def finalize(self) -> None:
        """Mark this AnalysisDocument as complete and immutable.

        After finalization, no further changes are permitted. Any attempt to
        modify fields will raise RuntimeError.
        """
        self._finalized = True

    @property
    def is_finalized(self) -> bool:
        return self._finalized

    def _check_mutable(self) -> None:
        if self._finalized:
            raise RuntimeError(
                "AnalysisDocument has been finalized and is immutable. "
                "Create a new AnalysisDocument for a new analysis."
            )

    def set_claim(self, claim: Claim) -> None:
        """Add a claim during analysis construction."""
        self._check_mutable()
        self.claims.append(claim)

    def set_concepts(self, concepts: list[Concept]) -> None:
        self._check_mutable()
        self.concepts = concepts

    def set_establishedness_annotations(
        self, annotations: list[EstablishednessAnnotation]
    ) -> None:
        self._check_mutable()
        self.establishedness_annotations = annotations

    def set_evidence_annotations(self, annotations: list[EvidenceAnnotation]) -> None:
        self._check_mutable()
        self.evidence_annotations = annotations

    def set_novelty_annotations(self, annotations: list[NoveltyAnnotation]) -> None:
        self._check_mutable()
        self.novelty_annotations = annotations

    def set_claim_graph(self, graph: ClaimGraph) -> None:
        self._check_mutable()
        self.claim_graph = graph

    def set_concept_graph(self, graph: ConceptGraph) -> None:
        self._check_mutable()
        self.concept_graph = graph

    def set_trust_profile(self, profile: TrustProfile) -> None:
        self._check_mutable()
        self.trust_profile = profile

    def set_evidence_gap_report(self, report: EvidenceGapReport) -> None:
        self._check_mutable()
        self.evidence_gap_report = report

    def set_novelty_index(self, index: NoveltyIndex) -> None:
        self._check_mutable()
        self.novelty_index = index

    def set_overconfidence_report(self, report: OverconfidenceReport) -> None:
        self._check_mutable()
        self.overconfidence_report = report

    def set_structural_integrity_report(self, report: StructuralIntegrityReport) -> None:
        self._check_mutable()
        self.structural_integrity_report = report

    def set_coherence_report(self, report: CoherenceReport) -> None:
        self._check_mutable()
        self.coherence_report = report

    def set_response_narrative(self, narrative: ResponseNarrative) -> None:
        self._check_mutable()
        self.response_narrative = narrative

    def set_verification_punchlist(self, punchlist: VerificationPunchlist) -> None:
        self._check_mutable()
        self.verification_punchlist = punchlist

    def validate(self) -> list[str]:
        """Validate this AnalysisDocument against structural invariants.

        Returns:
            A list of validation error messages. Empty list means valid.
        """
        errors: list[str] = []

        if self.metadata is None:
            errors.append("metadata is required")
        if not self.claims:
            errors.append("at least one claim is required")

        # Validate cross-references
        claim_ids = {c.id for c in self.claims}
        concept_ids: set[str] = set()
        if self.concepts:
            concept_ids = {c.id for c in self.concepts}

        if self.establishedness_annotations:
            for ann in self.establishedness_annotations:
                if ann.claim_id not in claim_ids:
                    errors.append(
                        f"EstablishednessAnnotation references unknown claim {ann.claim_id}"
                    )

        if self.evidence_annotations:
            for ann in self.evidence_annotations:
                if ann.claim_id not in claim_ids:
                    errors.append(f"EvidenceAnnotation references unknown claim {ann.claim_id}")

        if self.novelty_annotations:
            for ann in self.novelty_annotations:
                if ann.claim_id not in claim_ids:
                    errors.append(f"NoveltyAnnotation references unknown claim {ann.claim_id}")

        if self.claim_graph:
            for rel in self.claim_graph.relationships:
                if rel.source_claim_id not in claim_ids:
                    errors.append(f"ClaimGraph references unknown source claim {rel.source_claim_id}")
                if rel.target_claim_id not in claim_ids:
                    errors.append(f"ClaimGraph references unknown target claim {rel.target_claim_id}")

        if self.concept_graph and self.concepts:
            for rel in self.concept_graph.relationships:
                if rel.source_concept_id not in concept_ids:
                    errors.append(
                        f"ConceptGraph references unknown source concept {rel.source_concept_id}"
                    )
                if rel.target_concept_id not in concept_ids:
                    errors.append(
                        f"ConceptGraph references unknown target concept {rel.target_concept_id}"
                    )

        if self.verification_punchlist:
            for entry in self.verification_punchlist.entries:
                if entry.claim_id not in claim_ids:
                    errors.append(f"PunchlistEntry references unknown claim {entry.claim_id}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict matching the AnalysisDocument JSON Schema v1.0.

        This is the primary serialization path. Interfaces consume this dict.
        """
        import dataclasses

        def _convert(obj: Any) -> Any:
            if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
                result: dict[str, Any] = {}
                for f in dataclasses.fields(obj):
                    value = getattr(obj, f.name)
                    # Skip internal fields
                    if f.name.startswith("_"):
                        continue
                    # Skip None values to keep output clean
                    if value is None:
                        continue
                    if isinstance(value, tuple):
                        value = [_convert(v) for v in value]
                    elif isinstance(value, list):
                        value = [_convert(v) for v in value]
                    elif isinstance(value, dict):
                        value = {k: _convert(v) for k, v in value.items()}
                    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
                        value = _convert(value)
                    result[f.name] = value
                return result
            return obj

        doc: dict[str, Any] = {
            "schema_version": self.schema_version,
            "metadata": _convert(self.metadata),
        }

        # Runtime objects
        runtime: dict[str, Any] = {}
        if self.raw_input:
            runtime["raw_input"] = _convert(self.raw_input)
        if self.normalized_text:
            runtime["normalized_text"] = _convert(self.normalized_text)
        if self.position_index:
            runtime["position_index"] = _convert(self.position_index)
        if self.execution_trace:
            runtime["execution_trace"] = _convert(self.execution_trace)
        doc["runtime_objects"] = runtime

        # Analysis objects
        analysis: dict[str, Any] = {
            "claims": [_convert(c) for c in self.claims],
        }
        optional_fields = [
            ("concepts", self.concepts),
            ("establishedness_annotations", self.establishedness_annotations),
            ("evidence_annotations", self.evidence_annotations),
            ("novelty_annotations", self.novelty_annotations),
            ("claim_graph", self.claim_graph),
            ("concept_graph", self.concept_graph),
            ("trust_profile", self.trust_profile),
            ("evidence_gap_report", self.evidence_gap_report),
            ("novelty_index", self.novelty_index),
            ("overconfidence_report", self.overconfidence_report),
            ("structural_integrity_report", self.structural_integrity_report),
            ("coherence_report", self.coherence_report),
            ("response_narrative", self.response_narrative),
            ("verification_punchlist", self.verification_punchlist),
        ]
        for key, value in optional_fields:
            if value is not None:
                analysis[key] = _convert(value)

        doc["analysis_objects"] = analysis
        return doc
