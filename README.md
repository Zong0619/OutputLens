# OutputLens

> **See what your AI isn't telling you.**

OutputLens is an open-source analysis framework for AI-generated text.

Instead of determining whether a response is *true* or *false*, OutputLens helps readers understand:

- What claims were made
- Which claims deserve verification
- Why each claim was classified that way

OutputLens does **not** determine truth.

It helps readers decide **what to investigate—not what to believe.**

---

## Status

**Current milestone:** Milestone 0 — Infrastructure Complete

**Next milestone:** Milestone 1 — Claim Extractor (A2)

The framework specification and project documentation are under active development.

---

## Repository

```
specification/     Framework specification
docs/              Project documentation and governance
src/               Python reference implementation
tests/             Unit and integration tests
benchmarks/        Evaluation datasets and harness
conformance_tests/ Specification conformance suite
```

---

## Project Principles

OutputLens is built around four core ideas:

- Analysis, not generation
- Classification, not truth determination
- Engine first, interface second
- Reader empowerment through structural transparency

---

## License

Apache License 2.0