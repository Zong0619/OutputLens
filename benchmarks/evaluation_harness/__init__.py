"""OutputLens Evaluation Harness -- implementation-agnostic quality measurement.

Consumes serialized AnalysisDocuments (JSON) and golden dataset annotations.
Computes canonical metrics: agreement, consistency, usefulness, explainability.
Does NOT define correctness. Does NOT modify analyzers.

Per M6-001: Evaluation Does Not Define Correctness.
"""

__version__ = "0.1.0"
