"""Tests for the orchestration layer — dependency resolution, execution, and the analyzer contract."""

from typing import Any

import pytest

from outputlens.orchestration.analyzer import (
    AnalysisContext,
    Analyzer,
    AnalyzerDeclaration,
    AnalyzerInput,
)
from outputlens.orchestration.engine import (
    AnalyzerRegistry,
    OrchestrationEngine,
    resolve_execution_plan,
)


# ---------------------------------------------------------------------------
# Mock Analyzers for testing
# ---------------------------------------------------------------------------


def make_declaration(
    analyzer_id: str,
    inputs: tuple[AnalyzerInput, ...] = (),
    layer: str = "foundation",
) -> AnalyzerDeclaration:
    return AnalyzerDeclaration(
        id=analyzer_id,
        version="0.1.0",
        responsibility=f"Test analyzer {analyzer_id}",
        inputs=inputs,
        output_type=dict,
        layer=layer,
    )


class MockAnalyzer(Analyzer):
    """An analyzer that returns its declaration ID as output."""

    def __init__(self, declaration: AnalyzerDeclaration, should_fail: bool = False):
        self.declaration = declaration
        self.should_fail = should_fail

    def analyze(self, context: AnalysisContext) -> Any:
        if self.should_fail:
            raise RuntimeError(f"Analyzer {self.declaration.id} failed intentionally")
        # Return a dict with the analyzer's ID for verification
        return {"analyzer_id": self.declaration.id, "status": "success"}


def make_analyzer(
    analyzer_id: str,
    inputs: tuple[AnalyzerInput, ...] = (),
    layer: str = "foundation",
    should_fail: bool = False,
) -> MockAnalyzer:
    return MockAnalyzer(make_declaration(analyzer_id, inputs, layer), should_fail)


# ---------------------------------------------------------------------------
# Dependency Resolution Tests
# ---------------------------------------------------------------------------


class TestResolveExecutionPlan:
    def test_single_analyzer(self):
        registry = AnalyzerRegistry()
        decl = make_declaration("a1")
        registry.register(decl, lambda: make_analyzer("a1"))

        plan = resolve_execution_plan(frozenset({"a1"}), registry)
        assert plan == [["a1"]]

    def test_independent_analyzers_same_layer(self):
        registry = AnalyzerRegistry()
        for aid in ("a1", "a2", "a3"):
            registry.register(make_declaration(aid), lambda aid=aid: make_analyzer(aid))

        plan = resolve_execution_plan(frozenset({"a1", "a2", "a3"}), registry)
        # All independent — should be in one layer
        assert len(plan) == 1
        assert set(plan[0]) == {"a1", "a2", "a3"}

    def test_linear_dependency_chain(self):
        registry = AnalyzerRegistry()
        registry.register(
            make_declaration("a1"),
            lambda: make_analyzer("a1"),
        )
        registry.register(
            make_declaration("a2", inputs=(AnalyzerInput("a1", "a1"),)),
            lambda: make_analyzer("a2"),
        )
        registry.register(
            make_declaration("a3", inputs=(AnalyzerInput("a2", "a2"),)),
            lambda: make_analyzer("a3"),
        )

        plan = resolve_execution_plan(frozenset({"a3"}), registry)
        # a3 depends on a2 which depends on a1 → 3 layers
        assert len(plan) == 3
        assert plan[0] == ["a1"]
        assert plan[1] == ["a2"]
        assert plan[2] == ["a3"]

    def test_diamond_dependency(self):
        """a4 depends on a2 and a3, which both depend on a1."""
        registry = AnalyzerRegistry()
        for aid in ("a1", "a2", "a3", "a4"):
            if aid == "a1":
                decl = make_declaration("a1")
            elif aid in ("a2", "a3"):
                decl = make_declaration(aid, inputs=(AnalyzerInput("a1", "a1"),))
            else:  # a4
                decl = make_declaration(
                    "a4",
                    inputs=(AnalyzerInput("a2", "a2"), AnalyzerInput("a3", "a3")),
                )
            registry.register(decl, lambda aid=aid: make_analyzer(aid))

        plan = resolve_execution_plan(frozenset({"a4"}), registry)
        # Layer 0: a1
        # Layer 1: a2, a3 (both depend only on a1)
        # Layer 2: a4 (depends on a2 and a3)
        assert plan[0] == ["a1"]
        assert set(plan[1]) == {"a2", "a3"}
        assert plan[2] == ["a4"]

    def test_transitive_closure(self):
        """Requesting only a3 should pull in its transitive dependencies."""
        registry = AnalyzerRegistry()
        registry.register(make_declaration("a1"), lambda: make_analyzer("a1"))
        registry.register(
            make_declaration("a2", inputs=(AnalyzerInput("a1", "a1"),)),
            lambda: make_analyzer("a2"),
        )
        registry.register(
            make_declaration("a3", inputs=(AnalyzerInput("a2", "a2"),)),
            lambda: make_analyzer("a3"),
        )

        plan = resolve_execution_plan(frozenset({"a3"}), registry)
        # Should include a1 and a2 even though they weren't explicitly requested
        all_analyzers = {aid for layer in plan for aid in layer}
        assert all_analyzers == {"a1", "a2", "a3"}

    def test_cycle_detection(self):
        registry = AnalyzerRegistry()
        registry.register(
            make_declaration("a1", inputs=(AnalyzerInput("a2", "a2"),)),
            lambda: make_analyzer("a1"),
        )
        registry.register(
            make_declaration("a2", inputs=(AnalyzerInput("a1", "a1"),)),
            lambda: make_analyzer("a2"),
        )

        with pytest.raises(ValueError, match="Dependency cycle"):
            resolve_execution_plan(frozenset({"a1", "a2"}), registry)

    def test_unregistered_analyzer_raises(self):
        registry = AnalyzerRegistry()
        with pytest.raises(ValueError, match="not registered"):
            resolve_execution_plan(frozenset({"nonexistent"}), registry)

    def test_optional_dependency_not_pulled_in(self):
        """Optional deps should not be in transitive closure if producer not requested."""
        registry = AnalyzerRegistry()
        registry.register(make_declaration("a1"), lambda: make_analyzer("a1"))
        registry.register(
            make_declaration(
                "a2",
                inputs=(
                    AnalyzerInput("a1", "a1"),
                    AnalyzerInput("optional_a", "optional_a", required=False),
                ),
            ),
            lambda: make_analyzer("a2"),
        )

        plan = resolve_execution_plan(frozenset({"a2"}), registry)
        all_analyzers = {aid for layer in plan for aid in layer}
        assert all_analyzers == {"a1", "a2"}
        assert "optional_a" not in all_analyzers


