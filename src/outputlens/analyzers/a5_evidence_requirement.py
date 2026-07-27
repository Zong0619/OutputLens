"""A5: Evidence Requirement Analyzer -- classifies each claim by evidence demand.

Phase 3.1: Pattern-based R1-R4 classification with signal-based reasoning.
Analyses claim text for citation patterns, evidence gestures, definitional
structures, and unsupported specificity.

Spec reference: OutputLens Framework Specification, Chapter 13 (A5).
"""

from __future__ import annotations

import re
from typing import Any

from outputlens.analysis.model import Claim, EvidenceAnnotation
from outputlens.orchestration.analyzer import (
    AnalysisContext,
    Analyzer,
    AnalyzerDeclaration,
    AnalyzerError,
    AnalyzerInput,
)
from outputlens.orchestration.engine import AnalyzerRegistry


# ---------------------------------------------------------------------------
# R2: Evidence Provided -- citation and source patterns
# ---------------------------------------------------------------------------

# Explicit citation patterns: "According to X", "X et al. (YEAR)", "[N]"
_CITATION_PATTERNS = [
    re.compile(r'according\s+to\s+', re.IGNORECASE),
    re.compile(r'\bet\s+al\.?\s*[\(\[]\s*\d{4}', re.IGNORECASE),
    re.compile(r'\[[\d,\s]+\]'),  # [1], [1,2,3]
    re.compile(r'\(\s*[A-Z][a-z]+\s*(?:et\s+al\.?)?\s*,?\s*\d{4}\s*\)'),  # (Smith 2023)
    re.compile(r'\(\s*[A-Z][a-z]+\s*(?:et\s+al\.?)?\s*,?\s*\d{4}\s*\)'),
]

# Source mention patterns: "published in", "a study by", specific source references.
# Must indicate a concrete source, not just name an institution.
_SOURCE_PATTERNS = [
    re.compile(r'published\s+(?:in|by)\s+', re.IGNORECASE),
    re.compile(r'(?:a|the)\s+\d{4}\s+study\s+(?:by|in|from)', re.IGNORECASE),
    re.compile(r'(?:announced|reported|demonstrated|showed|found)\s+(?:by|in)\s+(?:a|the)\s+', re.IGNORECASE),
    re.compile(r'(?:journal|conference|proceedings)\s+(?:of|name)', re.IGNORECASE),
    re.compile(r'study\s+(?:published|released|presented)\s+(?:in|at|by)\s+', re.IGNORECASE),
]

# Specific named entity patterns suggesting evidence: "Nature", "Science", "arXiv"
_KNOWN_PUBLICATION_VENUES = frozenset({
    "nature", "science", "cell", "lancet", "nejm", "jama", "pnas",
    "arxiv", "ieee", "acm", "springer", "elsevier", "plos",
    "the new england journal", "the lancet", "physical review",
})


def _detect_r2_signals(claim_text: str) -> list[str]:
    """Detect signals that evidence has been provided for this claim.

    Returns a list of signal descriptions (empty if no evidence detected).
    """
    signals: list[str] = []

    # Check citation patterns
    for pattern in _CITATION_PATTERNS:
        if pattern.search(claim_text):
            signals.append("explicit_citation")
            break

    # Check source mentions
    for pattern in _SOURCE_PATTERNS:
        if pattern.search(claim_text):
            signals.append("named_source")
            break

    # Check for known publication venues
    text_lower = claim_text.lower()
    for venue in _KNOWN_PUBLICATION_VENUES:
        if venue in text_lower:
            if "named_source" not in signals:
                signals.append("named_source")
            signals.append("publication_venue")
            break

    return signals


# ---------------------------------------------------------------------------
# R3: Evidence Expected (Gesture) -- patterns that suggest evidence without providing it
# ---------------------------------------------------------------------------

