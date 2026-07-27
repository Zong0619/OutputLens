# OutputLens -- Implementation Roadmap

**Last updated**: 2026-07-27
**Reference**: Implementation Readiness Assessment (2026-07-27)

---

## Overview

The roadmap is organized into milestones designed to validate the architecture
as quickly as possible. Each milestone produces a testable artifact and provides
feedback that can refine the specification.

**Current**: Milestone 0 (COMPLETE)
**Next**: Milestone 1 (Claim Extraction)

---

## Milestone 0: Infrastructure -- COMPLETE (2026-07-27)

**Goal**: Build the foundation -- everything that has zero AI dependencies and
can be verified with pure unit tests.

**Deliverables**:
- [x] Repository scaffolding, Python project setup, pyproject.toml
- [x] AnalysisDocument JSON Schema v1.0
- [x] Core domain model (Python dataclasses for all A1-A19 objects)
- [x] Runtime Model (R1-R8: RawInput, NormalizedText, PositionIndex, etc.)
- [x] Text normalization pipeline (A1: Text Normalizer)
- [x] Analyzer base contract (abstract interface + AnalysisContext)
- [x] Orchestration layer (dependency resolution + execution engine)
- [x] 81 unit tests passing

**Architecture validated**:
- Schema-first design (JSON Schema defines the contract)
- Immutability (frozen dataclasses)
- Dependency resolution (topological sort with layering)
- Parallel execution scheduling
- Cross-reference integrity in AnalysisDocument

---

## Milestone 1: Claim Extraction (Target: Weeks 2-3)

**Goal**: Implement the first real analyzer (A2) and validate that claim
extraction is reliable enough to build on.

**Deliverables**:
- [ ] A2: Claim Extractor implementation
  - Sentence splitting + clause-level decomposition
  - 9-type claim classification (factual_assertion through meta_claim)
  - Confidence marker detection (hedges and certainty expressions)
  - Integration with Runtime Model (consumes NormalizedText + Segments)
  - Integration with Orchestration (registered as an analyzer)
- [ ] GOLD-CLAIM v0.1: 50-100 AI responses with manual annotations
  - 3 annotators per response
  - Claim boundaries, claim types, confidence markers
  - Inter-annotator agreement metrics
- [ ] Evaluation harness v0.1: boundary F1, type accuracy, marker F1
- [ ] Target: Claim extraction >80% F1 on evaluation set

**Architecture validated**:
- That the A2 analyzer contract is implementable
- That claim types are reliably distinguishable
- That confidence marker detection works on real AI text
- That the orchestrator handles a real analyzer end-to-end
- That the AnalysisDocument schema accommodates real claim data

**Specification feedback expected**:
- Claim type taxonomy reliability (which distinctions survive annotation)
- Claim boundary operationalization (splitting vs. merging rules)
- Quality target calibration

---

## Milestone 2: Concept Extraction (Target: Week 4)

**Goal**: Implement concept extraction and validate the A2->A3 dependency chain.

**Deliverables**:
- [ ] A3: Concept Extractor implementation
  - Named entity recognition, domain concept identification, novel construct detection
  - Coreference resolution
  - Significance filtering
  - Domain association
- [ ] GOLD-CONCEPT v0.1: 50 annotated responses
- [ ] Target: Concept extraction >75% F1 on significant concepts

**Architecture validated**:
- That the A2->A3 dependency chain works end-to-end
- That concept types are reliably distinguishable
- That significance filtering can be operationalized
- That domain associations are useful for downstream classification

---

## Milestone 3: Classification -- THE CRITICAL VALIDATION (Target: Weeks 5-7)

**Goal**: Implement the core classification analyzers and validate that
OutputLens's value proposition -- epistemological classification of claims --
is achievable.

