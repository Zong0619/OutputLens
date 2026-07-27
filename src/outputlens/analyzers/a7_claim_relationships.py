"""A7: Claim Relationship Mapper -- conservative discourse-based graph construction.

Phase 4.2: Builds a directed claim graph using discourse markers and structural
adjacency. Distinguishes contrast (→ concedes) from contradiction (→ contradicts)
per A7-001. Computes graph-level properties: foundational claims, orphans,
contradiction clusters, cascading uncertainty chains.

Spec reference: OutputLens Framework Specification, Chapter 14 (A7).
"""

from __future__ import annotations

import re
from typing import Any

from outputlens.analysis.model import (
    Claim,
    ClaimGraph,
    ClaimRelationship,
    EstablishednessAnnotation,
    NoveltyAnnotation,
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
# Discourse marker → relationship type mapping (conservative per A7-001)
# ---------------------------------------------------------------------------

_SUPPORT_MARKERS = [
    r'\btherefore\b', r'\bthus\b', r'\bconsequently\b', r'\bhence\b',
    r'\bas\s+a\s+result\b', r'\bso\b', r'\baccordingly\b',
    r'\bthis\s+(?:shows|demonstrates|proves|indicates|suggests)\b',
]
_ELABORATE_MARKERS = [
    r'\bfor\s+example\b', r'\bfor\s+instance\b', r'\bspecifically\b',
    r'\bsuch\s+as\b', r'\bin\s+particular\b', r'\bto\s+illustrate\b',
    r'\bthat\s+is\b', r'\bnamely\b',
]
_CONCEDE_MARKERS = [
    r'\bhowever\b', r'\bbut\b', r'\balthough\b', r'\beven\s+though\b',
    r'\bon\s+the\s+other\s+hand\b', r'\bnevertheless\b', r'\bnonetheless\b',
    r'\bdespite\b', r'\bin\s+spite\s+of\b', r'\bwhereas\b', r'\bwhile\b',
]
_DEPENDS_ON_MARKERS = [
    r'\bbased\s+on\b', r'\bdepends?\s+on\b', r'\brelies?\s+on\b',
    r'\brequires?\b', r'\bprerequisite\b', r'\bassuming\b',
]
_SEQUENCE_MARKERS = [
    r'\bfirst[,\s]', r'\bsecond[,\s]', r'\bthird[,\s]', r'\bfinally[,\s]',
    r'\bnext[,\s]', r'\bthen\b', r'\bsubsequently\b', r'\bafter\s+that\b',
]
_RESTATE_MARKERS = [
    r'\bin\s+other\s+words\b', r'\bthat\s+is\s+to\s+say\b',
    r'\bi\.e\.\s', r'\bto\s+put\s+it\s+differently\b',
]
_GENERALIZE_MARKERS = [
    r'\bin\s+general\b', r'\bmore\s+broadly\b', r'\bin\s+fact\b',
    r'\bindeed\b', r'\bmoreover\b', r'\bfurthermore\b',
]

# Contradiction: ONLY with strong signals (A7-001)
_CONTRADICT_MARKERS = [
    r'\bnot\b', r'\bno\b', r'\bneither\b', r'\bnever\b',
    r'\b(?:do|does|did|is|are|was|were|has|have|had)\s+not\b',
    r'\b(?:cannot|can\s+not)\b',
    r'\bwrong\b', r'\bincorrect\b', r'\bfalse\b',
]

# Compiled patterns for efficiency
def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]

_SUPPORT_RE = _compile(_SUPPORT_MARKERS)
_ELABORATE_RE = _compile(_ELABORATE_MARKERS)
_CONCEDE_RE = _compile(_CONCEDE_MARKERS)
_DEPENDS_ON_RE = _compile(_DEPENDS_ON_MARKERS)
_SEQUENCE_RE = _compile(_SEQUENCE_MARKERS)
_RESTATE_RE = _compile(_RESTATE_MARKERS)
_GENERALIZE_RE = _compile(_GENERALIZE_MARKERS)
_CONTRADICT_RE = _compile(_CONTRADICT_MARKERS)


