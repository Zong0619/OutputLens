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

---

### A3-001: Rule-based named entity recognition with curated lists

**Date**: 2026-07-27
**Component**: A3 Concept Extractor -- Phase 2.1 (`src/outputlens/analyzers/a3_concept_extractor.py`)
**Spec Reference**: Chapter 12 (A3: Concept Extractor). Specification is silent on
extraction methodology.

**Choice**: The reference implementation uses deterministic pattern matching
with curated entity lists. Person names: title-prefix, particle-aware, initials,
and general capitalized patterns with organization/location exclusion.
Organizations: suffix-based pattern + known-org lookup. Locations: curated list
of ~140 countries, cities, and US states. Works: quoted title extraction with
minimum-length heuristics.

**Alternatives**: An independent implementation could use:
- spaCy/NLTK for named entity recognition
- An LLM-based extractor
- A transformer-based NER model
- Different entity type taxonomies

**Rationale**: A rule-based approach preserves determinism and zero external
dependencies. Curated lists for locations and known organizations provide high
precision for common cases. Pattern-based person/organization extraction covers
the most common structures in AI-generated text. The approach is intentionally
conservative -- false negatives (missed entities) are preferred over false
positives (non-entities classified as entities).

**Stability**: Medium. Entity lists will expand. Phase 2.3 (coreference) and
Phase 2.2 (domain concepts) will augment the concept index with additional
concept types.

---

### A3-002: Claim-based significance filtering

**Date**: 2026-07-27
**Component**: A3 Concept Extractor -- `_claim_references_text` / `extract_concepts`
**Spec Reference**: Chapter 12 (A3). Specification requires significance filtering
but does not define the mechanism.

**Choice**: A named entity is included as a Concept only if at least one Claim
references it (position-based overlap detection). Entities that appear in the
text but are not the subject/object of any claim are excluded.

**Alternatives**: An independent implementation could use:
- Frequency-based filtering (entities mentioned N+ times are significant)
- Grammatical role filtering (only subjects/objects are significant)
- Domain relevance scoring
- No filtering (all entities are concepts)

