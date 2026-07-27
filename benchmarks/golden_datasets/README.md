# Golden Datasets

This directory will contain manually annotated corpora for evaluating analyzer
quality. These are NOT conformance tests -- they measure how well analyzers
perform, not whether they conform to the specification.

## Dataset Format

Each golden dataset is a JSON file containing:
- `dataset_id`: unique identifier
- `version`: semantic version
- `description`: what this dataset evaluates
- `annotator_count`: number of annotators per item
- `items`: array of annotated items

Each item contains:
- `response_text`: the full AI-generated response
- `source_model`: which model generated it (optional)
- `domain`: topic domain
- `annotations`: manual annotations (format varies by dataset type)

## Planned Datasets

| Dataset | Purpose | Status |
|---|---|---|
| GOLD-CLAIM v0.1 | Claim boundary + type evaluation | Not started |
| GOLD-CONCEPT v0.1 | Concept extraction evaluation | Not started |
| GOLD-ESTABLISHED v0.1 | Establishedness classification evaluation | Not started |
| GOLD-EVIDENCE v0.1 | Evidence requirement evaluation | Not started |

## Annotation Process

See `docs/IMPLEMENTATION_GUIDE.md` for annotation guidelines.
