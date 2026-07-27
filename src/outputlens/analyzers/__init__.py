"""Analyzer implementations for the OutputLens reference engine.

Each analyzer module provides a `register(registry)` function that registers
the analyzer with the orchestration layer.

To add a new analyzer:
1. Create a module in this package (e.g., a4_establishedness.py)
2. Implement the Analyzer subclass
3. Provide a `register(registry)` function
4. Import and call register() in application startup
"""

from outputlens.analyzers import (
    a1_normalizer, a2_claim_extractor, a3_concept_extractor,
    a4_establishedness, a5_evidence_requirement,
)
from outputlens.orchestration.engine import AnalyzerRegistry


def register_all(registry: AnalyzerRegistry) -> None:
    """Register all reference implementation analyzers.

    Called at application startup to populate the analyzer catalog.
    """
    a1_normalizer.register(registry)
    a2_claim_extractor.register(registry)
    a3_concept_extractor.register(registry)
    a4_establishedness.register(registry)
    a5_evidence_requirement.register(registry)
