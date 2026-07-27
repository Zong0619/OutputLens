"""A2: Claim Extractor -- deterministic sentence-based claim extraction.

Phase 1.1: Basic Claim Infrastructure
- Splits normalized text into sentences
- Preserves complete source position information
- Produces valid Claim objects with traceable text spans

Spec reference: OutputLens Framework Specification, Chapter 12 (A2).
"""

from __future__ import annotations

import re
from typing import Any

from outputlens.analysis.model import Claim
from outputlens.orchestration.analyzer import (
    AnalysisContext,
    Analyzer,
    AnalyzerDeclaration,
    AnalyzerError,
    AnalyzerInput,
)
from outputlens.orchestration.engine import AnalyzerRegistry
from outputlens.runtime.model import NormalizedText, Segment


# ---------------------------------------------------------------------------
# Abbreviation list -- terms that should NOT trigger sentence splitting
# ---------------------------------------------------------------------------

# Title abbreviations -- followed by proper names (Dr. Smith, Prof. Jones).
# These should NOT trigger sentence splitting even when followed by a capital letter.
_TITLE_ABBREVIATIONS: frozenset[str] = frozenset({
    "mr", "mrs", "ms", "dr", "prof", "gen", "sen", "rep", "gov",
    "col", "lt", "capt", "sgt", "rev", "hon", "st",
})

# General abbreviations -- terms with periods that do not end sentences,
# but CAN end sentences when followed by a capital letter (e.g., "etc. The").
# These only block splitting when followed by lowercase continuation.
_GENERAL_ABBREVIATIONS: frozenset[str] = frozenset({
    # Academic
    "ph.d", "m.d", "b.a", "m.a", "phd", "md", "ba", "ma",
    # Latin / scholarly
    "et al", "etc", "i.e", "e.g", "vs", "viz", "cf",
    # Common
    "inc", "ltd", "co", "corp", "dept", "est", "approx",
    # Temporal
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    # US states
    "ala", "alaska", "ariz", "ark", "calif", "colo", "conn", "del", "fla",
    "ga", "ill", "ind", "kan", "ky", "la", "md", "mass", "mich", "minn",
    "miss", "mo", "mont", "neb", "nev", "nh", "nj", "nm", "ny", "nc",
    "nd", "ohio", "okla", "ore", "pa", "ri", "sc", "sd", "tenn", "tex",
    "utah", "vt", "va", "wash", "wva", "wis", "wyo",
})

# Sentence-ending punctuation
_SENTENCE_END = re.compile(r'(?<=[.!?])')


def _is_title_abbreviation(text: str, period_pos: int) -> bool:
    """Check if a period at `period_pos` is part of a title abbreviation (Dr., Mr., Prof.)."""
    start = period_pos - 1
    while start >= 0 and (text[start].isalpha() or text[start] == '.'):
        start -= 1
    start += 1
    word = text[start:period_pos].lower().rstrip('.')
    return word in _TITLE_ABBREVIATIONS


def _is_general_abbreviation(text: str, period_pos: int) -> bool:
    """Check if a period at `period_pos` is part of a general abbreviation (etc., i.e.)."""
    start = period_pos - 1
    while start >= 0 and (text[start].isalpha() or text[start] == '.'):
        start -= 1
    start += 1
    word = text[start:period_pos].lower().rstrip('.')
    return word in _GENERAL_ABBREVIATIONS


def _is_decimal_or_acronym(text: str, period_pos: int) -> bool:
    """Check if a period is part of a decimal number or acronym initial.

    Returns True for patterns like '3.14' or 'U.S.' where the period
    should NOT be treated as a sentence boundary.
    """
    # Check for digit.digit pattern (decimal numbers)
    if period_pos > 0 and period_pos < len(text) - 1:
        if text[period_pos - 1].isdigit() and text[period_pos + 1].isdigit():
            return True

    # Check for single-letter acronym pattern (e.g., U.S., Ph.D.)
    # A period preceded by 1-2 letters and followed by another letter
    before = text[max(0, period_pos - 2):period_pos]
    if period_pos < len(text) - 1 and text[period_pos + 1].isalpha():
        if re.match(r'^[A-Za-z]\.?$', before[-2:]) if len(before) >= 1 else False:
            # Actually, check more carefully: single uppercase or short abbrev
            if len(before.rstrip('.')) <= 2 and before.rstrip('.').isalpha():
                return True

    return False


