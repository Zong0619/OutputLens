# OutputLens Evaluation Report v1

**Date**: 2026-07-27
**Engine version**: 0.1.0 (reference implementation)
**Report status**: Initial baseline

---

## 1. Evaluation Purpose

This report establishes the first quantitative baseline for the OutputLens
reference implementation. It measures analytical behavior, consistency,
explainability, and agreement with annotation protocols.

**Per M6-001**: This evaluation does NOT determine whether OutputLens is
objectively correct. It measures:

- **Agreement**: How closely analyzer classifications align with human
  annotations on the same epistemological dimensions.
- **Consistency**: Whether similar inputs produce similar outputs.
- **Explainability**: Whether the reasoning produced is specific, traceable,
  and non-circular.
- **Usefulness**: Whether the verification punchlist prioritizes claims
  a reader would actually want to investigate.

Where agreement is low, that is a finding about task difficulty -- not a
failure. Epistemological classification is inherently subjective at the
boundaries between levels.

---

## 2. Evaluation Methodology

### 2.1 Infrastructure

| Component | Status | Description |
|---|---|---|
| Golden Datasets | Schema defined, data pending | GOLD-CLAIM, GOLD-ESTABLISHED, GOLD-EVIDENCE, GOLD-NOVELTY, GOLD-PUNCHLIST |
| Evaluation Harness | Implemented (25 tests) | Implementation-agnostic metric computation from AnalysisDocuments |
| Benchmark Corpora | Structure defined, samples populated | BENCH-DIVERSITY (10 items), BENCH-CHALLENGE (8 patterns), BENCH-TEMPORAL (5 items) |

### 2.2 Metrics

| Category | Metric | Description |
|---|---|---|
| Extraction | Boundary F1 | Claim span alignment: precision, recall, F1 |
| Extraction | Type accuracy | Claim type agreement with gold annotations |
| Classification | Exact agreement | % of classifications matching gold exactly |
| Classification | Adjacent agreement | % within 1 level (e.g., E2 vs E3 counts as agreement) |
| Classification | Cohen's kappa | Agreement corrected for chance |
| Classification | Distribution | Level frequency analysis |
| Reasoning | Signal mention rate | % of reasoning referencing specific detected signals |
| Reasoning | Circular rate | % of reasoning that restates classification without explanation |
| Synthesis | Punchlist precision | Fraction of entries annotated "should verify" |
| Synthesis | Punchlist recall | Fraction of gold "should verify" claims appearing in punchlist |
| Synthesis | Usefulness | Human rating 1-5 |

### 2.3 Annotation Assumptions

- Annotators classify epistemological characteristics, not truth.
- Inter-annotator disagreement is expected, especially at E2/E3 and N2/N3 boundaries.
- Reasoning annotations require minimum 20 characters and must explain WHY.
- Per A6-001: Novelty annotations record "apparent novelty," not objective novelty.
- Per A16-001: Punchlist annotations record "would you investigate?" not "is this false?"

---

## 3. Dataset Overview

### 3.1 Golden Datasets

| Dataset | Evaluates | Status |
|---|---|---|
| GOLD-CLAIM | A2 Claim Extractor | Schema + guidelines complete; annotated data pending |
| GOLD-ESTABLISHED | A4 Establishedness Analyzer | Schema + guidelines complete; annotated data pending |
| GOLD-EVIDENCE | A5 Evidence Requirement Analyzer | Schema + guidelines complete; annotated data pending |
| GOLD-NOVELTY | A6 Novelty Analyzer | Schema + guidelines complete; annotated data pending |
| GOLD-PUNCHLIST | A16 Verification Punchlist | Schema + guidelines complete; annotated data pending |

**Current limitation**: Golden datasets exist as schemas and annotation
guidelines only. No annotated data has been collected. Quantitative
agreement metrics (F1, kappa, precision/recall) will be reported in
Evaluation Report v2 after the initial annotation phase.

### 3.2 Benchmark Corpora

| Corpus | Items | Purpose | Status |
|---|---|---|---|
| BENCH-DIVERSITY | 10 items, 10 domains | Consistency measurement | Structure complete, sample items populated |
| BENCH-CHALLENGE | 8 challenge patterns | Stress-testing | Patterns defined, infrastructure ready |
| BENCH-TEMPORAL | 5 items | Regression detection | Immutable set, policy documented |

---

## 4. Metric Results

### 4.1 Extraction (A2)

**Status**: Infrastructure ready. Quantitative results pending annotated data.

The evaluation harness supports boundary F1 computation with 50% overlap
alignment. Claim type accuracy is measured via confusion matrix against
gold-standard type annotations.

**Preliminary qualitative assessment** (from M1 evaluation examples):
- Sentence splitting: Reliable for simple declarative sentences.
- Conjunction decomposition: Correctly splits ", and" and ", but" patterns with
  independent clauses. Known false positives on list continuations.
