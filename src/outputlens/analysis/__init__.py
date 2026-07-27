"""Analysis Model -- objects representing analytical findings about text.

Contains the core domain model dataclasses (A1-A19) and the AnalysisDocument
boundary object that bridges the Analysis Model and Interface Model.
"""

from outputlens.analysis.document import AnalysisDocument, SCHEMA_VERSION
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

__all__ = [
    "AnalysisDocument",
    "SCHEMA_VERSION",
    "Claim",
    "ClaimGraph",
    "ClaimRelationship",
    "CoherenceReport",
    "Concept",
    "ConceptGraph",
    "ConceptRelationship",
    "ConfidenceMarker",
    "EstablishednessAnnotation",
    "EvidenceAnnotation",
    "EvidenceGapReport",
    "NoveltyAnnotation",
    "NoveltyIndex",
    "OverconfidenceReport",
    "PunchlistEntry",
    "ResponseNarrative",
    "StructuralIntegrityReport",
    "TrustProfile",
    "VerificationPunchlist",
]
