"""Evaluation metrics for OutputLens analyzers.

Each module provides functions that take AnalysisDocument data (dicts) and
golden dataset annotations, and return metric values. All functions are
deterministic and implementation-agnostic.

Per M6-001: Metrics measure agreement, consistency, usefulness, and
explainability. They do NOT measure correctness or truth.
"""

from benchmarks.evaluation_harness.metrics.extraction import (
    compute_claim_boundary_f1,
    compute_claim_type_accuracy,
)
from benchmarks.evaluation_harness.metrics.classification import (
    compute_agreement,
    compute_confusion,
    compute_distribution,
    compute_kappa,
)
from benchmarks.evaluation_harness.metrics.reasoning import (
    compute_reasoning_specificity,
)
from benchmarks.evaluation_harness.metrics.synthesis import (
    compute_punchlist_precision_recall,
    compute_trust_profile_correlation,
)

__all__ = [
    "compute_claim_boundary_f1",
    "compute_claim_type_accuracy",
    "compute_agreement",
    "compute_confusion",
    "compute_distribution",
    "compute_kappa",
    "compute_reasoning_specificity",
    "compute_punchlist_precision_recall",
    "compute_trust_profile_correlation",
]