# ---------------------------------------------------------------------------
# Registry Tests
# ---------------------------------------------------------------------------


class TestAnalyzerRegistry:
    def test_register_and_retrieve(self):
        registry = AnalyzerRegistry()
        decl = make_declaration("a1")
        registry.register(decl, lambda: make_analyzer("a1"))
        reg = registry.get("a1")
        assert reg.declaration.id == "a1"

    def test_duplicate_registration_raises(self):
        registry = AnalyzerRegistry()
        registry.register(make_declaration("a1"), lambda: make_analyzer("a1"))
        with pytest.raises(ValueError, match="already registered"):
            registry.register(make_declaration("a1"), lambda: make_analyzer("a1"))

    def test_unregistered_lookup_raises(self):
        registry = AnalyzerRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_validate_catches_missing_dependencies(self):
        registry = AnalyzerRegistry()
        registry.register(
            make_declaration("a1", inputs=(AnalyzerInput("missing", "missing"),)),
            lambda: make_analyzer("a1"),
        )
        errors = registry.validate()
        assert len(errors) == 1
        assert "missing" in errors[0]

    def test_validate_clean_registry(self):
        registry = AnalyzerRegistry()
        registry.register(make_declaration("a1"), lambda: make_analyzer("a1"))
        errors = registry.validate()
        assert len(errors) == 0


# ---------------------------------------------------------------------------
# Orchestration Engine Tests
# ---------------------------------------------------------------------------