def _detect_relationship(text: str) -> str | None:
    """Detect the strongest relationship type from discourse markers.

    Returns None if no marker detected (→ implicit adjacency).
    Priority: contradiction > depends_on > supports > restates >
             elaborates > generalizes > concedes > sequences
    """
    markers: list[tuple[list[re.Pattern], str]] = [
        (_CONTRADICT_RE, "contradicts"),
        (_DEPENDS_ON_RE, "depends_on"),
        (_SUPPORT_RE, "supports"),
        (_RESTATE_RE, "restates"),
        (_ELABORATE_RE, "elaborates"),
        (_GENERALIZE_RE, "generalizes"),
        (_CONCEDE_RE, "concedes"),
        (_SEQUENCE_RE, "sequences"),
    ]
    for patterns, rel_type in markers:
        for pat in patterns:
            if pat.search(text):
                return rel_type
    return None


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def _map_relationships(claims: list[Claim], text: str) -> list[ClaimRelationship]:
    """Build claim relationships from discourse structure.

    Strategy:
    1. For each adjacent pair of claims, check the text BETWEEN them for
       discourse markers indicating a relationship.
    2. Also check the SECOND claim's text for markers that relate it to
       the preceding claim.
    3. Default: adjacent claims in the same segment → implicit "elaborates"
       if no explicit marker is found.
    """
    relationships: list[ClaimRelationship] = []
    if len(claims) < 2:
        return relationships

    for i in range(len(claims) - 1):
        source = claims[i]
        target = claims[i + 1]

        # Get the text between the two claims and the start of the target claim
        between = text[source.end_char:target.start_char]
        target_start = target.text[:80]  # First 80 chars of target

        # Detect explicit relationship
        rel_type = _detect_relationship(between + " " + target_start)

        if rel_type:
            relationships.append(ClaimRelationship(
                source_claim_id=source.id,
                target_claim_id=target.id,
                relationship_type=rel_type,
                strength="explicit",
            ))
        elif source.segment_id == target.segment_id:
            # Same segment, adjacent → implicit elaboration
            relationships.append(ClaimRelationship(
                source_claim_id=source.id,
                target_claim_id=target.id,
                relationship_type="elaborates",
                strength="implicit",
            ))

    return relationships


