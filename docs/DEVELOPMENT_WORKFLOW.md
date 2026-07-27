# OutputLens -- Development Workflow

**Audience**: All contributors (human and AI).
**Authority**: Repository policy. Must be followed for all development.
**Stability**: This document defines the engineering process. Changes require explicit justification.

---

## Preamble

OutputLens is developed through a sequence of **milestones**. Each milestone has
defined objectives, produces testable deliverables, and concludes with a formal
review. This document defines the standard workflow for every milestone, from
onboarding through acceptance.

The workflow exists to ensure that:

- Implementation remains aligned with the specification.
- Architecture evolves only through evidence, not preference.
- Documentation stays current with implementation.
- Engineering decisions are recorded and traceable.
- The repository remains the single source of truth.

Deviations from this workflow are permitted only when the workflow itself
prevents necessary progress. Such deviations must be documented and justified.

---

## 1. Project Onboarding

Before making any implementation changes, every contributor must onboard
themselves to the current state of the project.

### AI Contributor Protocol

AI contributors must follow the AI Contributor Protocol:

1. Read `docs/PROJECT_CONTEXT.md` -- understand what OutputLens is, its core
   philosophy, design principles, architecture status, capability boundaries,
   and non-goals.
2. Read `docs/PROJECT_STATE.md` -- understand the current milestone, completed
   milestones, implementation progress, open questions, and immediate TODO items.
3. Read `docs/ARCHITECTURE.md` -- understand the three-layer architecture,
   analyzer framework, orchestration layer, execution flow, and key invariants.
4. Read `docs/IMPLEMENTATION_GUIDE.md` -- understand the analyzer contract,
   coding conventions, testing expectations, and cardinal rules for avoiding
   specification violations.
5. Read `docs/IMPLEMENTATION_DECISIONS.md` -- understand which implementation
   choices have been made and why, and where the specification is intentionally
   silent.

### Human Contributor Protocol

Human contributors should read the same documents in the same order. The
documents are designed to be read linearly -- each builds on the previous.

### Onboarding Checklist

Before writing code, confirm that you understand:

- [ ] What OutputLens is and is not (boundaries, non-goals).
- [ ] The current milestone and its objectives.
- [ ] Which analyzers are implemented and which are pending.
- [ ] The architecture status (FROZEN -- changes require evidence).
- [ ] Outstanding implementation questions.
- [ ] The analyzer contract and how to implement a new analyzer.
- [ ] How to distinguish implementation decisions from specification requirements.

---

## 2. Planning

Before writing code, plan the work.

### Understand the Milestone

- Read the milestone objectives in `docs/ROADMAP.md`.
- Review `reports/Mx.md` for the previous milestone to understand lessons
  learned and any preparation needed.
- Identify which analyzers will be implemented or modified.
- Identify which specification chapters are relevant.

### Break Into Phases

- Decompose the milestone into engineering phases where appropriate.
- Each phase should produce a testable, verifiable increment.
- Phases should be ordered so that each builds on the previous.
- Prefer small increments over large monolithic changes.
- Avoid implementing features outside the current milestone scope.

### Identify Risks

- Which specification requirements are untested?
- Which architectural assumptions will this milestone validate?
- What engineering judgments will be required where the specification is silent?
- What could cause this milestone to fail?

---

## 3. Implementation

During implementation, follow the specification, preserve existing architecture,
and record decisions.

### Follow the Specification

- The specification is the normative authority. When in doubt, consult the
  relevant specification chapter.
- If the specification is ambiguous, document the ambiguity and the resolution
  in `docs/IMPLEMENTATION_DECISIONS.md`.
- If the specification appears wrong, do NOT redesign it immediately. Document
  the evidence, explain the inconsistency, and recommend the smallest possible
  revision. Continue implementation with a documented workaround.

### Preserve Architecture

- The architecture is FROZEN (`docs/PROJECT_CONTEXT.md`).
- Do NOT introduce new architectural concepts unless implementation demonstrates
  that the current specification is internally inconsistent or impossible to
  implement.
