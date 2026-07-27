"""A8: Concept Relationship Mapper -- infers concept graph from claim relationships.

Phase 5.1: Builds a concept graph by projecting claim relationships onto the
concepts they reference. Supplements with explicit relational language patterns.

Spec reference: OutputLens Framework Specification, Chapter 14 (A8).
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from outputlens.analysis.model import (
    ClaimGraph,
    Concept,
    ConceptGraph,
    ConceptRelationship,
)
from outputlens.orchestration.analyzer import (
    AnalysisContext,
    Analyzer,
    AnalyzerDeclaration,
    AnalyzerError,
    AnalyzerInput,
)
from outputlens.orchestration.engine import AnalyzerRegistry
from outputlens.runtime.model import NormalizedText


# ---------------------------------------------------------------------------
# Explicit concept relationship patterns
# ---------------------------------------------------------------------------

_RELATION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\b(\w+(?:\s+\w+){0,3})\s+is\s+(?:a|an)\s+(\w+(?:\s+\w+){0,3})\b', re.IGNORECASE), "is_a"),
    (re.compile(r'\b(\w+(?:\s+\w+){0,3})\s+(?:is|are)\s+(?:part|composed)\s+of\s+(\w+(?:\s+\w+){0,3})\b', re.IGNORECASE), "part_of"),
    (re.compile(r'\b(\w+(?:\s+\w+){0,3})\s+(?:causes?|leads?\s+to|produces?)\s+(\w+(?:\s+\w+){0,3})\b', re.IGNORECASE), "causes"),
    (re.compile(r'\b(\w+(?:\s+\w+){0,3})\s+(?:measures?|quantifies?)\s+(\w+(?:\s+\w+){0,3})\b', re.IGNORECASE), "measures"),
    (re.compile(r'\b(\w+(?:\s+\w+){0,3})\s+defines?\s+(\w+(?:\s+\w+){0,3})\b', re.IGNORECASE), "defines"),
    (re.compile(r'\b(\w+(?:\s+\w+){0,3})\s+(?:contrasts?\s+with|oppos(?:es?|ite)\s+(?:of|to))\s+(\w+(?:\s+\w+){0,3})\b', re.IGNORECASE), "contrasts_with"),
]


def _infer_from_claims(
    concepts: list[Concept],
    claim_graph: ClaimGraph,
) -> list[ConceptRelationship]:
    """Infer concept relationships from claim relationships.

    If Claim A (about concept X) relates to Claim B (about concept Y),
    then X and Y are related.
    """
    # Build concept → claims map
    concept_claims: dict[str, set[str]] = {}
    for c in concepts:
        concept_claims[c.id] = set(c.referencing_claim_ids)

    relationships: list[ConceptRelationship] = []
    seen: set[tuple[str, str, str]] = set()

    for claim_rel in claim_graph.relationships:
        source_cid = claim_rel.source_claim_id
        target_cid = claim_rel.target_claim_id

        # Find concepts referenced by source and target claims
        for concept_a in concepts:
            if source_cid not in concept_claims.get(concept_a.id, set()):
                continue
            for concept_b in concepts:
                if concept_a.id == concept_b.id:
                    continue
                if target_cid not in concept_claims.get(concept_b.id, set()):
                    continue

                key = (concept_a.id, concept_b.id, "related_to")
                if key not in seen:
                    seen.add(key)
                    relationships.append(ConceptRelationship(
                        source_concept_id=concept_a.id,
                        target_concept_id=concept_b.id,
                        relationship_type="related_to",
                        evidence="claim_inferred",
                    ))

    return relationships


def _compute_centrality(
    concepts: list[Concept],
    relationships: list[ConceptRelationship],
) -> dict[str, float]:
    """Compute simple degree centrality for each concept."""
    degree: dict[str, int] = defaultdict(int)
    for rel in relationships:
        degree[rel.source_concept_id] += 1
        degree[rel.target_concept_id] += 1
    max_deg = max(degree.values()) if degree else 1
    return {cid: round(deg / max_deg, 3) for cid, deg in degree.items()}


def _find_bridges(
    concepts: list[Concept],
    relationships: list[ConceptRelationship],
) -> list[str]:
    """Identify bridge concepts connecting otherwise disconnected components."""
    adj: dict[str, set[str]] = defaultdict(set)
    for rel in relationships:
        adj[rel.source_concept_id].add(rel.target_concept_id)
        adj[rel.target_concept_id].add(rel.source_concept_id)

    # Simple heuristic: a concept is a bridge if removing it disconnects its neighbors
    bridges: list[str] = []
    for cid in adj:
        neighbors = adj[cid]
        if len(neighbors) < 2:
            continue
        # Check if neighbors connect without this node
        connected_without = 0
        for n in neighbors:
            other_neighbors = adj.get(n, set()) - {cid}
            if other_neighbors & (neighbors - {n}):
                connected_without += 1
        if connected_without < len(neighbors) / 2:
            bridges.append(cid)
    return bridges


def build_concept_graph(
    concepts: list[Concept],
    claim_graph: ClaimGraph,
) -> ConceptGraph:
    """Build the complete concept relationship graph."""
    relationships = _infer_from_claims(concepts, claim_graph)

    centrality = _compute_centrality(concepts, relationships)
    bridges = _find_bridges(concepts, relationships)

    novel_ids = tuple(
        c.id for c in concepts if c.concept_type == "novel_construct"
    )

    return ConceptGraph(
        relationships=tuple(relationships),
        centrality_scores=centrality,
        bridge_concept_ids=tuple(bridges),
        novel_construct_ids=novel_ids,
    )


class ConceptRelationshipMapper(Analyzer):
    declaration = AnalyzerDeclaration(
        id="a8",
        version="0.1.0",
        responsibility="Build concept relationship graph from claim relationships "
        "and concept co-occurrence patterns.",
        inputs=(
            AnalyzerInput("a3", "a3", required=True),
            AnalyzerInput("a7", "a7", required=True),
            AnalyzerInput("a1", "a1", required=False),
        ),
        output_type=ConceptGraph,
        layer="structure",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        a3_out = context.get_output("a3", "a3")
        a7_out = context.get_output("a7", "a7")
        if a3_out is None:
            raise AnalyzerError("A8 requires A3 output.")
        if a7_out is None:
            raise AnalyzerError("A8 requires A7 output.")

        concepts = a3_out.get("concepts", [])
        claim_graph = a7_out.get("claim_graph")
        if claim_graph is None:
            return {"concept_graph": ConceptGraph()}

        graph = build_concept_graph(concepts, claim_graph)
        return {"concept_graph": graph}


def register(registry: AnalyzerRegistry) -> None:
    registry.register(ConceptRelationshipMapper.declaration,
                      lambda: ConceptRelationshipMapper())
