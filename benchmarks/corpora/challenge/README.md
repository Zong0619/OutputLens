# BENCH-CHALLENGE

**Purpose**: Stress-test analyzers on known-difficult patterns. Each item is
selected because it exhibits characteristics that historically challenge
rule-based extraction and classification.

**Mutability**: Appendable. New challenge patterns may be added as they are
discovered. Existing items are never modified.

**Target size**: 20+ curated cases initially.

## Challenge Patterns

| Pattern | Description | Example Signal |
|---|---|---|
| high_claim_density | Many propositions per sentence | 5+ claims in a single sentence |
| hedging_heavy | Pervasive uncertainty language | "may," "might," "potentially," "could be" |
| self_contradiction | Response contradicts itself | Two claims that cannot both be true |
| domain_mixing | Multiple domains in one response | Physics claims adjacent to philosophy claims |
| code_prose_mix | Code interspersed with natural language | Function definitions with explanatory text |
| mathematical_notation | Formulas and equations | LaTeX, math notation in claims |
| nested_structure | Deeply nested clauses | "Researchers found that X, which implies Y, suggests Z" |
| undefined_terms | Uses undefined technical jargon | Domain terms without definitions |
| list_heavy | Bullet points, numbered lists, enumerations | Structured list responses |
| implicit_claims | Claims implied but not explicitly stated | Requires inference to identify propositions |

## Usage

Run all analyzers against each item. Compare against baseline:
- Does claim extraction degrade on high-density text?
- Does classification over-hedge on hedging-heavy text?
- Does A7 detect (or incorrectly flag) contradictions?
- Does concept extraction handle domain mixing?

Each item's `notes` field documents why it was selected and what specific
analyzer behavior it is designed to stress-test.
