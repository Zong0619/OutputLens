# OutputLens -- Implementation Guide

**Audience**: Contributors implementing new analyzers, interfaces, or engine improvements.
**Prerequisites**: Read `docs/ARCHITECTURE.md` and `docs/PROJECT_CONTEXT.md` first.

---

## How to Implement a New Analyzer

### Step 1: Understand the Analyzer Contract

Every analyzer must conform to the contract defined in `src/outputlens/orchestration/analyzer.py`:

```python
class MyAnalyzer(Analyzer):
    declaration = AnalyzerDeclaration(
        id="a17",                          # Unique ID in the catalog
        version="0.1.0",                   # Semantic version
        responsibility="One sentence describing the analytical question this answers.",
        inputs=(                            # Declared dependencies
            AnalyzerInput("a2", "a2"),      # (producer_analyzer_id, output_name)
            AnalyzerInput("a4", "a4"),
        ),
        output_type=MyOutputType,           # The Python type this analyzer returns
        layer="synthesis",                  # foundation|classification|structure|synthesis|terminal
    )

    def analyze(self, context: AnalysisContext) -> MyOutputType:
        # Read ONLY declared inputs
        claims = context.get_output("a2", "a2")
        annotations = context.get_output("a4", "a4")

        # Perform analysis...

        return MyOutputType(...)
```

### Step 2: Declare Dependencies Correctly

- Each `AnalyzerInput` references a producer analyzer's ID and output name.
- Convention: output name matches the producer's analyzer ID.
- Required inputs (`required=True`, the default) will cause the orchestrator to
  pull the producer into the transitive closure. If the producer fails, analysis
  halts.
- Optional inputs (`required=False`) degrade gracefully. If the producer is
  unavailable, `context.get_output()` returns `None`.

**Rule**: Only declare inputs your analyzer actually reads. Reading undeclared
inputs from the context is a contract violation.

### Step 3: Implement analyze()

- Accept `context: AnalysisContext`. Read ONLY your declared inputs via
  `context.get_output(analyzer_id, output_name)`.
- Return a single typed output matching `declaration.output_type`.
- If a required input is missing, raise `AnalyzerError` with a descriptive message.
- If analysis fails for any other reason, raise `AnalyzerError`.
- If an optional input is missing, degrade gracefully (skip that part of analysis).

### Step 4: Register the Analyzer

In your analyzer's module, provide a factory function and register:

```python
# In src/outputlens/analyzers/my_analyzer.py

def register(registry: AnalyzerRegistry) -> None:
    registry.register(MyAnalyzer.declaration, lambda: MyAnalyzer())
```

Then import and call `register()` in the application startup.

### Step 5: Write Tests

Minimum test coverage for a new analyzer:

1. **Contract tests**: Verify declaration fields (id, version, inputs, layer).
2. **Input validation tests**: Verify the analyzer raises `AnalyzerError` when
   required inputs are missing.
3. **Output type tests**: Verify the return value matches `declaration.output_type`.
4. **Behavioral tests**: With mock inputs, verify the analyzer produces expected output.
5. **Edge case tests**: Empty input, single-item input, degenerate cases.
6. **Integration test**: Wire the analyzer into the orchestrator and run end-to-end.

### Step 6: Record Implementation Decisions

Add entries to `docs/IMPLEMENTATION_DECISIONS.md` for every significant choice
not mandated by the specification:

- What NLP library/technique is used?
- What heuristics or thresholds were chosen?
- What knowledge source does classification use?
- What graph algorithms are used?

---

## Coding Conventions

### Python Style

- Follow PEP 8. Ruff is configured in `pyproject.toml`.
- Line length: 100 characters.
- Use `from __future__ import annotations` in all modules (enables `X | None`
  syntax on Python 3.10).
- Docstrings: Google style. Every public class and method must have a docstring.

### Dataclasses

- All Analysis Model objects use `@dataclass(frozen=True)`.
- Use `tuple[...]` for immutable sequences, `list[...]` for mutable sequences
  (during construction only).
- Validate in `__post_init__`. Raise `ValueError` for invalid values.

### Type Annotations

- All public functions and methods must have type annotations.
- Use `| None` rather than `Optional[X]`.
- Use `X | Y` rather than `Union[X, Y]`.

### Immutability

- Analysis Model objects: `frozen=True` dataclasses. Never modify after creation.
- AnalysisDocument: Mutable during construction via setter methods. Call
  `finalize()` to make immutable. Attempted mutation after finalization raises
  `RuntimeError`.
