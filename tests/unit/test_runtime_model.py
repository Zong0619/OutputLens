"""Tests for Runtime Model objects and text normalization pipeline."""

import pytest

from outputlens.runtime.model import (
    AnalysisRequest,
    Metadata,
    NormalizedText,
    PositionIndex,
    PositionMapping,
    RawInput,
    Segment,
)
from outputlens.runtime.normalizer import (
    build_position_index,
    detect_segments,
    normalize,
    process,
)


class TestRawInput:
    def test_creation(self):
        ri = RawInput(text="Hello world")
        assert ri.text == "Hello world"
        assert ri.prompt is None

    def test_with_prompt(self):
        ri = RawInput(text="Hello", prompt="What is hello?")
        assert ri.prompt == "What is hello?"

    def test_empty_text_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            RawInput(text="")


class TestMetadata:
    def test_create_auto_generates_fields(self):
        meta = Metadata.create(engine_version="0.1.0")
        assert meta.engine_version == "0.1.0"
        assert meta.analysis_id  # auto-generated UUID
        assert meta.timestamp  # auto-generated

    def test_create_with_optional_fields(self):
        meta = Metadata.create(
            engine_version="0.1.0",
            prompt="Test prompt",
            model_identifier="claude-opus-4-8",
            domain_hint="physics",
        )
        assert meta.prompt == "Test prompt"
        assert meta.model_identifier == "claude-opus-4-8"
        assert meta.domain_hint == "physics"


class TestSegment:
    def test_valid_segment(self):
        seg = Segment(id="s1", type="paragraph", start_char=0, end_char=100)
        assert seg.id == "s1"

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Segment type must be one of"):
            Segment(id="s1", type="invalid", start_char=0, end_char=100)

    def test_invalid_span_raises(self):
        with pytest.raises(ValueError, match="end_char must be > start_char"):
            Segment(id="s1", type="paragraph", start_char=100, end_char=50)


class TestPositionIndex:
    def test_bidirectional_mapping(self):
        mappings = (
            PositionMapping(normalized_start=0, normalized_end=5, raw_start=0, raw_end=5),
        )
        pi = PositionIndex(mappings=mappings)

        assert pi.normalize_position(0) == 0
        assert pi.normalize_position(4) == 4
        assert pi.raw_position(0) == 0
        assert pi.raw_position(4) == 4

    def test_out_of_bounds_returns_none(self):
        pi = PositionIndex(mappings=())
        assert pi.normalize_position(100) is None
        assert pi.raw_position(100) is None

    def test_multi_mapping_lookup(self):
        mappings = (
            PositionMapping(normalized_start=0, normalized_end=5, raw_start=0, raw_end=5),
            PositionMapping(normalized_start=5, normalized_end=10, raw_start=10, raw_end=15),
        )
        pi = PositionIndex(mappings=mappings)

        assert pi.normalize_position(12) == 7  # raw 12 → norm 7
        assert pi.raw_position(7) == 12  # norm 7 → raw 12

    def test_invalid_mapping_raises(self):
        with pytest.raises(ValueError):
            PositionMapping(normalized_start=5, normalized_end=3, raw_start=0, raw_end=5)


class TestNormalize:
    def test_basic_text_preserved(self):
        result = normalize("Hello world.")
        assert "Hello world." in result

    def test_line_ending_normalization(self):
        result = normalize("line1\r\nline2\rline3")
        assert "\r\n" not in result
        assert "\r" not in result

    def test_multiple_blank_lines_collapsed(self):
        result = normalize("para1\n\n\n\n\npara2")
        assert "\n\n\n\n\n" not in result
        # max 2 blank lines → 1 separator
        assert "para1\n\npara2" in result

    def test_trailing_whitespace_stripped(self):
        result = normalize("hello   \nworld   ")
        # trailing spaces on lines stripped
        assert "hello\nworld" in result

    def test_unicode_normalization(self):
        # NFKC composes ligatures
        import unicodedata
        composed = "fi"  # already composed
        result = normalize(composed)
        assert result.strip() == composed


class TestDetectSegments:
    def test_paragraph_detection(self):
        text = "This is a paragraph.\n"
        segments = detect_segments(text)
        assert len(segments) >= 1
        para_segs = [s for s in segments if s.type == "paragraph"]
        assert len(para_segs) >= 1

    def test_heading_detection(self):
        text = "# Introduction\n\nContent here.\n"
        segments = detect_segments(text)
        headings = [s for s in segments if s.type == "heading"]
        assert len(headings) >= 1
        assert headings[0].label == "Introduction"

    def test_non_overlapping_positions(self):
        text = "First paragraph.\n\nSecond paragraph.\n"
        segments = detect_segments(text)
        for i in range(len(segments)):
            for j in range(i + 1, len(segments)):
                assert segments[i].end_char <= segments[j].start_char, (
                    f"Segments overlap: {segments[i]} and {segments[j]}"
                )


class TestBuildPositionIndex:
    def test_identical_text(self):
        text = "Hello world."
        result = build_position_index(text, text)
        assert len(result.mappings) == len(text)

    def test_position_preservation(self):
        raw = "Hello world."
        norm = normalize(raw)
        pi = build_position_index(raw, norm)
        # First character should map to first character
        assert pi.normalize_position(0) is not None


class TestProcessPipeline:
    def test_end_to_end(self):
        raw = RawInput(text="Hello world. This is a test.")
        norm, pi = process(raw)

        assert isinstance(norm, NormalizedText)
        assert isinstance(pi, PositionIndex)
        assert len(norm.text) > 0
        assert len(norm.segments) > 0
        assert len(pi.mappings) > 0

    def test_analysis_request_creation(self):
        raw = RawInput(text="Test text.", prompt="Test prompt")
        meta = Metadata.create(engine_version="0.1.0")
        req = AnalysisRequest(raw_input=raw, metadata=meta)

        assert req.raw_input is raw
        assert req.metadata is meta

    def test_complex_markdown_text(self):
        text = """# Title

This is a paragraph with **bold** and *italic*.

## Section 2

- List item 1
- List item 2

```
code block
```

> A blockquote.

Final paragraph."""
        raw = RawInput(text=text)
        norm, pi = process(raw)

        # Should handle all basic Markdown structures
        assert len(norm.text) > 0
        assert len(pi.mappings) > 0

        types = {s.type for s in norm.segments}
        # Should detect at least paragraphs and headings
        assert "paragraph" in types
