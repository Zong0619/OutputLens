# OutputLens

**See what your AI isn't telling you.**

OutputLens is an open-source analysis engine that decomposes AI-generated text
into structured claims and classifies each by its epistemological
characteristics -- how established it is, what evidence it requires, and how
novel it appears.

**OutputLens does not determine truth.** It helps readers decide what to
investigate -- not what to believe. Think of it as a nutrition label for
AI-generated text.

---

## Quick Start

```bash
pip install outputlens

# Analyze text from the command line
outputlens analyze --text "AI is transforming society. It has limitations."

# Pipe text from a file
cat response.txt | outputlens analyze --summary

# Get full JSON output
outputlens analyze --text "Water freezes at 0 degrees Celsius." --json
```

### API Server

```bash
pip install outputlens[api]
outputlens-serve

# Open http://localhost:8080 for the web demo
# POST to http://localhost:8080/analyze for JSON API
```

```bash
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Quantum entanglement allows particles to share quantum states."}'
```

---

## What OutputLens Does

1. **Extracts every claim** from AI-generated text, traceable to exact positions
   in the original.
2. **Classifies each claim** along three independent axes:
   - **Establishedness** (E1-E5): How firmly grounded is this claim?
   - **Evidence Requirement** (R1-R4): Does the response provide evidence?
   - **Novelty** (N1-N5): Is this canonical or a potentially new idea?
3. **Explains every classification** with natural language reasoning.
4. **Prioritizes what to verify** with a ranked punchlist.

## What OutputLens Does NOT Do

- Tell you what is true or false
- Fact-check claims for you
- Detect hallucinations
- Rate responses as "reliable" or "unreliable"

---

## Architecture

A 16-analyzer pipeline transforms text into a complete AnalysisDocument:

```
Text → A1 Normalize → A2 Extract Claims → A3 Extract Concepts
     → A4 Establishedness | A5 Evidence | A6 Novelty
     → A7 Claim Graph → A8 Concept Graph
     → A9-A15 Synthesis → A16 Verification Punchlist
```

Every interface (CLI, API, Web) consumes the same versioned
**AnalysisDocument** JSON.

---

## Example Output

```
OUTPUTLENS ANALYSIS
============================================================
Trust Profile:
  Established:         65.0%
  Plausible/Inferred:  25.0%
  Needs Verification:  10.0%

--- Claims to Verify ---
  #1 [no_evidence] The model achieves 94.7% accuracy...
      → Search for primary source or benchmark data.
  #2 [overconfident] This definitively proves that...
      → Claim states high certainty but has low establishedness.
```

---

## Project Status

| | |
|---|---|
| **Version** | v1.1.0-alpha |
| **Analyzers** | 16 of 16 implemented |
| **Tests** | 475 passing |
| **Milestones** | M0-M6 complete, M7 in progress |

---

## Documentation

| Document | Description |
|---|---|
| [Project Context](docs/PROJECT_CONTEXT.md) | Philosophy, design principles, non-goals |
| [Architecture](docs/ARCHITECTURE.md) | Three-layer architecture, analyzer framework |
| [Implementation Guide](docs/IMPLEMENTATION_GUIDE.md) | How to implement a new analyzer |
| [Development Workflow](docs/DEVELOPMENT_WORKFLOW.md) | Standard engineering process |
| [Roadmap](docs/ROADMAP.md) | Current and future milestones |
| [Contributing](CONTRIBUTING.md) | How to contribute |

---

## License

Apache 2.0. OutputLens is open source -- its methods, logic, and output
structure are transparent, auditable, and forkable.
