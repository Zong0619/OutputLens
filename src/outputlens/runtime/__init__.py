"""Runtime Model -- infrastructure objects for text ingestion, normalization, and position mapping."""

from outputlens.runtime.model import (
    AnalysisRequest,
    AnalyzerConfiguration,
    AnalyzerExecution,
    ExecutionTrace,
    Metadata,
    NormalizedText,
    PositionIndex,
    PositionMapping,
    RawInput,
    Segment,
)
from outputlens.runtime.normalizer import process as normalize_process

__all__ = [
    "AnalysisRequest",
    "AnalyzerConfiguration",
    "AnalyzerExecution",
    "ExecutionTrace",
    "Metadata",
    "NormalizedText",
    "PositionIndex",
    "PositionMapping",
    "RawInput",
    "Segment",
    "normalize_process",
]