class TestOrchestrationEngine:
    def test_simple_execution(self):
        registry = AnalyzerRegistry()
        decl = make_declaration("a1")
        registry.register(decl, lambda: make_analyzer("a1"))

        engine = OrchestrationEngine(registry)
        context = AnalysisContext()

        engine.execute(frozenset({"a1"}), context)

        assert context.has_output("a1", "a1")
        result = context.get_output("a1", "a1")
        assert result["status"] == "success"

    def test_dependency_chain_execution(self):
        registry = AnalyzerRegistry()
        registry.register(make_declaration("a1"), lambda: make_analyzer("a1"))
        registry.register(
            make_declaration("a2", inputs=(AnalyzerInput("a1", "a1"),)),
            lambda: make_analyzer("a2"),
        )

        engine = OrchestrationEngine(registry)
        context = AnalysisContext()

        engine.execute(frozenset({"a2"}), context)

        assert context.has_output("a1", "a1")
        assert context.has_output("a2", "a2")

    def test_callbacks_invoked(self):
        registry = AnalyzerRegistry()
        registry.register(make_declaration("a1"), lambda: make_analyzer("a1"))

        engine = OrchestrationEngine(registry)
        context = AnalysisContext()

        started: list[str] = []
        completed: list[str] = []

        engine.execute(
            frozenset({"a1"}), context,
            on_analyzer_start=lambda aid: started.append(aid),
            on_analyzer_complete=lambda aid, result, duration: completed.append(aid),
        )

        assert "a1" in started
        assert "a1" in completed

    def test_optional_analyzer_failure_non_fatal(self):
        registry = AnalyzerRegistry()
        registry.register(make_declaration("a1"), lambda: make_analyzer("a1", should_fail=True))

        engine = OrchestrationEngine(registry)
        context = AnalysisContext()

        # a1 has no dependents, so failure should be non-fatal
        engine.execute(frozenset({"a1"}), context)
        # Output is None on failure
        assert context.get_output("a1", "a1") is None

    def test_required_analyzer_failure_is_fatal(self):
        registry = AnalyzerRegistry()
        registry.register(make_declaration("a1"), lambda: make_analyzer("a1", should_fail=True))
        registry.register(
            make_declaration("a2", inputs=(AnalyzerInput("a1", "a1"),)),
            lambda: make_analyzer("a2"),
        )

        engine = OrchestrationEngine(registry)
        context = AnalysisContext()

        with pytest.raises(RuntimeError, match="has dependents"):
            engine.execute(frozenset({"a2"}), context)

    def test_declaration_post_init_validation(self):
        with pytest.raises(ValueError, match="analyzer id must not be empty"):
            AnalyzerDeclaration(
                id="", version="0.1.0", responsibility="test",
                inputs=(), output_type=dict, layer="foundation",
            )

        with pytest.raises(ValueError, match="layer must be one of"):
            AnalyzerDeclaration(
                id="a1", version="0.1.0", responsibility="test",
                inputs=(), output_type=dict, layer="invalid_layer",
            )

    def test_analysis_context_available_analyzers(self):
        ctx = AnalysisContext()
        assert len(ctx.available_analyzers) == 0
        ctx.set_output("a1", "a1", {"data": True})
        assert "a1" in ctx.available_analyzers

    def test_analysis_context_missing_output(self):
        ctx = AnalysisContext()
        assert ctx.get_output("nonexistent", "output") is None
        assert not ctx.has_output("nonexistent", "output")


# ---------------------------------------------------------------------------
# Integration: Registry + Engine + Realistic DAG
# ---------------------------------------------------------------------------