- Implementation improvements (better algorithms, cleaner code) are encouraged.
- Specification improvements (clarifying ambiguities) are permitted with evidence.
- Architecture redesigns require formal justification and governance review.

### Coding Standards

Follow `docs/IMPLEMENTATION_GUIDE.md`:

- **Analyzer contract**: Single responsibility, explicit inputs, typed output,
  no consumer awareness.
- **Determinism**: Same input must produce same output. No randomness, no
  external API calls without documenting the reproducibility implications.
- **Analyzer independence**: An analyzer knows nothing about which analyzers
  consume its output.
- **AnalysisDocument compatibility**: All analyzer outputs must flow into the
  AnalysisDocument through the established setter methods. Schema validation
  must pass.
- **Immutability**: Analysis Model objects are frozen dataclasses. Never modify
  after creation.
- **Type annotations**: All public functions and methods must have type
  annotations.

### Distinguish Implementation from Specification

Every implementation choice falls into one of two categories:

1. **Specification-mandated**: The specification explicitly requires this
   behavior. Cite the chapter and section.

2. **Implementation-chosen**: The specification is silent or delegates the
   choice. Record it in `docs/IMPLEMENTATION_DECISIONS.md` with:
   - What was chosen
   - What alternatives exist
   - What the specification requires (or that it is silent)
   - Why this choice was made
   - How stable this choice is (High/Medium/Low)

This distinction is the firewall that prevents implementation-specific behavior
from accidentally becoming a de facto specification requirement.

---

## 4. Testing

Testing is not optional. Work is not complete until tests pass.

### Test Requirements

- **Unit tests**: Every new function, class, and analyzer must have
  corresponding unit tests. Tests must cover: normal operation, edge cases,
  invalid inputs, and contract compliance.
- **Regression tests**: Every bug fix must include a regression test that
  fails before the fix and passes after.
- **Existing tests**: All existing tests must continue to pass. A change that
  breaks existing tests must either fix the tests (if the test expectation was
  wrong) or fix the implementation (if the implementation regressed).

### Running Tests

```bash
PYTHONPATH=src python3 -m pytest tests/ -v
```

All tests must pass before a milestone can be accepted.

### Test Organization

- `tests/unit/` -- Unit tests for individual components. One file per analyzer
  or module.
- `tests/integration/` -- Integration tests spanning multiple analyzers or the
  full pipeline.
- `tests/unit/test_aN_name_regression.py` -- Regression tests encoding known
  patterns that must be preserved.

### Golden Datasets

Golden datasets (`benchmarks/golden_datasets/`) are for quality evaluation, not
conformance testing. They measure how well analyzers perform, not whether they
conform to the specification. Golden datasets are versioned independently.

---

## 5. Milestone Review

After implementation is complete and all tests pass, perform a formal
engineering review.

### Review Scope

The review covers four dimensions:

1. **Architecture Review**: Does the implementation validate or challenge
   architectural assumptions? Is the analyzer contract preserved? Is the
   dependency model sufficient? Does the AnalysisDocument remain the correct
   integration contract?

2. **Specification Review**: Which specification requirements have been
   validated? Which were difficult to implement? What ambiguities were
   discovered? Where did implementation require engineering judgment beyond
   the written specification?

3. **Implementation Review**: Is the API design clean? Is the code organized
   and maintainable? Is extensibility preserved? Is determinism guaranteed?
   Is traceability to the specification maintained? What technical debt
   exists?

4. **Documentation Review**: Does `PROJECT_STATE.md` accurately reflect the
   current state? Are all implementation decisions recorded in
   `IMPLEMENTATION_DECISIONS.md`? Does any other documentation need updating?

### If Inconsistencies Are Discovered

1. Document the evidence.
2. Explain why the inconsistency exists.
3. Classify the issue:
   - **Implementation issue**: Fix the implementation.
   - **Specification ambiguity**: Recommend a specification clarification.
   - **Specification error**: Recommend the smallest possible revision.
   - **Architecture problem**: Only if the specification is internally
     inconsistent or impossible to implement.
