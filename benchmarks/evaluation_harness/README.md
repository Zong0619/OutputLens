# OutputLens Evaluation Harness

Implementation-agnostic quality measurement for OutputLens analyzers.
Consumes serialized AnalysisDocuments (JSON) and golden dataset annotations.

**Per M6-001**: Measures agreement, consistency, usefulness, and explainability.
Does NOT define correctness. Does NOT modify analyzers.

## Architecture

```
evaluation_harness/
├── loader.py        # AnalysisDocument and golden dataset loading/validation
├── metrics/
│   ├── extraction.py     # Claim boundary F1, type accuracy
│   ├── classification.py # Agreement (exact/adjacent), kappa, confusion, distribution
│   ├── reasoning.py      # Specificity, circularity, signal mention rate
│   └── synthesis.py      # Trust profile correlation, punchlist precision/recall
└── reporter.py      # Per-item evaluation and report aggregation
```

## Usage

```python
from benchmarks.evaluation_harness.loader import load_analysis_document, load_golden_dataset
from benchmarks.evaluation_harness.reporter import generate_report

dataset = load_golden_dataset("benchmarks/golden_datasets/data/GOLD-CLAIM/v0.1/data.json")
docs = [load_analysis_document(f"output/item_{i}.json") for i in range(len(dataset["items"]))]
report = generate_report(dataset, docs)
print(report["summary"])
```

## Key Properties

- **Implementation-agnostic**: Consumes JSON AnalysisDocuments, not Python objects
- **Deterministic**: Same inputs produce identical outputs
- **Versioned**: Harness v0.1.0 works with AnalysisDocument v1.0.0
- **Evaluation, not conformance**: Measures quality, not specification compliance

## Metrics

| Category | Metric | Description |
|---|---|---|
| Extraction | Boundary F1 | Claim span alignment precision/recall |
| Extraction | Type accuracy | Claim type classification agreement |
| Classification | Exact agreement | % of classifications matching gold exactly |
| Classification | Adjacent agreement | % within 1 level (e.g., E2 vs E3) |
| Classification | Cohen's kappa | Inter-rater agreement corrected for chance |
| Classification | Distribution | Level frequency analysis |
| Reasoning | Signal mention rate | % of reasoning referencing specific signals |
| Reasoning | Circular rate | % of reasoning that restates classification |
| Synthesis | Punchlist precision | Fraction of entries annotated "should verify" |
| Synthesis | Punchlist recall | Fraction of "should verify" claims in punchlist |
| Synthesis | Usefulness | Human-rated usefulness (1-5) |
