"""A6: Novelty Analyzer -- heuristic N1-N5 classification without external knowledge.

Phase 4.1: Evaluates novelty indicators from observable text signals only.
Uses A3 concept types (novel_construct), claim type signals, specificity
patterns, and established-framing markers. Does NOT consult external
knowledge bases or prior literature.

Knowledge boundary: A6-001. Classifications are heuristic indicators,
not verified novelty judgments.

Spec reference: OutputLens Framework Specification, Chapter 13 (A6).
"""

from __future__ import annotations

import re
from typing import Any

from outputlens.analysis.model import Claim, Concept, NoveltyAnnotation
from outputlens.orchestration.analyzer import (
    AnalysisContext,
    Analyzer,
    AnalyzerDeclaration,
    AnalyzerError,
    AnalyzerInput,
)
from outputlens.orchestration.engine import AnalyzerRegistry


# ---------------------------------------------------------------------------
# Signal 1: Concept-type-based novelty indicators
# ---------------------------------------------------------------------------

# Concepts flagged by A3 as novel_construct suggest the response introduces
# new ideas. Any claim referencing such a concept is likely N3+.
def _has_novel_construct(concepts: list[Concept], claim: Claim) -> bool:
    for c in concepts:
        if c.concept_type == "novel_construct" and claim.id in c.referencing_claim_ids:
            return True
    return False


# ---------------------------------------------------------------------------
# Signal 2: Claim-type-based priors
# ---------------------------------------------------------------------------

_CLAIM_TYPE_NOVELTY: dict[str, str] = {
    "conceptual_definition": "N1",   # Definitions present canonical knowledge
    "methodological_claim": "N1",    # Standard methods are canonical
    "meta_claim": "N5",              # Meta-claims are about the response, not knowledge
    "predictive_claim": "N3",        # Predictions go beyond established knowledge
    "normative_claim": "N3",         # Normative claims are not purely factual
}


# ---------------------------------------------------------------------------
# Signal 3: Established-framing markers (suggest canonical knowledge)
# ---------------------------------------------------------------------------

_ESTABLISHED_FRAMING = [
    re.compile(r'\b(?:is\s+(?:a|an|the)|refers?\s+to|is\s+defined\s+as)\b', re.IGNORECASE),
    re.compile(r'\b(?:according\s+to\s+(?:standard|established|conventional))\b', re.IGNORECASE),
    re.compile(r'\b(?:it\s+is\s+(?:well|widely)\s+(?:known|accepted|understood))\b', re.IGNORECASE),
    re.compile(r'\b(?:commonly\s+(?:known|used|referred\s+to))\b', re.IGNORECASE),
    re.compile(r'\b(?:in\s+(?:standard|traditional|conventional)\s+(?:practice|theory|usage))\b', re.IGNORECASE),
    re.compile(r'\b(?:textbook|canonical|classic(?:al)?)\s+(?:example|case|definition)\b', re.IGNORECASE),
]


def _detect_established_framing(text: str) -> bool:
    for pattern in _ESTABLISHED_FRAMING:
        if pattern.search(text):
            return True
    return False


# ---------------------------------------------------------------------------
# Signal 4: Specificity + absence of domain grounding → possible novelty
# ---------------------------------------------------------------------------

_SPECIFICITY_PATTERNS = [
    re.compile(r'\b\d{1,3}(?:\.\d+)?\s*%'),
    re.compile(r'\b\d+(?:\.\d+)?\s*(?:ms|kg|km|MB|GB|Hz|nm)\b'),
    re.compile(r'\b(?:only|exactly|precisely|specifically)\s+\d+'),
]


def _detect_specificity(text: str) -> list[str]:
    examples = []
    for pattern in _SPECIFICITY_PATTERNS:
        for match in pattern.finditer(text):
            examples.append(match.group(0))
    return examples[:3]


# ---------------------------------------------------------------------------
# Classification logic
# ---------------------------------------------------------------------------


