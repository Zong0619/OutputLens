"""A4: Establishedness Analyzer -- classifies claims by knowledge grounding.

Phase 3.2: Multi-signal heuristic E1-E5 classification. Uses claim type,
concept domain associations, hedging language, and specificity to estimate
how firmly each claim is grounded in established knowledge.

Spec reference: OutputLens Framework Specification, Chapter 13 (A4).
"""

from __future__ import annotations

import re
from typing import Any

from outputlens.analysis.model import Claim, Concept, EstablishednessAnnotation
from outputlens.orchestration.analyzer import (
    AnalysisContext,
    Analyzer,
    AnalyzerDeclaration,
    AnalyzerError,
    AnalyzerInput,
)
from outputlens.orchestration.engine import AnalyzerRegistry


# ---------------------------------------------------------------------------
# Signal 1: Claim-type-based priors
# ---------------------------------------------------------------------------

# Claim types that are inherently at specific establishedness levels
_CLAIM_TYPE_PRIORS: dict[str, str] = {
    "conceptual_definition": "E1",   # Definitions are self-contained
    "meta_claim": "E4",              # Unverifiable by design
    "normative_claim": "E4",         # Ought/is distinction
    "predictive_claim": "E3",        # Inherently uncertain
}

# Claim types that suggest higher establishedness when paired with domain concepts
_DOMAIN_SENSITIVE_TYPES = frozenset({
    "factual_assertion", "causal_claim", "comparative_claim",
    "methodological_claim", "attribution_claim",
})


# ---------------------------------------------------------------------------
# Signal 2: Hedging language detection
# ---------------------------------------------------------------------------

_HEDGE_PATTERNS = [
    re.compile(r'\b(?:may|might|could|can)\s+(?:be|have|also|potentially)\b', re.IGNORECASE),
    re.compile(r'\b(?:appears?\s+to|seems?\s+to|tends?\s+to)\b', re.IGNORECASE),
    re.compile(r'\b(?:potentially|possibly|perhaps|likely|unlikely)\b', re.IGNORECASE),
    re.compile(r'\b(?:some\s+evidence|preliminary|initial\s+results?)\b', re.IGNORECASE),
    re.compile(r'\b(?:speculative|hypothetical|theoretical(?:ly)?)\b', re.IGNORECASE),
    re.compile(r'\b(?:not\s+(?:fully|yet|completely|entirely)\s+understood)\b', re.IGNORECASE),
    re.compile(r'\b(?:remains?\s+(?:unclear|unknown|uncertain|to\s+be\s+seen))\b', re.IGNORECASE),
    re.compile(r'\b(?:debated|controversial|disputed|contested)\b', re.IGNORECASE),
    re.compile(r'\b(?:suggests?|indicates?|implies?|points?\s+to)\b', re.IGNORECASE),
]

# Strong certainty language -- suggests the model asserts this confidently
_CERTAINTY_PATTERNS = [
    re.compile(r'\b(?:definitely|certainly|undoubtedly|clearly|obviously|indeed)\b', re.IGNORECASE),
    re.compile(r'\b(?:it\s+is\s+(?:well\s*|widely\s*)?(?:known|established|accepted|understood))\b', re.IGNORECASE),
    re.compile(r'\b(?:proven|demonstrated|confirmed|verified|established)\b', re.IGNORECASE),
]


def _detect_hedging(claim_text: str) -> tuple[bool, int, list[str]]:
    """Detect hedging language. Returns (has_hedging, hedge_count, examples)."""
    examples: list[str] = []
    count = 0
    for pattern in _HEDGE_PATTERNS:
        for match in pattern.finditer(claim_text):
            examples.append(match.group(0))
            count += 1
    return count > 0, count, examples[:3]


def _detect_certainty(claim_text: str) -> tuple[bool, list[str]]:
    """Detect strong certainty language."""
    examples: list[str] = []
    for pattern in _CERTAINTY_PATTERNS:
        for match in pattern.finditer(claim_text):
            examples.append(match.group(0))
    return len(examples) > 0, examples[:3]


# ---------------------------------------------------------------------------
# Signal 3: Concept domain grounding
# ---------------------------------------------------------------------------

# Domains with well-established bodies of knowledge -- concepts in these
# domains are more likely to be established.
_WELL_ESTABLISHED_DOMAINS = frozenset({
    "physics", "mathematics", "chemistry", "biology",
    "computer_science",
})


def _domain_grounding_score(concept: Concept) -> float:
    """Score how well-grounded a concept's domain associations are.

    Returns 0.0-1.0 where higher = more established domain.
    """
    domains = concept.domain_associations
    if not domains:
        return 0.0
    # Fraction of domain weight in well-established domains
    total_weight = sum(domains.values())
    if total_weight == 0.0:
        return 0.0
    established_weight = sum(
        w for d, w in domains.items() if d in _WELL_ESTABLISHED_DOMAINS
    )
    return established_weight / total_weight


