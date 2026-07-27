# OutputLens Golden Datasets

Manually annotated corpora for evaluating analyzer quality. Golden datasets
measure agreement, consistency, usefulness, and explainability. They do NOT
define correctness or truth.

Per M6-001: Evaluation Does Not Define Correctness.

---

## Dataset Catalog

| Dataset | Evaluates | Annotation Type | Status |
|---|---|---|---|
| GOLD-CLAIM | A2 Claim Extractor | Claim boundaries, claim types, confidence markers | Schema defined |
| GOLD-CONCEPT | A3 Concept Extractor | Concept names, types, coreference, significance | Schema defined |
| GOLD-ESTABLISHED | A4 Establishedness Analyzer | E1-E5 levels with reasoning | Schema defined |
| GOLD-EVIDENCE | A5 Evidence Requirement Analyzer | R1-R4 levels with reasoning | Schema defined |
| GOLD-NOVELTY | A6 Novelty Analyzer | N1-N5 levels with reasoning | Schema defined |
| GOLD-PUNCHLIST | A16 Verification Punchlist | Priority ranking, usefulness ratings | Schema defined |

---

## Versioning Strategy

```
GOLD-CLAIM-v0.1    → Initial developer-annotated set (10-20 responses)
GOLD-CLAIM-v0.2    → Expanded set with expert annotators (50+ responses)
GOLD-CLAIM-v1.0    → Stable release with measured inter-annotator agreement

All datasets follow the same versioning pattern independently.
```

Each version is a directory under `data/<dataset_id>/<version>/` containing
the annotated JSON file and a metadata file describing annotators, agreement
metrics, and known limitations.

---

## Dataset Format

Every golden dataset is a JSON file with this structure:

```json
{
  "dataset_id": "GOLD-CLAIM",
  "version": "0.1.0",
  "description": "Claim boundary and type annotations for A2 evaluation.",
  "annotator_count": 3,
  "inter_annotator_agreement": {
    "metric": "boundary_f1",
    "value": 0.0,
    "note": "To be computed after annotation"
  },
  "items": [
    {
      "item_id": "001",
      "response_text": "The full AI-generated response text.",
      "source_model": "claude-opus-4-8",
      "domain": "physics",
      "prompt": "Explain quantum entanglement.",
      "annotations": { }
    }
  ]
}
```

Annotation formats are defined in individual schemas under `schemas/`.

---

## Annotation Guidelines

See `guidelines/` for per-dataset annotation instructions. Key boundary rules
(per M6-001 and existing knowledge boundary decisions):

1. **Classify epistemological characteristics, not truth.** Annotators assign
   E-levels, R-levels, N-levels -- not true/false judgments.
2. **Record uncertainty.** If an annotator cannot confidently assign a
   classification, they should mark it as uncertain rather than guessing.
3. **Disagreement is data.** Inter-annotator disagreement is a finding about
   task difficulty, not an error to eliminate.
4. **Reasoning is required.** Every classification annotation must include
   the reasoning behind it (min 20 characters).

---

## Evaluation Boundary Compliance

All datasets and guidelines preserve:

- **A4/A5-001**: Classifications are epistemological, not truth claims.
- **A6-001**: Novelty annotations record "apparent novelty from text signals,"
  not objective novelty verification.
- **A16-001**: Punchlist annotations record "would you investigate this claim?"
  not "is this claim false?"
- **M6-001**: Annotated data measures agreement; it does not define correctness.