- Runtime Model objects: Generally `frozen=True`. PositionIndex and
  NormalizedText are immutable once constructed.

---

## Testing Expectations

### Test Organization

```
tests/
├── unit/
│   ├── test_runtime_model.py    # Runtime dataclasses + normalizer
│   ├── test_analysis_model.py   # Analysis dataclasses + AnalysisDocument
│   ├── test_orchestration.py    # Dependency resolution + engine
│   └── test_a2_claim_extractor.py  # Per-analyzer unit tests
├── integration/
│   └── test_pipeline.py         # End-to-end analyzer chains
```

### Test Standards

- Every new analyzer must have a corresponding `tests/unit/test_aN_name.py` file.
- Every public method should have at least one test.
- Edge cases: empty input, single item, maximum items, invalid input.
- Immutability: verify that frozen dataclasses cannot be modified.
- Use pytest fixtures for common test data (sample RawInput, mock claims, etc.).

### Running Tests

```bash
PYTHONPATH=src python3 -m pytest tests/ -v
```

---

## Schema Validation

The AnalysisDocument JSON Schema lives at:
`src/outputlens/analysis/schemas/analysis_document_v1.json`

### Validating Output

```python
from outputlens.analysis.schemas import get_current_schema
import jsonschema

schema = get_current_schema()
doc = analysis_document.to_dict()
jsonschema.validate(doc, schema)
```

### Schema Changes

The JSON Schema is versioned. Changes to the schema MUST:
1. Bump the schema version.
2. Update `SCHEMA_VERSION` in `document.py`.
3. Add a new schema file (e.g., `analysis_document_v2.json`).
4. Add backward-compatibility handling in the schema loader.
5. Update conformance tests.

Within a major version (1.x.x), changes must be backward-compatible (additive only).
Breaking changes require a major version bump (2.0.0).

---

## Execution Model

### Analyzer Lifecycle

1. **Registration**: `registry.register(declaration, factory)` -- at startup.
2. **Resolution**: `resolve_execution_plan(requested, registry)` -- produces
   layered execution plan.
3. **Execution**: `engine.execute(requested, context)` -- runs analyzers in
   dependency order.
4. **Output recording**: Analyzer return value stored in `context.set_output()`.
5. **Document assembly**: Outputs copied to AnalysisDocument.

### Parallelism

Analyzers within the same layer (no mutual dependencies) execute concurrently
via `ThreadPoolExecutor`. The `max_workers` parameter controls concurrency.
Default: Python's default (`min(32, os.cpu_count() + 4)`).

### Error Handling

- **Required analyzer failure**: If a failed analyzer has dependents, analysis
  halts with `RuntimeError`.
- **Optional/terminal analyzer failure**: Failure is logged via callback. Output
  is set to `None`. Dependent analyzers should handle `None` gracefully.
- **Dependency cycle**: Detected during `resolve_execution_plan()`.
  Raises `ValueError`.

---

## How to Avoid Violating the Specification

### The Cardinal Rules

1. **Never put analytical logic in interface code.** Interfaces render
   AnalysisDocuments; they do not perform analysis.

2. **Never read undeclared inputs from AnalysisContext.** If your analyzer needs
   a new dependency, add it to `declaration.inputs`.

3. **Never modify an Analysis Model object after creation.** Use frozen
   dataclasses. Construct new objects if you need different data.

4. **Never produce an output type that doesn't match `declaration.output_type`.**

5. **Never skip the reasoning field on Annotations.** Min 20 characters. Must
   explain WHY the classification was made.

6. **Never assert truth in classification reasoning.** "This claim is E1" is
   correct. "This claim is true" violates Principle 17.

7. **Never use model metadata in analysis.** The engine operates on text. Model
   identifiers are stored in Metadata for the reader's context; analyzers must
   not consume them.

8. **Never design an analyzer for a specific interface.** If the browser
   extension needs a particular output format, the interface should transform
   the AnalysisDocument -- the engine should not produce interface-specific output.

### The Checklist

Before submitting a PR, verify:

- [ ] Analyzer conforms to the contract (declaration, inputs, output_type, layer)
- [ ] All inputs are declared; no undeclared context reads
- [ ] Output type matches declaration
- [ ] Reasoning strings meet minimum length and quality
- [ ] No truth assertions in reasoning or synthesis outputs
- [ ] Tests cover: contract, missing inputs, normal operation, edge cases
- [ ] Implementation decisions recorded in `IMPLEMENTATION_DECISIONS.md`
- [ ] Schema validation passes on test output
- [ ] `AnalysisDocument.validate()` returns no errors
