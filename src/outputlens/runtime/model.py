"""Runtime Model — dataclasses for the infrastructure objects (R1–R8).

These objects support execution. They carry no analytical insight themselves.
All objects are immutable once constructed.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class RawInput:
    """R2: The unmodified text as submitted by the user. Immutable ground truth."""

    text: str
    prompt: str | None = None

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError("RawInput.text must not be empty")


@dataclass(frozen=True)
class Metadata:
    """R3: Non-textual context of the analysis."""

    engine_version: str
    timestamp: datetime
    analysis_id: str
    prompt: str | None = None
    model_identifier: str | None = None
    domain_hint: str | None = None

    @classmethod
    def create(
        cls,
        engine_version: str,
        prompt: str | None = None,
        model_identifier: str | None = None,
        domain_hint: str | None = None,
    ) -> Metadata:
        """Factory: create Metadata with auto-generated timestamp and analysis ID."""
        return cls(
            engine_version=engine_version,
            timestamp=datetime.now(timezone.utc),
            analysis_id=str(uuid.uuid4()),
            prompt=prompt,
            model_identifier=model_identifier,
            domain_hint=domain_hint,
        )


@dataclass(frozen=True)
class AnalyzerConfiguration:
    """R4: Which analyzers to run, with what options."""

    requested_analyzers: tuple[str, ...] = ()
    analyzer_options: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class Segment:
    """R7: A structural division of the text."""

    id: str
    type: str  # paragraph, heading, list_item, code_block, blockquote, table_cell
    start_char: int
    end_char: int
    parent_id: str | None = None
    label: str | None = None

    VALID_TYPES = frozenset(
        {"paragraph", "heading", "list_item", "code_block", "blockquote", "table_cell"}
    )

    def __post_init__(self) -> None:
        if self.type not in self.VALID_TYPES:
            raise ValueError(f"Segment type must be one of {sorted(self.VALID_TYPES)}")
        if self.start_char < 0:
            raise ValueError("start_char must be >= 0")
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be > start_char")


@dataclass(frozen=True)
class PositionMapping:
    """A single bidirectional position mapping between normalized and raw text."""

    normalized_start: int
    normalized_end: int
    raw_start: int
    raw_end: int

    def __post_init__(self) -> None:
        if self.normalized_start < 0 or self.normalized_end < self.normalized_start:
            raise ValueError(
                f"Invalid normalized span: [{self.normalized_start}, {self.normalized_end})"
            )
        if self.raw_start < 0 or self.raw_end < self.raw_start:
            raise ValueError(f"Invalid raw span: [{self.raw_start}, {self.raw_end})")


@dataclass(frozen=True)
class PositionIndex:
    """R6: Bidirectional mapping between NormalizedText and RawInput positions."""

    mappings: tuple[PositionMapping, ...] = ()

    def normalize_position(self, raw_pos: int) -> int | None:
        """Map a RawInput position to a NormalizedText position.

        Returns None if the position falls outside known mappings.
        """
        for m in self.mappings:
            if m.raw_start <= raw_pos < m.raw_end:
                offset = raw_pos - m.raw_start
                return m.normalized_start + offset
        return None

    def raw_position(self, normalized_pos: int) -> int | None:
        """Map a NormalizedText position to a RawInput position."""
        for m in self.mappings:
            if m.normalized_start <= normalized_pos < m.normalized_end:
                offset = normalized_pos - m.normalized_start
                return m.raw_start + offset
        return None


@dataclass(frozen=True)
class NormalizedText:
    """R5: Canonical text representation for analysis."""

    text: str
    segments: tuple[Segment, ...] = ()

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError("NormalizedText.text must not be empty")


@dataclass(frozen=True)
class AnalysisRequest:
    """R1: Complete input to the analysis engine."""

    raw_input: RawInput
    metadata: Metadata
    configuration: AnalyzerConfiguration = field(default_factory=AnalyzerConfiguration)


@dataclass(frozen=True)
class AnalyzerExecution:
    """A single entry in the ExecutionTrace (R8)."""

    analyzer_id: str
    analyzer_version: str
    started_at: datetime
    completed_at: datetime
    status: str  # success, failure, skipped, degraded
    input_hashes: dict[str, str] = field(default_factory=dict)

    VALID_STATUSES = frozenset({"success", "failure", "skipped", "degraded"})

    def __post_init__(self) -> None:
        if self.status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid execution status: {self.status}")


@dataclass(frozen=True)
class ExecutionTrace:
    """R8: Record of every analyzer execution in a single analysis run."""

    analyzer_executions: tuple[AnalyzerExecution, ...] = ()
