# Contributor Guide

Complete workflow for contributing to OutputLens.

---

## Before You Start

Read these documents in order. They build on each other:

1. [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) -- what OutputLens is, philosophy,
   design principles, non-goals.
2. [ARCHITECTURE.md](ARCHITECTURE.md) -- three-layer architecture, analyzer
   framework, execution flow.
3. [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md) -- milestone process,
   change categories, acceptance criteria.

Then, depending on your contribution type:

| Contribution | Primary Guide | Secondary |
|---|---|---|
| New analyzer | [ANALYZER_DEVELOPMENT.md](ANALYZER_DEVELOPMENT.md) | [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) |
| New interface | [INTERFACE_DEVELOPMENT.md](INTERFACE_DEVELOPMENT.md) | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Evaluation data | [EVALUATION_GUIDE.md](EVALUATION_GUIDE.md) | [Benchmarks README](../benchmarks/) |
| Documentation | This guide | [CONTRIBUTING.md](../CONTRIBUTING.md) |

---

## During Development

### Understand the Milestone

Check [PROJECT_STATE.md](PROJECT_STATE.md) for the current milestone and
open questions. Read the relevant [milestone report](../reports/) for
lessons learned from previous work.

### Follow the Workflow

Per [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md):
1. Plan the work in phases.
2. Implement incrementally.
3. Test thoroughly.
4. Review formally.
5. Document completely.

### Record Decisions

If the specification is silent on your approach, add an entry to
[IMPLEMENTATION_DECISIONS.md](IMPLEMENTATION_DECISIONS.md) following
the template. This is the firewall that prevents implementation choices
from becoming de facto specification requirements.

### Preserve Boundaries

- **Analyzers**: Single responsibility, declared inputs, no consumer awareness.
- **Interfaces**: Rendering only. No analytical logic.
- **Evaluation**: Measures agreement, not correctness.
- **Architecture**: FROZEN. Changes require implementation evidence.

---

## Before Submission

### Tests

```bash
PYTHONPATH=src python3 -m pytest tests/ -v
```

All tests must pass. Add tests for new functionality.

### Documentation

- [ ] `PROJECT_STATE.md` updated (if milestone progress changed)
- [ ] `IMPLEMENTATION_DECISIONS.md` updated (if new choices made)
- [ ] Milestone report created (if completing a milestone)

### Boundary Checklist

- [ ] No analytical logic in interface code
- [ ] No external knowledge in core analyzers
- [ ] No truth claims in classification reasoning
- [ ] AnalysisDocument schema compatibility preserved
- [ ] Change category correctly identified (Implementation/Documentation/
      Specification/Architecture)

### Architecture Impact

If your change affects architecture, you must provide:
- Implementation evidence of inconsistency.
- Alternatives considered.
- Principle impact assessment.
- Compatibility plan.

Architecture changes are exceptional. Start at the lowest change category
and escalate only when evidence demands it.

---

## After Acceptance

- Commit with a descriptive message.
- The milestone report preserves the permanent engineering record.
- Update `PROJECT_STATE.md` for the transition to the next milestone.

---

## Quick Reference

| Question | Answer |
|---|---|
| How do I add an analyzer? | [ANALYZER_DEVELOPMENT.md](ANALYZER_DEVELOPMENT.md) |
| How do I build an interface? | [INTERFACE_DEVELOPMENT.md](INTERFACE_DEVELOPMENT.md) |
| Can interfaces classify claims? | No. Interfaces render; they do not analyze. |
| Can I use an LLM in my analyzer? | Not in core analyzers. Optional extensions only. |
| How do I evaluate my analyzer? | [EVALUATION_GUIDE.md](EVALUATION_GUIDE.md) |
| Where do I record design choices? | [IMPLEMENTATION_DECISIONS.md](IMPLEMENTATION_DECISIONS.md) |
| Can I change the architecture? | Only with implementation evidence of inconsistency. |
| Who approves changes? | Milestone review per DEVELOPMENT_WORKFLOW.md. |
