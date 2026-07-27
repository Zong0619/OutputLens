"""A11 + A12 + A13: Synthesis analyzers -- Novelty Index, Overconfidence,
and Structural Integrity.

Phase 4.3: Pure computation from classification and structure outputs.
- A11: Novelty Index from A6 (NoveltyAnnotations)
- A12: Overconfidence Detector from A2 (claims, confidence markers) + A4
- A13: Structural Integrity from A7 (ClaimGraph) + A4

Spec reference: OutputLens Framework Specification, Chapter 15 (A11-A13).
"""

from __future__ import annotations

from typing import Any

from outputlens.analysis.model import (
    Claim,
    ClaimGraph,
    EstablishednessAnnotation,
    NoveltyAnnotation,
    NoveltyIndex,
    OverconfidenceClaim,
    OverconfidenceReport,
    StructuralIntegrityReport,
)
from outputlens.orchestration.analyzer import (
    AnalysisContext,
    Analyzer,
    AnalyzerDeclaration,
    AnalyzerError,
    AnalyzerInput,
)
from outputlens.orchestration.engine import AnalyzerRegistry


# ---------------------------------------------------------------------------
# A11: Novelty Index Calculator
# ---------------------------------------------------------------------------


def compute_novelty_index(
    annotations: list[NoveltyAnnotation],
) -> NoveltyIndex:
    total = len(annotations)
    if total == 0:
        return NoveltyIndex(novelty_proportion=0.0)

    n3 = sum(1 for a in annotations if a.level == "N3")
    n4 = sum(1 for a in annotations if a.level == "N4")
    n5 = sum(1 for a in annotations if a.level == "N5")
    proportion = (n3 + n4 + n5) / total

    return NoveltyIndex(
        novelty_proportion=round(proportion, 3),
        n3_count=n3,
        n4_count=n4,
        n5_count=n5,
    )