**Deliverables**:
- [ ] A4: Establishedness Analyzer
- [ ] A5: Evidence Requirement Analyzer
- [ ] A9: Trust Profile Generator
- [ ] A10: Evidence Gap Analyzer
- [ ] GOLD-ESTABLISHED v0.1: 200 claims with expert annotations
- [ ] GOLD-EVIDENCE v0.1: 150 responses with evidence annotations
- [ ] Full A1->A2->A3->{A4,A5}->A9->A10 pipeline producing valid AnalysisDocuments
- [ ] Target: A4 agreement with experts >0.5 Cohen's kappa
- [ ] Target: A5 accuracy >80%
- [ ] Target: Reasoning rated "useful" by >60% of human evaluators

**This is the most important milestone.** If A4 cannot produce useful
classifications with useful reasoning, the core value proposition fails.
The project should not proceed past M3 until reasoning quality meets the
"useful" threshold.

**Architecture validated**:
- Classification methodology viability
- Axis independence (measure correlation between A4 and A6)
- Reasoning quality
- 5-level scale frequency distribution
- TrustProfile correlation with expert holistic ratings

---

## Milestone 4: Remaining Classifiers (Target: Week 8)

**Deliverables**:
- [ ] A6: Novelty Analyzer
- [ ] A7: Claim Relationship Mapper
- [ ] A11: Novelty Index Calculator
- [ ] A12: Overconfidence Detector
- [ ] A13: Structural Integrity Analyzer
- [ ] GOLD-NOVELTY v0.1
- [ ] Full classification layer end-to-end

---

## Milestone 5: Structure and Full Synthesis (Target: Weeks 9-10)

**Deliverables**:
- [ ] A8: Concept Relationship Mapper
- [ ] A14: Conceptual Coherence Analyzer
- [ ] A15: Response Narrative Generator
- [ ] A16: Verification Punchlist Generator
- [ ] GOLD-PUNCHLIST v0.1: 50 responses with human punchlist evaluation
- [ ] Complete AnalysisDocument with all 16 analyzers
- [ ] Target: Punchlist precision >70%, recall >60%, usefulness >3.5/5

---

## Milestone 6: First Interfaces (Target: Weeks 11-12)

**Deliverables**:
- [ ] Reference CLI: accepts text, outputs full AnalysisDocument as JSON
- [ ] Reference web interface: paste text, see TrustProfile + highlights + punchlist
- [ ] Both consume the same AnalysisDocument from the same engine
- [ ] Validate engine-interface separation

---

## Post-Milestone 6: Evaluation Infrastructure

**Deliverables**:
- [ ] Evaluation harness v1.0 (implementation-agnostic)
- [ ] BENCH-DIVERSITY: 10,000 AI responses across models, domains, languages
- [ ] BENCH-CHALLENGE: 500 curated difficult cases
- [ ] BENCH-TEMPORAL: 1,000 fixed responses for regression detection
- [ ] Public metrics dashboard (per-release trends)

---

## v2 Feature Roadmap (After Reference Implementation)

- [ ] Browser extension (inline highlights on ChatGPT, Claude, Gemini)
- [ ] MCP server (expose analysis to AI agents)
- [ ] REST API
- [ ] Shareable analysis links
- [ ] Implementation Decisions Register completion
- [ ] Contributor documentation: how to build a community analyzer
- [ ] Conformance test suite expansion (all MUST requirements covered)

---

## v3 Research Directions (After v2 Validation)

- [ ] Knowledge Layer (KU clustering from `restates` relationships)
- [ ] Cross-model comparative mode
- [ ] Domain profiles (Medical Safety, Legal Risk, Code Correctness)
- [ ] Personal knowledge base calibration
- [ ] Multi-turn conversation analysis
- [ ] Community analyzer ecosystem
- [ ] Extension registries
- [ ] Formal schema language for AnalysisDocument
- [ ] Non-English language support

---

## Future Specification Editions

**Edition 1 (Candidate Standard)**: Current. Published with reference
implementation. Seeks implementation experience.

**Edition 2 (Proposed Standard)**: After at least two independent implementations
exist. Incorporates implementation feedback. Backward-compatible with Edition 1
AnalysisDocuments.

**Edition 3 (Standard)**: Broad implementation experience. No unresolved issues.
May include the Knowledge Layer as normative.