_GESTURE_PATTERNS = [
    re.compile(r'\b(?:stud(?:y|ies)|research(?:ers?)?)\s+(?:shows?|suggests?|indicates?|finds?|demonstrates?|reveals?)\b',
               re.IGNORECASE),
    re.compile(r'\b(?:it\s+is\s+(?:known|believed|thought|understood|widely\s+accepted))\b',
               re.IGNORECASE),
    re.compile(r'\b(?:evidence|data|results?)\s+(?:suggests?|shows?|indicates?|points?\s+to)\b',
               re.IGNORECASE),
    re.compile(r'\b(?:experts?\s+(?:agree|believe|suggest|say)|many\s+(?:experts?|scientists?|researchers?))\b',
               re.IGNORECASE),
    re.compile(r'\b(?:it\s+has\s+been\s+(?:shown|demonstrated|observed|found|reported|established))\b',
               re.IGNORECASE),
    re.compile(r'\b(?:according\s+to\s+(?:research|studies|reports?|findings?))\b',
               re.IGNORECASE),
    re.compile(r'\b(?:commonly\s+(?:known|believed|accepted|used)|generally\s+(?:considered|accepted|recognized))\b',
               re.IGNORECASE),
    re.compile(r'\b(?:there\s+is\s+(?:evidence|growing\s+evidence|some\s+evidence))\b',
               re.IGNORECASE),
]


def _detect_r3_signals(claim_text: str) -> list[str]:
    """Detect signals that evidence is gestured at but not provided."""
    signals: list[str] = []
    for pattern in _GESTURE_PATTERNS:
        if pattern.search(claim_text):
            signals.append("evidence_gesture")
            break
    return signals


# ---------------------------------------------------------------------------
# R1: Self-Evident / Definitional
# ---------------------------------------------------------------------------

_DEFINITIONAL_PATTERNS = [
    re.compile(r'\bis\s+(?:a|an|the)\s+', re.IGNORECASE),
    re.compile(r'\bis\s+defined\s+as\s+', re.IGNORECASE),
    re.compile(r'\brefers?\s+to\s+', re.IGNORECASE),
    re.compile(r'\bmeans?\s+', re.IGNORECASE),
    re.compile(r'\b(?:in\s+other\s+words|that\s+is\s+to\s+say)\b', re.IGNORECASE),
]

_TAUTOLOGY_MARKERS = [
    re.compile(r'\b(?:all|every|each|any)\s+\w+\s+(?:is|are)\s+(?:a|an|the)\s+', re.IGNORECASE),
    re.compile(r'\bby\s+definition\b', re.IGNORECASE),
]

# Claims that are inherently unverifiable (opinions, normative statements)
_UNVERIFIABLE_PATTERNS = [
    re.compile(r'\b(?:should|ought|must|need\s+to)\s+', re.IGNORECASE),
    re.compile(r'\b(?:better|worse|best|worst|superior|inferior)\b', re.IGNORECASE),
    re.compile(r'\b(?:in\s+my\s+opinion|I\s+believe|I\s+think|personally)\b', re.IGNORECASE),
    re.compile(r'\b(?:beautiful|elegant|ugly|interesting|boring|exciting)\b', re.IGNORECASE),
]


def _detect_r1_signals(claim_text: str) -> list[str]:
    """Detect signals that this claim is self-evident or definitional."""
    signals: list[str] = []
    for pattern in _DEFINITIONAL_PATTERNS:
        if pattern.search(claim_text):
            signals.append("definitional_structure")
            break
    for pattern in _TAUTOLOGY_MARKERS:
        if pattern.search(claim_text):
            signals.append("tautological")
            break
    return signals


def _detect_unverifiable_signals(claim_text: str) -> list[str]:
    """Detect signals that this claim is inherently unverifiable (normative/subjective)."""
    signals: list[str] = []
    for pattern in _UNVERIFIABLE_PATTERNS:
        if pattern.search(claim_text):
            signals.append("normative_or_subjective")
            break
    return signals


# ---------------------------------------------------------------------------
# R4: Evidence Essential (Missing) -- specific claims without support
# ---------------------------------------------------------------------------

