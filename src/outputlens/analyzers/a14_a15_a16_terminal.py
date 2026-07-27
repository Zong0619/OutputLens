"""A14 + A15 + A16: Final synthesis and terminal analyzers.

Phase 5.2-5.4:
- A14: Conceptual Coherence Analyzer
- A15: Response Narrative Generator (rendering layer, per A15-001)
- A16: Verification Punchlist Generator (investigation priorities, per A16-001)

Spec reference: OutputLens Framework Specification, Chapters 15-16.
"""

from __future__ import annotations

from typing import Any

from outputlens.analysis.model import (
    Claim,
    ClaimGraph,
    CoherenceReport,
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
from outputlens.orchestration.analyzer import (
    AnalysisContext,
    Analyzer,
    AnalyzerDeclaration,
    AnalyzerError,
    AnalyzerInput,
)
from outputlens.orchestration.engine import AnalyzerRegistry


# ===================================================================
# A14: Conceptual Coherence Analyzer
# ===================================================================


def compute_coherence(graph: ConceptGraph, total_concepts: int) -> CoherenceReport:
    """Compute conceptual coherence metrics."""
    rel_count = len(graph.relationships)
    if total_concepts <= 1:
        return CoherenceReport(
            graph_connectivity=1.0,
            cluster_count=1 if total_concepts == 1 else 0,
            fragmentation_flag=False,
        )

    # Connectivity: fraction of concepts with at least one relationship
    connected: set[str] = set()
    for rel in graph.relationships:
        connected.add(rel.source_concept_id)
        connected.add(rel.target_concept_id)
    connectivity = len(connected) / total_concepts if total_concepts > 0 else 1.0

    # Cluster detection via simple connected components
    adj: dict[str, set[str]] = {}
    for rel in graph.relationships:
        adj.setdefault(rel.source_concept_id, set()).add(rel.target_concept_id)
        adj.setdefault(rel.target_concept_id, set()).add(rel.source_concept_id)
    visited: set[str] = set()
    clusters = 0
    for node in adj:
        if node in visited:
            continue
        clusters += 1
        stack = [node]
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            stack.extend(adj.get(n, set()) - visited)
    # Concepts not in any relationship are isolated clusters
    all_ids = set()
    for rel in graph.relationships:
        all_ids.add(rel.source_concept_id)
        all_ids.add(rel.target_concept_id)
    isolated = total_concepts - len(all_ids)
    clusters += isolated

    fragmentation = connectivity < 0.5 or clusters >= 4

    # Average path length (simple approximation)
    avg_path = 0.0
    if len(adj) >= 2:
        avg_path = round(2.0 / connectivity, 1) if connectivity > 0 else 0.0

    return CoherenceReport(
        graph_connectivity=round(connectivity, 3),
        cluster_count=clusters,
        average_path_length=avg_path,
        bridge_concept_ids=graph.bridge_concept_ids,
        fragmentation_flag=fragmentation,
    )


class ConceptualCoherenceAnalyzer(Analyzer):
    declaration = AnalyzerDeclaration(
        id="a14",
        version="0.1.0",
        responsibility="Compute conceptual coherence metrics from the concept graph.",
        inputs=(
            AnalyzerInput("a8", "a8", required=True),
            AnalyzerInput("a3", "a3", required=True),
        ),
        output_type=CoherenceReport,
        layer="synthesis",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        a8_out = context.get_output("a8", "a8")
        a3_out = context.get_output("a3", "a3")
        if a8_out is None:
            raise AnalyzerError("A14 requires A8 output.")
        if a3_out is None:
            raise AnalyzerError("A14 requires A3 output.")
        graph = a8_out.get("concept_graph", ConceptGraph())
        concepts = a3_out.get("concepts", [])
        return {"coherence_report": compute_coherence(graph, len(concepts))}


# ===================================================================
# A15: Response Narrative Generator (rendering layer per A15-001)
# ===================================================================


def generate_narrative(
    trust: TrustProfile,
    evidence_gap: EvidenceGapReport,
    novelty: NoveltyIndex,
    overconfidence: OverconfidenceReport,
    structural: StructuralIntegrityReport,
    coherence: CoherenceReport,
) -> ResponseNarrative:
    """Generate a 3-5 sentence plain-language summary from synthesis outputs.

    Per A15-001: This is a rendering layer. It does not perform new analysis,
    create classifications, or override analyzer results.
    """
    parts: list[str] = []

    # Trust profile -- always first
    if trust.established_pct >= 50:
        parts.append(
            f"This response is largely grounded in established knowledge "
            f"({trust.established_pct:.0f}% of claims), "
        )
    elif trust.needs_verification_pct >= 30:
        parts.append(
            f"A significant portion of this response requires verification "
            f"({trust.needs_verification_pct:.0f}% of claims), "
        )
    else:
        parts.append(
            f"This response contains a mix of established knowledge "
            f"({trust.established_pct:.0f}%) and claims needing investigation "
            f"({trust.needs_verification_pct:.0f}%). "
        )

    # Evidence gap
    if evidence_gap.gap_ratio >= 0.5:
        parts.append(
            f"More than half of the claims lack supporting evidence "
            f"({evidence_gap.r4_count} claims provide no evidence at all). "
        )
    elif evidence_gap.r4_count > 0:
        parts.append(
            f"{evidence_gap.r4_count} claim(s) make specific assertions "
            f"without providing supporting evidence. "
        )

    # Overconfidence
    if len(overconfidence.overconfident_claims) > 0:
        parts.append(
            f"{len(overconfidence.overconfident_claims)} claim(s) express "
            f"high confidence but have low establishedness. "
        )

    # Structural integrity
    if structural.contradiction_count > 0:
        parts.append(
            f"The response contains {structural.contradiction_count} "
            f"contradiction cluster(s) that may indicate internal inconsistency. "
        )
    if structural.orphan_proportion > 0.3:
        parts.append(
            f"{structural.orphan_proportion:.0%} of claims are structurally "
            f"disconnected from the response's argument. "
        )

    # Coherence
    if coherence.fragmentation_flag:
        parts.append(
            "The concepts in this response are fragmented across multiple "
            "disconnected topic areas. "
        )

    # Novelty
    if novelty.novelty_proportion > 0.3:
        parts.append(
            f"{novelty.novelty_proportion:.0%} of claims go beyond established "
            f"knowledge. This may be appropriate for exploratory contexts "
            f"but requires additional scrutiny for factual use. "
        )

    # Fallback
    if not parts:
        parts.append(
            "The analysis did not identify notable patterns requiring attention. "
        )

    narrative = "".join(parts).strip()
    # Ensure minimum length
    if len(narrative) < 50:
        narrative += (
            " Review the verification punchlist for specific claims to investigate."
        )

    return ResponseNarrative(narrative_text=narrative)


class ResponseNarrativeGenerator(Analyzer):
    declaration = AnalyzerDeclaration(
        id="a15",
        version="0.1.0",
        responsibility="Generate a plain-language summary of analysis findings. "
        "Rendering layer only -- no new analysis per A15-001.",
        inputs=(
            AnalyzerInput("a9", "a9", required=True),
            AnalyzerInput("a10", "a10", required=True),
            AnalyzerInput("a11", "a11", required=True),
            AnalyzerInput("a12", "a12", required=True),
            AnalyzerInput("a13", "a13", required=True),
            AnalyzerInput("a14", "a14", required=True),
        ),
        output_type=ResponseNarrative,
        layer="synthesis",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        def _get_output(aid: str, key: str) -> Any | None:
            out = context.get_output(aid, aid)
            return out.get(key) if isinstance(out, dict) else None

        trust = _get_output("a9", "trust_profile")
        ev_gap = _get_output("a10", "evidence_gap_report")
        novelty = _get_output("a11", "novelty_index")
        overconf = _get_output("a12", "overconfidence_report")
        struct = _get_output("a13", "structural_integrity_report")
        coherence = _get_output("a14", "coherence_report")

        # Provide safe defaults for missing optional inputs
        if trust is None:
            trust = TrustProfile(established_pct=0, plausible_pct=0, needs_verification_pct=0)
        if ev_gap is None:
            ev_gap = EvidenceGapReport(gap_ratio=0, r3_count=0, r4_count=0)
        if novelty is None:
            novelty = NoveltyIndex(novelty_proportion=0)
        if overconf is None:
            overconf = OverconfidenceReport()
        if struct is None:
            struct = StructuralIntegrityReport(
                foundation_health=1.0, contradiction_count=0, orphan_proportion=0.0)
        if coherence is None:
            coherence = CoherenceReport(graph_connectivity=1.0, cluster_count=0)

        narrative = generate_narrative(trust, ev_gap, novelty, overconf, struct, coherence)
        return {"response_narrative": narrative}


# ===================================================================
# A16: Verification Punchlist Generator (investigation priorities per A16-001)
# ===================================================================


def _score_claim(
    claim: Claim,
    e_anns: dict[str, str],
    ev_anns: dict[str, str],
    n_anns: dict[str, str],
    graph: ClaimGraph | None,
    overconfident_ids: set[str],
) -> tuple[int, str, str, str, str]:
    """Score a claim for punchlist inclusion. Returns (score, trigger, importance, risk, verification)."""
    cid = claim.id
    score = 0
    triggers: list[str] = []
    importance = "peripheral"
    risk = "Minimal impact if incorrect."
    verification = "Review the claim against known sources."

    e_level = e_anns.get(cid, "E5")
    ev_level = ev_anns.get(cid, "R4")
    n_level = n_anns.get(cid, "N5")

    # Evidence urgency
    if ev_level == "R4":
        score += 4
        triggers.append("no_evidence")
        verification = "Search for primary sources or data supporting this claim."
        risk = "Claim is presented as fact without supporting evidence."
    elif ev_level == "R3":
        score += 2
        triggers.append("no_evidence")

    # Novelty trigger
    if n_level in ("N3", "N4"):
        score += 2
        triggers.append("novel_claim")
        risk = "Claim may represent novel or non-standard information."

    # Overconfidence
    if cid in overconfident_ids:
        score += 3
        triggers.append("overconfident")
        risk = "Claim is stated confidently but has low epistemological support."

    # Structural importance
    if graph:
        if cid in graph.foundational_claim_ids:
            score += 3
            importance = "foundational"
            risk += " This claim is foundational to the response's argument."
        elif cid not in graph.orphan_claim_ids:
            importance = "structural"
        if cid in graph.orphan_claim_ids:
            triggers.append("orphaned")
            score += 1

    # Contradiction
    if graph:
        for cluster in graph.contradiction_clusters:
            if cid in cluster:
                score += 3
                triggers.append("contradicted")
                risk += " This claim is contradicted by another claim in the response."
                break

    trigger = triggers[0] if triggers else "no_evidence"
    return score, trigger, importance, risk, verification


def generate_punchlist(
    claims: list[Claim],
    e_annotations: list[EstablishednessAnnotation],
    ev_annotations: list[EvidenceAnnotation],
    n_annotations: list[NoveltyAnnotation],
    claim_graph: ClaimGraph | None,
    overconfidence: OverconfidenceReport | None,
) -> VerificationPunchlist:
    """Generate the prioritized verification punchlist.

    Per A16-001: Generates investigation priorities only. Does not verify
    claims, determine truth, or provide correctness judgments.
    """
    e_map = {a.claim_id: a.level for a in e_annotations}
    ev_map = {a.claim_id: a.level for a in ev_annotations}
    n_map = {a.claim_id: a.level for a in n_annotations}
    overconfident_ids = {oc.claim_id for oc in (overconfidence.overconfident_claims if overconfidence else ())}

    scored: list[tuple[int, Claim, str, str, str, str]] = []
    for claim in claims:
        score, trigger, importance, risk, verification = _score_claim(
            claim, e_map, ev_map, n_map, claim_graph, overconfident_ids)
        if score > 0:
            scored.append((score, claim, trigger, importance, risk, verification))

    scored.sort(key=lambda x: x[0], reverse=True)

    entries: list[PunchlistEntry] = []
    for rank, (score, claim, trigger, importance, risk, verification) in enumerate(scored[:10], 1):
        entries.append(PunchlistEntry(
            rank=rank,
            claim_id=claim.id,
            claim_text=claim.text[:200],
            attention_trigger=trigger,
            structural_importance=importance,
            risk_if_wrong=risk,
            suggested_verification=verification,
        ))

    if len(entries) >= 5:
        severity = "systematic_verification_needed"
    elif len(entries) >= 2:
        severity = "several_concerns"
    else:
        severity = "minor_flags"

    return VerificationPunchlist(
        entries=tuple(entries),
        overall_severity=severity,
        prioritization_rationale=(
            "Claims ranked by verification urgency, structural importance, "
            "novelty signals, and overconfidence patterns."
        ),
    )


class VerificationPunchlistGenerator(Analyzer):
    declaration = AnalyzerDeclaration(
        id="a16",
        version="0.1.0",
        responsibility="Generate prioritized list of claims to investigate. "
        "Investigation priorities only -- no truth determination per A16-001.",
        inputs=(
            AnalyzerInput("a2", "a2", required=True),
            AnalyzerInput("a4", "a4", required=True),
            AnalyzerInput("a5", "a5", required=True),
            AnalyzerInput("a6", "a6", required=True),
            AnalyzerInput("a7", "a7", required=True),
            AnalyzerInput("a9", "a9", required=False),
            AnalyzerInput("a12", "a12", required=False),
            AnalyzerInput("a13", "a13", required=False),
        ),
        output_type=VerificationPunchlist,
        layer="terminal",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        def _get( aid: str, key: str) -> Any | None:
            out = context.get_output(aid, aid)
            return out.get(key) if isinstance(out, dict) else None

        claims = _get("a2", "claims") or []
        e_anns = _get("a4", "establishedness_annotations") or []
        ev_anns = _get("a5", "evidence_annotations") or []
        n_anns = _get("a6", "novelty_annotations") or []
        graph = _get("a7", "claim_graph")
        overconf = _get("a12", "overconfidence_report")

        punchlist = generate_punchlist(claims, e_anns, ev_anns, n_anns, graph, overconf)
        return {"verification_punchlist": punchlist}


# ===================================================================
# Registration
# ===================================================================


def register(registry: AnalyzerRegistry) -> None:
    registry.register(ConceptualCoherenceAnalyzer.declaration,
                      lambda: ConceptualCoherenceAnalyzer())
    registry.register(ResponseNarrativeGenerator.declaration,
                      lambda: ResponseNarrativeGenerator())
    registry.register(VerificationPunchlistGenerator.declaration,
                      lambda: VerificationPunchlistGenerator())
