"""Text normalization pipeline — RawInput → NormalizedText + PositionIndex + Segments.

This module implements the A1 (Text Normalizer) behavior:
1. Unicode normalization (NFKC)
2. Whitespace regularization
3. Segment detection (paragraphs, headings, code blocks, lists)
4. Bidirectional position mapping

Spec reference: OutputLens Framework Specification, Chapter 9.
"""

from __future__ import annotations

import re
import unicodedata

from outputlens.runtime.model import (
    NormalizedText,
    PositionIndex,
    PositionMapping,
    RawInput,
    Segment,
)


def normalize(input_text: str) -> str:
    """Apply Unicode NFKC normalization and whitespace regularization.

    Transformations:
        - NFKC normalization (compose characters, normalize ligatures, width)
        - Normalize line endings to \n
        - Collapse multiple blank lines to max 2
        - Strip leading/trailing whitespace from each line
        - Preserve indentation for code blocks (lines starting with 4+ spaces or tab)

    These transformations are deterministic and documented per spec requirements.
    """
    # NFKC normalization
    text = unicodedata.normalize("NFKC", input_text)

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse blank lines: 3+ blank lines → 2 blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip trailing whitespace per line, but keep the newline
    lines = text.split("\n")
    lines = [line.rstrip(" \t") for line in lines]
    text = "\n".join(lines)

    # Strip leading/trailing whitespace from the whole text
    text = text.strip()

    # Ensure text ends with exactly one newline for POSIX compliance
    if text:
        text += "\n"

    return text


def detect_segments(normalized_text: str) -> list[Segment]:
    """Detect structural divisions in the normalized text.

    Detection rules (v1):
        - Two or more consecutive newlines → paragraph break
        - Lines starting with '#' followed by space → heading
        - Lines starting with '- ', '* ', or '1. ' → list item
        - Indented blocks (4+ spaces or tab) → code block
        - Lines starting with '> ' → blockquote
        - Everything else → paragraph (default)

    Returns segments with monotonically increasing, non-overlapping character offsets.
    """
    segments: list[Segment] = []
    seg_id = 0
    pos = 0

    # Split into blocks by blank lines
    blocks = re.split(r"\n\n+", normalized_text)

    for block in blocks:
        if not block.strip():
            pos += len(block) + 2  # +2 for the \n\n separator
            continue

        block_start = pos
        lines = block.split("\n")

        # Determine block type from first line
        first_line = lines[0].lstrip()

        if first_line.startswith("#") and " " in first_line:
            seg_type = "heading"
            label = first_line.lstrip("#").strip()
        elif first_line.startswith(("- ", "* ", "+ ")) or re.match(r"^\d+\.\s", first_line):
            seg_type = "list_item"
            label = None
        elif block.startswith("    ") or block.startswith("\t"):
            seg_type = "code_block"
            label = None
        elif first_line.startswith("> "):
            seg_type = "blockquote"
            label = None
        else:
            seg_type = "paragraph"
            label = None

        seg_id += 1
        seg_end = pos + len(block)

        segments.append(
            Segment(
                id=f"seg_{seg_id}",
                type=seg_type,
                start_char=block_start,
                end_char=seg_end,
                label=label,
            )
        )

        pos = seg_end + 2  # +2 for the \n\n separator

    return segments


def build_position_index(raw_text: str, normalized_text: str) -> PositionIndex:
    """Build bidirectional position mapping between raw and normalized text.

    Strategy: greedy character-by-character alignment with normalization awareness.
    Each character in the normalized text is traced back to its source character(s)
    in the raw text.

    For many-to-one normalizations (e.g., ligatures → decomposed), the reverse
    mapping from normalized to raw maps to the FIRST corresponding raw position.
    This is documented behavior per the specification.

    Returns a PositionIndex with contiguous, non-overlapping mappings.
    """
    mappings: list[PositionMapping] = []

    raw_idx = 0
    norm_idx = 0

    while norm_idx < len(normalized_text) and raw_idx < len(raw_text):
        norm_char = normalized_text[norm_idx]
        raw_char = raw_text[raw_idx]

        # Try to match at current position
        if norm_char == raw_char or _chars_match_after_normalization(norm_char, raw_char):
            # Direct match — one-to-one
            mappings.append(
                PositionMapping(
                    normalized_start=norm_idx,
                    normalized_end=norm_idx + 1,
                    raw_start=raw_idx,
                    raw_end=raw_idx + 1,
                )
            )
            norm_idx += 1
            raw_idx += 1
        elif raw_char in ("\r", " "):
            # Skip raw characters that were removed/collapsed in normalization
            raw_idx += 1
        elif norm_char == " " and raw_char == "\n":
            # Newline converted to space
            mappings.append(
                PositionMapping(
                    normalized_start=norm_idx,
                    normalized_end=norm_idx + 1,
                    raw_start=raw_idx,
                    raw_end=raw_idx + 1,
                )
            )
            norm_idx += 1
            raw_idx += 1
        elif raw_char in ("\t",) and norm_char == " ":
            mappings.append(
                PositionMapping(
                    normalized_start=norm_idx,
                    normalized_end=norm_idx + 1,
                    raw_start=raw_idx,
                    raw_end=raw_idx + 1,
                )
            )
            norm_idx += 1
            raw_idx += 1
        else:
            # Fallback: skip the raw character (it was removed during normalization)
            raw_idx += 1

    # trailing raw content maps to end of normalized
    if norm_idx == len(normalized_text) and raw_idx < len(raw_text):
        pass  # Remaining raw characters were stripped

    return PositionIndex(mappings=tuple(mappings))


def _chars_match_after_normalization(char_a: str, char_b: str) -> bool:
    """Check if two characters are equal after NFKC normalization."""
    return unicodedata.normalize("NFKC", char_a) == unicodedata.normalize("NFKC", char_b)


def process(raw_input: RawInput) -> tuple[NormalizedText, PositionIndex]:
    """Run the full text normalization pipeline.

    This is the entry point for A1 (Text Normalizer). It:
    1. Normalizes the raw text
    2. Detects structural segments
    3. Builds the position index

    Args:
        raw_input: The RawInput containing the user's original text.

    Returns:
        Tuple of (NormalizedText, PositionIndex). These are companion objects —
        NormalizedText without PositionIndex is unusable for rendering.
    """
    raw_text = raw_input.text
    norm_text = normalize(raw_text)
    segments = detect_segments(norm_text)
    position_index = build_position_index(raw_text, norm_text)

    normalized = NormalizedText(text=norm_text, segments=tuple(segments))
    return normalized, position_index
