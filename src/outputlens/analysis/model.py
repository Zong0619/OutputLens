"""Analysis Model — dataclasses for analytical objects (A1–A19).

Every object represents an analytical finding about the text. All objects are
immutable once produced. Each object has a specific producer (analyzer) and
well-defined consumers.

Spec reference: OutputLens Framework Specification Edition 1, Chapters 19–23.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Foundation Objects (A1–A3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfidenceMarker:
    """A1: A linguistic expression of certainty or uncertainty associated with a claim.

    Producer: A2 (Claim Extractor)
    Consumers: A5 (Evidence Requirement Analyzer), A12 (Overconfidence Detector)
    """

    id: str
    type: str  # "hedge" | "certainty"
    start_char: int
    end_char: int
    claim_id: str
    expression: str = ""
    intensity: str = "moderate"  # "weak" | "moderate" | "strong"

    VALID_TYPES = frozenset({"hedge", "certainty"})
    VALID_INTENSITIES = frozenset({"weak", "moderate", "strong"})

    def __post_init__(self) -> None:
        if self.type not in self.VALID_TYPES:
            raise ValueError(f"ConfidenceMarker type must be one of {sorted(self.VALID_TYPES)}")
        if self.intensity not in self.VALID_INTENSITIES:
            raise ValueError(f"Intensity must be one of {sorted(self.VALID_INTENSITIES)}")
        if self.start_char < 0 or self.end_char <= self.start_char:
            raise ValueError("Invalid position span")


@dataclass(frozen=True)
class Claim:
    """A2: A single, self-contained proposition extracted from the text.

    The central object in OutputLens. Every analytical dimension operates on Claims.

    Producer: A2 (Claim Extractor)
    Consumers: A3–A7, A9–A13, A16
    """

    id: str
    text: str
    start_char: int
    end_char: int
    segment_id: str
    claim_type: str
    confidence_markers: tuple[ConfidenceMarker, ...] = ()
    knowledge_signature: str = ""

    CLAIM_TYPES = frozenset(
        {
            "factual_assertion",
            "conceptual_definition",
            "causal_claim",
            "predictive_claim",
            "normative_claim",
            "methodological_claim",
            "comparative_claim",
            "attribution_claim",
            "meta_claim",
        }
    )

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Claim text must not be empty")
        if self.claim_type not in self.CLAIM_TYPES:
            raise ValueError(f"claim_type must be one of {sorted(self.CLAIM_TYPES)}")
        if self.start_char < 0 or self.end_char <= self.start_char:
            raise ValueError(f"Invalid position span: [{self.start_char}, {self.end_char})")


@dataclass(frozen=True)
class ConceptSurfaceForm:
    """A text span that refers to a Concept."""

    text: str
    start_char: int
    end_char: int


@dataclass(frozen=True)
class Concept:
    """A3: A significant idea, entity, or construct in the response.

    Producer: A3 (Concept Extractor)
    Consumers: A4, A6, A8, A14
    """

    id: str
    canonical_name: str
    concept_type: str
    surface_forms: tuple[ConceptSurfaceForm, ...] = ()
    domain_associations: dict[str, float] = field(default_factory=dict)
    referencing_claim_ids: tuple[str, ...] = ()
    definition_provided: bool = False
    definition_claim_id: str | None = None

    CONCEPT_TYPES = frozenset(
        {
            "named_entity_person",
            "named_entity_organization",
            "named_entity_location",
            "named_entity_work",
            "domain_concept",
            "novel_construct",
            "common_concept",
        }
    )

    def __post_init__(self) -> None:
        if self.concept_type not in self.CONCEPT_TYPES:
            raise ValueError(f"concept_type must be one of {sorted(self.CONCEPT_TYPES)}")
        if not self.canonical_name.strip():
            raise ValueError("canonical_name must not be empty")


# ---------------------------------------------------------------------------
# Classification Annotations (A4–A6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EstablishednessAnnotation:
    """A4: Establishedness classification for a single Claim.

    Producer: A4 (Establishedness Analyzer)
    Consumers: A7, A9, A12, A13, A16

    Levels:
        E1 — Common Knowledge
        E2 — Domain Established
        E3 — Plausible but Unverified
        E4 — Unverifiable (by design)
        E5 — Unknown / Boundary
    """

    claim_id: str
    level: str
    reasoning: str

    LEVELS = frozenset({"E1", "E2", "E3", "E4", "E5"})

    def __post_init__(self) -> None:
        if self.level not in self.LEVELS:
            raise ValueError(f"Establishedness level must be one of {sorted(self.LEVELS)}")
        if len(self.reasoning.strip()) < 20:
            raise ValueError(
                f"Reasoning must be at least 20 characters, got {len(self.reasoning)}"
            )


@dataclass(frozen=True)
class EvidenceAnnotation:
    """A5: Evidence requirement classification for a single Claim.

    Producer: A5 (Evidence Requirement Analyzer)
    Consumers: A10, A16

    Levels:
        R1 — Self-Evident / Definitional
        R2 — Evidence Provided
        R3 — Evidence Expected
        R4 — Evidence Essential
    """

    claim_id: str
    level: str
    reasoning: str

    LEVELS = frozenset({"R1", "R2", "R3", "R4"})

    def __post_init__(self) -> None:
        if self.level not in self.LEVELS:
            raise ValueError(f"Evidence level must be one of {sorted(self.LEVELS)}")
        if len(self.reasoning.strip()) < 20:
            raise ValueError(f"Reasoning must be at least 20 characters")


@dataclass(frozen=True)
class NoveltyAnnotation:
    """A6: Novelty classification for a single Claim.

    Producer: A6 (Novelty Analyzer)
    Consumers: A7, A11, A16

    Levels:
        N1 — Canonical
        N2 — Non-Trivial Synthesis
        N3 — Potentially Novel
        N4 — Apparently Original
        N5 — Uncertain
    """

    claim_id: str
    level: str
    reasoning: str

    LEVELS = frozenset({"N1", "N2", "N3", "N4", "N5"})

    def __post_init__(self) -> None:
        if self.level not in self.LEVELS:
            raise ValueError(f"Novelty level must be one of {sorted(self.LEVELS)}")
        if len(self.reasoning.strip()) < 20:
            raise ValueError(f"Reasoning must be at least 20 characters")


# ---------------------------------------------------------------------------
# Structure Objects (A7–A10)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClaimRelationship:
    """A7: A typed, directed relationship between two Claims.

    Producer: A7 (Claim Relationship Mapper)
    Consumers: A8, A13, A16
    """

    source_claim_id: str
    target_claim_id: str
    relationship_type: str
    strength: str = "implicit"

    RELATIONSHIP_TYPES = frozenset(
        {"supports", "contradicts", "elaborates", "depends_on", "generalizes", "restates", "concedes", "sequences"}
    )
    STRENGTHS = frozenset({"explicit", "implicit"})

    def __post_init__(self) -> None:
        if self.relationship_type not in self.RELATIONSHIP_TYPES:
            raise ValueError(f"Relationship type must be one of {sorted(self.RELATIONSHIP_TYPES)}")
        if self.strength not in self.STRENGTHS:
            raise ValueError(f"Strength must be one of {sorted(self.STRENGTHS)}")
        if self.source_claim_id == self.target_claim_id:
            raise ValueError("A claim cannot have a relationship with itself")


@dataclass(frozen=True)
class ConceptRelationship:
    """A8: A typed, directed relationship between two Concepts.

    Producer: A8 (Concept Relationship Mapper)
    Consumers: A14
    """

    source_concept_id: str
    target_concept_id: str
    relationship_type: str
    evidence: str = "cooccurrence"

    RELATIONSHIP_TYPES = frozenset(
        {"is_a", "part_of", "causes", "precedes", "related_to", "contrasts_with",
         "analogous_to", "defines", "measures", "depends_on"}
    )
    EVIDENCE_TYPES = frozenset({"explicit", "claim_inferred", "cooccurrence"})

    def __post_init__(self) -> None:
        if self.relationship_type not in self.RELATIONSHIP_TYPES:
            raise ValueError(f"Relationship type must be one of {sorted(self.RELATIONSHIP_TYPES)}")
        if self.evidence not in self.EVIDENCE_TYPES:
            raise ValueError(f"Evidence must be one of {sorted(self.EVIDENCE_TYPES)}")


@dataclass(frozen=True)
class ClaimGraph:
    """A9: The complete argument structure of the response.

    Producer: A7 (Claim Relationship Mapper)
    Consumers: A8, A13, A16
    """

    relationships: tuple[ClaimRelationship, ...] = ()
    foundational_claim_ids: tuple[str, ...] = ()
    orphan_claim_ids: tuple[str, ...] = ()
    contradiction_clusters: tuple[tuple[str, ...], ...] = ()
    cascading_uncertainty_chains: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class ConceptGraph:
    """A10: The complete conceptual structure of the response.

    Producer: A8 (Concept Relationship Mapper)
    Consumers: A14
    """

    relationships: tuple[ConceptRelationship, ...] = ()
    centrality_scores: dict[str, float] = field(default_factory=dict)
    clusters: tuple[tuple[str, ...], ...] = ()
    bridge_concept_ids: tuple[str, ...] = ()
    novel_construct_ids: tuple[str, ...] = ()
    missing_connections: tuple[tuple[str, str], ...] = ()


# ---------------------------------------------------------------------------
# Synthesis Objects (A11–A17)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrustProfile:
    """A11: Three-part distribution of claim establishedness.

    Producer: A9 (Trust Profile Generator)
    Consumers: A15, A16, all interfaces
    """

    established_pct: float
    plausible_pct: float
    needs_verification_pct: float

    CAVEAT = "This is not a reliability score. Different contexts need different standards."

    def __post_init__(self) -> None:
        total = self.established_pct + self.plausible_pct + self.needs_verification_pct
        if not (99.0 <= total <= 101.0):  # Allow small floating point errors
            raise ValueError(f"TrustProfile percentages must sum to ~100, got {total}")
        for name, val in (
            ("established_pct", self.established_pct),
            ("plausible_pct", self.plausible_pct),
            ("needs_verification_pct", self.needs_verification_pct),
        ):
            if not (0.0 <= val <= 100.0):
                raise ValueError(f"{name} must be between 0 and 100, got {val}")


@dataclass(frozen=True)
class EvidenceGapReport:
    """A12: Quantification of claims requiring evidence that the response omits.

    Producer: A10 (Evidence Gap Analyzer)
    Consumers: A15
    """

    gap_ratio: float
    r3_count: int
    r4_count: int
    by_claim_type: dict[str, dict[str, int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (0.0 <= self.gap_ratio <= 1.0):
            raise ValueError(f"gap_ratio must be between 0 and 1, got {self.gap_ratio}")


@dataclass(frozen=True)
class NoveltyIndex:
    """A13: Proportion of claims that go beyond established knowledge.

    Producer: A11 (Novelty Index Calculator)
    Consumers: A15
    """

    novelty_proportion: float
    n3_count: int = 0
    n4_count: int = 0
    n5_count: int = 0

    CAVEAT = "High novelty is not inherently good or bad. It depends on your context and use case."

    def __post_init__(self) -> None:
        if not (0.0 <= self.novelty_proportion <= 1.0):
            raise ValueError(f"novelty_proportion must be between 0 and 1")


@dataclass(frozen=True)
class OverconfidenceClaim:
    """A single overconfident claim entry."""

    claim_id: str
    confidence_level: str
    establishedness_level: str
    description: str = ""


@dataclass(frozen=True)
class OverconfidenceReport:
    """A14: Claims where linguistic confidence conflicts with epistemological support.

    Producer: A12 (Overconfidence Detector)
    Consumers: A15, A16
    """

    overconfident_claims: tuple[OverconfidenceClaim, ...] = ()
    pattern_summary: str = ""


@dataclass(frozen=True)
class StructuralIntegrityReport:
    """A15: Assessment of the response's argument structure.

    Producer: A13 (Structural Integrity Analyzer)
    Consumers: A15, A16
    """

    foundation_health: float
    contradiction_count: int
    orphan_proportion: float
    cascading_uncertainty_chain_count: int = 0

    def __post_init__(self) -> None:
        if not (0.0 <= self.foundation_health <= 1.0):
            raise ValueError("foundation_health must be between 0 and 1")
        if not (0.0 <= self.orphan_proportion <= 1.0):
            raise ValueError("orphan_proportion must be between 0 and 1")


@dataclass(frozen=True)
class CoherenceReport:
    """A16: Quantification of conceptual coherence.

    Producer: A14 (Conceptual Coherence Analyzer)
    Consumers: A15
    """

    graph_connectivity: float
    cluster_count: int
    average_path_length: float = 0.0
    bridge_concept_ids: tuple[str, ...] = ()
    fragmentation_flag: bool = False

    def __post_init__(self) -> None:
        if not (0.0 <= self.graph_connectivity <= 1.0):
            raise ValueError("graph_connectivity must be between 0 and 1")


@dataclass(frozen=True)
class ResponseNarrative:
    """A17: 3–5 sentence plain-language summary of the analysis.

    Producer: A15 (Response Narrative Generator)
    Consumers: All interfaces
    """

    narrative_text: str

    def __post_init__(self) -> None:
        if len(self.narrative_text.strip()) < 50:
            raise ValueError("ResponseNarrative must be at least 50 characters")


# ---------------------------------------------------------------------------
# Terminal Objects (A18–A19)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PunchlistEntry:
    """A18: A single prioritized action item for the reader.

    Producer: A16 (Verification Punchlist Generator)
    Consumers: All interfaces
    """

    rank: int
    claim_id: str
    attention_trigger: str
    structural_importance: str
    risk_if_wrong: str
    suggested_verification: str
    claim_text: str = ""
    suggested_query: str = ""

    TRIGGERS = frozenset(
        {"no_evidence", "novel_claim", "overconfident", "foundational", "contradicted", "orphaned"}
    )
    IMPORTANCE = frozenset({"foundational", "structural", "peripheral"})

    def __post_init__(self) -> None:
        if self.attention_trigger not in self.TRIGGERS:
            raise ValueError(f"attention_trigger must be one of {sorted(self.TRIGGERS)}")
        if self.structural_importance not in self.IMPORTANCE:
            raise ValueError(f"structural_importance must be one of {sorted(self.IMPORTANCE)}")
        if self.rank < 1:
            raise ValueError(f"rank must be >= 1, got {self.rank}")


@dataclass(frozen=True)
class VerificationPunchlist:
    """A19: Ranked, prioritized list of claims to investigate.

    Producer: A16 (Verification Punchlist Generator)
    Consumers: All interfaces
    """

    entries: tuple[PunchlistEntry, ...] = ()
    overall_severity: str = "minor_flags"
    prioritization_rationale: str = ""

    SEVERITIES = frozenset({"minor_flags", "several_concerns", "systematic_verification_needed"})

    def __post_init__(self) -> None:
        if self.overall_severity not in self.SEVERITIES:
            raise ValueError(f"overall_severity must be one of {sorted(self.SEVERITIES)}")
