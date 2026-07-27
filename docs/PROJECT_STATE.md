# OutputLens -- Project State

**Last updated**: 2026-07-27 (Milestone 6 complete)
**Purpose**: Living document. Updated continuously as the project evolves.

---

## Current Milestone

**Milestone 6: Evaluation Infrastructure** -- IN PROGRESS
- Phase 6.1 (Golden Dataset Foundation) -- COMPLETE
- Phase 6.2 (Evaluation Harness) -- COMPLETE
- Phase 6.3 (Benchmark Corpora) -- COMPLETE
- Phase 6.4 (Evaluation Report + M6 Completion) -- COMPLETE

**Milestone 7: Interfaces and Community Readiness** -- IN PROGRESS
- Phase 7.1 (CLI Interface) -- COMPLETE (accepted)
- Phase 7.2 (REST API) -- COMPLETE (accepted)
- Phase 7.3 (Web Demo) -- COMPLETE (accepted)
- Phase 7.4 (README + CONTRIBUTING) -- COMPLETE

475 tests passing. Next: Phase 7.5 (M7 Report + Completion).

**Previous Milestones (all complete)**:
- M0: Infrastructure (81 tests)
- M1: Claim Extraction (104 A2 tests)
- M2: Concept Extraction (69 A3 tests)
- M3: Classification Layer (A4, A5, A9, A10 -- 83 tests)
- M4: Remaining Classifiers (A6, A7, A11, A12, A13 -- 52 tests)
- M5: Final Analyzers (A8, A14, A15, A16 -- 13 tests)

**Status**: All 16 analyzers implemented. 402 tests passing. Reference engine functionally complete. M6 adds evaluation infrastructure only -- no analyzer changes.

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
| A3 | Concept Extractor | Implemented (M2 complete) |
| A4 | Establishedness Analyzer | Implemented (M3) |
| A5 | Evidence Requirement Analyzer | Implemented (M3) |
| A6 | Novelty Analyzer | Implemented (M4) |
| A7 | Claim Relationship Mapper | Implemented (M4) |
| A9 | Trust Profile Generator | Implemented (M3) |
| A10 | Evidence Gap Analyzer | Implemented (M3) |
| A11 | Novelty Index Calculator | Implemented (M4) |
| A12 | Overconfidence Detector | Implemented (M4) |
| A8 | Concept Relationship Mapper | Implemented (M5) |
| A13 | Structural Integrity Analyzer | Implemented (M4) |
| A14 | Conceptual Coherence Analyzer | Implemented (M5) |
| A15 | Response Narrative Generator | Implemented (M5) |
| A16 | Verification Punchlist Generator | Implemented (M5) |

### Tests

| File | Tests | Status |
|---|---|---|
| `tests/unit/test_runtime_model.py` | 24 | All passing |
| `tests/unit/test_analysis_model.py` | 32 | All passing |
| `tests/unit/test_orchestration.py` | 25 | All passing |
| `tests/unit/test_a2_claim_extractor.py` | 86 | All passing |
| `tests/unit/test_a2_regression.py` | 18 | All passing |
| `tests/unit/test_a3_concept_extractor.py` | 69 | All passing |
| `tests/unit/test_a5_evidence_requirement.py` | 41 | All passing |
| `tests/unit/test_a4_establishedness.py` | 27 | All passing |
| `tests/unit/test_a6_novelty.py` | 24 | All passing |
| `tests/unit/test_a7_claim_relationships.py` | 19 | All passing |
| `tests/unit/test_a9_a10_synthesis.py` | 15 | All passing |
| `tests/unit/test_a11_a12_a13_synthesis.py` | 9 | All passing |
| `tests/unit/test_a8_a14_a15_a16.py` | 13 | All passing |
| `tests/unit/test_evaluation_harness.py` | 25 | All passing |
| `tests/unit/test_benchmark_corpora.py` | 13 | All passing |
| `tests/unit/test_cli_interface.py` | 14 | All passing |
| `tests/unit/test_api_interface.py` | 14 | All passing |
| `tests/unit/test_web_demo.py` | 7 | All passing |
| **Total** | **475** | **All passing** |

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