4. Do NOT redesign the architecture without strong evidence.

---

## 6. Documentation

Documentation is part of the implementation. A milestone is not complete until
documentation is updated.

### Required Updates

After every milestone:

- **`docs/PROJECT_STATE.md`**: Update current milestone, test counts, analyzer
  status, open questions, TODO items, and recent decisions.

### Conditional Updates

Update as needed:

- **`docs/IMPLEMENTATION_DECISIONS.md`**: Add entries for every significant
  implementation choice not mandated by the specification.

### Do Not Modify Without Governance

- **`docs/PROJECT_CONTEXT.md`**: Only when governance-level architectural
  changes are required. This should be rare.
- **`docs/ARCHITECTURE.md`**: Only when the architecture has been validated to
  require change through implementation evidence.

---

## 7. Milestone Reports

Every completed milestone must produce a permanent engineering report.

### Creating a Milestone Report

1. Copy `reports/TEMPLATE.md` to `reports/Mx.md` (where x is the milestone
   number).
2. Fill in all sections with milestone-specific content.
3. The report must be complete and accurate -- it is a permanent historical
   record.

### Report Sections

The template requires:

- **Goals**: What this milestone was intended to achieve.
- **Completed Work**: Factual list of deliverables, files changed, tests added.
- **Architecture Impact**: What was validated, challenged, or unchanged.
- **Specification Validation**: Requirements validated, difficulties
   encountered, ambiguities discovered.
- **Implementation Decisions**: References to `IMPLEMENTATION_DECISIONS.md`.
- **Known Limitations**: False positives, false negatives, deferred work.
- **Test Summary**: Counts and status for all test files.
- **Lessons Learned**: What would we do differently? What surprised us?
- **Recommended Next Milestone**: With rationale and any preparation needed.
- **Repository State**: Directory tree showing all files after completion.
- **References**: Links to specification, roadmap, decisions register.

### Relationship to PROJECT_STATE

- `docs/PROJECT_STATE.md` is the living document -- it reflects the current
  moment.
- `reports/Mx.md` is a permanent historical record -- it preserves the state
  at the moment of milestone completion.

Milestone Reports must never be overwritten by future PROJECT_STATE updates.
They are the project's institutional memory.

---

## 8. Acceptance

Before beginning the next milestone, the current milestone must be formally
accepted.

### Acceptance Criteria

All of the following must be true:

- [ ] Milestone objectives have been completed.
- [ ] All tests pass (unit, integration, regression).
- [ ] `docs/PROJECT_STATE.md` is current.
- [ ] `docs/IMPLEMENTATION_DECISIONS.md` is current (all new decisions recorded).
- [ ] Known limitations are documented.
- [ ] Architecture remains consistent (or inconsistencies are documented and
  justified).
- [ ] Specification remains implementable (or issues are documented).
- [ ] `reports/Mx.md` has been created and is complete.

### Acceptance Decision

- **Accepted**: The milestone satisfies all criteria. Proceed to the next
  milestone.
- **Accepted with caveats**: The milestone satisfies core criteria but has
  documented limitations or technical debt. Proceed, but address the caveats
  before or during the next milestone.
- **Rejected**: The milestone fails one or more criteria. The specific failures
  must be documented. Implementation must be corrected before re-review.

---

## 9. Version Control

After milestone acceptance, changes must be committed to the repository.

### Commit Strategy

- **During development**: Commit frequently with descriptive messages. Each
  commit should represent a coherent change.
- **At milestone acceptance**: Commit all remaining changes. The commit
  message should reference the milestone number and summarize the completed
  work.

Example commit message:

```
M1: Claim Extraction (A2) -- complete

- Deterministic rule-based sentence splitter
- Coordinating conjunction decomposition
- Subordinating conjunction and compound sentence handling
- List and enumeration support (bullet, dash, numbered)
- 104 A2-specific tests (86 unit + 18 regression)
- 185 total tests passing

See reports/M1.md for full milestone report.
```

