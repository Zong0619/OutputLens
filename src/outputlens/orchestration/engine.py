"""Orchestration layer — dependency resolution, scheduling, and execution.

The orchestration layer is the thin coordinator that:
1. Maintains the analyzer registry
2. Resolves dependencies into an execution DAG
3. Schedules analyzers as soon as their dependencies are satisfied
4. Routes outputs between analyzers
5. Validates that the DAG has no cycles

The orchestration layer does NOT perform analysis. It performs coordination.

Spec reference: OutputLens Framework Specification, Chapters 7–8.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable

from outputlens.orchestration.analyzer import (
    AnalysisContext,
    Analyzer,
    AnalyzerDeclaration,
    AnalyzerError,
    AnalyzerInput,
)


@dataclass
class AnalyzerRegistration:
    """An analyzer registered in the catalog."""

    declaration: AnalyzerDeclaration
    factory: Callable[[], Analyzer]
    """Factory function that creates a new analyzer instance."""


class AnalyzerRegistry:
    """Catalog of available analyzers and their declarations."""

    def __init__(self) -> None:
        self._analyzers: dict[str, AnalyzerRegistration] = {}

    def register(self, declaration: AnalyzerDeclaration, factory: Callable[[], Analyzer]) -> None:
        """Register an analyzer in the catalog."""
        if declaration.id in self._analyzers:
            raise ValueError(f"Analyzer '{declaration.id}' is already registered")
        self._analyzers[declaration.id] = AnalyzerRegistration(
            declaration=declaration, factory=factory
        )

    def get(self, analyzer_id: str) -> AnalyzerRegistration:
        """Get an analyzer registration by ID."""
        if analyzer_id not in self._analyzers:
            raise KeyError(f"Analyzer '{analyzer_id}' is not registered")
        return self._analyzers[analyzer_id]

    @property
    def analyzer_ids(self) -> frozenset[str]:
        return frozenset(self._analyzers.keys())

    def validate(self) -> list[str]:
        """Validate that all declared input dependencies reference registered analyzers.

        Returns:
            List of validation errors. Empty list means valid registry.
        """
        errors: list[str] = []
        for reg in self._analyzers.values():
            for inp in reg.declaration.inputs:
                if inp.analyzer_id not in self._analyzers:
                    if inp.required:
                        errors.append(
                            f"Analyzer '{reg.declaration.id}' requires input from "
                            f"unregistered analyzer '{inp.analyzer_id}'"
                        )
        return errors


def resolve_execution_plan(
    requested_analyzers: frozenset[str],
    registry: AnalyzerRegistry,
) -> list[list[str]]:
    """Resolve analyzer dependencies into a layered execution plan.

    This is a topological sort with layering: analyzers with all dependencies
    satisfied appear in the earliest possible layer. Each layer is a list of
    analyzer IDs that can execute in parallel.

    Args:
        requested_analyzers: The set of analyzer IDs to execute.
        registry: The analyzer registry.

    Returns:
        A list of layers, each a list of analyzer IDs. Layers execute sequentially;
        analyzers within a layer may execute in parallel.

    Raises:
        ValueError: If a dependency cycle is detected or a requested analyzer is
                    not registered.
    """
    # Validate that all requested analyzers are registered
    for aid in requested_analyzers:
        if aid not in registry.analyzer_ids:
            raise ValueError(f"Requested analyzer '{aid}' is not registered")

    # Build the full set of analyzers needed (transitive closure)
    needed: set[str] = set()
    queue: deque[str] = deque(requested_analyzers)

    while queue:
        aid = queue.popleft()
        if aid in needed:
            continue
        if aid not in registry.analyzer_ids:
            continue  # Optional dependency on unregistered analyzer
        needed.add(aid)
        reg = registry.get(aid)
        for inp in reg.declaration.inputs:
            if inp.required and inp.analyzer_id not in needed:
                queue.append(inp.analyzer_id)

    # Build dependency graph and in-degree count (within the needed set)
    deps: dict[str, set[str]] = {}
    in_degree: dict[str, int] = {}
    for aid in needed:
        reg = registry.get(aid)
        deps[aid] = set()
        in_degree[aid] = 0

    for aid in needed:
        reg = registry.get(aid)
        for inp in reg.declaration.inputs:
            if inp.required and inp.analyzer_id in needed:
                deps[aid].add(inp.analyzer_id)
                in_degree[aid] += 1

    # Topological sort with layering (Kahn's algorithm variant)
    layers: list[list[str]] = []
    remaining = set(needed)

    while remaining:
        # Find all analyzers with no unsatisfied dependencies
        current_layer: list[str] = []
        for aid in sorted(remaining):
            if in_degree[aid] == 0:
                current_layer.append(aid)

        if not current_layer:
            # Cycle detected — identify the cycle for error reporting
            cycle_analyzers = sorted(remaining)
            raise ValueError(
                f"Dependency cycle detected among analyzers: {cycle_analyzers}. "
                f"Dependencies: { {a: sorted(deps[a]) for a in cycle_analyzers} }"
            )

        layers.append(current_layer)
        for aid in current_layer:
            remaining.remove(aid)
            # Reduce in-degree of analyzers that depend on this one
            for other in remaining:
                if aid in deps.get(other, set()):
                    in_degree[other] -= 1

    return layers


class OrchestrationEngine:
    """Coordinates analyzer execution according to the resolved dependency DAG.

    The engine:
    - Accepts an AnalysisRequest (via the runtime model)
    - Resolves which analyzers to run
    - Executes them in dependency order
    - Assembles the AnalysisDocument incrementally
    - Finalizes the document when all analyzers complete
    """

    def __init__(self, registry: AnalyzerRegistry, max_workers: int | None = None):
        self.registry = registry
        self.max_workers = max_workers

    def execute(
        self,
        requested_analyzers: frozenset[str],
        context: AnalysisContext,
        on_analyzer_start: Callable[[str], None] | None = None,
        on_analyzer_complete: Callable[[str, Any, float], None] | None = None,
        on_analyzer_error: Callable[[str, Exception], None] | None = None,
    ) -> AnalysisContext:
        """Execute the requested analyzers in dependency order.

        Args:
            requested_analyzers: Which analyzers to run.
            context: The AnalysisContext, pre-populated with Runtime Model objects
                     (A1 output).
            on_analyzer_start: Optional callback invoked when an analyzer begins.
            on_analyzer_complete: Optional callback invoked with (analyzer_id, output, duration_seconds).
            on_analyzer_error: Optional callback invoked with (analyzer_id, exception).

        Returns:
            The AnalysisContext with all analyzer outputs populated.

        Raises:
            ValueError: If dependency resolution fails.
            RuntimeError: If a required analyzer fails and no fallback exists.
        """
        # Resolve execution plan
        layers = resolve_execution_plan(requested_analyzers, self.registry)

        # Execute layer by layer
        for layer in layers:
            if len(layer) == 1:
                # Single analyzer — execute directly (no threading overhead)
                self._execute_analyzer(
                    layer[0], context, on_analyzer_start, on_analyzer_complete, on_analyzer_error
                )
            else:
                # Multiple analyzers — execute in parallel
                self._execute_layer_parallel(
                    layer, context, on_analyzer_start, on_analyzer_complete, on_analyzer_error
                )

        return context

    def _execute_analyzer(
        self,
        analyzer_id: str,
        context: AnalysisContext,
        on_start: Callable[[str], None] | None,
        on_complete: Callable[[str, Any, float], None] | None,
        on_error: Callable[[str, Exception], None] | None,
    ) -> None:
        """Execute a single analyzer and record its output."""
        reg = self.registry.get(analyzer_id)
        analyzer = reg.factory()

        if on_start:
            on_start(analyzer_id)

        start_time = time.monotonic()
        try:
            result = analyzer.analyze(context)
            duration = time.monotonic() - start_time

            # Record output — convention: output name matches analyzer_id
            context.set_output(analyzer_id, analyzer_id, result)

            if on_complete:
                on_complete(analyzer_id, result, duration)

        except Exception as exc:
            if on_error:
                on_error(analyzer_id, exc)

            # Check if this analyzer's output is required by others
            has_dependents = any(
                inp.analyzer_id == analyzer_id and inp.required
                for other_id in self.registry.analyzer_ids
                for inp in self.registry.get(other_id).declaration.inputs
            )

            if has_dependents:
                raise RuntimeError(
                    f"Required analyzer '{analyzer_id}' failed and has dependents. "
                    f"Analysis cannot continue."
                ) from exc
            else:
                # Optional or terminal analyzer — failure is logged but not fatal
                context.set_output(analyzer_id, analyzer_id, None)

    def _execute_layer_parallel(
        self,
        analyzer_ids: list[str],
        context: AnalysisContext,
        on_start: Callable[[str], None] | None,
        on_complete: Callable[[str, Any, float], None] | None,
        on_error: Callable[[str, Exception], None] | None,
    ) -> None:
        """Execute multiple independent analyzers concurrently."""
        errors: list[tuple[str, Exception]] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures: dict[Future, str] = {}
            for aid in analyzer_ids:
                future = executor.submit(
                    self._execute_analyzer,
                    aid,
                    context,
                    on_start,
                    on_complete,
                    on_error,
                )
                futures[future] = aid

            for future in as_completed(futures):
                aid = futures[future]
                try:
                    future.result()
                except Exception as exc:
                    errors.append((aid, exc))

        if errors:
            error_msgs = [f"  {aid}: {exc}" for aid, exc in errors]
            raise RuntimeError(
                "One or more analyzers failed during parallel execution:\n"
                + "\n".join(error_msgs)
            )


def get_default_registry() -> AnalyzerRegistry:
    """Return an empty registry. Analyzers are registered by the application.

    In the reference implementation, analyzer registration happens at startup
    by importing analyzer modules, which call registry.register().
    """
    return AnalyzerRegistry()
