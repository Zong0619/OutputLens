# Evaluation Guide

How to evaluate OutputLens analyzer quality and contribute evaluation data.

---

## Evaluation Philosophy

Per **M6-001**: Evaluation does not define correctness.

Evaluation measures:
- **Agreement**: How closely analyzer classifications align with human annotations.
- **Consistency**: Whether similar inputs produce similar outputs.
- **Usefulness**: Whether outputs (punchlist, narrative) help readers.
- **Explainability**: Whether reasoning is specific, traceable, and non-circular.

Evaluation does NOT measure:
- Truth or factual correctness.
- Objective novelty.
- Whether the analyzer is "right" or "wrong."

---

## Evaluation Components

| Component | Purpose | Location |
|---|---|---|
| **Golden Datasets** | Measure agreement with human annotation | `benchmarks/golden_datasets/` |
| **Evaluation Harness** | Compute canonical metrics | `benchmarks/evaluation_harness/` |
| **Benchmark Corpora** | Measure consistency, stability, regression | `benchmarks/corpora/` |

---

## Golden Datasets

### What They Measure

| Dataset | Evaluates | Annotation |
|---|---|---|
| GOLD-CLAIM | A2 Claim Extractor | Claim boundaries, types, confidence markers |
| GOLD-ESTABLISHED | A4 Establishedness | E1-E5 levels with reasoning |
| GOLD-EVIDENCE | A5 Evidence Requirement | R1-R4 levels with reasoning |
| GOLD-NOVELTY | A6 Novelty | N1-N5 levels with reasoning |
| GOLD-PUNCHLIST | A16 Verification Punchlist | Investigation priorities, usefulness |

### Annotation Guidelines

See `benchmarks/golden_datasets/guidelines/README.md` for full protocols.
Key rules:

1. **Classify epistemological characteristics, not truth.** Assign E-levels,
   not true/false judgments.
2. **Record uncertainty.** If uncertain, mark it. Uncertainty is data.
3. **Disagreement is expected.** Inter-annotator disagreement is a finding
   about task difficulty, not an error.
4. **Reasoning is required.** Every classification annotation must include
   reasoning (min 20 characters).

### Knowledge Boundaries During Annotation

- **A6-001**: Novelty annotations record "apparent novelty from text signals,"
  not objective novelty.
- **A16-001**: Punchlist annotations record "would you investigate this claim?"
  not "is this claim false?"

---

## Evaluation Harness

The harness computes metrics from AnalysisDocuments and golden dataset
annotations. See `benchmarks/evaluation_harness/README.md` for usage.

### Metrics

| Category | Metric | Description |
|---|---|---|
| Extraction | Boundary F1 | Claim span alignment |
| Extraction | Type accuracy | Claim type agreement |
| Classification | Exact agreement | % matching gold exactly |
| Classification | Adjacent agreement | % within 1 level |
| Classification | Cohen's kappa | Agreement corrected for chance |
| Reasoning | Signal mention rate | % referencing specific signals |
| Reasoning | Circular rate | % restating classification |
| Synthesis | Punchlist precision | Fraction annotated "should verify" |
| Synthesis | Punchlist recall | Fraction of "should verify" in punchlist |

---

## Benchmark Corpora

### Corpus Types

| Corpus | Purpose | Mutability |
|---|---|---|
| BENCH-DIVERSITY | Consistency across domains | Appendable |
| BENCH-CHALLENGE | Stress-test difficult cases | Appendable |
| BENCH-TEMPORAL | Regression detection | **Immutable** |

### Adding Items

- **DIVERSITY**: Add responses covering new domains, models, or styles.
  Include metadata (domain, word count, claim density estimate).
- **CHALLENGE**: Add responses exhibiting patterns known to stress analyzers.
  Document why each item is challenging.
- **TEMPORAL**: New items require maintainer review. Existing items are
  **never modified**. Deprecation only via manifest flag.

---

## Contributing Evaluation Data

1. **Follow annotation guidelines.** Read `benchmarks/golden_datasets/guidelines/`.
2. **Start small.** Annotate 5-10 responses for your chosen dataset.
3. **Record your expertise level.** Self-report domain expertise
   (none/general/domain_informed/domain_expert).
4. **Submit with metadata.** Include annotator ID, timestamp, and notes.
5. **Expect disagreement.** Your annotations will be compared with others.
   Disagreement is valuable data.

---

## Reference

- [M6-001](IMPLEMENTATION_DECISIONS.md) -- Evaluation Does Not Define Correctness
- [Golden Dataset README](../benchmarks/golden_datasets/README.md) -- formats, versioning
- [Evaluation Harness README](../benchmarks/evaluation_harness/README.md) -- usage
- [Corpus README](../benchmarks/corpora/README.md) -- corpus formats