class NoveltyIndexCalculator(Analyzer):
    declaration = AnalyzerDeclaration(
        id="a11",
        version="0.1.0",
        responsibility="Compute the proportion of claims at N3+ from novelty "
        "classifications.",
        inputs=(AnalyzerInput("a6", "a6", required=True),),
        output_type=NoveltyIndex,
        layer="synthesis",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        a6_out = context.get_output("a6", "a6")
        if a6_out is None:
            raise AnalyzerError("A11 requires A6 output.")
        anns = a6_out.get("novelty_annotations", [])
        return {"novelty_index": compute_novelty_index(anns)}


# ---------------------------------------------------------------------------
# A12: Overconfidence Detector
# ---------------------------------------------------------------------------


def detect_overconfidence(
    claims: list[Claim],
    e_annotations: list[EstablishednessAnnotation],
) -> OverconfidenceReport:
    """Detect claims where linguistic confidence conflicts with low establishedness.

    A claim is overconfident if it has certainty markers AND is classified
    as E3, E4, or E5 (low establishedness).
    """
    e_map = {a.claim_id: a.level for a in e_annotations}
    overconfident: list[OverconfidenceClaim] = []

    for claim in claims:
        e_level = e_map.get(claim.id, "E5")
        if e_level not in ("E3", "E4", "E5"):
            continue

        # Check for confidence markers on the claim
        if not claim.confidence_markers:
            continue

        certainty_markers = [
            cm for cm in claim.confidence_markers if cm.type == "certainty"
        ]
        if not certainty_markers:
            continue

        marker_examples = [cm.expression for cm in certainty_markers[:2]]
        description = (
            f"Claim states with confidence ({', '.join(marker_examples)}) "
            f"but is classified as {e_level} (low establishedness)."
        )
        overconfident.append(OverconfidenceClaim(
            claim_id=claim.id,
            confidence_level="high",
            establishedness_level=e_level,
            description=description,
        ))

    if overconfident:
        summary = (
            f"{len(overconfident)} claim(s) express high confidence "
            f"but have low establishedness classifications. "
            f"This pattern may indicate the model is overstating certainty."
        )
    else:
        summary = "No overconfidence pattern detected."

    return OverconfidenceReport(
        overconfident_claims=tuple(overconfident),
        pattern_summary=summary,
    )


class OverconfidenceDetector(Analyzer):
    declaration = AnalyzerDeclaration(
        id="a12",
        version="0.1.0",
        responsibility="Detect claims where linguistic confidence conflicts "
        "with epistemological establishedness.",
        inputs=(
            AnalyzerInput("a2", "a2", required=True),
            AnalyzerInput("a4", "a4", required=True),
        ),
        output_type=OverconfidenceReport,
        layer="synthesis",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        a2_out = context.get_output("a2", "a2")
        a4_out = context.get_output("a4", "a4")
        if a2_out is None:
            raise AnalyzerError("A12 requires A2 output.")
        if a4_out is None:
            raise AnalyzerError("A12 requires A4 output.")
        claims = a2_out.get("claims", [])
        e_anns = a4_out.get("establishedness_annotations", [])
        return {"overconfidence_report": detect_overconfidence(claims, e_anns)}


# ---------------------------------------------------------------------------
# A13: Structural Integrity Analyzer
# ---------------------------------------------------------------------------


def compute_structural_integrity(
    graph: ClaimGraph,
    e_annotations: list[EstablishednessAnnotation],
    total_claims: int,
) -> StructuralIntegrityReport:
    """Compute structural integrity metrics from the claim graph.

    Foundation health: proportion of foundational claims that are well-established.
    """
    e_map = {a.claim_id: a.level for a in e_annotations}
    foundational = graph.foundational_claim_ids

    if foundational:
        established_foundational = sum(
            1 for cid in foundational if e_map.get(cid, "E5") in ("E1", "E2")
        )
        foundation_health = established_foundational / len(foundational)
    else:
        foundation_health = 1.0  # No foundations → no foundation risk

    orphan_proportion = (
        len(graph.orphan_claim_ids) / total_claims if total_claims > 0 else 0.0
    )

    return StructuralIntegrityReport(
        foundation_health=round(foundation_health, 3),
        contradiction_count=len(graph.contradiction_clusters),
        orphan_proportion=round(orphan_proportion, 3),
        cascading_uncertainty_chain_count=len(graph.cascading_uncertainty_chains),
    )


class StructuralIntegrityAnalyzer(Analyzer):
    declaration = AnalyzerDeclaration(
        id="a13",
        version="0.1.0",
        responsibility="Assess the argument structure: foundation health, "
        "contradictions, orphans, and cascading uncertainty.",
        inputs=(
            AnalyzerInput("a7", "a7", required=True),
            AnalyzerInput("a2", "a2", required=True),
            AnalyzerInput("a4", "a4", required=True),
        ),
        output_type=StructuralIntegrityReport,
        layer="synthesis",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        a7_out = context.get_output("a7", "a7")
        a2_out = context.get_output("a2", "a2")
        a4_out = context.get_output("a4", "a4")
        if a7_out is None:
            raise AnalyzerError("A13 requires A7 output.")
        if a2_out is None:
            raise AnalyzerError("A13 requires A2 output.")
        if a4_out is None:
            raise AnalyzerError("A13 requires A4 output.")

        graph = a7_out.get("claim_graph")
        claims = a2_out.get("claims", [])
        e_anns = a4_out.get("establishedness_annotations", [])

        report = compute_structural_integrity(graph, e_anns, len(claims))
        return {"structural_integrity_report": report}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry: AnalyzerRegistry) -> None:
    registry.register(NoveltyIndexCalculator.declaration,
                      lambda: NoveltyIndexCalculator())
    registry.register(OverconfidenceDetector.declaration,
                      lambda: OverconfidenceDetector())
    registry.register(StructuralIntegrityAnalyzer.declaration,
                      lambda: StructuralIntegrityAnalyzer())