- Abbreviation handling: Title abbreviations (Dr., Prof.) correctly block
  splitting. General abbreviations (etc., approx.) correctly allow splitting
  when followed by capital letters.
- List detection: Bullet and numbered lists correctly split. Dash-based lists
  detected.

### 4.2 Classification

**Status**: Infrastructure ready. Quantitative results pending annotated data.

#### A4: Establishedness (E1-E5)

Heuristic signals: claim type priors, concept domain grounding, hedging
detection, specificity detection. Known to default conservatively to E3
when signals are insufficient (intentional per A4/A5-001).

#### A5: Evidence Requirement (R1-R4)

Pattern-based signal detection: citation patterns (R2), evidence gestures
(R3), definitional structures (R1), specific unsupported claims (R4).
Most tractable classification axis. Evaluation examples show 6/7 PASS on
representative cases.

#### A6: Novelty (N1-N5)

Heuristic signals from A3 concept types, claim types, and established
framing markers. Correctly defaults to N5 when signals are insufficient.
Knowledge boundary compliance verified: reasoning explicitly acknowledges
heuristic nature.

### 4.3 Reasoning

**Preliminary assessment**: All 16 analyzers produce reasoning strings meeting
the minimum 20-character requirement. Signal-based analyzers (A4, A5, A6)
reference specific detected signals (citation patterns, hedging markers,
concept types) rather than restating classification labels.

**Known gap**: Some reasoning for default classifications is generic
("insufficient signals detected"). This is correct per the knowledge
boundary but may not be maximally useful to readers.

### 4.4 Synthesis

**A9 Trust Profile**: Correctly computes three-part distribution from A4+A5.
Rounding compensation ensures percentages always sum to 100.

**A16 Punchlist**: Multi-factor prioritization (evidence urgency, structural
impact, overconfidence, novelty). Known to produce useful rankings on
evaluation examples. Per A16-001: entries explain why to investigate,
not what is false.

---

## 5. Findings

### Strengths

1. **Deterministic pipeline**: All 16 analyzers produce identical output for
   identical input. Reproducibility is verified at the architecture level
   (immutable objects, no external API calls).

2. **Signal-based reasoning**: Classification reasoning references specific
   detected signals rather than circularly restating labels. This makes
   classifications auditable and debatable.

3. **Knowledge boundary integrity**: All three classification axes (E, R, N)
   respect the A4/A5-001 boundary. No analyzer consults external knowledge.
   Conservative defaults (E3, R4, N5) are used when signals are insufficient.

4. **Pipeline depth**: The 16-analyzer decomposition chain transforms raw
   text into a complete AnalysisDocument with extracted claims, concepts,
   three-axis classifications, relationship graphs, synthesis metrics, and
   a verification punchlist -- all within the knowledge boundary.

### Weaknesses

1. **Classification granularity**: Without external knowledge, A4 cannot
   distinguish "common knowledge" (E1) from "domain established" (E2) for
   claims that lack concept domain associations.

2. **Reasoning depth**: Default classifications produce generic reasoning.
   This is honest but may limit reader usefulness.

3. **A6 novelty assessment**: Heuristic novelty classification is inherently
   coarse. N2 (Non-Trivial Synthesis) is particularly difficult to detect
   without knowledge of what constitutes "standard" combinations.

### Unexpected Behaviors

None identified in evaluation examples. All analyzer outputs are consistent
with documented heuristics and known limitations.

---

## 6. Known Limitations

1. **No annotated golden datasets**: Quantitative agreement metrics (F1,
   kappa, precision/recall) cannot yet be computed. All metric results
   in this report are qualitative assessments from evaluation examples.

2. **Small benchmark corpora**: BENCH-DIVERSITY (10 items) provides
   structural validation but not statistical coverage.

3. **Subjective dimensions**: Establishedness (E2/E3 boundary) and novelty
   (N2/N3 boundary) are inherently subjective. Inter-annotator agreement
   is expected to be moderate, and this is a finding about task difficulty,
   not analyzer quality.

4. **Single implementation**: Only the reference implementation exists.
   Cross-implementation consistency cannot yet be measured.

5. **No interface evaluation**: Browser extension, CLI, and web interface
   are not yet built. Reader-facing usefulness has not been evaluated.

---

## 7. Future Improvements

1. **Annotated data collection**: Populate GOLD-CLAIM, GOLD-ESTABLISHED,
   GOLD-EVIDENCE, and GOLD-PUNCHLIST with initial developer annotations
   (10-20 responses each). Compute first quantitative metrics.

2. **Corpus expansion**: Grow BENCH-DIVERSITY to 100+ items with real AI
   responses from multiple models.

3. **Inter-annotator agreement study**: Measure agreement on E, R, and N
   classifications to establish task difficulty baselines.

4. **Interface evaluation**: Build reference interfaces (CLI, web) and
   evaluate reader-facing usefulness of the punchlist and narrative.

5. **Cross-implementation comparison**: Encourage community implementations
   and compare evaluation results.

---

*End of Evaluation Report v1.*
