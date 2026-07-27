# Analyzer Development Guide

How to implement a new analyzer for the OutputLens engine.

---

## Analyzer Philosophy

Every analyzer follows four principles:

1. **Single responsibility.** An analyzer answers exactly one analytical
   question. If you need to answer two questions, write two analyzers.
2. **Independence.** An analyzer knows nothing about which analyzers consume
   its output. It declares its inputs; the orchestrator handles the rest.
3. **Determinism.** Same inputs produce identical outputs. No randomness.
   No external API calls without documenting reproducibility impact.
4. **Traceability.** Every output must be traceable to specific input
   positions or objects. Classifications reference claim IDs. Surface forms
   have character offsets.

---

## Analyzer Contract

Every analyzer implements the contract in `src/outputlens/orchestration/analyzer.py`:

```python
class MyAnalyzer(Analyzer):
    declaration = AnalyzerDeclaration(
        id="a17",                    # Unique ID
        version="0.1.0",             # Semantic version
        responsibility="One sentence describing the analytical question.",
        inputs=(                      # Declared dependencies
            AnalyzerInput("a2", "a2"),
        ),
        output_type=list,             # Python type returned
        layer="classification",       # foundation|classification|structure|synthesis|terminal
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        claims = context.get_output("a2", "a2")["claims"]
        # Perform analysis...
        return {"my_output": result}
```

### Input Declaration

- Each `AnalyzerInput` references a producer analyzer's ID and output name.
- Convention: output name matches the producer's analyzer ID.
- Required inputs (`required=True`) halt analysis if unavailable.
- Only read declared inputs from the context. Reading undeclared inputs
  is a contract violation.

### Output Convention

- Return a dict with a single key matching your analyzer ID.
- The value must match `declaration.output_type`.
- The output flows into the AnalysisDocument through setter methods.

### Layers

| Layer | Description | Examples |
|---|---|---|
| foundation | Primitives consumed by everything | A1, A2, A3 |
| classification | Independent per-claim axes | A4, A5, A6 |
| structure | Relationships between primitives | A7, A8 |
| synthesis | Response-level aggregation | A9-A15 |
| terminal | Reader-facing output | A16 |

---

## Development Process

1. **Understand the specification.** Read the relevant spec chapter for your
   analyzer. Understand its inputs, outputs, and classification scale.
2. **Create an implementation plan.** Identify signals, heuristics, or
   algorithms. Document where the specification is silent.
3. **Record decisions.** Add entries to `docs/IMPLEMENTATION_DECISIONS.md`
   for every choice not mandated by the specification.
4. **Implement the analyzer.** Follow the contract. Use frozen dataclasses.
   Validate in `__post_init__`.
5. **Add tests.** Contract tests, input validation, normal operation, edge
   cases, orchestration integration.
6. **Register.** Add your `register(registry)` function and import it in
   `src/outputlens/analyzers/__init__.py`.
7. **Perform milestone review.** Per `DEVELOPMENT_WORKFLOW.md`.

---

## Testing Requirements

| Test Type | What It Verifies |
|---|---|
| Contract | Declaration fields correct (id, version, inputs, layer) |
| Input validation | Raises `AnalyzerError` when required inputs missing |
| Output type | Return value matches `declaration.output_type` |
| Behavior | With mock inputs, produces expected output |
| Edge cases | Empty input, single item, max items, invalid input |
| Integration | Wired into orchestrator, runs end-to-end |

---

## Knowledge Boundary

Core analyzers must remain knowledge-agnostic per **A4/A5-001**. They
classify epistemological characteristics from observable text signals.
They do not consult external knowledge bases, fact databases, search
engines, or LLMs.

If your analyzer requires external knowledge, it must be designed as an
**optional extension** (v3+) that:
- Is opt-in.
- Does not modify core analyzer behavior.
- Produces its own annotations.
- Never asserts truth.

---

## Reference

- [Implementation Guide](IMPLEMENTATION_GUIDE.md) -- coding conventions, checklist
- [Architecture](ARCHITECTURE.md) -- analyzer framework, execution model
- [Implementation Decisions](IMPLEMENTATION_DECISIONS.md) -- existing choices
- [Development Workflow](DEVELOPMENT_WORKFLOW.md) -- milestone process