def _is_sentence_boundary(text: str, period_pos: int) -> bool:
    """Determine if a sentence-ending punctuation mark is a true boundary.

    Returns False for abbreviations, decimals, and acronyms.
    """
    char = text[period_pos]

    # ! and ? are almost always sentence boundaries
    if char in ('!', '?'):
        # Exception: ? or ! inside quotes followed by lowercase continuation
        # But for Phase 1.1, treat all ! and ? as boundaries
        return True

    # For periods: first, check what follows
    after = text[period_pos + 1:]
    m = re.match(r'\s+', after)

    # Period at end of text
    if not m:
        if period_pos == len(text) - 1 or text[period_pos + 1] == '\n':
            return True
        # Period followed immediately by non-space (e.g., URL, filename)
        return False

    # Check what follows the whitespace
    next_non_space_pos = period_pos + 1 + len(m.group())
    if next_non_space_pos >= len(text):
        return True  # End of text after whitespace

    next_char = text[next_non_space_pos]

    # Capital letter or digit after whitespace strongly suggests new sentence,
    # EXCEPT when the period is part of:
    #   - A title abbreviation (Dr. Smith)
    #   - An acronym initial (U.S. policy)
    #   - A general abbreviation followed by a digit (approx. 3.14, Jan. 2025)
    if next_char.isupper() or next_char.isdigit():
        if _is_title_abbreviation(text, period_pos):
            return False  # "Dr. Smith" -- not a boundary
        if _is_decimal_or_acronym(text, period_pos):
            return False  # "U.S. policy" -- not a boundary
        if next_char.isdigit() and _is_general_abbreviation(text, period_pos):
            return False  # "approx. 3.14", "Jan. 2025" -- not a boundary
        return True  # "etc. The" -- boundary; "sentence. Next" -- boundary

    # Phase 1.4: List markers (bullets, dashes, numbered items) indicate
    # new sentence boundaries. Patterns: "cleaned. - Models..." or "done. 1. Next..."
    if next_char in ('-', '*', '+', '•', '‣', '◦'):
        # Bullet/dash followed by space indicates a new list item
        if next_non_space_pos + 1 < len(text) and text[next_non_space_pos + 1] == ' ':
            return True
    # Numbered list: "1. Text" or "1) Text"
    if next_char.isdigit():
        rest = text[next_non_space_pos:]
        if re.match(r'\d+[.)]\s', rest):
            return True

    # Quotation mark or bullet followed by capital
    if next_char in ('"', '“', '”', '‘') and next_non_space_pos + 1 < len(text):
        if text[next_non_space_pos + 1].isupper():
            if _is_title_abbreviation(text, period_pos):
                return False
            return True

    # Lowercase after period: check if it's an abbreviation or decimal
    if _is_title_abbreviation(text, period_pos):
        return False
    if _is_general_abbreviation(text, period_pos):
        return False
    if _is_decimal_or_acronym(text, period_pos):
        return False

    # Period followed by lowercase with no abbreviation -- could be a
    # fragment boundary or error in the text. Conservative: not a boundary.
    return False


def split_sentences(text: str) -> list[tuple[int, int, str]]:
    """Split normalized text into sentences with position information.

    Uses deterministic, rule-based splitting. No ML dependencies.
    No external libraries beyond Python stdlib.

    Args:
        text: The normalized text string from A1 (NormalizedText.text).

    Returns:
        List of (start_char, end_char, sentence_text) tuples with
        non-overlapping, monotonically increasing character offsets.
    """
    if not text.strip():
        return []

    sentences: list[tuple[int, int, str]] = []
    pos = 0
    text_len = len(text)

    while pos < text_len:
        # Skip leading whitespace
        while pos < text_len and text[pos] in (' ', '\n', '\t'):
            pos += 1
        if pos >= text_len:
            break

        start = pos

        # Find the next sentence boundary.
        # _SENTENCE_END is a zero-width lookbehind -- match.start() is the
        # position AFTER the punctuation. _is_sentence_boundary expects the
        # position OF the punctuation, so we test (cand - 1).
        boundary = -1
        for match in _SENTENCE_END.finditer(text, pos):
            punct_pos = match.start() - 1
            # Guard: skip boundaries before our current search start.
            # This prevents infinite loops when consecutive punctuation
            # marks create matches at already-processed positions.
            if punct_pos < start:
                continue
            if punct_pos >= 0 and _is_sentence_boundary(text, punct_pos):
                boundary = punct_pos
                break

        if boundary >= 0:
            end = boundary + 1  # Include the punctuation
            # If there's a closing quote after the punctuation, include it
            if end < text_len and text[end] in ('"', '”', '’', "'", ')'):
                end += 1
        else:
            # No boundary found -- the rest of the text is one sentence
            end = text_len

        # Trim trailing whitespace from the sentence text
        sentence_text = text[start:end].strip()
        if sentence_text:
            sentences.append((start, end, sentence_text))

        pos = end

    return sentences


