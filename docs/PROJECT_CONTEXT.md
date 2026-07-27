# OutputLens -- Project Context

**Last revised**: 2026-07-27
**Stability**: This document should almost never change. Changes require explicit justification.

---

## What OutputLens Is

OutputLens is an open-source analysis engine that decomposes AI-generated text into
structured claims and classifies each by its epistemological characteristics.

**Tagline**: *See what your AI isn't telling you.*

OutputLens is NOT a fact checker, hallucination detector, novelty checker, deep
research tool, RAG system, or content moderator. It is a reader's tool -- it
illuminates the structure of AI-generated text so the reader can make informed
judgments about what to trust, verify, or explore further.

**Core metaphor**: OutputLens is a nutrition label for AI-generated text. A
nutrition label tells you what's in your food without telling you whether it's
"good" or "bad." OutputLens tells you what's in an AI response -- established
claims, novel ideas, unsupported assertions -- without telling you what to
believe.

---

## Core Philosophy

1. **Epistemological Humility** -- OutputLens classifies claims by epistemological
   characteristics, never by truth. Every classification is presented as a lens
   through which to view the text, not as a verdict.

2. **Model Agnosticism** -- OutputLens operates on text, not on model metadata.
   It works on output from any LLM without knowing what model produced it.

3. **Structural Transparency** -- Every classification is accompanied by natural
   language reasoning. The reader always sees WHY a classification was made.

4. **Reader Empowerment** -- OutputLens equips the reader's judgment; it does not
   replace it. The verification punchlist says "here's what to investigate" --
   not "we investigated it, here's the answer."

5. **Open by Default** -- OutputLens is open source (Apache 2.0). Its analysis
   methods, classification logic, and output structure are transparent,
   auditable, and forkable.

6. **Engine First, Interface Second** -- The analysis engine is the product.
   Every interface (browser extension, CLI, API, MCP server, IDE extension) is
   a renderer of engine output.

---

## Design Principles

The full set of 20 Design Principles is defined in the OutputLens Framework
Specification, Chapter 2. The principles are organized into four categories:

- **Identity** (P1-P5): What OutputLens IS -- analysis, not generation; lens, not
  verdict; model agnostic; reader empowerment; open by default.
- **Structural** (P6-P10): How OutputLens is organized -- engine first; one
  analyzer, one responsibility; immutable analysis objects; explicit dependency
  declaration; layered separation.
- **Analytical** (P11-P15): How OutputLens thinks -- text-anchored analysis;
  classification requires reasoning; independent axes of analysis;
  proposition-aware but claim-centric; progressive analytical depth.
- **Boundary** (P16-P20): What OutputLens DOES NOT DO -- post-generation only;
  no truth determination; no content suppression; domain-agnostic core;
  composable analysis.

Every design proposal, analyzer, interface, and change must be evaluated against
these principles. A proposal that violates a principle must either be rejected or
must explicitly justify a principle revision.

---

## Architecture Status: FROZEN

The OutputLens framework architecture was designed over an extensive conceptual
design phase (Product Design Document, Analyzer Framework, Layered Object
Taxonomy, Knowledge Layer Critique, Product Boundary Analysis, Design Principles,
Specification Outline, Standards Quality Critique, Implementation Readiness
Assessment, Reference Implementation & Evaluation Infrastructure).

**The architecture is frozen.** Changes to the framework architecture require:

1. Implementation evidence that the current specification is internally
   inconsistent or impossible to implement.
2. A formal proposal evaluated against the 20 Design Principles.
3. Explicit acknowledgment of which principles are strained or revised.
4. Consensus of the project maintainers.

Implementation decisions (how a specific analyzer classifies claims) are distinct
from architectural decisions (what an analyzer is, how analyzers declare
dependencies, what the AnalysisDocument contains). Implementation decisions are
recorded in `docs/IMPLEMENTATION_DECISIONS.md` and do NOT require architectural
approval.

---

## Current Implementation Status

**Edition**: OutputLens Framework Specification Edition 1 (Candidate Standard)
**Phase**: Milestone 0 (Infrastructure) -- COMPLETE
**Next**: Milestone 1 (A2: Claim Extractor)