def _classify_novelty(
    claim: Claim,
    concepts: list[Concept],
) -> tuple[str, list[str], str]:
    """Classify a claim's novelty using text-signal heuristics.

    Returns: (level N1-N5, signals list, reasoning)
    """
    text = claim.text
    signals: list[str] = []

    # --- Check claim-type prior ---
    type_prior = _CLAIM_TYPE_NOVELTY.get(claim.claim_type)
    if type_prior:
        signals.append(f"claim_type_{claim.claim_type}")
        if type_prior == "N1":
            reasoning = (
                f"This claim has type '{claim.claim_type}', which typically "
                f"presents canonical, well-established material (N1)."
            )
            return "N1", signals, reasoning
        elif type_prior == "N3":
            reasoning = (
                f"This claim has type '{claim.claim_type}', which inherently "
                f"goes beyond established factual knowledge (N3)."
            )
            return "N3", signals, reasoning
        # N5 for meta: fall through to default handling

    # --- Novel construct detection ---
    has_novel = _has_novel_construct(concepts, claim)
    if has_novel:
        signals.append("novel_construct_referenced")

    # --- Established framing ---
    has_framing = _detect_established_framing(text)
    if has_framing:
        signals.append("established_framing")

    # --- Specificity ---
    specifics = _detect_specificity(text)
    has_specifics = len(specifics) > 0
    if has_specifics:
        signals.append("specific_claim")
        signals.append(f"details: {specifics}")

    # --- Determine level ---
    if has_novel and has_specifics:
        level = "N4"
        signals.append("high_novelty_indicators")
        reasoning = (
            f"This claim references a novel construct and makes specific "
            f"assertions ({', '.join(specifics)}). These combined signals "
            f"suggest the claim may be apparently original (N4). This is a "
            f"heuristic assessment based on text patterns, not external "
            f"verification."
        )
    elif has_novel:
        level = "N3"
        signals.append("novelty_indicator")
        reasoning = (
            f"This claim references a concept flagged as a novel construct. "
            f"This suggests the claim may go beyond established knowledge (N3). "
            f"This assessment is based on A3 concept typing, not external "
            f"novelty verification."
        )
    elif has_framing and not has_specifics:
        level = "N1"
        reasoning = (
            f"This claim uses established-framing language consistent with "
            f"presenting canonical material. No contrary novelty signals "
            f"detected. Classified as Canonical (N1)."
        )
    elif has_specifics and not has_framing:
        level = "N3"
        reasoning = (
            f"This claim makes specific assertions ({', '.join(specifics)}) "
            f"without established-framing context. It may represent a "
            f"non-trivial synthesis or go beyond canonical knowledge (N3). "
            f"This is a heuristic signal, not a verified novelty assessment."
        )
    elif claim.claim_type == "factual_assertion" and has_framing:
        level = "N2"
        signals.append("framed_factual")
        reasoning = (
            f"This factual claim uses established-framing language while "
            f"making a specific assertion. This pattern is consistent with "
            f"a non-trivial synthesis of known ideas (N2)."
        )
    else:
        level = "N5"
        signals.append("insufficient_signals")
        reasoning = (
            f"Insufficient signals to assess novelty. No novel constructs, "
            f"established framing, or specific-claim patterns were detected. "
            f"Conservative default: Uncertain (N5)."
        )

    return level, signals, reasoning


def classify_novelty(
    claims: list[Claim],
    concepts: list[Concept],
) -> list[NoveltyAnnotation]:
    """Classify the novelty of each claim using heuristic text signals.

    Args:
        claims: The ClaimSet from A2.
        concepts: The ConceptIndex from A3.

    Returns:
        List of NoveltyAnnotation objects.
    """
    annotations: list[NoveltyAnnotation] = []
    for claim in claims:
        level, signals, reasoning = _classify_novelty(claim, concepts)
        annotation = NoveltyAnnotation(
            claim_id=claim.id,
            level=level,
            reasoning=reasoning,
        )
        annotations.append(annotation)
    return annotations


# ---------------------------------------------------------------------------
# Orchestration Analyzer wrapper
# ---------------------------------------------------------------------------


class NoveltyAnalyzer(Analyzer):
    """A6: Classifies each claim by novelty level (N1-N5) using text signals.

    Input: ClaimSet from A2, ConceptIndex from A3
    Output: list[NoveltyAnnotation]
    """

    declaration = AnalyzerDeclaration(
        id="a6",
        version="0.1.0",
        responsibility="Classify each claim by novelty level (N1-N5) using "
        "heuristic text signals: concept types, claim types, established "
        "framing markers, and specificity patterns. Does not consult "
        "external knowledge sources.",
        inputs=(
            AnalyzerInput("a2", "a2", required=True),
            AnalyzerInput("a3", "a3", required=True),
        ),
        output_type=list,
        layer="classification",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        a2_output = context.get_output("a2", "a2")
        a3_output = context.get_output("a3", "a3")
        if a2_output is None:
            raise AnalyzerError("A6 requires A2 output.")
        if a3_output is None:
            raise AnalyzerError("A6 requires A3 output.")

        claims = a2_output.get("claims", [])
        concepts = a3_output.get("concepts", [])
        annotations = classify_novelty(claims, concepts)
        return {"novelty_annotations": annotations}


def register(registry: AnalyzerRegistry) -> None:
    registry.register(NoveltyAnalyzer.declaration, lambda: NoveltyAnalyzer())