def _find_segment_for_position(
    segments: tuple[Segment, ...], char_pos: int
) -> str:
    """Find which segment a character position belongs to.

    Returns the segment ID, or "seg_unknown" if no matching segment.
    """
    for seg in segments:
        if seg.start_char <= char_pos < seg.end_char:
            return seg.id
    # For positions that span segment boundaries, use the first containing segment
    for seg in segments:
        if seg.start_char <= char_pos <= seg.end_char:
            return seg.id
    return "seg_unknown"


def _make_claim_id(index: int) -> str:
    """Generate a stable claim ID from a 1-based index."""
    return f"c{index}"


# ---------------------------------------------------------------------------
# Phase 1.2: Atomic Claim Extraction -- conjunction splitting
# ---------------------------------------------------------------------------

# Phase 1.2: Coordinating conjunctions that can join independent clauses.
# Pattern: ", <conjunction> " where what follows is an independent clause.
_COORD_CONJUNCTION_PATTERN = re.compile(
    r',\s+(and|or|but|yet|so|nor)\s+',
    re.IGNORECASE,
)

# Phase 1.3: Compound sentence connectors.
#   Group 1: Adverbial connectors -- "; however, " or ". However, " style.
#   Group 2: Subordinating conjunctions preceded by comma.
_COMPOUND_PATTERN = re.compile(
    r'(?:;\s*|,\s+)'
    r'(however|therefore|thus|consequently|moreover|furthermore|nevertheless|nonetheless|instead|otherwise|meanwhile|hence|accordingly)'
    r'\s*,?\s*',
    re.IGNORECASE,
)

_SUBORD_PATTERN = re.compile(
    r',\s+(because|although|though|even though|while|whereas|since|unless)\s+',
    re.IGNORECASE,
)


def _has_independent_clause(text: str) -> bool:
    """Check if `text` contains an independent clause (has a subject + verb).

    Phase 1.2 heuristic: text must contain at least one verb-like word
    (common English verbs or words ending in -ing/-ed/-es/-s after a
    noun/pronoun) AND be at least 3 words long.

    This is intentionally simple. Full clause analysis requires NLP parsing.
    """
    words = text.split()
    if len(words) < 3:
        return False

    # Simple verb indicators: common verbs, auxiliaries, or inflection patterns
    verb_indicators = {
        "is", "are", "was", "were", "be", "been", "being",
        "has", "have", "had", "having",
        "do", "does", "did", "doing",
        "can", "could", "will", "would", "shall", "should",
        "may", "might", "must",
        "provides", "contains", "includes", "represents", "describes",
        "shows", "demonstrates", "indicates", "suggests", "implies",
        "means", "results", "leads", "causes", "produces",
        "uses", "works", "requires", "allows", "enables", "makes",
    }
    for word in words:
        lower = word.lower().rstrip('.,;:!?")')
        if lower in verb_indicators:
            return True
        if len(lower) > 3 and (
            lower.endswith("ing") or lower.endswith("ed")
            or (lower.endswith("s") and not lower.endswith("ss"))
        ):
            return True
    return False


def _find_split_points(text: str) -> list[int]:
    """Find valid split positions for compound/conjunction decomposition.

    Returns a sorted list of character offsets (comma positions) where the
    text should be split. Applies all three Phase 1.2/1.3 patterns.
    """
    split_positions: set[int] = set()

    # Phase 1.2: Coordinating conjunctions
    for match in _COORD_CONJUNCTION_PATTERN.finditer(text):
        comma_pos = match.start()
        after = text[match.end():]
        if _has_independent_clause(after):
            split_positions.add(comma_pos)

    # Phase 1.3: Adverbial connectors (however, therefore, etc.)
    for match in _COMPOUND_PATTERN.finditer(text):
        # Split at the semicolon or comma that precedes the connector
        split_pos = match.start()
        after = text[match.end():]
        if _has_independent_clause(after):
            split_positions.add(split_pos)

    # Phase 1.3: Subordinating conjunctions (because, although, while, etc.)
    for match in _SUBORD_PATTERN.finditer(text):
        comma_pos = match.start()
        after = text[match.end():]
        if _has_independent_clause(after):
            split_positions.add(comma_pos)

    return sorted(split_positions)