# ---------------------------------------------------------------------------
# Signal 4: Specificity detection
# ---------------------------------------------------------------------------

_SPECIFICITY_PATTERNS = [
    re.compile(r'\b\d{1,3}(?:\.\d+)?\s*%'),           # Percentages
    re.compile(r'\b\d{4}\b'),                           # Years
    re.compile(r'\b\d+(?:\.\d+)?\s*(?:ms|kg|km|MB|GB)'),  # Units
    re.compile(r'\b(?:only|exactly|precisely)\s+\d+'),  # Exact quantities
]


def _detect_specificity(claim_text: str) -> tuple[bool, list[str]]:
    """Detect highly specific claims that go beyond general knowledge."""
    examples: list[str] = []
    for pattern in _SPECIFICITY_PATTERNS:
        for match in pattern.finditer(claim_text):
            examples.append(match.group(0))
    return len(examples) > 0, examples[:3]


# ---------------------------------------------------------------------------
# Classification logic
# ---------------------------------------------------------------------------


def _classify_establishedness(
    claim: Claim,
    concepts: list[Concept],
) -> tuple[str, list[str], str]:
    """Classify a claim's establishedness using multi-signal heuristics.

    Returns: (level E1-E5, signals list, reasoning)
    """
    text = claim.text
    signals: list[str] = []
    signal_details: list[str] = []

    # --- Check claim-type prior ---
    type_prior = _CLAIM_TYPE_PRIORS.get(claim.claim_type)
    if type_prior:
        signals.append(f"claim_type_{claim.claim_type}")
        signal_details.append(f"claim type '{claim.claim_type}' maps to {type_prior}")
        reasoning = (
            f"This claim has type '{claim.claim_type}', which is classified as "
            f"{type_prior} by default. "
            f"{_type_prior_explanation(claim.claim_type)}"
        )
        return type_prior, signals, reasoning

    # --- Concept domain grounding ---
    # Find concepts referenced by this claim
    claim_concepts = [c for c in concepts if claim.id in c.referencing_claim_ids]
    domain_score = 0.0
    domain_signals: list[str] = []
    if claim_concepts:
        scores = [_domain_grounding_score(c) for c in claim_concepts]
        domain_score = sum(scores) / len(scores) if scores else 0.0
        for c in claim_concepts:
            if c.domain_associations:
                domain_signals.append(
                    f"'{c.canonical_name}' → {_format_domains(c.domain_associations)}"
                )

    # --- Hedging detection ---
    has_hedging, hedge_count, hedge_examples = _detect_hedging(text)

    # --- Certainty detection ---
    has_certainty, cert_examples = _detect_certainty(text)

    # --- Specificity detection ---
    has_specifics, spec_examples = _detect_specificity(text)

    # --- Determine level ---
    if domain_score >= 0.5 and not has_hedging:
        # Strong domain grounding without hedging → E2
        level = "E2"
        signals.append("strong_domain_grounding")
        signal_details.append(
            f"concepts grounded in established domains (score={domain_score:.1f})"
        )
        if has_certainty:
            signals.append("certainty_markers")
            signal_details.append(f"certainty markers: {cert_examples}")
        reasoning = (
            f"This claim references concepts grounded in well-established domains "
            f"({'; '.join(domain_signals[:2])}). "
            f"No hedging language detected. "
            f"This is consistent with domain-established knowledge (E2)."
        )

    elif has_hedging and hedge_count >= 2:
        # Strong hedging → E4 or E3
        if domain_score < 0.3:
            level = "E4"
            signals.append("heavy_hedging")
            signal_details.append(f"multiple hedging markers: {hedge_examples}")
            reasoning = (
                f"This claim uses significant hedging language "
                f"({', '.join(hedge_examples)}), indicating the model itself "
                f"is uncertain. Combined with low domain grounding "
                f"(score={domain_score:.1f}), this suggests the claim is "
                f"speculative or unverifiable by design (E4)."
            )
        else:
            level = "E3"
            signals.append("hedging_present")
            signals.append("some_domain_grounding")
            signal_details.append(f"hedging: {hedge_examples}")
            reasoning = (
                f"This claim uses hedging language "
                f"({', '.join(hedge_examples)}) but references concepts "
                f"with some domain grounding (score={domain_score:.1f}). "
                f"This is plausible but not definitively established (E3)."
            )

    elif has_specifics and domain_score < 0.3:
        # Specific claim without domain grounding → E3 or E5
        if domain_score == 0.0 and not claim_concepts:
            level = "E5"
            signals.append("no_domain_context")
            signal_details.append("no domain-associated concepts referenced")
            reasoning = (
                f"This claim makes specific assertions "
                f"({', '.join(spec_examples)}) but references no concepts "
                f"with domain associations. The analyzer cannot determine "
                f"establishedness and defaults to Unknown (E5)."
            )
        else:
            level = "E3"
            signals.append("specific_claim")
            signals.append("weak_domain_grounding")
            signal_details.append(f"specific assertions: {spec_examples}")
            reasoning = (
                f"This claim makes specific assertions "
                f"({', '.join(spec_examples)}) with limited domain grounding "
                f"(score={domain_score:.1f}). It is plausible but unverified (E3)."
            )

    elif domain_score >= 0.3:
        # Some domain grounding, no strong hedging → E2
        level = "E2"
        signals.append("domain_grounding")
        signal_details.append(f"domain score={domain_score:.1f}")
        if domain_signals:
            signal_details.append(f"concepts: {'; '.join(domain_signals[:2])}")
        reasoning = (
            f"This claim references concepts with domain associations "
            f"({'; '.join(domain_signals[:2]) if domain_signals else 'present'}). "
            f"Without contrary hedging signals, this suggests "
            f"domain-established knowledge (E2)."
        )

    else:
        # Default conservative
        level = "E3"
        signals.append("insufficient_signals")
        signal_details.append("insufficient signals for strong classification")
        reasoning = (
            f"This claim could not be strongly classified. "
            f"No clear domain grounding, hedging, or definitional structure "
            f"was detected. Conservative default: Plausible but Unverified (E3)."
        )

    # Add signal context to reasoning
    if signal_details:
        pass  # Already incorporated above

    return level, signals, reasoning


