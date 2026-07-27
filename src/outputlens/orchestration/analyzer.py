"""Analyzer base contract — the abstract interface every analyzer implements.

Spec reference: OutputLens Framework Specification, Chapter 7.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AnalyzerInput:
    """Declaration of an input dependency for an analyzer.

    Each analyzer declares which specific outputs from which specific analyzers
    it requires as input. The orchestration layer resolves these declarations
    into an execution DAG.
    """

    analyzer_id: str
    """The ID of the analyzer whose output this input consumes."""

    output_name: str
    """The name of the output field within that analyzer's output."""

    required: bool = True
    """Whether this input is required. If False, the analyzer degrades gracefully
    when the producing analyzer is unavailable."""


@dataclass(frozen=True)
class AnalyzerDeclaration:
    """Complete declaration of an analyzer's contract.

    Every analyzer MUST declare:
    - id: Unique identifier in the analyzer catalog
    - version: Semantic version of this analyzer
    - responsibility: One sentence describing the analytical question it answers
    - inputs: Named references to specific outputs of specific analyzers
    - output_type: The Python type this analyzer produces (for validation)
    - layer: Foundation | Classification | Structure | Synthesis | Terminal
    """

    id: str
    version: str
    responsibility: str
    inputs: tuple[AnalyzerInput, ...]
    output_type: type
    layer: str
    metadata: dict[str, str] = field(default_factory=dict)

    VALID_LAYERS = frozenset(
        {"foundation", "classification", "structure", "synthesis", "terminal"}
    )

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("analyzer id must not be empty")
        if self.layer not in self.VALID_LAYERS:
            raise ValueError(f"layer must be one of {sorted(self.VALID_LAYERS)}")


class Analyzer(ABC):
    """Base class for all OutputLens analyzers.

    Every analyzer:
    - Has exactly one analytical responsibility
    - Declares its inputs explicitly
    - Produces exactly one typed output
    - Has no knowledge of which analyzers consume its output
    - Is independent — given the same inputs, produces the same output

    Subclasses must:
    1. Define `declaration` as a class attribute
    2. Implement `analyze(context)`
    """

    declaration: AnalyzerDeclaration
    """Class-level declaration of this analyzer's contract."""

    @abstractmethod
    def analyze(self, context: AnalysisContext) -> Any:
        """Execute this analyzer's analytical operation.

        Args:
            context: The AnalysisContext containing all available analyzer outputs.
                     This analyzer should only access inputs declared in its
                     AnalyzerDeclaration.

        Returns:
            The analyzer's typed output. The type must match declaration.output_type.

        Raises:
            AnalyzerError: If a required input is missing or analysis fails.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.declaration.id}, v{self.declaration.version})"


class AnalysisContext:
    """The shared context passed to each analyzer during execution.

    Contains all analyzer outputs produced so far. An analyzer should only read
    the specific inputs declared in its AnalyzerDeclaration. Reading undeclared
    inputs is a contract violation.

    The context is mutable during analysis construction and frozen afterwards.
    """

    def __init__(self) -> None:
        self._outputs: dict[str, dict[str, Any]] = {}
        """analyzer_id → {output_name: value}"""

    def set_output(self, analyzer_id: str, output_name: str, value: Any) -> None:
        """Record an analyzer's output. Called by the orchestration layer."""
        if analyzer_id not in self._outputs:
            self._outputs[analyzer_id] = {}
        self._outputs[analyzer_id][output_name] = value

    def get_output(self, analyzer_id: str, output_name: str) -> Any | None:
        """Retrieve an analyzer's output by analyzer ID and output name.

        Returns None if the output is not available.
        """
        analyzer_outputs = self._outputs.get(analyzer_id)
        if analyzer_outputs is None:
            return None
        return analyzer_outputs.get(output_name)

    def has_output(self, analyzer_id: str, output_name: str) -> bool:
        """Check whether a specific output is available."""
        return self.get_output(analyzer_id, output_name) is not None

    @property
    def available_analyzers(self) -> frozenset[str]:
        """Set of analyzer IDs that have produced output."""
        return frozenset(self._outputs.keys())


class AnalyzerError(Exception):
    """Raised when an analyzer encounters an error during execution."""
    pass
