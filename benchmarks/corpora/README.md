# OutputLens Benchmark Corpora

Collections of AI-generated responses for measuring analyzer consistency,
performance, stability, and regression behavior.

**Per M6-001**: Benchmark corpora measure behavioral characteristics.
They do NOT define correctness, truth, or quality rankings.

---

## Corpus Catalog

| Corpus | Purpose | Size | Mutability |
|---|---|---|---|
| BENCH-DIVERSITY | Consistency and distribution analysis across domains | 50+ responses | Appendable |
| BENCH-CHALLENGE | Stress-test analyzers on known-difficult patterns | 20+ responses | Appendable |
| BENCH-TEMPORAL | Regression detection across analyzer versions | 20+ responses | **Immutable** |

## Distinction from Golden Datasets

| | Golden Datasets | Benchmark Corpora |
|---|---|---|
| **Purpose** | Measure agreement with human annotation | Measure consistency, stability, performance |
| **Annotations** | Yes (human-labeled) | No (unannotated) |
| **Measures** | Agreement, usefulness, explainability | Distribution stability, latency, regression |
| **Truth claims** | None (per M6-001) | None (per M6-001) |
| **Mutability** | Versioned releases | Per-corpus policy |

## Corpus Format

Each corpus is a directory containing:
- `README.md` -- corpus-specific documentation
- `manifest.json` -- index of all items with metadata
- `items/` -- individual response files (one JSON per item)

Each item file follows this structure:
```json
{
  "item_id": "div_001",
  "response_text": "The full AI-generated response text.",
  "source_model": "claude-opus-4-8",
  "prompt": "The prompt that generated this response (optional).",
  "domain": "physics",
  "word_count": 150,
  "claim_density_estimate": "medium",
  "added_date": "2026-07-27",
  "notes": "Any observations about this item."
}
```
