# OutputLens -- Project State

**Last updated**: 2026-07-27
**Purpose**: Living document. Updated continuously as the project evolves.

---

## Current Milestone

**Milestone 0: Infrastructure** -- COMPLETE (2026-07-27)

## Completed Milestones

- **M0: Infrastructure** -- Repository scaffolding, AnalysisDocument JSON Schema
  v1.0, core domain model (all A1-A19 dataclasses), Runtime Model (R1-R8 +
  text normalizer), Analyzer base contract, Orchestration layer (dependency
  resolution + execution engine). 81 unit tests passing.

## Current Branch

`main` (repository root: `/Users/winnie/Developer/OutputLens`)

## Current Specification Edition

OutputLens Framework Specification Edition 1 (Candidate Standard)

The specification outline is stable. The full specification text has been
designed but not yet written as a standalone document. Design documents
are preserved in the project plan file.

## Implementation Progress

### Infrastructure (M0) -- Complete

| Component | File | Status |
|---|---|---|
| Project scaffold | `pyproject.toml`, directory structure | Done |
| JSON Schema v1.0 | `src/outputlens/analysis/schemas/analysis_document_v1.json` | Done |
| Runtime Model dataclasses | `src/outputlens/runtime/model.py` | Done |
| Text Normalizer (A1) | `src/outputlens/runtime/normalizer.py` | Done |
| Analysis Model dataclasses | `src/outputlens/analysis/model.py` | Done |
| AnalysisDocument | `src/outputlens/analysis/document.py` | Done |
| Analyzer base contract | `src/outputlens/orchestration/analyzer.py` | Done |
| Orchestration engine | `src/outputlens/orchestration/engine.py` | Done |
| Package exports | All `__init__.py` files | Done |

### Analyzers

| ID | Name | Status |
|---|---|---|
| A1 | Text Normalizer | Implemented |
| A2 | Claim Extractor | **Next: Milestone 1** |
| A3-A16 | All remaining analyzers | Not started |

### Tests

| File | Tests | Status |
|---|---|---|
| `tests/unit/test_runtime_model.py` | 24 | All passing |
| `tests/unit/test_analysis_model.py` | 32 | All passing |
| `tests/unit/test_orchestration.py` | 25 | All passing |
| **Total** | **81** | **All passing** |

### Interfaces

None implemented. Reference CLI and web interface are scheduled for Milestone 6.

### Evaluation Infrastructure

Not started. Scheduled after Milestone 3 (Classification).

---

## Completed Infrastructure

The following are built, tested, and stable:

- **Text normalization pipeline**: RawInput -> NFKC normalization -> whitespace
  regularization -> segment detection -> PositionIndex (bidirectional mapping).
- **AnalysisDocument construction**: Incremental assembly during analysis,
  immutability after finalization, schema-conformant JSON serialization,
  cross-reference validation.
- **Orchestration engine**: Analyzer registry, topological sort with layering,
  parallel execution within layers, transitive dependency resolution, failure
  handling (fatal for required analyzers, non-fatal for terminal/optional),
  execution callbacks.
- **Domain model**: All 19 Analysis Model objects validated (type enums,
  reasoning length requirements, immutability, cross-reference integrity).
- **JSON Schema**: Complete v1.0 schema covering all object types, with $defs
  for reuse.

---

## Current Blockers

None. Ready to begin Milestone 1 (A2: Claim Extractor).

---

## Next Milestone

**Milestone 1: Claim Extraction (Target: 2-3 weeks)**

Deliverables:
- A2: Claim Extractor -- first real analyzer implementation
- Integration with Runtime Model and orchestration layer
- Gold-standard evaluation set: 50-100 AI responses with manually annotated
  claim boundaries, claim types, and confidence markers
- Evaluation harness v0.1
- Target: Claim extraction >80% F1 on evaluation set

See `docs/ROADMAP.md` for full milestone details.

---

## Recently Made Engineering Decisions

| Date | Decision | Rationale |
|---|---|---|
| 2026-07-27 | Python 3.10+ for reference implementation | Only available Python version in dev environment |
| 2026-07-27 | Frozen dataclasses for all Analysis Model objects | Enforces immutability principle at the type level |
| 2026-07-27 | `from __future__ import annotations` in all modules | Enables `X | None` syntax on Python 3.10 |
| 2026-07-27 | AnalysisDocument as mutable-during-construction, immutable-after-finalization | Accommodates incremental assembly without violating Principle 8 |
| 2026-07-27 | Analyzer output convention: output name matches analyzer_id | Simplifies context.get_output() calls; no additional naming layer needed |
| 2026-07-27 | Orchestrator uses ThreadPoolExecutor for parallel layers | Acceptable for CPU-bound analysis; async execution can be added later |
| 2026-07-27 | JSON Schema v1.0 uses draft 2020-12 | Current IETF standard; widely supported |

---

## Open Implementation Questions

1. **A2 implementation approach**: Should the reference Claim Extractor use
   an LLM-based approach (breaking model agnosticism at the implementation
   level), a rule-based NLP pipeline, or a hybrid? The specification is silent
   on methodology -- this is an implementation decision to be recorded in
   `IMPLEMENTATION_DECISIONS.md`.

2. **A4 classification knowledge source**: How does the Establishedness
   Analyzer determine what is "common knowledge" vs. "domain established"?
   Options: use an LLM, use a knowledge base, use heuristics. The specification
   does not mandate a specific approach. The reference implementation should
   try multiple approaches and measure trade-offs.

3. **Golden dataset annotation**: Who annotates? Domain experts vs. crowd
   workers vs. the development team? Annotation quality directly impacts
   evaluation validity.

4. **Reasoning quality bar**: The spec requires reasoning for every
   classification (min 20 chars). But what constitutes "useful" reasoning vs.
   circular/generic reasoning? This will be discovered during M3.

5. **Graph algorithm selection**: The spec defines graph-level properties
   (foundational claims, centrality, clusters) but does not mandate specific
   algorithms. The reference implementation should document its choices.

---

## Immediate TODO

- [ ] Create `docs/IMPLEMENTATION_DECISIONS.md` with initial empty register
- [ ] Create `docs/ROADMAP.md`
- [ ] Begin Milestone 1: design and implement A2 Claim Extractor
- [ ] Build GOLD-CLAIM v0.1 (first 50 annotated AI responses)
- [ ] Build evaluation harness v0.1 for claim extraction metrics
- [ ] Create analyzer registration module in `src/outputlens/analyzers/`
- [ ] Write `README.md` with project overview, installation, and quick start