def split_conjunctions(text: str, sentence_start: int) -> list[tuple[int, int, str]]:
    """Split a sentence into atomic claims at conjunction boundaries.

    Phases 1.2-1.3: Handles coordinating conjunctions, adverbial connectors,
    and subordinating conjunctions where what follows forms an independent clause.
    Conservative: only splits when both parts have meaningful content.

    Args:
        text: The full sentence text.
        sentence_start: The character offset in the normalized text.

    Returns:
        List of (start, end, text) tuples. If no splits found, single tuple.
    """
    split_positions = _find_split_points(text)
    if not split_positions:
        return [(sentence_start, sentence_start + len(text), text)]

    # Build sub-claims at split positions
    sub_claims: list[tuple[int, int, str]] = []
    prev_split = 0

    for split_pos in split_positions:
        sub_text = text[prev_split:split_pos].strip()
        # Only create a claim if it has meaningful content
        if sub_text and len(sub_text.split()) >= 2:
            abs_start = sentence_start + prev_split
            abs_end = sentence_start + split_pos
            sub_claims.append((abs_start, abs_end, sub_text))
        # Advance past the comma/semicolon and any following whitespace
        prev_split = split_pos
        while prev_split < len(text) and text[prev_split] in (',', ';', ' ', '\t'):
            prev_split += 1
        # Skip the connector word itself
        remaining = text[prev_split:]
        connector_match = re.match(
            r'(and|or|but|yet|so|nor|however|therefore|thus|consequently|'
            r'moreover|furthermore|nevertheless|nonetheless|instead|otherwise|'
            r'meanwhile|hence|accordingly|because|although|though|while|'
            r'whereas|since|unless)\s+',
            remaining,
            re.IGNORECASE,
        )
        if connector_match:
            prev_split += len(connector_match.group())

    # Final segment
    final_text = text[prev_split:].strip()
    if final_text:
        # Capitalize if original became lowercase after connector removal
        if final_text and final_text[0].islower():
            final_text = final_text[0].upper() + final_text[1:]
        abs_start = sentence_start + prev_split
        abs_end = sentence_start + len(text)
        sub_claims.append((abs_start, abs_end, final_text))

    if len(sub_claims) < 2:
        return [(sentence_start, sentence_start + len(text), text)]

    return sub_claims


def extract_claims(
    normalized_text: NormalizedText,
) -> list[Claim]:
    """Extract claims from normalized text.

    Phase 1.1: Sentences are split into sentence-level units.
    Phase 1.2: Sentences are further split at coordinating conjunctions
               (", and ", ", but ", ", or ") where what follows forms an
               independent clause.

    Position information is preserved from the normalized text.

    Args:
        normalized_text: The NormalizedText from A1, containing the canonical
            text string and segment boundaries.

    Returns:
        List of Claim objects with traceable position spans.
    """
    text = normalized_text.text
    segments = normalized_text.segments
    sentences = split_sentences(text)

    claims: list[Claim] = []
    claim_index = 0

    for _start, _end, sentence_text in sentences:
        # Phase 1.2: split conjunctions within each sentence
        sub_claims = split_conjunctions(sentence_text, _start)

        for sub_start, sub_end, sub_text in sub_claims:
            claim_index += 1
            segment_id = _find_segment_for_position(segments, sub_start)
            claim = Claim(
                id=_make_claim_id(claim_index),
                text=sub_text,
                start_char=sub_start,
                end_char=sub_end,
                segment_id=segment_id,
                claim_type="factual_assertion",
            )
            claims.append(claim)

    return claims


# ---------------------------------------------------------------------------
# Orchestration Analyzer wrapper
# ---------------------------------------------------------------------------


class ClaimExtractorAnalyzer(Analyzer):
    """A2: Extracts claims from normalized text via deterministic sentence splitting.

    Input: NormalizedText + Segments from A1 (Text Normalizer)
    Output: list[Claim]
    """

    declaration = AnalyzerDeclaration(
        id="a2",
        version="0.1.0",
        responsibility="Decompose normalized text into individual Claims by "
        "splitting into sentences, preserving source position information.",
        inputs=(
            AnalyzerInput("a1", "a1", required=True),
        ),
        output_type=list,
        layer="foundation",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        """Execute claim extraction.

        Reads NormalizedText from A1's output in the context.
        """
        a1_output = context.get_output("a1", "a1")
        if a1_output is None:
            raise AnalyzerError(
                "A2 (Claim Extractor) requires A1 (Text Normalizer) output. "
                "Ensure A1 is executed before A2."
            )

        # A1 returns {"normalized_text": NormalizedText, "position_index": PositionIndex}
        normalized_text = a1_output.get("normalized_text")
        if normalized_text is None or not isinstance(normalized_text, NormalizedText):
            raise AnalyzerError(
                "A2 requires NormalizedText from A1 output."
            )

        claims = extract_claims(normalized_text)
        return {"claims": claims}


def register(registry: AnalyzerRegistry) -> None:
    """Register the A2 Claim Extractor analyzer."""
    registry.register(ClaimExtractorAnalyzer.declaration, lambda: ClaimExtractorAnalyzer())