_STATISTICAL_PATTERNS = [
    re.compile(r'\b\d{1,3}(?:\.\d+)?%\s+(?:of\s+)?'),
    re.compile(r'\b\d+(?:\.\d+)?\s*%'),
    re.compile(r'\b(?:increased|decreased|reduced|improved)\s+by\s+\d+', re.IGNORECASE),
    re.compile(r'\b\d+\s+(?:times|fold)\b', re.IGNORECASE),
    re.compile(r'\b(?:correlation|correlated)\s+(?:of|coefficient)', re.IGNORECASE),
]

_ATTRIBUTION_PATTERNS = [
    re.compile(r'\b(?:discovered|invented|created|developed|proposed|introduced)\s+by\s+',
               re.IGNORECASE),
    re.compile(r'\b(?:first|initially|originally)\s+(?:discovered|developed|described|proposed)',
               re.IGNORECASE),
    re.compile(r'\b(?:coined|named|termed)\s+(?:by|the)\s+', re.IGNORECASE),
    re.compile(r'\b(?:conducted|performed|carried\s+out)\s+by\s+', re.IGNORECASE),
]

_CAUSAL_PATTERNS = [
    re.compile(r'\b(?:causes?|leads?\s+to|results?\s+in|triggers?|produces?)\b', re.IGNORECASE),
    re.compile(r'\b(?:due\s+to|because\s+of|as\s+a\s+result\s+of|owing\s+to)\b', re.IGNORECASE),
    re.compile(r'\b(?:affects?|influences?|impacts?|determines?)\b', re.IGNORECASE),
]


def _detect_r4_signals(claim_text: str) -> list[str]:
    """Detect signals that this claim demands evidence but provides none."""
    signals: list[str] = []
    for pattern in _STATISTICAL_PATTERNS:
        if pattern.search(claim_text):
            signals.append("specific_statistic")
            break
    for pattern in _ATTRIBUTION_PATTERNS:
        if pattern.search(claim_text):
            signals.append("specific_attribution")
            break
    for pattern in _CAUSAL_PATTERNS:
        if pattern.search(claim_text):
            signals.append("causal_claim")
            break
    return signals


# ---------------------------------------------------------------------------
# Classification logic
# ---------------------------------------------------------------------------


