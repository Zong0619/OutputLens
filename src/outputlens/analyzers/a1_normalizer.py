"""A1: Text Normalizer -- wrapped as an Orchestration Analyzer.

This wraps the standalone normalizer.process() function (in runtime/normalizer.py)
into an Analyzer class conforming to the orchestration contract.

Spec reference: OutputLens Framework Specification, Chapter 12 (A1).
"""

from __future__ import annotations

from typing import Any

from outputlens.orchestration.analyzer import (
    AnalysisContext,
    Analyzer,
    AnalyzerDeclaration,
    AnalyzerError,
    AnalyzerInput,
)
from outputlens.orchestration.engine import AnalyzerRegistry
from outputlens.runtime.model import NormalizedText, PositionIndex, RawInput
from outputlens.runtime.normalizer import process as normalize_process


class TextNormalizerAnalyzer(Analyzer):
    """A1: Produces NormalizedText and PositionIndex from RawInput."""

    declaration = AnalyzerDeclaration(
        id="a1",
        version="0.1.0",
        responsibility="Normalize raw text input: Unicode NFKC normalization, "
        "whitespace regularization, segment detection, and position index construction.",
        inputs=(),  # No dependencies -- this is the entry point
        output_type=dict,
        layer="foundation",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        """Execute text normalization.

        Reads RawInput directly from the context's pre-populated data.
        In the reference implementation, RawInput is placed into context
        by the application bootstrap before the orchestrator runs.
        """
        raw_input = context.get_output("_bootstrap", "raw_input")
        if raw_input is None or not isinstance(raw_input, RawInput):
            raise AnalyzerError(
                "A1 (Text Normalizer) requires RawInput to be pre-populated "
                "in context under '_bootstrap.raw_input'"
            )

        normalized_text, position_index = normalize_process(raw_input)

        return {
            "normalized_text": normalized_text,
            "position_index": position_index,
        }


def register(registry: AnalyzerRegistry) -> None:
    """Register the A1 Text Normalizer analyzer."""
    registry.register(TextNormalizerAnalyzer.declaration, lambda: TextNormalizerAnalyzer())