**Rationale**: Claim-based filtering operationalizes the specification's
"significance" requirement without requiring syntactic parsing. A concept is
significant if the response makes claims ABOUT it. This is a conservative filter
that errs toward inclusion (an entity mentioned in a claim might be peripheral,
but at least it's relevant to something the response asserts).

**Stability**: Medium. The heuristic may be refined when evaluation reveals
whether it over-includes or under-includes concepts.

---

### A3-003: All concepts default to empty domain_associations and definition_provided=False

**Date**: 2026-07-27
**Component**: A3 Concept Extractor -- Phase 2.1
**Spec Reference**: Specification defines `domain_associations` and
`definition_provided` fields but does not mandate how they are populated.

**Choice**: In Phase 2.1, `domain_associations` defaults to `{}` (empty dict)
and `definition_provided` defaults to `False` for all concepts. These fields
will be populated in Phase 2.4 (Domain Association and Definition Detection).

**Alternatives**: An independent implementation could populate these fields
immediately using heuristics or ML-based classification.

**Rationale**: Domain association and definition detection are separate
analytical concerns. Deferring them to Phase 2.4 keeps Phase 2.1 focused on
named entity recognition with correct position preservation and claim
association. The default values are explicit and valid per the specification.

---

### A3-004: Multi-strategy domain concept extraction with technical suffix heuristics

**Date**: 2026-07-27
**Component**: A3 Concept Extractor -- Phase 2.2
**Spec Reference**: Specification is silent on domain concept identification
methodology.

**Choice**: Domain concepts are identified through three complementary strategies:
1. Multi-word capitalized terms ("Quantum Entanglement", "Machine Learning")
2. Single-word technical terms identified by suffix patterns (words ending in
   -tion, -ics, -ology, -ment, etc.)
3. Multi-word noun phrases with technical content, filtered by claim significance

All strategies use claim-based significance filtering and exclude spans already
captured as named entities.

**Alternatives**: An independent implementation could use:
- TF-IDF or frequency-based key term extraction
- An LLM to identify domain-specific terminology
- A domain-specific ontology or knowledge base
- Part-of-speech tagging for noun phrase extraction

**Rationale**: The three-strategy approach balances precision (capitalized terms
are highly likely to be domain concepts) with recall (technical suffix patterns
catch single-word terms; noun phrases catch multi-word concepts regardless of
capitalization). All strategies are deterministic and require no external
dependencies. Claim-based filtering ensures only response-relevant terms are
included.

**Stability**: Medium. The technical suffix list and capitalization heuristics
will evolve as evaluation reveals domain-specific patterns. The distinction
between domain_concept and common_concept may benefit from ML-based
classification in future versions.

---

### A3-005: Conservative pronoun and definite-NP coreference resolution

**Date**: 2026-07-27
**Component**: A3 Concept Extractor -- Phase 2.3
**Spec Reference**: Specification is silent on coreference resolution methodology.

**Choice**: Two-pass coreference resolution: (1) third-person pronouns matched to
nearest preceding concept of compatible gender/number type; (2) "the <role>"
definite NPs matched via curated role-to-type mapping (~45 entries). Both
passes are within-segment, conservative, and require unambiguous antecedents.

**Alternatives**: spaCy/Stanford CoreNLP coref, LLM-based, or no coref at all.

**Rationale**: Deterministic, zero-dependency approach handling the most common
AI response patterns (entity introduced, then referenced by pronoun/role).
Conservative: false negatives preferred over false positives.

**Stability**: Low. Role mapping and pronoun heuristics will expand with
evaluation. Cross-paragraph coref is a known limitation.

---

### A5-001: Pattern-based evidence requirement classification with signal detection

**Date**: 2026-07-27
**Component**: A5 Evidence Requirement Analyzer (`src/outputlens/analyzers/a5_evidence_requirement.py`)
**Spec Reference**: Chapter 13 (A5: Evidence Requirement Analyzer).

**Choice**: Four-level classification (R1-R4) using explicit signal detection:
- R1: Definitional structure, tautologies, normative claims, meta-claims
- R2: Citation patterns (et al., brackets, parenthetical), source mentions
  (published in, study by), known publication venues
- R3: Evidence gestures without specifics (studies show, research indicates,
  experts agree, it is known that)
- R4: Specific unsupported claims (statistics, attributions, causal claims)
  and default for factual assertions without detected signals
Classification follows a priority order: R2 > R1 > R3 > R4. R3 escalates to
R4 when combined with specific-statistic signals.

**Alternatives**: An independent implementation could use an LLM to judge
evidence presence, or a more sophisticated NLP pipeline.

**Rationale**: Evidence requirement is the most tractable classification axis.
Citation patterns, evidence gestures, and statistical claims are detectable
through surface-level text patterns. Signal-based classification produces
reasoning that explains WHAT was detected, not just the assigned level.

---

### A4/A5-001: Knowledge Boundary -- Core Analyzers Must Remain Knowledge-Agnostic

**Date**: 2026-07-27
**Component**: A4 (Establishedness Analyzer), A5 (Evidence Requirement Analyzer)
**Spec Reference**: Principles 2 (Lens, Not Verdict), 3 (Model Agnostic), 17
(No Truth Determination), 19 (Domain-Agnostic Core).

**Choice**: The core classification analyzers (A4, A5) intentionally operate
without external knowledge sources. They classify claims based on observable
signals present in the text and analysis context -- claim types, concept domain
associations, linguistic hedging/certainty patterns, citation presence, and
specificity markers. They do not consult fact databases, knowledge graphs,
search engines, or external truth sources.

When signals are insufficient to make a confident classification, the analyzers
default to conservative levels (E3 for establishedness, R4 for evidence
requirement) rather than guessing or deferring to an external authority.

**Alternatives considered and rejected**:
- **External knowledge base**: Would improve classification of common knowledge
  claims (e.g., "Water freezes at 0°C" → E1 instead of E3). Rejected because it
  would make the analyzer dependent on a curated knowledge source, introduce
  maintenance burden, and blur the boundary between epistemological
  classification and fact verification.
- **LLM-based classification**: Would improve accuracy across all levels.
  Rejected for core analyzers because it would violate model agnosticism
  (Principle 3) at the implementation level, introduce non-determinism, and
  create dependency on external API services.
- **Web search integration**: Would enable real-time evidence verification.
  Rejected because it would transform OutputLens from an analysis tool into a
  fact-checking system, violating Principles 2 and 17.

**Future extension policy**: External knowledge sources may be introduced as
optional extensions in v3+ (e.g., domain profiles, knowledge layer plugins).
Such extensions MUST:
1. Be opt-in -- the core analyzers function without them.
2. Not modify the core analyzer behavior or output contracts.
3. Produce their own annotations rather than altering existing classifications.
4. Clearly distinguish their output from core epistemological classification.
5. Never assert truth or falsehood.

This preserves the OutputLens boundary: the system classifies epistemological
characteristics of claims; it does not determine what is true.

**Rationale**: This is the single most important boundary decision in
OutputLens. It preserves:
- **Epistemological humility** (Principle 2): Classifications are lenses, not
  verdicts. A low-establishedness classification means "the analyzer cannot
  confirm this is established knowledge," not "this claim is false."
- **Reader empowerment** (Principle 4): The reader, not the tool, decides what
  to believe. Adding external truth sources would shift this responsibility.
- **Non-goal integrity**: OutputLens is explicitly not a fact checker,
  hallucination detector, or truth verification system. External knowledge
  sources would erode all three non-goals.
- **Open-source viability**: An analysis engine that requires a maintained
  knowledge base is harder to fork, audit, and deploy independently.
- **Determinism**: Observable text signals produce consistent output. External
  knowledge sources (especially LLMs and web search) introduce variability.

**Stability**: High. This is a constitutional constraint. Changing it would
require revising Principles 2, 3, and 17, and redefining the project's
non-goals -- a governance-level decision.

---

### A6-001: Novelty Without External Knowledge

**Date**: 2026-07-27
**Component**: A6 (Novelty Analyzer) -- Milestone 4 planning
**Spec Reference**: Principles 2, 3, 17, 19; A4/A5-001 knowledge boundary.

**Choice**: The core A6 Novelty Analyzer evaluates novelty indicators from
observable text signals only. It uses A3 concept types (novel_construct flag),
claim type signals, specificity patterns, established framing markers, and
textual comparison signals within the analyzed response. It does not query
external knowledge bases, search prior literature, determine whether an idea
has appeared before, or claim that a concept is objectively novel.

Novelty classifications represent heuristic indicators, not verified novelty
judgments. The N1-N5 scale describes how the claim relates to what is
observably presented as established knowledge within the text itself.

**Alternatives considered and rejected**: Literature search, knowledge base
comparison, prior art databases -- all would move A6 toward novelty
verification, violating the knowledge boundary.

**Future extension policy**: Same as A4/A5-001. Optional knowledge-based
novelty analysis may be added as an extension in v3+ without modifying the
core A6 contract.

**Rationale**: Objective novelty detection requires external knowledge.
Maintaining the knowledge boundary preserves the OutputLens principle that
the system classifies epistemological characteristics rather than determining
external reality.

**Stability**: High. This is a constitutional constraint derived from
A4/A5-001.

---

### A7-001: Discourse Contrast vs Logical Contradiction

**Date**: 2026-07-27
**Component**: A7 (Claim Relationship Mapper) -- Milestone 4 planning
**Spec Reference**: Chapter 14 (A7). Specification defines relationship types
but is silent on detection methodology.

**Choice**: The initial A7 implementation uses conservative relationship
mapping. Discourse markers such as "however," "but," "although," and "on the
other hand" indicate contrast or qualification, not automatically logical
contradiction. The implementation distinguishes:
- **contradicts**: Claims that cannot both be true (direct negation, mutually
  exclusive assertions).
- **concedes**: Acknowledgment of limitations or counterpoints.
- **elaborates**: Additional detail or examples.
- **supports**: Premises, reasons, or evidence for another claim.
- **depends_on**: Logical prerequisite relationships.

Explicit contrast markers map to `concedes` by default, not `contradicts`.
Contradiction detection requires stronger signals: direct negation patterns,
mutually exclusive predicates, or explicit disagreement language.

**Alternatives**: Automatic mapping of all contrast markers to contradiction
(too aggressive -- creates false structural conflicts). Full semantic
contradiction detection (requires NLP beyond Phase 4.2 scope).

**Rationale**: Conservative relationship mapping prioritizes precision over
recall. False contradiction detection is more harmful to structural integrity
analysis than missing some implicit contradictions. Over-claiming
contradictions would mislead the reader and undermine trust in the analysis.

**Stability**: Medium. Relationship detection will improve as evaluation
reveals patterns. The contrast-vs-contradiction distinction is a permanent
design choice.

---

### A15-001: Narrative Generation as Rendering Layer, Not Analysis

**Date**: 2026-07-27
**Component**: A15 (Response Narrative Generator) -- Milestone 5 planning
**Spec Reference**: Principles 2, 4, 6, 15. Specification Chapter 15 (A15).

**Choice**: A15 is a rendering layer over existing analyzer outputs. It may
summarize findings from A9-A14 synthesis outputs but must not create new
classifications, introduce unsupported interpretations, override existing
analyzer results, or perform independent analysis. The narrative is a
translation of analytical findings into plain language -- not a new analysis.

**Rationale**: Keeping narrative generation separate from analysis preserves
the Engine-First boundary (Principle 6). The narrative is an interface-friendly
rendering of what the engine already computed. Allowing A15 to reinterpret or
extend analysis would blur the Analysis/Interface boundary.

**Stability**: High. This is a boundary constraint derived from Principle 6.

---

### A16-001: Verification Assistance, Not Fact-Checking

**Date**: 2026-07-27
**Component**: A16 (Verification Punchlist Generator) -- Milestone 5 planning
**Spec Reference**: Principles 2, 4, 17. Specification Chapter 16 (A16).

**Choice**: A16 generates investigation priorities only. It does not verify
claims, determine truth, or provide final correctness judgments. Each punchlist
entry explains WHY a claim deserves attention and suggests verification
approaches -- not what the correct answer is.

**Rationale**: OutputLens helps readers decide what to investigate, not what
to believe (Principle 4). The punchlist is a research agenda, not a list of
errors. This preserves the boundary between epistemological analysis and truth
determination (Principle 17). A16 that claimed "this claim is false" would
violate the project's non-goals.

**Stability**: High. This is a constitutional constraint.

---

### M6-001: Evaluation Does Not Define Correctness

**Date**: 2026-07-27
**Component**: Milestone 6 -- Evaluation Infrastructure
**Spec Reference**: Principles 2, 4, 17. A4/A5-001, A6-001, A16-001.

**Choice**: Evaluation infrastructure measures agreement, consistency,
usefulness, and explainability. It does not establish that analyzer outputs
are objectively correct. Golden datasets are measurement tools representing
annotated human judgments, not absolute truth.

**Annotation guidelines explicitly instruct annotators to**:
- Classify epistemological characteristics, not truth or correctness.
- Record uncertainty when they cannot confidently assign a classification.
- Note disagreements as data, not errors to be resolved.

**Evaluation metrics report**:
- Agreement between analyzer and human annotators (Cohen's kappa, F1).
- Inter-annotator agreement as a measure of task difficulty.
- Reasoning quality as rated by human evaluators.

**Evaluation metrics do NOT report**:
- "Accuracy" or "correctness" of classifications.
- "Error rates" implying the analyzer was wrong.
- Any metric that could be interpreted as truth verification.

**Rationale**: OutputLens evaluates analytical usefulness rather than truth
determination. If evaluation claimed to measure correctness, it would
contradict Principles 2 and 17, and undermine the project's non-goals.

**Stability**: High. Constitutional constraint.
