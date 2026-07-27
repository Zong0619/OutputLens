# OutputLens -- Architecture Overview

**Audience**: Engineers implementing or extending OutputLens.
**Scope**: High-level architecture. For normative requirements, see the Specification.

---

## Three-Layer Architecture

OutputLens has three conceptual layers with strict boundaries:

```
RUNTIME MODEL               ANALYSIS MODEL              INTERFACE MODEL
(infrastructure)            (analytical findings)       (presentation)

RawInput                    Claim                       HighlightSpec
NormalizedText              Concept                     TrustSummaryCard
PositionIndex               EstablishednessAnnotation   PunchlistView
Metadata                    EvidenceAnnotation          ViewConfiguration
Segment                     NoveltyAnnotation           InteractionState
                             ClaimGraph
                             ConceptGraph
                             TrustProfile
                             VerificationPunchlist
                                  |
                                  |
                     AnalysisDocument (boundary object)
                     Contains Runtime + Analysis objects.
                     Consumed by every Interface.
```

**Rule**: Objects belong to exactly one layer. An Analysis object never contains
rendering instructions (colors, layout). An Interface object never contains
analytical logic. The AnalysisDocument is the single cross-layer container.

---

## Analyzer Framework

Analyzers are the computational units of OutputLens. Each analyzer:

- Answers exactly ONE analytical question
- Declares its inputs explicitly (which other analyzers' outputs it needs)
- Produces exactly ONE typed output
- Has NO knowledge of which analyzers consume its output
- Is independent -- same inputs produce same outputs

### The Analyzer Contract

```python
class Analyzer(ABC):
    declaration: AnalyzerDeclaration  # id, version, responsibility, inputs, output_type, layer

    @abstractmethod
    def analyze(self, context: AnalysisContext) -> Any:
        """Execute analysis. Only access declared inputs from context."""
        ...
```

### The Analyzer Catalog (v2, 16 analyzers)

| Layer | Analyzers | Role |
|---|---|---|
| Foundation | A1, A2, A3 | Text normalization, claim extraction, concept extraction |
| Classification | A4, A5, A6 | Establishedness, evidence requirement, novelty (run in parallel) |
| Structure | A7, A8 | Claim relationships, concept relationships |
| Synthesis | A9-A15 | Trust profile, evidence gap, novelty index, overconfidence, structural integrity, coherence, narrative (mostly parallel) |
| Terminal | A16 | Verification punchlist |

---

## Orchestration Layer

The orchestration layer is thin coordination logic. It does NOT perform analysis.

### Dependency Resolution

Given a set of requested analyzers, the orchestrator:
1. Computes transitive closure (pulls in all dependencies)
2. Builds a dependency graph from declared analyzer inputs
3. Performs topological sort with layering (Kahn's algorithm variant)
4. Produces an execution plan: list of layers, each a list of analyzer IDs

Analyzers with no mutual dependencies appear in the same layer and execute in parallel.

### Execution

```
Layer 0: [A1]                              # Foundation: text normalization
Layer 1: [A2]                              # Foundation: claim extraction
Layer 2: [A3]                              # Foundation: concept extraction
Layer 3: [A4, A5, A6]                      # Classification: all three axes parallel
Layer 4: [A7]                              # Structure: claim relationships
Layer 5: [A8, A9, A10, A11, A12, A13, A14] # Structure + Synthesis: parallel
Layer 6: [A15]                             # Synthesis: narrative (needs A9-A14)
Layer 7: [A16]                             # Terminal: punchlist (needs most upstream)
```

Layers execute sequentially. Analyzers within a layer execute concurrently via
ThreadPoolExecutor.

### AnalysisContext

A shared context object that carries all analyzer outputs. Each analyzer reads
only its declared inputs. The context is the data-flow mechanism -- analyzers
don't call each other directly.

---

## Execution Flow (End to End)

```
1. User submits text (via CLI, API, browser extension, etc.)

2. Interface creates AnalysisRequest(RawInput, Metadata, AnalyzerConfiguration)

3. Orchestrator resolves execution plan from requested analyzers

4. A1: Text Normalizer runs
   - RawInput -> NFKC normalization -> whitespace regularization
   - Segment detection (paragraphs, headings, code blocks, lists)
   - PositionIndex construction (bidirectional raw<->normalized mapping)
   - Output: NormalizedText + PositionIndex + Segments

5. A2: Claim Extractor runs
   - Input: NormalizedText, Segments
   - Decomposes text into individual Claims
   - Detects confidence markers (hedges, certainty expressions)
   - Output: ClaimSet

6. A3: Concept Extractor runs
   - Input: NormalizedText, ClaimSet
   - Identifies significant concepts, resolves coreferences
   - Output: ConceptIndex

7. A4, A5, A6: Classification analyzers run IN PARALLEL
   - A4: Establishedness (E1-E5) per claim
   - A5: Evidence Requirement (R1-R4) per claim
   - A6: Novelty (N1-N5) per claim
   - Output: Three sets of Annotations

8. A7: Claim Relationship Mapper runs
   - Input: ClaimSet, NormalizedText, EstablishednessAnnotations, NoveltyAnnotations
   - Builds directed graph of claim relationships
   - Computes graph-level properties (foundational claims, orphans, contradictions)
   - Output: ClaimGraph

9. A8-A14: Structure + Synthesis analyzers run IN PARALLEL
   - A8: ConceptGraph from claims + concepts
   - A9: TrustProfile from establishedness annotations
   - A10: EvidenceGapReport from evidence annotations
   - A11: NoveltyIndex from novelty annotations
   - A12: OverconfidenceReport from confidence markers + establishedness
   - A13: StructuralIntegrityReport from claim graph
   - A14: CoherenceReport from concept graph

10. A15: Response Narrative Generator runs
    - Input: A9-A14 outputs
    - Output: 3-5 sentence natural language summary

11. A16: Verification Punchlist Generator runs
    - Input: Claims, all annotations, claim graph, trust profile, overconfidence,
      structural integrity
    - Output: Ranked, prioritized list of claims to verify

12. AnalysisDocument is assembled and finalized (immutable)

13. Interface renders AnalysisDocument for the user
```

---

## The AnalysisDocument

The AnalysisDocument is the single integration contract between engine and
interfaces. Every interface consumes it. Every analyzer contributes to it.

**Structure** (JSON Schema v1.0):

```
AnalysisDocument
├── schema_version: "1.0.0"
├── metadata: { engine_version, timestamp, analysis_id, prompt?, model_identifier?, domain_hint? }
├── runtime_objects: { raw_input, normalized_text, position_index, execution_trace? }
└── analysis_objects: {
      claims: [Claim],
      concepts?: [Concept],
      establishedness_annotations?: [EstablishednessAnnotation],
      evidence_annotations?: [EvidenceAnnotation],
      novelty_annotations?: [NoveltyAnnotation],
      claim_graph?: ClaimGraph,
      concept_graph?: ConceptGraph,
      trust_profile?: TrustProfile,
      evidence_gap_report?: EvidenceGapReport,
      novelty_index?: NoveltyIndex,
      overconfidence_report?: OverconfidenceReport,
      structural_integrity_report?: StructuralIntegrityReport,
      coherence_report?: CoherenceReport,
      response_narrative?: ResponseNarrative,
      verification_punchlist?: VerificationPunchlist,
    }
```

**Schema**: `src/outputlens/analysis/schemas/analysis_document_v1.json`

---

## Classification Axes

Every claim is classified along three independent axes:

| Axis | Scale | Question Answered |
|---|---|---|
| Establishedness | E1-E5 | How firmly is this claim grounded in established knowledge? |
| Evidence Requirement | R1-R4 | What evidential support does this claim demand? Does the response provide it? |
| Novelty | N1-N5 | How does this claim relate to existing knowledge? Is it canonical or original? |

Each classification includes natural language reasoning (min 20 characters).

---

## Repository Structure

```
outputlens/
├── specification/              # Canonical specification (language-agnostic)
│   └── edition-1/
├── src/outputlens/             # Reference implementation (Python)
│   ├── runtime/                #   Runtime Model: RawInput, NormalizedText, etc.
│   │   ├── model.py            #     R1-R8 dataclasses
│   │   └── normalizer.py       #     A1 Text Normalizer
│   ├── analysis/               #   Analysis Model: domain objects
│   │   ├── model.py            #     A1-A19 dataclasses
│   │   ├── document.py         #     AnalysisDocument (boundary object)
│   │   └── schemas/            #     JSON Schema + loader
│   ├── analyzers/              #   Analyzer implementations (A2-A16)
│   ├── orchestration/          #   Engine coordination
│   │   ├── analyzer.py         #     Analyzer base contract
│   │   └── engine.py           #     Dependency resolution + execution
│   └── interfaces/             #   Reference interfaces (CLI, web)
├── tests/                      # Unit + integration tests
├── conformance_tests/          # Conformance test suite
├── benchmarks/                 # Golden datasets + evaluation harness
├── docs/                       # Project documentation
├── pyproject.toml
└── README.md
```

---

## Key Invariants

These are enforced at the type level or in validation:

1. **Immutability**: All Analysis Model dataclasses are `frozen=True`. The
   AnalysisDocument uses explicit `_finalized` guard.
2. **Schema conformance**: `AnalysisDocument.to_dict()` produces output matching
   the JSON Schema.
3. **Cross-reference integrity**: `AnalysisDocument.validate()` checks that all
   annotation claim_ids and relationship references are valid.
4. **Reasoning requirement**: Annotation constructors enforce min 20-char reasoning.
5. **Type enums**: All classification levels, claim types, concept types,
   relationship types are validated at construction time.
