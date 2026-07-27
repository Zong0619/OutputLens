# OutputLens -- Implementation Decisions Register

**Purpose**: Record every significant implementation choice not mandated by the
specification. This is the firewall that prevents implementation-specific
behavior from accidentally becoming a de facto specification requirement.

**Audience**: Implementers (reference and community). When an independent
implementer asks "must I use X?", the answer is in this register.

**Maintenance**: Updated with every PR that makes a significant implementation
choice. Reviewed during architecture discussions.

---

## How to Use This Register

When you make an implementation choice that the specification does NOT mandate,
add an entry below. Each entry should answer:

1. **What was chosen?** -- The specific implementation approach.
2. **What alternatives exist?** -- Other conformant approaches.
3. **What does the specification require?** -- The relevant spec requirement
   (or note that the spec is silent).
4. **Why this choice?** -- Rationale.

---

## Template

```markdown
### [ANALYZER_ID]-[NNN]: [Short Title]

**Date**: YYYY-MM-DD
**Component**: [Analyzer ID or module path]
**Spec Reference**: [Chapter/Section, or "Specification is silent"]

**Choice**: [What we implemented.]

**Alternatives**: [Other conformant approaches an independent implementation could use.]

**Rationale**: [Why we chose this approach for the reference implementation.]

**Stability**: [High/Medium/Low -- how likely this choice is to change.]
```

---

## Decisions

*No decisions recorded yet. This register will be populated as analyzers are
implemented and implementation choices are made.*

---

### A1-001: Python dataclasses with frozen=True for Analysis Model immutability

**Date**: 2026-07-27
**Component**: All Analysis Model objects (`src/outputlens/analysis/model.py`)
**Spec Reference**: Chapter 17 (Object Model Overview -- immutability principle),
Principle 8 (Immutable Analysis Objects)

**Choice**: All Analysis Model objects are implemented as Python `@dataclass(frozen=True)`.
Validation is performed in `__post_init__`. Objects cannot be modified after construction.

**Alternatives**: An independent implementation could use:
- Immutable records in any language (Java records, Scala case classes, Kotlin data classes)
- Manual immutability with getter-only access and private constructors
- A builder pattern with a final `build()` that returns an immutable object

**Rationale**: Frozen dataclasses are idiomatic Python, provide type safety, and
enforce immutability at the language level. `__post_init__` validation runs
automatically on construction.

**Stability**: High. This is a Python-specific implementation of a normative
specification requirement. The immutability requirement is permanent; the
mechanism for enforcing it is language-specific.

---

### A1-002: NFKC normalization for text input

**Date**: 2026-07-27
**Component**: A1 Text Normalizer (`src/outputlens/runtime/normalizer.py`)
**Spec Reference**: Chapter 9 (Analysis Input and Normalization)

**Choice**: The reference implementation uses Unicode NFKC normalization. Line
endings are normalized to `\n`. Trailing whitespace is stripped per line.
Multiple blank lines (3+) are collapsed to max 2.

**Alternatives**: The specification requires deterministic Unicode normalization
but does not mandate NFKC specifically. An independent implementation could use
NFC (if it handles compatibility characters separately) or a custom normalization
pipeline. The specific normalization choices must be documented and reproducible.

**Rationale**: NFKC is the most aggressive standard normalization form. It
composes characters, normalizes ligatures, and handles compatibility equivalents.
This maximizes the chance that text from diverse sources (web, PDF, terminal)
normalizes to a consistent form.

**Stability**: High. Changing normalization form would change PositionIndex
mappings and affect reproducibility across engine versions.

---

### ORCH-001: ThreadPoolExecutor for parallel analyzer execution

**Date**: 2026-07-27
**Component**: Orchestration layer (`src/outputlens/orchestration/engine.py`)
**Spec Reference**: Chapter 8 (Execution Model -- parallelism)

**Choice**: The orchestrator uses `concurrent.futures.ThreadPoolExecutor` for
parallel execution of analyzers within the same layer. Default `max_workers`
is Python's default (typically `min(32, os.cpu_count() + 4)`).

**Alternatives**: An independent implementation could use:
- `ProcessPoolExecutor` for CPU-bound analyzers
- `asyncio` for I/O-bound analyzers (e.g., API calls to LLMs)
- Single-threaded execution (still conformant if dependencies are respected)

**Rationale**: ThreadPoolExecutor is simple, built-in, and sufficient for the
reference implementation's needs. Most analyzers are currently synchronous.
As analyzers become more I/O-bound (LLM API calls), an async execution model
may be warranted.

**Stability**: Medium. The choice of executor is an implementation detail.
The specification requires that independent analyzers be ELIGIBLE for parallel
execution; it does not mandate the mechanism.

---

### DOC-001: AnalysisDocument incremental construction pattern

**Date**: 2026-07-27
**Component**: AnalysisDocument (`src/outputlens/analysis/document.py`)
**Spec Reference**: Chapter 26 (AnalysisDocument Structure), Principle 8

**Choice**: The AnalysisDocument is mutable during construction (setter methods
like `set_claim()`, `set_trust_profile()`) and becomes immutable after
`finalize()` is called. Attempted mutation after finalization raises
`RuntimeError`. This is enforced by a `_finalized` boolean flag.

**Alternatives**: An independent implementation could use:
- A Builder pattern: `AnalysisDocumentBuilder` -> `build()` -> immutable document
- Accumulator objects per layer, assembled at finalization
- Functional construction: pass all outputs to a constructor at once

