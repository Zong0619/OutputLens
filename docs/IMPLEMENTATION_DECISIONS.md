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