### Tags and Releases

- **Git tags**: Create an annotated tag at milestone boundaries:
  ```bash
  git tag -a v0.1.0 -m "Milestone 1: Claim Extraction complete"
  ```
  Tags use semantic versioning. The version corresponds to the engine version
  in `src/outputlens/__init__.py`.

- **GitHub Releases**: For milestone-level releases (M1, M3, M6 -- the
  externally visible milestones), create a GitHub Release. The release notes
  should summarize the milestone report. Attach any relevant artifacts.

### Repository Hygiene

- Do not commit generated files, caches, or virtual environments.
- Do not commit golden datasets that are still under construction (use
  `.gitignore` for draft data).
- Do not commit API keys, credentials, or environment-specific configuration.

---

## 10. Begin Next Milestone

Only after the previous milestone has been formally accepted should
implementation begin for the next milestone.

### Transition Checklist

Before starting Milestone N+1:

- [ ] Milestone N has been formally accepted.
- [ ] `reports/M[N].md` has been created and is complete.
- [ ] All changes have been committed and pushed.
- [ ] `docs/PROJECT_STATE.md` has been updated for the transition.
- [ ] Outstanding action items from Milestone N are documented.
- [ ] Any preparation needed for Milestone N+1 (per the previous milestone
  report's "Recommended Next Milestone" section) has been completed.

### Repeat

Follow this workflow for every milestone. The workflow is designed to be
self-similar -- each milestone follows the same process, at increasing levels
of analytical sophistication.

---

## Engineering Principles

These principles guide all development. They are derived from the Design
Principles (`docs/PROJECT_CONTEXT.md`) and adapted for engineering practice.

1. **Repository is the single source of truth.** The code, tests, documentation,
   and specification in the repository are authoritative. No external document,
   conversation, or design artifact overrides them.

2. **Documentation is part of the implementation.** A feature without
   documentation is incomplete. A change without updated `PROJECT_STATE.md`
   and `IMPLEMENTATION_DECISIONS.md` is unfinished.

3. **Determinism over complexity.** Prefer simple, deterministic approaches
   over complex, probabilistic ones. Complexity is only justified when
   deterministic approaches demonstrably fail to meet quality targets.

4. **Small, reviewable milestones.** Each milestone should be completable in
   weeks, not months. Each should produce a testable, verifiable artifact.
   Each should validate specific architectural assumptions.

5. **Architecture evolves only through implementation evidence.** The
   architecture is FROZEN. Changes require proof that the current architecture
   prevents necessary progress -- not preference, not speculation, not
   "future-proofing."

6. **Preserve backward compatibility whenever practical.** The AnalysisDocument
   schema is the integration contract. Changes within a major version must be
   additive. Breaking changes require a major version bump with explicit
   migration guidance.

7. **Test everything that can be tested.** Every function, every analyzer
   contract, every edge case. Tests are the project's safety net -- they
   prevent regressions, document expected behavior, and enable confident
   refactoring.

8. **Record decisions, not just code.** The `IMPLEMENTATION_DECISIONS.md`
   register is as important as the implementation itself. Future contributors
   (including future AI assistants) must understand WHY choices were made,
   not just WHAT was implemented.

9. **Respect the layers.** Runtime objects support execution. Analysis objects
   represent findings. Interface objects support presentation. Never put
   analytical logic in interface code. Never put rendering instructions in
   analysis objects.

10. **The reader is the beneficiary.** OutputLens exists to help readers
    understand AI-generated text. Every feature, every analyzer, every
    classification serves that purpose. Features that serve implementers at
    the expense of readers are misaligned with the project's mission.

---

## Change Control

Every proposed change must be classified into exactly one of the following
categories. The category determines the review process and justification
required.

### 1. Implementation Change

**Definition**: Modifies implementation only. Does not require specification
changes. Does not affect architecture.

**Examples**:
- Improving an analyzer's algorithm (same output contract, better quality)
- Adding a new abbreviation to the sentence splitter's abbreviation list
- Refactoring code for clarity or performance
- Adding tests for an existing feature
- Fixing a bug

**Process**:
- Record significant choices in `IMPLEMENTATION_DECISIONS.md`.
- Run the full test suite.
- Update `PROJECT_STATE.md` if the change affects implementation status.

**Justification required**: Standard PR description.

---

### 2. Documentation Change

**Definition**: Clarifies or improves documentation. Does not alter
implementation behavior. Does not modify the specification.

**Examples**:
- Fixing a typo in `ARCHITECTURE.md`
- Adding examples to `IMPLEMENTATION_GUIDE.md`
- Updating `PROJECT_STATE.md` to reflect current progress
- Improving docstrings

**Process**:
- Verify that the documentation change accurately reflects reality.
- No test suite run required (unless the change is to documented API behavior
  that tests verify).

**Justification required**: Brief description of what was changed and why.

---

### 3. Specification Change

**Definition**: Changes framework behavior or requirements. Must be reflected
in the Specification. May require implementation updates.

**Examples**:
- Adding a new classification level to the Establishedness scale
- Changing the required fields of the AnalysisDocument schema
- Adding a new normative requirement for analyzer output
- Clarifying an ambiguous specification requirement

**Process**:
1. Document the problem the change addresses.
2. Propose the smallest possible revision.
3. Include rationale and compatibility considerations.
4. If accepted, update the specification.
5. Update the reference implementation to conform.
6. Update the JSON Schema if the AnalysisDocument structure changes.
7. Update conformance tests.
8. Record in the milestone report.

**Justification required**: Problem statement, proposed revision,
compatibility impact, alternatives considered.

---

### 4. Architecture Change

**Definition**: Changes the core system architecture. Changes analyzer
relationships, execution model, integration contracts, or other foundational
design decisions.

**Examples**:
- Changing the analyzer contract (what an analyzer IS)
- Changing how analyzers declare dependencies
- Changing the AnalysisDocument as the integration contract
- Changing the layered architecture (Runtime/Analysis/Interface)
- Changing the immutability requirement
- Adding or removing a classification axis

**Process**:
1. Document the problem with implementation evidence. A claim that "the current
   architecture is wrong" is insufficient. Show what cannot be built, what
   contract cannot be satisfied, or what invariant cannot be maintained.
2. Explain why implementation-level or specification-level changes are
   insufficient to address the problem.
3. Propose the architecture change.
4. List alternatives considered and why they were rejected.
5. Evaluate the proposal against the 20 Design Principles
   (`docs/PROJECT_CONTEXT.md`). Identify which principles are strained or would
   require revision.
6. If accepted, update the specification to reflect the new architecture.
7. Update the reference implementation.
8. Update all architecture documentation.
9. Create a new specification edition if the change is backward-incompatible.
10. Record in a milestone report with explicit acknowledgment of the
    architectural revision.

**Justification required**: Implementation evidence, alternatives analysis,
principle impact assessment, compatibility plan.

---

### Classification Rule

Contributors must determine the category of a change before implementing it.

- If a problem can be solved within the existing implementation, it is an
  **Implementation Change**.
- If it requires changing what the specification requires, it is a
  **Specification Change**.
- If it requires changing how the framework is fundamentally organized, it is
  an **Architecture Change**.

**Implementation issues should not automatically become specification changes.
Specification issues should not automatically become architecture changes.
Architecture changes require the highest level of justification.**

When in doubt, start at the lowest category and escalate only when evidence
demonstrates that the lower category is insufficient.

---

## Repository Policy

This document is part of the project's governance. It applies to all
contributors -- human and AI -- for all future development.

**Last revised**: 2026-07-27
**Supersedes**: None (initial version)
**Enforcement**: Milestone reviews verify compliance with this workflow.
Deviations must be documented and justified in the milestone report.
