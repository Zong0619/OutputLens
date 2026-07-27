"""A9 + A10: Synthesis analyzers -- Trust Profile and Evidence Gap.

Phase 3.3: Pure computation from classification outputs.
- A9 (Trust Profile Generator): aggregates E-levels and R-levels into a
  three-part trust distribution.
- A10 (Evidence Gap Analyzer): computes evidence gap ratio and breakdowns.

Spec reference: OutputLens Framework Specification, Chapter 15 (A9, A10).
"""

from __future__ import annotations

from typing import Any

from outputlens.analysis.model import (
    EstablishednessAnnotation,
    EvidenceAnnotation,
    EvidenceGapReport,
    TrustProfile,
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
# A9: Trust Profile Generator
# ---------------------------------------------------------------------------


def compute_trust_profile(
    establishedness_annotations: list[EstablishednessAnnotation],
    evidence_annotations: list[EvidenceAnnotation],
) -> TrustProfile:
    """Compute the three-part trust distribution.

    Logic:
    - established: claims at E1 (Common Knowledge) or E2 (Domain Established)
    - plausible: claims at E3 (Plausible but Unverified)
    - needs_verification: claims at E4 (Unverifiable), E5 (Unknown), or
      any claim at R4 (Evidence Essential) regardless of E-level

    Args:
        establishedness_annotations: From A4.
        evidence_annotations: From A5.

    Returns:
        TrustProfile with percentages summing to 100.
    """
    total = len(establishedness_annotations)
    if total == 0:
        return TrustProfile(
            established_pct=0.0,
            plausible_pct=0.0,
            needs_verification_pct=100.0,
        )

    # Build a set of claim_ids at R4
    r4_claims: set[str] = {
        ann.claim_id for ann in evidence_annotations if ann.level == "R4"
    }

    established = 0
    plausible = 0
    needs_verification = 0

    for ann in establishedness_annotations:
        cid = ann.claim_id
        if cid in r4_claims:
            needs_verification += 1
        elif ann.level in ("E1", "E2"):
            established += 1
        elif ann.level == "E3":
            plausible += 1
        else:
            needs_verification += 1  # E4, E5

    # Compute percentages with rounding compensation on the last value
    ep = round(established / total * 100, 1)
    pp = round(plausible / total * 100, 1)
    nvp = round(100.0 - ep - pp, 1)  # Last value absorbs rounding error

    return TrustProfile(
        established_pct=ep,
        plausible_pct=pp,
        needs_verification_pct=nvp,
    )


class TrustProfileGenerator(Analyzer):
    """A9: Generates the three-part trust distribution."""

    declaration = AnalyzerDeclaration(
        id="a9",
        version="0.1.0",
        responsibility="Compute the three-part trust distribution from "
        "establishedness and evidence classifications.",
        inputs=(
            AnalyzerInput("a4", "a4", required=True),
            AnalyzerInput("a5", "a5", required=True),
        ),
        output_type=TrustProfile,
        layer="synthesis",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        a4_out = context.get_output("a4", "a4")
        a5_out = context.get_output("a5", "a5")
        if a4_out is None:
            raise AnalyzerError("A9 requires A4 output.")
        if a5_out is None:
            raise AnalyzerError("A9 requires A5 output.")

        e_anns = a4_out.get("establishedness_annotations", [])
        ev_anns = a5_out.get("evidence_annotations", [])

        profile = compute_trust_profile(e_anns, ev_anns)
        return {"trust_profile": profile}


# ---------------------------------------------------------------------------
# A10: Evidence Gap Analyzer
# ---------------------------------------------------------------------------


def compute_evidence_gap(
    evidence_annotations: list[EvidenceAnnotation],
) -> EvidenceGapReport:
    """Compute the evidence gap report.

    Args:
        evidence_annotations: From A5.

    Returns:
        EvidenceGapReport with gap ratio and breakdowns.
    """
    total = len(evidence_annotations)
    if total == 0:
        return EvidenceGapReport(gap_ratio=0.0, r3_count=0, r4_count=0)

    r3_count = sum(1 for a in evidence_annotations if a.level == "R3")
    r4_count = sum(1 for a in evidence_annotations if a.level == "R4")
    gap_ratio = (r3_count + r4_count) / total

    return EvidenceGapReport(
        gap_ratio=round(gap_ratio, 3),
        r3_count=r3_count,
        r4_count=r4_count,
    )


class EvidenceGapAnalyzer(Analyzer):
    """A10: Computes the evidence gap report."""

    declaration = AnalyzerDeclaration(
        id="a10",
        version="0.1.0",
        responsibility="Compute the evidence gap ratio and breakdown from "
        "evidence requirement classifications.",
        inputs=(
            AnalyzerInput("a5", "a5", required=True),
        ),
        output_type=EvidenceGapReport,
        layer="synthesis",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        a5_out = context.get_output("a5", "a5")
        if a5_out is None:
            raise AnalyzerError("A10 requires A5 output.")

        ev_anns = a5_out.get("evidence_annotations", [])
        report = compute_evidence_gap(ev_anns)
        return {"evidence_gap_report": report}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry: AnalyzerRegistry) -> None:
    """Register A9 and A10."""
    registry.register(TrustProfileGenerator.declaration, lambda: TrustProfileGenerator())
    registry.register(EvidenceGapAnalyzer.declaration, lambda: EvidenceGapAnalyzer())
