# OutputLens Annotation Guidelines

Guidelines for human annotators contributing to OutputLens golden datasets.
All annotation work must follow these protocols.

---

## General Principles

### 1. Classify Epistemological Characteristics, Not Truth

Per **A4/A5-001** and **M6-001**: Annotators classify epistemological
characteristics (establishedness, evidence requirement, novelty), NOT whether
a claim is true or false. For example:
- "This claim is common knowledge" (E1) -- correct annotation
- "This claim is true" -- NOT a valid annotation

### 2. Record Uncertainty

If you cannot confidently assign a classification:
- Set `uncertain: true` on the annotation.
- Optionally provide an `alternative_level` (your second choice).
- Uncertainty IS data. It tells us which classifications are inherently
  difficult. Do not guess to appear confident.

### 3. Disagreement Is Expected

Different annotators may reasonably disagree on epistemological
classifications. This is especially true for:
- The E2/E3 boundary (domain established vs. plausible)
- The N2/N3 boundary (synthesis vs. potentially novel)
- The R2/R3 boundary (evidence provided vs. evidence expected)

Disagreement is measured and reported. It is a finding about task difficulty,
not an error to eliminate.

### 4. Reasoning Is Required

Every classification annotation must include reasoning (min 20 characters).
The reasoning should explain WHY you assigned this level, not just restate it:
- Good: "This is standard textbook material on quantum mechanics, taught in introductory courses." (E2)
- Bad: "This is E2." (circular -- not useful)
- Good: "The claim asserts a specific percentage without naming a source or study." (R4)
- Bad: "No evidence." (too short, not informative)

---

## GOLD-CLAIM: Claim Annotations

### Task

Read the AI response and identify every individual claim. A claim is a single,
self-contained proposition that can be independently evaluated.

### Claim Boundaries

- One sentence may contain multiple claims: "Water freezes at 0C and boils at 100C."
  → Two claims.
- One claim may span multiple sentences (rare). When in doubt, split.
- Mark claim boundaries at the character offset in the original text.
- If uncertain about a boundary, set `uncertain: true`.

### Claim Types

Assign one of 9 claim types per the specification:
- `factual_assertion`: A claim about what is true in the world.
- `conceptual_definition`: A claim that defines or characterizes a concept.
- `causal_claim`: X causes, leads to, or influences Y.
- `predictive_claim`: What will or would happen.
- `normative_claim`: What should or ought to be.
- `methodological_claim`: How something is or should be done.
- `comparative_claim`: Similarity, difference, or ranking.
- `attribution_claim`: Who said, discovered, or published something.
- `meta_claim`: About the response itself or its limitations.

### Confidence Markers

Identify hedging language ("may," "suggests," "potentially") and certainty
language ("definitely," "clearly," "it is proven that"). Mark the exact
span and assign intensity (weak/moderate/strong).

---

## GOLD-ESTABLISHED: Establishedness Annotations

### Task

For each extracted claim, assign an E-level with reasoning.

### E1 -- Common Knowledge

Widely known across educated general audiences. Taught in introductory
contexts. Not disputed. Examples: "Water freezes at 0C." "The Earth orbits
the Sun."

### E2 -- Domain Established

Accepted within a specific field. Found in textbooks, review articles,
consensus statements. Examples: "Quantum entanglement violates Bell's
inequalities." "Natural selection is the primary mechanism of evolution."

### E3 -- Plausible but Unverified

Reasonable given established knowledge but without clear consensus or
canonical source. Examples: "Entanglement may play a role in avian
magnetoreception."

### E4 -- Unverifiable (by design)

Subjective, normative, or speculative claims. Examples: "The Many-Worlds
interpretation is more elegant than Copenhagen."

### E5 -- Unknown / Boundary

The annotator cannot assess establishedness. Use when the domain is too
specialized or the claim is too nuanced for confident classification.

### Per A6-001

Novelty and establishedness are separate axes. A novel claim CAN be
well-established (E2) in a niche domain. Do not assume novelty implies
low establishedness, or vice versa.

---

## GOLD-EVIDENCE: Evidence Requirement Annotations

### Task

For each claim, assess what evidential support it demands and whether the
response provides it.

### R1 -- Self-Evident / Definitional

True by definition or trivial logical consequence. Examples: "A bachelor is
an unmarried man." Definitions, tautologies, mathematical identities.

### R2 -- Evidence Provided

The response itself cites, references, or describes supporting evidence.
Examples: "A 2023 Nature study found that..." (with specifics).

### R3 -- Evidence Expected

Claim gestures at evidence without specifics. Examples: "Studies show..." (no
specific study named). "Research indicates..." (no citation).

### R4 -- Evidence Essential

Specific, substantive assertion with no supporting evidence. Examples: "73%
of patients experienced complete remission." (no source).

### Note

Evidence requirement is independent of establishedness. A well-established
claim (E1) can have poor evidence provision (R4) if the model asserts it
without citation. Both axes matter.

---

## GOLD-NOVELTY: Novelty Annotations

### Task

For each claim, assess how it relates to existing knowledge based on
observable text signals. Per **A6-001**, this is NOT objective novelty
verification. Annotators should assess "apparent novelty from what the
text presents as established."

### N1 -- Canonical

Standard material appearing in any competent treatment. Textbook definitions,
well-known facts.

### N2 -- Non-Trivial Synthesis

Known ideas presented in non-obvious combination or framing.

### N3 -- Potentially Novel

Introduces a concept, connection, or hypothesis not obviously present in
established knowledge.

### N4 -- Apparently Original

Reads as if generating a new idea, hypothesis, or framework.

### N5 -- Uncertain

Annotator cannot assess novelty. Use freely -- this IS a valid result.

---

## GOLD-PUNCHLIST: Punchlist Annotations

### Task

Review an OutputLens Verification Punchlist and evaluate each entry.

Per **A16-001**: The punchlist provides investigation priorities, not truth
determination. Annotators evaluate whether they WOULD investigate, not whether
the claim IS false.

### Questions to Answer for Each Entry

1. **Would you investigate this claim?** (should_verify: true/false)
   Do you agree this claim deserves attention?

2. **What priority?** (1-5, 1=highest)
   How urgently should this claim be investigated relative to others?

3. **Why?** (reason)
   Explain your reasoning.

4. **How would you investigate?** (suggested_verification)
   What approach would you take?

### Missing Claims

If you identify claims that SHOULD be in the punchlist but are not, add them
to the `missing_claims` array. This measures punchlist recall.

### Overall Usefulness

Rate the punchlist 1-5: "How useful is this punchlist for a reader who wants
to know what to verify?"

---

## Version History

| Version | Date | Changes |
|---|---|---|
| 0.1.0 | 2026-07-27 | Initial annotation guidelines for all 5 datasets. |
