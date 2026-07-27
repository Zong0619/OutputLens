# Interface Development Guide

How to build an interface that consumes OutputLens analysis results.

---

## Core Principle: Engine First, Interface Second

The analysis engine is the product. Every interface is a **renderer** of
engine output. Interfaces consume AnalysisDocuments. They do not perform
analysis.

---

## What Interfaces Do

| Allowed | Not Allowed |
|---|---|
| Format AnalysisDocument JSON for display | Extract claims |
| Choose which fields to show | Classify concepts or claims |
| Apply visual styling (colors, layout) | Calculate trust scores or evidence ratios |
| Handle transport (HTTP, terminal, GUI) | Infer novelty or risk levels |
| Filter and sort existing data | Generate new analytical conclusions |
| Present the verification punchlist | Re-prioritize punchlist entries |

---

## The AnalysisDocument Contract

Every interface consumes the same versioned JSON:

```json
{
  "schema_version": "1.0.0",
  "analysis_objects": {
    "claims": [...],
    "trust_profile": {...},
    "verification_punchlist": {...},
    "response_narrative": {...}
  }
}
```

The schema is the **only** contract. Interfaces must not depend on internal
Python dataclasses or engine implementation details. If the schema version
changes, interfaces update to support the new version.

---

## Interface Patterns

### CLI Interface

```
User input → Engine → AnalysisDocument → Formatted text output
```

Read from args, stdin, or file. Run the engine via `engine_runner.run_analysis()`.
Output JSON (machine contract) or formatted text (human-readable).

Reference: `src/outputlens/interfaces/cli.py`

### REST API

```
HTTP Request → Engine → AnalysisDocument → JSON Response
```

Thin HTTP wrapper. Validate request, run engine, return JSON. No analytical
logic in route handlers.

Reference: `src/outputlens/interfaces/api.py`

### Web Interface

```
Browser → REST API → Engine → AnalysisDocument JSON → DOM Rendering
```

Static frontend. JavaScript reads API response and renders to DOM. All
values come from the JSON. No computation in frontend code.

Reference: `src/outputlens/interfaces/web/`

### MCP Server, IDE Extension, etc.

Same pattern: consume AnalysisDocument JSON, render for your platform.

---

## Building a New Interface

1. **Study the schema.** Understand which fields are always present and
   which are optional (depend on which analyzers ran).
2. **Use the shared runner.** Import `engine_runner.run_analysis()` for
   consistent engine invocation.
3. **Consume JSON, not objects.** Load AnalysisDocument JSON. Do not
   import `outputlens.analysis.model` in interface code.
4. **Render, don't analyze.** Every value you display must come from the
   engine output. If you need a value that isn't in the AnalysisDocument,
   the engine should produce it -- not the interface.
5. **Add boundary tests.** Verify your interface contains no analytical
   function names (`classify_*`, `extract_*`, `compute_*`).
6. **Keep it optional.** If your interface requires external dependencies,
   make them optional extras (`[myinterface]`).

---

## Boundary Checklist

Before submitting an interface PR, verify:

- [ ] No `classify_*` functions in interface code
- [ ] No `extract_*` functions in interface code
- [ ] No trust/evidence/novelty computation in interface code
- [ ] All displayed values trace to specific AnalysisDocument fields
- [ ] JSON output matches the schema version
- [ ] Boundary tests pass (source inspection)
- [ ] Dependencies are optional where possible

---

## Reference

- [Architecture](ARCHITECTURE.md) -- three-layer architecture
- [Implementation Guide](IMPLEMENTATION_GUIDE.md) -- coding conventions
- [M7-001](IMPLEMENTATION_DECISIONS.md) -- interface boundary preservation
- [Engine runner](../src/outputlens/interfaces/engine_runner.py) -- shared entry point