def _classify_evidence(claim: Claim) -> tuple[str, list[str], str]:
    """Classify a single claim's evidence requirement.

    Returns: (level, signals, reasoning)
    """
    text = claim.text
    signals: list[str] = []
    level = "R4"  # Default: evidence essential but missing

    # Detect all signal types
    r2_signals = _detect_r2_signals(text)
    r3_signals = _detect_r3_signals(text)
    r1_signals = _detect_r1_signals(text)
    unverifiable_signals = _detect_unverifiable_signals(text)
    r4_signals = _detect_r4_signals(text)

    # Normative/subjective claims are unverifiable by design
    if unverifiable_signals and not r2_signals:
        signals = unverifiable_signals
        level = "R1"  # Self-evident in the sense of being inherently non-empirical
        reasoning = (
            f"This claim expresses a normative or subjective judgment "
            f"(detected: {unverifiable_signals[0]}). Such claims are not "
            f"empirically verifiable by design and do not require external evidence."
        )
        return level, signals, reasoning

    # R2: Evidence is present
    if r2_signals:
        signals = r2_signals
        level = "R2"
        signal_desc = ", ".join(r2_signals)
        reasoning = (
            f"The response provides evidence for this claim: detected "
            f"{signal_desc}. A source or citation is present in the claim text."
        )
        return level, signals, reasoning

    # R1: Definitional or self-evident
    if r1_signals and not r4_signals:
        signals = r1_signals
        level = "R1"
        signal_desc = ", ".join(r1_signals)
        reasoning = (
            f"This claim has a definitional or tautological structure "
            f"(detected: {signal_desc}). Such claims are self-evident or true "
            f"by definition and do not require external evidence."
        )
        return level, signals, reasoning

    # R3: Gestures at evidence
    if r3_signals:
        signals = r3_signals
        # Check if also has R4 signals (specific but only gestured at)
        if r4_signals:
            signals.extend(r4_signals)
            level = "R4"  # Specific claim + only gestured evidence = R4
            signal_desc = ", ".join(signals)
            reasoning = (
                f"This claim makes a specific assertion ({', '.join(r4_signals)}) "
                f"but only gestures at evidence ({r3_signals[0]}) without "
                f"providing a specific source. Specific claims require "
                f"specific evidence."
            )
        else:
            level = "R3"
            reasoning = (
                f"This claim gestures at supporting evidence "
                f"(detected: {r3_signals[0]}) without providing a specific "
                f"citation or source. The evidence is expected but not provided."
            )
        return level, signals, reasoning

    # R4: Specific but unsupported
    if r4_signals:
        signals = r4_signals
        level = "R4"
        signal_desc = ", ".join(r4_signals)
        reasoning = (
            f"This claim makes a specific assertion ({signal_desc}) without "
            f"providing any supporting evidence, citation, or source. "
            f"Claims of this type require evidence to be verifiable."
        )
        return level, signals, reasoning

    # Default: no strong signals either way
    # Check claim type for additional context
    if claim.claim_type == "meta_claim":
        level = "R1"
        signals.append("meta_claim")
        reasoning = (
            "This is a meta-claim about the response itself. It does not "
            "require external evidence."
        )
    elif claim.claim_type == "conceptual_definition":
        level = "R1"
        signals.append("definitional_structure")
        reasoning = (
            "This claim provides a conceptual definition. Definitions are "
            "self-evident by nature and do not require external evidence."
        )
    else:
        level = "R4"
        signals.append("no_evidence_detected")
        reasoning = (
            "No evidence provision, citation, definitional structure, or "
            "evidence gesture was detected for this claim. As a factual "
            "assertion, it would benefit from supporting evidence."
        )

    return level, signals, reasoning


def classify_evidence(claims: list[Claim]) -> list[EvidenceAnnotation]:
    """Classify the evidence requirement for each claim.

    Args:
        claims: The ClaimSet from A2.

    Returns:
        List of EvidenceAnnotation objects with signal-based reasoning.
    """
    annotations: list[EvidenceAnnotation] = []
    for claim in claims:
        level, signals, reasoning = _classify_evidence(claim)
        annotation = EvidenceAnnotation(
            claim_id=claim.id,
            level=level,
            reasoning=reasoning,
        )
        annotations.append(annotation)
    return annotations


# ---------------------------------------------------------------------------
# Orchestration Analyzer wrapper
# ---------------------------------------------------------------------------


class EvidenceRequirementAnalyzer(Analyzer):
    """A5: Classifies each claim by its evidence requirement (R1-R4).

    Input: ClaimSet from A2
    Output: list[EvidenceAnnotation]
    """

    declaration = AnalyzerDeclaration(
        id="a5",
        version="0.1.0",
        responsibility="Classify each claim by evidence requirement level "
        "(R1-R4) using pattern-based signal detection: citations, evidence "
        "gestures, definitional structures, and unsupported specificity.",
        inputs=(
            AnalyzerInput("a2", "a2", required=True),
        ),
        output_type=list,
        layer="classification",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        """Execute evidence requirement classification."""
        a2_output = context.get_output("a2", "a2")
        if a2_output is None:
            raise AnalyzerError(
                "A5 (Evidence Requirement) requires A2 (Claim Extractor) output."
            )

        claims = a2_output.get("claims")
        if claims is None or not isinstance(claims, list):
            raise AnalyzerError("A5 requires claims list from A2 output.")

        annotations = classify_evidence(claims)
        return {"evidence_annotations": annotations}


def register(registry: AnalyzerRegistry) -> None:
    """Register the A5 Evidence Requirement analyzer."""
    registry.register(
        EvidenceRequirementAnalyzer.declaration,
        lambda: EvidenceRequirementAnalyzer(),
    )