class TestRealisticPipeline:
    """Test with a realistic subset of the OutputLens analyzer DAG.

    Foundation:  a1 (text normalizer) → a2 (claim extractor) → a3 (concept extractor)
    Classification: a4 (establishedness) ∥ a5 (evidence) ∥ a6 (novelty)
    Structure: a7 (claim relationships) → a8 (concept relationships)
    Synthesis: a9 (trust profile) ∥ a10 (evidence gap)
    Terminal: a16 (punchlist)
    """

    def test_full_dag_resolution(self):
        registry = AnalyzerRegistry()

        # Foundation
        registry.register(make_declaration("a1"), lambda: make_analyzer("a1"))
        registry.register(
            make_declaration("a2", inputs=(AnalyzerInput("a1", "a1"),)),
            lambda: make_analyzer("a2"),
        )
        registry.register(
            make_declaration("a3", inputs=(
                AnalyzerInput("a1", "a1"), AnalyzerInput("a2", "a2"),
            )),
            lambda: make_analyzer("a3"),
        )

        # Classification (all depend on a2 + a3)
        for aid in ("a4", "a5", "a6"):
            registry.register(
                make_declaration(aid, inputs=(
                    AnalyzerInput("a2", "a2"), AnalyzerInput("a3", "a3"),
                )),
                lambda aid=aid: make_analyzer(aid),
            )

        # Structure
        registry.register(
            make_declaration("a7", inputs=(
                AnalyzerInput("a2", "a2"), AnalyzerInput("a4", "a4"), AnalyzerInput("a6", "a6"),
            )),
            lambda: make_analyzer("a7"),
        )
        registry.register(
            make_declaration("a8", inputs=(AnalyzerInput("a7", "a7"),)),
            lambda: make_analyzer("a8"),
        )

        # Synthesis
        registry.register(
            make_declaration("a9", inputs=(AnalyzerInput("a4", "a4"),)),
            lambda: make_analyzer("a9"),
        )
        registry.register(
            make_declaration("a10", inputs=(AnalyzerInput("a5", "a5"),)),
            lambda: make_analyzer("a10"),
        )

        # Terminal
        registry.register(
            make_declaration("a16", inputs=(
                AnalyzerInput("a4", "a4"), AnalyzerInput("a5", "a5"),
                AnalyzerInput("a9", "a9"), AnalyzerInput("a10", "a10"),
            )),
            lambda: make_analyzer("a16"),
        )

        plan = resolve_execution_plan(
            frozenset({"a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10", "a16"}),
            registry,
        )

        # Verify layering:
        # Layer 0: a1
        # Layer 1: a2
        # Layer 2: a3
        # Layer 3: a4, a5, a6 (all parallel — all depend on a2 + a3)
        # Layer 4: a7, a9, a10 (a7 depends on a4 + a6; a9 on a4; a10 on a5)
        # Layer 5: a8, a16 (a8 depends on a7; a16 depends on a9, a10, a4, a5)
        assert plan[0] == ["a1"]
        assert plan[1] == ["a2"]
        assert plan[2] == ["a3"]
        assert set(plan[3]) == {"a4", "a5", "a6"}
        assert set(plan[4]) == {"a7", "a9", "a10"}
        assert set(plan[5]) == {"a8", "a16"}

    def test_full_dag_execution(self):
        """Verify the entire DAG executes without errors."""
        registry = AnalyzerRegistry()

        # Register all analyzers
        registry.register(make_declaration("a1"), lambda: make_analyzer("a1"))
        registry.register(
            make_declaration("a2", inputs=(AnalyzerInput("a1", "a1"),)),
            lambda: make_analyzer("a2"),
        )
        registry.register(
            make_declaration("a3", inputs=(
                AnalyzerInput("a1", "a1"), AnalyzerInput("a2", "a2"),
            )),
            lambda: make_analyzer("a3"),
        )
        for aid in ("a4", "a5", "a6"):
            registry.register(
                make_declaration(aid, inputs=(
                    AnalyzerInput("a2", "a2"), AnalyzerInput("a3", "a3"),
                )),
                lambda aid=aid: make_analyzer(aid),
            )
        registry.register(
            make_declaration("a7", inputs=(
                AnalyzerInput("a2", "a2"), AnalyzerInput("a4", "a4"), AnalyzerInput("a6", "a6"),
            )),
            lambda: make_analyzer("a7"),
        )
        registry.register(
            make_declaration("a8", inputs=(AnalyzerInput("a7", "a7"),)),
            lambda: make_analyzer("a8"),
        )
        registry.register(
            make_declaration("a9", inputs=(AnalyzerInput("a4", "a4"),)),
            lambda: make_analyzer("a9"),
        )
        registry.register(
            make_declaration("a10", inputs=(AnalyzerInput("a5", "a5"),)),
            lambda: make_analyzer("a10"),
        )
        registry.register(
            make_declaration("a16", inputs=(
                AnalyzerInput("a4", "a4"), AnalyzerInput("a5", "a5"),
                AnalyzerInput("a9", "a9"), AnalyzerInput("a10", "a10"),
            )),
            lambda: make_analyzer("a16"),
        )

        engine = OrchestrationEngine(registry)
        context = AnalysisContext()

        # Pre-populate A1 output (text normalization)
        context.set_output("a1", "a1", {"normalized": True})

        # Execute everything from a2 through a16
        engine.execute(frozenset({"a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10", "a16"}), context)

        # All should have produced output
        for aid in ("a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10", "a16"):
            assert context.has_output(aid, aid), f"Missing output from {aid}"

    def test_partial_analysis_subsets(self):
        """Verify we can request a subset of analyzers."""
        registry = AnalyzerRegistry()
        registry.register(make_declaration("a1"), lambda: make_analyzer("a1"))
        registry.register(
            make_declaration("a2", inputs=(AnalyzerInput("a1", "a1"),)),
            lambda: make_analyzer("a2"),
        )
        registry.register(
            make_declaration("a4", inputs=(AnalyzerInput("a2", "a2"),)),
            lambda: make_analyzer("a4"),
        )

        engine = OrchestrationEngine(registry)
        context = AnalysisContext()
        context.set_output("a1", "a1", {"normalized": True})

        # Only request a4 — should pull in a2 automatically
        engine.execute(frozenset({"a4"}), context)

        assert context.has_output("a2", "a2")
        assert context.has_output("a4", "a4")
