# Contributing to OutputLens

OutputLens is an open-source analytical engine. Contributions are welcome
across analyzers, interfaces, evaluation datasets, and documentation.

---

## Development Setup

```bash
git clone https://github.com/outputlens/outputlens.git
cd outputlens
pip install -e ".[dev]"
```

### Running Tests

```bash
PYTHONPATH=src python3 -m pytest tests/ -v
```

All tests must pass before submitting a pull request.

### Optional Dependencies

```bash
pip install -e ".[api]"   # Flask for API server and web demo
```

---

## Contribution Types

| Type | Description | Reference |
|---|---|---|
| **Analyzer** | Implement a new analyzer or improve an existing one | [IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md) |
| **Interface** | Build a new interface (CLI, API, browser extension, IDE plugin) | See Interface Development below |
| **Evaluation** | Annotate golden datasets, expand benchmark corpora | [Benchmarks README](benchmarks/) |
| **Documentation** | Improve docs, fix errors, add examples | This file and `docs/` |

---

## Architecture Rules

All contributions must preserve:

1. **Analyzer independence.** Each analyzer has one responsibility, declared
   inputs, and no knowledge of its consumers.
2. **AnalysisDocument as contract.** All analyzer output flows into the
   versioned AnalysisDocument JSON schema. Interfaces consume this schema.
3. **Engine First, Interface Second.** Interfaces render AnalysisDocuments.
   They must not contain analytical logic -- no claim extraction, no
   classification, no score computation.
4. **No hidden analysis in interfaces.** JavaScript, HTML templates, and
   CLI formatting code must not duplicate or extend analyzer logic.

These rules are non-negotiable. They are enforced by automated tests
(source inspection for forbidden function names in interface code) and
by code review.

---

## New Analyzer Development

See [IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md) for the complete
guide. Quick checklist:

1. Create a module in `src/outputlens/analyzers/`
2. Implement the `Analyzer` subclass with a `declaration` and `analyze(context)` method
3. Declare all input dependencies explicitly via `AnalyzerInput`
4. Produce a single typed output
5. Provide a `register(registry)` function
6. Write tests covering: contract, inputs, normal operation, edge cases
7. Record implementation decisions in `docs/IMPLEMENTATION_DECISIONS.md`
8. Register in `src/outputlens/analyzers/__init__.py`

---

## Interface Development

Interfaces consume AnalysisDocuments and render results. They do not
perform analysis.

**To build a new interface:**

1. Consume AnalysisDocument JSON from the engine (via API, CLI, or library).
2. Read the fields you need (`trust_profile`, `claims`, `verification_punchlist`, etc.).
3. Render them for your target platform (terminal, browser, IDE, voice).
4. Do not compute new values. Do not classify. Do not extract claims.

**Reference interfaces** (in `src/outputlens/interfaces/`):
- `cli.py` -- command-line interface
- `api.py` -- REST API server
- `web/` -- browser-based demo
- `engine_runner.py` -- shared engine invocation

---

## Evaluation Contributions

### Golden Datasets

Golden datasets measure agreement between analyzer outputs and human
annotations. See `benchmarks/golden_datasets/guidelines/` for annotation
protocols. Per M6-001: annotations classify epistemological characteristics,
not truth.

### Benchmark Corpora

Benchmark corpora measure consistency, performance, and regression behavior.
See `benchmarks/corpora/` for corpus formats.

**BENCH-TEMPORAL is immutable.** Items are never modified or removed.

---

## Pull Request Process

1. **Tests.** Add tests for new functionality. Ensure all existing tests pass.
2. **Documentation.** Update `PROJECT_STATE.md` and `IMPLEMENTATION_DECISIONS.md`
   if your change introduces new implementation choices.
3. **Decision record.** If the specification is silent on your approach,
   add an entry to `IMPLEMENTATION_DECISIONS.md` following the template.
4. **Boundary check.** Verify your change does not:
   - Add analytical logic to interfaces.
   - Modify analyzer outputs without schema version consideration.
   - Introduce external knowledge into core analyzers.
   - Claim truth or correctness in classification reasoning.
5. **Review.** All PRs are reviewed against the Design Principles
   (`docs/PROJECT_CONTEXT.md`) and the cardinal rules in
   `docs/IMPLEMENTATION_GUIDE.md`.

---

## Change Categories

Per [DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md), classify your
change before implementing:

| Category | Scope | Requires |
|---|---|---|
| **Implementation** | Code only, no spec changes | Standard PR |
| **Documentation** | Docs only, no behavior change | Standard PR |
| **Specification** | Changes requirements or behavior | Spec revision + implementation update |
| **Architecture** | Changes foundational design | Evidence of inconsistency + governance review |

Architecture changes require the highest justification. Start at the lowest
category and escalate only when evidence demands it.

---

## Questions?

Open an issue or discussion on the repository. Before asking, check:
- [IMPLEMENTATION_DECISIONS.md](docs/IMPLEMENTATION_DECISIONS.md) -- your
  question may already be answered.
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) -- for structural questions.
- [PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) -- for philosophy and boundaries.