**Rationale**: The incremental pattern allows analyzers to contribute outputs as
they complete, enabling progressive UI updates (future). The finalization guard
is a runtime enforcement of the specification's immutability requirement. The
Builder pattern would be cleaner but adds an extra abstraction layer.

**Stability**: Medium. A Builder pattern may be adopted if the incremental
mutation pattern causes bugs or complexity.

---

### A2-001: Rule-based deterministic sentence splitting for Phase 1.1

**Date**: 2026-07-27
**Component**: A2 Claim Extractor (`src/outputlens/analyzers/a2_claim_extractor.py`)
**Spec Reference**: Chapter 12 (A2: Claim Extractor). Specification is silent on
extraction methodology.

**Choice**: The reference implementation uses a deterministic, rule-based approach
with no ML dependencies. Sentence boundaries are detected via regex patterns
with explicit abbreviation lists. All claims default to `factual_assertion` type.

**Alternatives**: An independent implementation could use:
- An LLM-based extractor (prompt the model to decompose text into claims)
- An NLP library (spaCy, NLTK, Stanza)
- A hybrid approach (rules for common cases, ML for edge cases)
- A different claim type defaulting strategy

**Rationale**: A rule-based approach aligns with the project's open-by-default
philosophy (no external API dependencies), preserves model agnosticism at the
implementation level, and guarantees deterministic output for identical input.
The approach is intentionally simple for Phase 1.1 -- correctness and traceability
are prioritized over sophistication. Claim type refinement is deferred to
later phases.

**Stability**: Medium. The sentence splitting approach will be augmented in
Phases 1.2-1.5 with conjunction splitting, compound sentence handling, and
list support. The core rule-based strategy may be supplemented or replaced
if evaluation reveals recall/precision below targets.

---

### A2-002: Title vs. general abbreviation distinction

**Date**: 2026-07-27
**Component**: A2 Claim Extractor -- `_is_title_abbreviation` / `_is_general_abbreviation`
**Spec Reference**: Specification is silent.

**Choice**: Abbreviations are split into two categories:
- **Title abbreviations** (Dr., Mr., Prof.): Never end a sentence when followed
  by a capital letter (proper name continuation).
- **General abbreviations** (etc., i.e., approx., Jan.): May end sentences when
  followed by a capital letter, but do NOT end sentences when followed by a
  digit (approx. 3.14, Jan. 2025).

**Alternatives**: An independent implementation could use a single abbreviation
list with contextual disambiguation, or a different categorization scheme.

**Rationale**: The two-category distinction captures the most common sentence
boundary ambiguity patterns without requiring complex context analysis. Title
abbreviations are almost always followed by proper names. General abbreviations
can appear mid-sentence or at sentence boundaries depending on context.

**Stability**: Low. The abbreviation lists will expand as evaluation reveals
additional patterns. The categorization may need refinement for edge cases.

---

### A2-003: All claims default to factual_assertion in Phase 1.1

**Date**: 2026-07-27
**Component**: A2 Claim Extractor -- claim type assignment
**Spec Reference**: Chapter 19 (A2: Claim). The specification defines 9 claim
types but does not mandate how they are assigned.

**Choice**: All claims extracted in Phase 1.1 receive `claim_type="factual_assertion"`.
No claim type classification is attempted. Type refinement is deferred to later
phases when structural and linguistic analysis capabilities improve.

**Alternatives**: An independent implementation could:
- Use heuristics to classify claim types (question marks → meta_claim, etc.)
- Use an LLM to classify claim types
- Implement full claim type classification from the start

**Rationale**: Phase 1.1 focuses on sentence splitting with correct position
preservation. Claim type classification requires additional linguistic analysis
that would distract from validating the core extraction pipeline.

**Stability**: Low. This will change in Phase 1.2+ as claim type heuristics
are introduced.

---

### A2-004: Supported and unsupported linguistic structures (M1)

**Date**: 2026-07-27
**Component**: A2 Claim Extractor -- all phases
**Spec Reference**: Specification is silent on specific linguistic patterns.

**Supported structures** (reliably decomposed):
- Simple declarative sentences (period-terminated)
- Question and exclamation sentences
- Coordinating conjunctions with comma (", and ", ", but ", ", or ")
  when what follows forms an independent clause
- Subordinating conjunctions (", because", ", although", ", while")
  when what follows forms an independent clause
- Adverbial connectors preceded by comma/semicolon (", however", "; therefore")
- Dash-based bullet lists (-, *, +)
- Numbered lists (1., 2., 1), 2))
- Common abbreviations (Dr., Mr., Prof., etc., i.e., e.g., approx., Jan., U.S.)

**Unsupported structures** (not decomposed; remain as single claims):
- Semicolon-separated clauses without explicit connectors
- Colon-separated explanations
- "if" conditionals (kept together as tightly coupled)
- Relative clauses (", which ...") -- correctly kept with main clause
- Appositives -- correctly kept with main clause
- Nested that-clauses ("Researchers found that...")
- Coordinating conjunctions without comma ("X and Y")

**Known limitations** (false positives -- split when should not):
- Coordinating conjunctions where the second clause is a continuation
  of a list rather than an independent clause
- "while" used temporally rather than contrastively (may split incorrectly)

**Known limitations** (false negatives -- not split when should):
- Semicolon-separated independent clauses
- Complex multi-clause sentences with implicit boundaries

**Stability**: Medium. These patterns will evolve as the golden dataset
reveals additional false positive/negative patterns.