Completed:
- Repository scaffolding
- AnalysisDocument JSON Schema v1.0
- Core domain model (Python dataclasses for all A1-A19 objects)
- Runtime Model (R1-R8: RawInput, NormalizedText, PositionIndex, etc.)
- Text normalization pipeline (A1: Text Normalizer)
- Analyzer base contract
- Orchestration layer (dependency resolution, scheduling, parallel execution)
- 81 unit tests covering all infrastructure components

---

## Primary Integration Contract

The **AnalysisDocument** is the single integration contract between the engine
and all interfaces. It is defined by:

- **JSON Schema**: `src/outputlens/analysis/schemas/analysis_document_v1.json`
- **Python model**: `src/outputlens/analysis/document.py` (AnalysisDocument class)
- **Spec reference**: OutputLens Framework Specification, Chapter 26

Every interface consumes AnalysisDocuments. Every analyzer contributes to them.
The schema is versioned (current: `1.0.0`). Backward compatibility within a major
version is guaranteed. The schema is the interoperability bedrock.

---

## Current Language

**Primary implementation language**: Python 3.10+

The reference implementation is written in Python. The specification is
language-agnostic. Community implementations in other languages are explicitly
encouraged -- the AnalysisDocument JSON Schema is the contract, not the Python
dataclasses.

---

## Repository Organization

```
outputlens/
├── specification/          # Canonical specification (Markdown)
├── src/outputlens/         # Reference implementation (Python)
│   ├── runtime/            #   Runtime Model + text normalizer
│   ├── analysis/           #   Analysis Model + AnalysisDocument + JSON Schema
│   ├── analyzers/          #   Analyzer implementations (A2-A16)
│   ├── orchestration/      #   Analyzer base contract + engine
│   └── interfaces/         #   Reference interfaces (CLI, etc.)
├── tests/                  # Unit and integration tests
├── conformance_tests/      # Conformance test suite
├── benchmarks/             # Golden datasets and evaluation harness
├── docs/                   # Project documentation (this directory)
├── pyproject.toml
└── README.md
```

---

## Current Analyzer Catalog

| ID | Name | Layer | Status |
|---|---|---|---|
| A1 | Text Normalizer | Foundation | Implemented |
| A2 | Claim Extractor | Foundation | Next milestone |
| A3 | Concept Extractor | Foundation | Pending |
| A4 | Establishedness Analyzer | Classification | Pending |
| A5 | Evidence Requirement Analyzer | Classification | Pending |
| A6 | Novelty Analyzer | Classification | Pending |
| A7 | Claim Relationship Mapper | Structure | Pending |
| A8 | Concept Relationship Mapper | Structure | Pending |
| A9 | Trust Profile Generator | Synthesis | Pending |
| A10 | Evidence Gap Analyzer | Synthesis | Pending |
| A11 | Novelty Index Calculator | Synthesis | Pending |
| A12 | Overconfidence Detector | Synthesis | Pending |
| A13 | Structural Integrity Analyzer | Synthesis | Pending |
| A14 | Conceptual Coherence Analyzer | Synthesis | Pending |
| A15 | Response Narrative Generator | Synthesis | Pending |
| A16 | Verification Punchlist Generator | Terminal | Pending |

---

## What MUST NEVER Change Without Governance

The following require a formal governance process (specification revision,
principle evaluation, community review) to change:

1. **The 20 Design Principles** -- The constitution of OutputLens.
2. **The three classification axes** -- Establishedness, Evidence Requirement,
   Novelty. Axes may be added; existing axes may not be removed or redefined
   without an edition boundary.
3. **The AnalysisDocument as the integration contract** -- Every interface
   consumes it. Every analyzer contributes to it.
4. **The Engine-First separation** -- Analytical logic in interface code is a
   violation of Principle 6.
5. **The Analyzer Contract** -- Single responsibility, explicit inputs, typed
   output, no consumer awareness. This is the extensibility model.
6. **Immutability of Analysis objects** -- Once produced, never modified.
7. **Classification requires reasoning** -- Every annotation MUST carry a
   natural language explanation.
8. **No truth determination** -- OutputLens classifies epistemological
   characteristics, not truth.
9. **Model agnosticism** -- The engine operates on text, not model metadata.
10. **The product boundaries** -- Not a fact checker, not a hallucination
    detector, not a content moderator, not a generation-time guardrail.

