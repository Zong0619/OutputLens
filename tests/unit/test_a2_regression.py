"""Regression tests for A2 Claim Extractor -- known patterns from AI responses.

These tests encode specific claim extraction behaviors that must be preserved
across changes. If a test here fails, the change must be intentional and
the test expectation updated with documentation of why it changed.
"""

from __future__ import annotations

import pytest

from outputlens.analyzers.a2_claim_extractor import extract_claims, split_sentences
from outputlens.runtime.model import NormalizedText, Segment


def _make_norm(text: str) -> NormalizedText:
    return NormalizedText(
        text=text,
        segments=(Segment(id="s1", type="paragraph", start_char=0, end_char=len(text)),),
    )


class TestRegressionSimpleSentences:
    """Simple declarative sentences should produce one claim each."""

    def test_single_declarative(self):
        claims = extract_claims(_make_norm("AI is transforming society.\n"))
        assert len(claims) == 1
        assert claims[0].text == "AI is transforming society."

    def test_two_simple_sentences(self):
        claims = extract_claims(
            _make_norm("AI models are improving. They still have limitations.\n")
        )
        assert len(claims) == 2

    def test_three_sentences_mixed_punctuation(self):
        claims = extract_claims(
            _make_norm("What is AI? It is a technology. It is powerful!\n")
        )
        assert len(claims) == 3


class TestRegressionConjunctions:
    """Coordinating conjunctions with commas should split."""

    def test_comma_and_split(self):
        claims = extract_claims(
            _make_norm("The model was trained on data, and it was tested on benchmarks.\n")
        )
        assert len(claims) == 2

    def test_comma_but_split(self):
        claims = extract_claims(
            _make_norm("The approach works well, but it has limitations.\n")
        )
        assert len(claims) == 2

    def test_phrase_list_not_split(self):
        """Comma-separated phrases without independent clauses stay together."""
        claims = extract_claims(
            _make_norm("We need accuracy, precision, and recall.\n")
        )
        assert len(claims) == 1


class TestRegressionAbbreviations:
    """Known abbreviations must not cause false sentence splits."""

    def test_dr_prefix(self):
        claims = extract_claims(
            _make_norm("Dr. Smith conducted research. The results were significant.\n")
        )
        assert len(claims) == 2
        assert "Dr. Smith" in claims[0].text

    def test_us_acronym(self):
        claims = extract_claims(
            _make_norm("The U.S. economy is large. It influences global markets.\n")
        )
        assert len(claims) == 2
        assert "U.S." in claims[0].text


class TestRegressionCompoundStructures:
    """Compound and complex structures should be handled conservatively."""

    def test_because_clause_split(self):
        claims = extract_claims(
            _make_norm("The study was significant, because it involved many subjects.\n")
        )
        assert len(claims) == 2

    def test_relative_clause_preserved(self):
        claims = extract_claims(
            _make_norm("The model, which was trained on diverse data, performs well.\n")
        )
        assert len(claims) == 1

    def test_appositive_preserved(self):
        claims = extract_claims(
            _make_norm("GPT-4, a large language model, was released in 2023.\n")
        )
        assert len(claims) == 1


class TestRegressionListPatterns:
    """Common list patterns in AI responses."""

    def test_dash_bullet_list(self):
        claims = extract_claims(
            _make_norm("Key points: - Data quality matters. - Models need tuning. - Results vary.\n")
        )
        assert len(claims) >= 3

    def test_numbered_list(self):
        claims = extract_claims(
            _make_norm("Steps: 1. Collect data. 2. Clean data. 3. Train model.\n")
        )
        assert len(claims) >= 3


class TestRegressionPositionIntegrity:
    """Position spans must always be correct and traceable."""

    def test_positions_match_text(self):
        text = "First claim. Second claim. Third claim.\n"
        claims = extract_claims(_make_norm(text))
        for claim in claims:
            extracted = text[claim.start_char:claim.end_char].strip()
            assert claim.text in extracted or extracted in claim.text, (
                f"Position mismatch: claim '{claim.text[:30]}...' "
                f"at [{claim.start_char}:{claim.end_char}]"
            )

    def test_sequential_claim_ids(self):
        text = "A. B. C. D.\n"
        claims = extract_claims(_make_norm(text))
        ids = [c.id for c in claims]
        assert ids == [f"c{i}" for i in range(1, len(ids) + 1)]


class TestRegressionDegenerateInputs:
    """Edge cases that should not crash or hang."""

    def test_empty_input(self):
        claims = extract_claims(_make_norm("\n"))
        assert claims == []

    def test_punctuation_only(self):
        claims = extract_claims(_make_norm("... ??? !!!\n"))
        # Should produce some output without hanging
        assert isinstance(claims, list)

    def test_very_short_input(self):
        claims = extract_claims(_make_norm("Hi.\n"))
        assert len(claims) == 1