def _type_prior_explanation(claim_type: str) -> str:
    """Explain why a claim type maps to its default level."""
    explanations = {
        "conceptual_definition": "Definitions are self-contained and do not "
            "require external verification.",
        "meta_claim": "Meta-claims are about the response itself and are "
            "unverifiable by design.",
        "normative_claim": "Normative claims express values or ought-statements "
            "that cannot be empirically settled.",
        "predictive_claim": "Predictions about the future are inherently "
            "uncertain and go beyond established knowledge.",
    }
    return explanations.get(claim_type, "")


def _format_domains(domains: dict[str, float]) -> str:
    """Format domain associations for reasoning text."""
    top = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:2]
    return ", ".join(f"{d}({w:.1f})" for d, w in top)


def classify_establishedness(
    claims: list[Claim],
    concepts: list[Concept],
) -> list[EstablishednessAnnotation]:
    """Classify the establishedness of each claim.

    Args:
        claims: The ClaimSet from A2.
        concepts: The ConceptIndex from A3 (for domain context).

    Returns:
        List of EstablishednessAnnotation objects with signal-based reasoning.
    """
    annotations: list[EstablishednessAnnotation] = []
    for claim in claims:
        level, signals, reasoning = _classify_establishedness(claim, concepts)
        annotation = EstablishednessAnnotation(
            claim_id=claim.id,
            level=level,
            reasoning=reasoning,
        )
        annotations.append(annotation)
    return annotations


# ---------------------------------------------------------------------------
# Orchestration Analyzer wrapper
# ---------------------------------------------------------------------------


class EstablishednessAnalyzer(Analyzer):
    """A4: Classifies each claim by establishedness level (E1-E5).

    Input: ClaimSet from A2, ConceptIndex from A3
    Output: list[EstablishednessAnnotation]
    """

    declaration = AnalyzerDeclaration(
        id="a4",
        version="0.1.0",
        responsibility="Classify each claim by establishedness level (E1-E5) "
        "using multi-signal heuristics: claim type, concept domain grounding, "
        "hedging language, and specificity.",
        inputs=(
            AnalyzerInput("a2", "a2", required=True),
            AnalyzerInput("a3", "a3", required=True),
        ),
        output_type=list,
        layer="classification",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        """Execute establishedness classification."""
        a2_output = context.get_output("a2", "a2")
        if a2_output is None:
            raise AnalyzerError("A4 requires A2 (Claim Extractor) output.")
        a3_output = context.get_output("a3", "a3")
        if a3_output is None:
            raise AnalyzerError("A4 requires A3 (Concept Extractor) output.")

        claims = a2_output.get("claims", [])
        concepts = a3_output.get("concepts", [])

        annotations = classify_establishedness(claims, concepts)
        return {"establishedness_annotations": annotations}


def register(registry: AnalyzerRegistry) -> None:
    """Register the A4 Establishedness analyzer."""
    registry.register(
        EstablishednessAnalyzer.declaration,
        lambda: EstablishednessAnalyzer(),
    )
