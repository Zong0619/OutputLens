# OutputLens -- Project State

**Last updated**: 2026-07-27 (Milestone 1 complete)
**Purpose**: Living document. Updated continuously as the project evolves.

---

## Current Milestone

**Milestone 2: Concept Extraction** -- IN PROGRESS
- Phase 2.1 (Named Entity Recognition) -- COMPLETE (2026-07-27)
- Phase 2.2 (Domain Concept Identification) -- PENDING

**Next**: Phase 2.2 after Phase 2.1 review

## Completed Milestones

- **M0: Infrastructure** -- Repository scaffolding, AnalysisDocument JSON Schema
  v1.0, core domain model (all A1-A19 dataclasses), Runtime Model (R1-R8 +
  text normalizer), Analyzer base contract, Orchestration layer (dependency
  resolution + execution engine). 81 unit tests passing.
- **M1: Claim Extraction** -- Deterministic rule-based A2 Claim Extractor with
  sentence splitting, conjunction decomposition, compound sentence handling,
  list/enumeration support, and regression test suite. 86 unit + 18 regression
  tests passing. Implementation decisions documented.

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
| A2 | Claim Extractor | Implemented (M1 complete) |
| A3 | Concept Extractor | Phase 2.1 done (named entities) |
| A4-A16 | All remaining analyzers | Not started |

### Tests

| File | Tests | Status |
|---|---|---|
| `tests/unit/test_runtime_model.py` | 24 | All passing |
| `tests/unit/test_analysis_model.py` | 32 | All passing |
| `tests/unit/test_orchestration.py` | 25 | All passing |
| `tests/unit/test_a2_claim_extractor.py` | 86 | All passing |
| `tests/unit/test_a2_regression.py` | 18 | All passing |
| `tests/unit/test_a3_concept_extractor.py` | 48 | All passing |
| **Total** | **233** | **All passing** |

### Interfaces

None implemented. Reference CLI and web interface are scheduled for Milestone 6.

### Evaluation Infrastructure

Scaffolding only (`benchmarks/golden_datasets/README.md`). Full evaluation
infrastructure (golden datasets, evaluation harness) scheduled after M3.

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

None. Ready to begin Milestone 2 (A3: Concept Extractor).

---

## Next Milestone

**Milestone 2: Concept Extraction** -- A3: Concept Extractor

See `docs/ROADMAP.md` and `reports/M1.md` for full milestone details.

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

1. **A2 implementation approach** -- RESOLVED (2026-07-27): Rule-based
   deterministic approach. See IMPLEMENTATION_DECISIONS.md A2-001.

2. **A4 classification knowledge source**: How does the Establishedness
   Analyzer determine what is "common knowledge" vs. "domain established"?
   Options: use an LLM, use a knowledge base, use heuristics. The specification
   does not mandate a specific approach.

3. **Golden dataset annotation**: Who annotates? Domain experts vs. crowd
   workers vs. the development team? Annotation quality directly impacts
   evaluation validity.

4. **Reasoning quality bar**: The spec requires reasoning for every
   classification (min 20 chars). But what constitutes "useful" reasoning vs.
   circular/generic reasoning? This will be discovered during M3.

5. **Graph algorithm selection**: The spec defines graph-level properties
   (foundational claims, centrality, clusters) but does not mandate specific
   algorithms. The reference implementation should document its choices.

6. **A1 output convention** -- NEW (2026-07-27): The `_bootstrap.raw_input`
   convention for passing RawInput to A1 is an implementation artifact not
   defined in the specification. Should be formalized or redesigned before M2.

---

## Immediate TODO

- [ ] Resolve A1 `_bootstrap.raw_input` convention (codify or redesign)
- [ ] Write `README.md` with project overview, installation, and quick start
- [ ] Begin Milestone 2: A3 Concept Extractor
- [ ] Build GOLD-CLAIM v0.1 (first 50 annotated AI responses)
- [ ] Build evaluation harness v0.1 for claim extraction metrics