def _compute_graph_properties(
    claims: list[Claim],
    relationships: list[ClaimRelationship],
    e_annotations: list[EstablishednessAnnotation],
) -> tuple[list[str], list[str], list[tuple[str, ...]], list[tuple[str, ...]]]:
    """Compute graph-level properties from relationships and classifications.

    Returns: (foundational_ids, orphan_ids, contradiction_clusters, uncertainty_chains)
    """
    claim_ids = {c.id for c in claims}

    # Build in-degree from depends_on edges
    in_degree: dict[str, int] = {cid: 0 for cid in claim_ids}
    out_degree: dict[str, int] = {cid: 0 for cid in claim_ids}
    e_levels: dict[str, str] = {a.claim_id: a.level for a in e_annotations}

    for rel in relationships:
        out_degree[rel.source_claim_id] = out_degree.get(rel.source_claim_id, 0) + 1
        if rel.relationship_type == "depends_on":
            in_degree[rel.target_claim_id] = in_degree.get(rel.target_claim_id, 0) + 1

    # Foundational claims: high in-degree of depends_on
    if claim_ids:
        max_in = max(in_degree.values()) if in_degree else 0
        threshold = max(2, max_in // 2) if max_in >= 2 else 2
        foundational = [cid for cid, deg in in_degree.items() if deg >= threshold]
    else:
        foundational = []

    # Orphan claims: no relationships at all
    orphans = [cid for cid in claim_ids
               if in_degree.get(cid, 0) == 0 and out_degree.get(cid, 0) == 0]

    # Contradiction clusters: groups of mutually contradicting claims
    contradict_edges = [(r.source_claim_id, r.target_claim_id)
                        for r in relationships if r.relationship_type == "contradicts"]
    clusters = _find_contradiction_clusters(contradict_edges)

    # Cascading uncertainty chains: depends_on paths rooted in uncertain claims
    chains = _find_uncertainty_chains(relationships, e_levels)

    return foundational, orphans, clusters, chains


def _find_contradiction_clusters(
    edges: list[tuple[str, str]],
) -> list[tuple[str, ...]]:
    """Find connected components in the contradiction subgraph."""
    if not edges:
        return []
    # Build adjacency
    adj: dict[str, set[str]] = {}
    for s, t in edges:
        adj.setdefault(s, set()).add(t)
        adj.setdefault(t, set()).add(s)
    # BFS for connected components
    visited: set[str] = set()
    clusters: list[tuple[str, ...]] = []
    for node in adj:
        if node in visited:
            continue
        component: set[str] = set()
        stack = [node]
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            component.add(n)
            stack.extend(adj.get(n, set()) - visited)
        if len(component) >= 2:
            clusters.append(tuple(sorted(component)))
    return clusters


def _find_uncertainty_chains(
    relationships: list[ClaimRelationship],
    e_levels: dict[str, str],
) -> list[tuple[str, ...]]:
    """Find depends_on chains where the root is at E3+.

    Returns chains of length >= 2 where the first claim is uncertain.
    """
    # Build depends_on adjacency (target → source)
    dep_edges: dict[str, list[str]] = {}
    for rel in relationships:
        if rel.relationship_type == "depends_on":
            dep_edges.setdefault(rel.target_claim_id, []).append(rel.source_claim_id)

    chains: list[tuple[str, ...]] = []
    for target, sources in dep_edges.items():
        for source in sources:
            source_level = e_levels.get(source, "E5")
            if source_level in ("E3", "E4", "E5"):
                chains.append((source, target))

    return chains


def build_claim_graph(
    claims: list[Claim],
    text: str,
    e_annotations: list[EstablishednessAnnotation],
) -> ClaimGraph:
    """Build the complete claim relationship graph.

    Args:
        claims: The ClaimSet from A2.
        text: The NormalizedText from A1.
        e_annotations: EstablishednessAnnotations from A4 (for uncertainty chains).

    Returns:
        ClaimGraph with relationships and computed properties.
    """
    relationships = _map_relationships(claims, text)
    foundational, orphans, clusters, chains = _compute_graph_properties(
        claims, relationships, e_annotations,
    )

    return ClaimGraph(
        relationships=tuple(relationships),
        foundational_claim_ids=tuple(foundational),
        orphan_claim_ids=tuple(orphans),
        contradiction_clusters=tuple(clusters),
        cascading_uncertainty_chains=tuple(chains),
    )


# ---------------------------------------------------------------------------
# Orchestration Analyzer wrapper
# ---------------------------------------------------------------------------


class ClaimRelationshipMapper(Analyzer):
    """A7: Builds the claim relationship graph from discourse structure."""

    declaration = AnalyzerDeclaration(
        id="a7",
        version="0.1.0",
        responsibility="Map logical and rhetorical relationships between claims "
        "using discourse markers and structural adjacency. Distinguishes "
        "contrast from contradiction per A7-001.",
        inputs=(
            AnalyzerInput("a2", "a2", required=True),
            AnalyzerInput("a1", "a1", required=True),
            AnalyzerInput("a4", "a4", required=True),
            AnalyzerInput("a6", "a6", required=False),
        ),
        output_type=ClaimGraph,
        layer="structure",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        a1_out = context.get_output("a1", "a1")
        a2_out = context.get_output("a2", "a2")
        a4_out = context.get_output("a4", "a4")

        if a1_out is None:
            raise AnalyzerError("A7 requires A1 output.")
        if a2_out is None:
            raise AnalyzerError("A7 requires A2 output.")
        if a4_out is None:
            raise AnalyzerError("A7 requires A4 output.")

        text = a1_out.get("normalized_text")
        if text is None or not isinstance(text, NormalizedText):
            raise AnalyzerError("A7 requires NormalizedText from A1.")
        claims = a2_out.get("claims", [])
        e_anns = a4_out.get("establishedness_annotations", [])

        graph = build_claim_graph(claims, text.text, e_anns)
        return {"claim_graph": graph}


def register(registry: AnalyzerRegistry) -> None:
    registry.register(ClaimRelationshipMapper.declaration,
                      lambda: ClaimRelationshipMapper())