---

## What Kinds of Future Changes Are Expected

The following changes are expected and encouraged without architectural approval
(they are recorded in `IMPLEMENTATION_DECISIONS.md`):

1. **New analyzers** -- Community analyzers (Bias, Safety, Citation, Medical,
   Legal, Code Correctness) that conform to the Analyzer Contract.
2. **Improved analyzer implementations** -- Better classification methodology,
   better claim extraction, better graph algorithms. These change analyzer
   behavior but not analyzer contracts.
3. **New interfaces** -- A Raycast extension, an Obsidian plugin, a Slack bot.
   Interfaces consume AnalysisDocuments; they don't modify the engine.
4. **Domain profiles** -- Collections of domain-specific analyzers for medicine,
   law, code, etc.
5. **Golden dataset expansions** -- More annotated data for evaluation.
6. **Performance improvements** -- Faster analyzers, better parallelism.
7. **Language support** -- Non-English claim extraction and classification.

---

## Relationship Between Specification, Reference Implementation, and Conformance Suite

- **Specification** (`specification/`) -- The normative authority. Defines what
  MUST, SHOULD, and MAY be done. Written in English, language-agnostic.

- **Reference Implementation** (`src/outputlens/`) -- A complete Python
  implementation that demonstrates the specification. It is NOT the definition
  of the framework. When the implementation and specification disagree, the
  specification wins.

- **Conformance Suite** (`conformance_tests/`) -- Tests that verify an
  implementation satisfies specification requirements. Tests validate schema
  conformance, structural invariants, analyzer contracts, and execution model
  compliance. Tests do NOT validate classification accuracy -- that is an
  analyzer quality question evaluated by golden datasets.

---

## Capability Boundaries

**What OutputLens promises to every user:**

1. You will see what claims were made, traceable to positions in the original text.
2. You will understand what kind of claim each one is (establishedness, evidence
   requirement, novelty).
3. You will know which claims deserve your attention (the Verification Punchlist).
4. You will see the reasoning behind every classification.
5. You will get the same analysis regardless of which AI produced the text.
6. You own the analysis -- it's open source.

**What OutputLens explicitly does NOT promise:**

1. It does not tell you what is true or false.
2. It does not verify claims for you.
3. It does not catch all problems -- it's an aid, not a safety guarantee.
4. It does not tell you whether a response is "good" -- that depends on your context.
5. It does not work equally well in every domain -- it knows its limits.
6. It does not make the AI better or worse -- it's a reader's tool.

Full capability boundaries are defined in the OutputLens User Contract
(specification front matter).

---

## Non-Goals (Permanent)

- OutputLens is NOT a fact checker
- OutputLens is NOT a hallucination detector
- OutputLens is NOT a novelty checker
- OutputLens is NOT a deep research tool
- OutputLens is NOT a RAG system
- OutputLens is NOT a content moderator
- OutputLens is NOT a generation-time guardrail
- OutputLens is NOT a replacement for domain expertise

These non-goals are normative. Proposals that cross these boundaries must be
rejected or explicitly acknowledged as scope changes requiring governance.

---

## Document Hierarchy

Normative Authority

1. Specification

Engineering Guidance

2. PROJECT_CONTEXT

3. ARCHITECTURE

4. IMPLEMENTATION_GUIDE

Implementation Record

5. IMPLEMENTATION_DECISIONS

Living Status

6. PROJECT_STATE

Planning

7. ROADMAP

---

## AI Contributor Protocol

Before making implementation changes:

1. Read PROJECT_CONTEXT.md.

2. Read PROJECT_STATE.md.

3. Follow the Specification.

4. Distinguish Specification Requirements from Implementation Decisions.

5. Do not redesign the architecture.

6. Record implementation-specific decisions in IMPLEMENTATION_DECISIONS.md.

7. If implementation reveals a specification inconsistency,
   document the evidence before proposing any architectural revision.

---

## Repository Is The Memory

Conversation history is not authoritative.

Individual AI memory is not authoritative.

The repository is the project's single source of truth.

When conflicts exist:

Specification

↓

Repository Documentation

↓

Implementation

↓

Conversation

The repository always wins.