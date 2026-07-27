"""A3: Concept Extractor -- deterministic concept identification.

Phase 2.1: Named Entity Recognition
- Identifies persons, organizations, locations, and works
- Assigns each to referencing claims
- Produces valid Concept objects with traceable surface forms

Spec reference: OutputLens Framework Specification, Chapter 12 (A3).
"""

from __future__ import annotations

import re
from typing import Any

from outputlens.analysis.model import Claim, Concept, ConceptSurfaceForm
from outputlens.orchestration.analyzer import (
    AnalysisContext,
    Analyzer,
    AnalyzerDeclaration,
    AnalyzerError,
    AnalyzerInput,
)
from outputlens.orchestration.engine import AnalyzerRegistry
from outputlens.runtime.model import NormalizedText


# ---------------------------------------------------------------------------
# Phase 2.1: Named Entity Recognition -- patterns and heuristics
# ---------------------------------------------------------------------------

# Organization suffixes that signal an organization name
_ORG_SUFFIXES: frozenset[str] = frozenset({
    "university", "college", "institute", "institution",
    "corporation", "corp", "incorporated", "inc",
    "limited", "ltd", "llc", "llp",
    "laboratory", "labs", "lab",
    "research", "center", "centre",
    "foundation", "society", "association", "organization",
    "agency", "authority", "commission", "committee",
    "academy", "school", "hospital", "clinic",
    "bank", "group", "holdings", "enterprises",
    "technologies", "systems", "solutions", "analytics",
    "department", "ministry", "federation", "alliance",
})

# Common person name prefixes (titles)
_NAME_PREFIXES: frozenset[str] = frozenset({
    "mr", "mrs", "ms", "miss", "dr", "prof", "professor",
    "gen", "general", "sen", "senator", "rep", "representative",
    "gov", "governor", "president", "secretary", "minister",
    "ambassador", "mayor", "judge", "justice",
    "col", "colonel", "lt", "lieutenant", "capt", "captain",
    "sgt", "sergeant", "rev", "reverend", "hon", "honorable",
    "sir", "lord", "lady", "baron", "duke", "earl",
})

# Common location names (countries, major cities, continents)
_KNOWN_LOCATIONS: frozenset[str] = frozenset({
    # Continents
    "africa", "antarctica", "asia", "australia", "europe",
    "north america", "south america",
    # Major countries
    "united states", "china", "india", "russia", "japan",
    "germany", "united kingdom", "france", "brazil", "canada",
    "australia", "south korea", "mexico", "indonesia", "italy",
    "spain", "netherlands", "switzerland", "sweden", "norway",
    "denmark", "finland", "poland", "ukraine", "turkey",
    "israel", "saudi arabia", "uae", "singapore", "new zealand",
    "south africa", "nigeria", "egypt", "kenya", "ethiopia",
    "argentina", "chile", "colombia", "peru", "vietnam",
    "thailand", "malaysia", "philippines", "pakistan", "iran",
    "iraq", "portugal", "greece", "austria", "belgium",
    "ireland", "czech republic", "romania", "hungary",
    # Major cities
    "new york", "london", "paris", "tokyo", "beijing",
    "shanghai", "mumbai", "delhi", "moscow", "berlin",
    "san francisco", "los angeles", "chicago", "boston",
    "washington", "seattle", "toronto", "sydney", "seoul",
    "hong kong", "dubai", "singapore", "amsterdam", "zurich",
    "geneva", "brussels", "vienna", "madrid", "barcelona",
    "rome", "milan", "munich", "stockholm", "oslo",
    "copenhagen", "helsinki", "warsaw", "istanbul",
    # US states
    "alabama", "alaska", "arizona", "arkansas", "california",
    "colorado", "connecticut", "delaware", "florida", "georgia",
    "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas",
    "kentucky", "louisiana", "maine", "maryland",
    "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire",
    "new jersey", "new mexico", "new york state", "north carolina",
    "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
    "rhode island", "south carolina", "south dakota", "tennessee",
    "texas", "utah", "vermont", "virginia", "washington state",
    "west virginia", "wisconsin", "wyoming",
})


def _make_concept_id(index: int) -> str:
    """Generate a stable concept ID from a 1-based index."""
    return f"con{index}"


# ---------------------------------------------------------------------------
# Person name extraction
# ---------------------------------------------------------------------------

# Pattern: Title + capitalized name (Dr. John Smith, Prof. Jane Doe)
_TITLE_NAME_PATTERN = re.compile(
    r'\b(?:' + '|'.join(re.escape(p) for p in _NAME_PREFIXES) + r')\.?\s+'
    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})'
)

# Pattern: Simple capitalized multi-word name.
# Matches "Albert Einstein", "John von Neumann", "Marie Curie".
# Strategy: two passes. First try particle-aware names, then simple capitalized pairs.
_LOWERCASE_PARTICLES_RE = r'(?:von|van|de|der|den|du|di|da|le|la|el|al)'

# Pattern A: Name with lowercase particle -- "John von Neumann", "Ludwig van Beethoven"
_PARTICLE_NAME_PATTERN = re.compile(
    r'\b([A-Z][a-z]+\s+' + _LOWERCASE_PARTICLES_RE + r'\s+[A-Z][a-z]+)\b'
)

# Pattern B: Simple capitalized pairs/triples -- "Albert Einstein", "Marie Curie"
_CAPITALIZED_NAME_PATTERN = re.compile(
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b'
)

# Pattern: Known initials pattern (J. Robert Oppenheimer, J.R.R. Tolkien)
_INITIALS_NAME_PATTERN = re.compile(
    r'\b((?:[A-Z]\.\s*){1,3}[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b'
)


def _is_likely_person(text: str, span_text: str) -> bool:
    """Heuristic: check if a capitalized sequence looks like a person name.

    Excludes sequences that are likely organizations, locations, or
    sentence-initial capitalization.
    """
    span_lower = span_text.lower().rstrip('.,;:!?)"\'')
    words = span_text.split()

    # Must be 2+ capitalized words
    if len(words) < 2:
        return False

    # Exclude known locations
    if span_lower in _KNOWN_LOCATIONS:
        return False

    # Exclude if every word starts with lowercase (not a name)
    if all(w[0].islower() for w in words if w[0].isalpha()):
        return False

    # Must have at least two capitalized words. Allow lowercase particles
    # (von, van, de, etc.) between capitalized name parts.
    _LOWERCASE_PARTICLES = frozenset({
        "von", "van", "de", "der", "den", "du", "di", "da",
        "le", "la", "el", "al",
    })
    capitalized_count = sum(
        1 for w in words
        if w and w[0].isupper() and w.lower().rstrip('.,;:!?)"\'') not in _ORG_SUFFIXES
    )
    # Also count if the first word is lowercase but it's a known particle
    has_particle = any(w.lower() in _LOWERCASE_PARTICLES for w in words)
    if capitalized_count < 2 and not has_particle:
        return False
    if capitalized_count < 1:
        return False

    # Exclude organization indicators
    if span_lower.endswith(tuple(' ' + s for s in _ORG_SUFFIXES)):
        return False
    last_word = words[-1].lower().rstrip('.,;:!?)"\'')
    if last_word in _ORG_SUFFIXES:
        return False

    return True


def extract_persons(text: str) -> list[tuple[str, int, int]]:
    """Extract person names from text with position spans.

    Returns list of (canonical_name, start_char, end_char) tuples.
    """
    persons: list[tuple[str, int, int]] = []
    seen_spans: set[tuple[int, int]] = set()

    # Priority 1: Title-prefixed names (Dr. Smith, Prof. Jones)
    for match in _TITLE_NAME_PATTERN.finditer(text):
        start = match.start()
        end = match.end()
        name = match.group(0).strip()
        span_key = (start, end)
        if span_key not in seen_spans and _is_likely_person(text, name):
            persons.append((name, start, end))
            seen_spans.add(span_key)

    # Priority 2: Particle names (John von Neumann, Ludwig van Beethoven)
    for match in _PARTICLE_NAME_PATTERN.finditer(text):
        start = match.start()
        end = match.end()
        name = match.group(0).strip()
        span_key = (start, end)
        if span_key not in seen_spans and _is_likely_person(text, name):
            persons.append((name, start, end))
            seen_spans.add(span_key)

    # Priority 3: Initials patterns (J. Robert Oppenheimer)
    for match in _INITIALS_NAME_PATTERN.finditer(text):
        start = match.start()
        end = match.end()
        name = match.group(0).strip()
        span_key = (start, end)
        if span_key not in seen_spans and _is_likely_person(text, name):
            persons.append((name, start, end))
            seen_spans.add(span_key)

    # Priority 4: General capitalized name patterns
    for match in _CAPITALIZED_NAME_PATTERN.finditer(text):
        start = match.start()
        end = match.end()
        name = match.group(0).strip()
        span_key = (start, end)
        if span_key not in seen_spans and _is_likely_person(text, name):
            persons.append((name, start, end))
            seen_spans.add(span_key)

    return persons


# ---------------------------------------------------------------------------
# Organization extraction
# ---------------------------------------------------------------------------

# Pattern: Capitalized sequence optionally ending with an organization suffix.
# Matches "Stanford University", "Max Planck Institute", "Microsoft Corp"
_ORG_PATTERN = re.compile(
    r'\b((?:[A-Z][a-zA-Z]*(?:\s+(?:of|and|&|the)\s+)?){1,6}'
    r'\s+(?:' + '|'.join(re.escape(s) for s in _ORG_SUFFIXES) + r'))\b',
    re.IGNORECASE,
)

# Known organizations that don't need suffixes (acronyms and well-known names)
_KNOWN_ORGS: frozenset[str] = frozenset({
    "nasa", "nato", "fbi", "cia", "nsa", "unicef", "unesco", "who",
    "wto", "imf", "eu", "opec", "interpol",
    "google", "microsoft", "apple", "amazon", "meta", "openai",
    "anthropic", "deepmind", "tesla", "spacex", "IBM",
    "mit", "stanford", "harvard", "yale", "oxford", "cambridge",
    "princeton", "caltech", "berkeley", "cornell", "columbia",
    "white house", "congress", "senate", "pentagon", "supreme court",
    "united nations", "world bank", "red cross",
})


def extract_organizations(text: str) -> list[tuple[str, int, int]]:
    """Extract organization names from text with position spans."""
    orgs: list[tuple[str, int, int]] = []
    seen_spans: set[tuple[int, int]] = set()

    # Priority 1: Organization suffix pattern
    for match in _ORG_PATTERN.finditer(text):
        start = match.start()
        end = match.end()
        name = match.group(0).strip()
        span_key = (start, end)
        if span_key not in seen_spans and len(name.split()) >= 2:
            orgs.append((name, start, end))
            seen_spans.add(span_key)

    # Priority 2: Known organizations (case-insensitive match)
    for org_name in _KNOWN_ORGS:
        pattern = re.compile(r'\b' + re.escape(org_name) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(text):
            start = match.start()
            end = match.end()
            span_key = (start, end)
            if span_key not in seen_spans:
                orgs.append((match.group(0), start, end))
                seen_spans.add(span_key)

    return orgs


# ---------------------------------------------------------------------------
# Location extraction
# ---------------------------------------------------------------------------


def extract_locations(text: str) -> list[tuple[str, int, int]]:
    """Extract location names from text with position spans."""
    locations: list[tuple[str, int, int]] = []
    seen_spans: set[tuple[int, int]] = set()

    # Check known locations
    for loc_name in _KNOWN_LOCATIONS:
        # Build regex that matches the location as a phrase
        pattern = re.compile(r'\b' + re.escape(loc_name) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(text):
            start = match.start()
            end = match.end()
            span_key = (start, end)
            if span_key not in seen_spans:
                # Preserve original capitalization from text
                locations.append((match.group(0), start, end))
                seen_spans.add(span_key)

    return locations


# ---------------------------------------------------------------------------
# Work (publication) extraction
# ---------------------------------------------------------------------------

# Pattern: Quoted titles -- "Title of Work"
_QUOTED_TITLE_PATTERN = re.compile(r'"([^"]{3,100})"')
_QUOTED_TITLE_PATTERN_2 = re.compile(r'“([^”]{3,100})”')  # Curly quotes
_SINGLE_QUOTED_TITLE = re.compile(r"'([^']{3,100})'")


def extract_works(text: str) -> list[tuple[str, int, int]]:
    """Extract work/publication titles from quoted text.

    Returns list of (title_text, start_char, end_char) tuples.
    Only extracts when the quoted text appears to be a title
    (3+ words or contains title-case words).
    """
    works: list[tuple[str, int, int]] = []
    seen_spans: set[tuple[int, int]] = set()

    for pattern in [_QUOTED_TITLE_PATTERN, _QUOTED_TITLE_PATTERN_2, _SINGLE_QUOTED_TITLE]:
        for match in pattern.finditer(text):
            title = match.group(1).strip()
            # Heuristic: a quoted title is typically 3+ words or has title case
            words = title.split()
            if len(words) < 3:
                # Short quote -- might be a term, not a work title
                # Accept if it has title case words
                has_title_case = any(
                    w[0].isupper() and w[0].isalpha() for w in words
                )
                if not has_title_case:
                    continue

            start = match.start()
            end = match.end()
            span_key = (start, end)
            if span_key not in seen_spans:
                works.append((title, start, end))
                seen_spans.add(span_key)

    return works


# ---------------------------------------------------------------------------
# Phase 2.2: Domain Concept Identification
# ---------------------------------------------------------------------------

# Technical term indicators -- suffixes that suggest a term is domain-specific
_TECHNICAL_SUFFIXES: frozenset[str] = frozenset({
    "tion", "sion", "ics", "ology", "ism", "ity", "sis", "osis",
    "esis", "ance", "ence", "ization", "isation", "ification",
    "metry", "nomy", "graphy", "pathy", "ation", "itive",
    "ment", "able", "ical", "ular", "ture",
    "ssion", "xion", "lysis", "morphism",
})

# Multi-word capitalized term pattern -- "Quantum Entanglement", "Machine Learning"
_CAPITALIZED_TERM_PATTERN = re.compile(
    r'\b((?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4}))\b'
)


def _is_technical_term(word: str) -> bool:
    """Check if a word has technical/domain-specific characteristics."""
    lower = word.lower().rstrip('.,;:!?)"\'')
    if len(lower) < 5:
        return False
    for suffix in _TECHNICAL_SUFFIXES:
        if lower.endswith(suffix) and len(lower) > len(suffix) + 1:
            return True
    return False


def _is_stop_word(word: str) -> bool:
    """Check if a word is a stop word that should not be a concept."""
    stop_words = frozenset({
        "the", "a", "an", "this", "that", "these", "those",
        "it", "its", "he", "she", "they", "we", "you", "i",
        "is", "are", "was", "were", "be", "been", "being",
        "has", "have", "had", "do", "does", "did",
        "can", "could", "will", "would", "shall", "should",
        "may", "might", "must", "to", "of", "in", "for", "on",
        "with", "at", "by", "from", "as", "into", "through",
        "during", "before", "after", "above", "below", "between",
        "and", "but", "or", "nor", "not", "so", "yet",
        "also", "very", "too", "just", "now", "then", "here",
        "there", "when", "where", "why", "how", "all", "each",
        "every", "both", "few", "more", "most", "other", "some",
        "such", "only", "own", "same", "than", "rather",
        "first", "second", "third", "last", "next", "several",
        "many", "much", "one", "two", "three",
    })
    return word.lower().rstrip('.,;:!?)"\'') in stop_words


def _span_overlaps_entities(
    start: int, end: int, entities: list[tuple[str, int, int]]
) -> bool:
    """Check if a span overlaps with any already-extracted named entity."""
    for _name, e_start, e_end in entities:
        if not (end <= e_start or start >= e_end):
            return True
    return False


def extract_domain_concepts(
    text: str,
    claims: list[Claim],
    named_entities: list[tuple[str, int, int]],
) -> list[tuple[str, int, int, str]]:
    """Extract domain and common concepts beyond named entities.

    Phase 2.2 heuristics:
    - Multi-word capitalized terms → domain_concept
    - Single technical words (with domain suffixes) → domain_concept
    - Multi-word noun phrases referenced by multiple claims → domain_concept
    - Other claim-referenced noun phrases → common_concept

    Returns: list of (canonical_name, start_char, end_char, concept_type)
    """
    concepts: list[tuple[str, int, int, str]] = []
    seen_spans: set[tuple[int, int]] = set()

    # Strategy 1: Multi-word capitalized terms
    for match in _CAPITALIZED_TERM_PATTERN.finditer(text):
        start = match.start()
        end = match.end()
        span_key = (start, end)
        if span_key in seen_spans:
            continue
        if _span_overlaps_entities(start, end, named_entities):
            continue

        term = match.group(0).strip()
        words = term.split()
        # Must be 2+ words, not just a sentence-initial capital
        if len(words) < 2:
            continue
        # Check if it's referenced by at least one claim
        if not any(
            _claim_references_text(c, start, end) for c in claims
        ):
            continue

        seen_spans.add(span_key)
        concepts.append((term, start, end, "domain_concept"))

    # Strategy 2: Single-word technical terms.
    # Match words of 5+ alpha chars, then filter with _is_technical_term.
    words = re.finditer(r'\b([A-Za-z][a-z]{4,})\b', text)
    for match in words:
        start = match.start()
        end = match.end()
        span_key = (start, end)
        if span_key in seen_spans:
            continue
        if _span_overlaps_entities(start, end, named_entities):
            continue

        term = match.group(0).strip()
        if not _is_technical_term(term):
            continue
        if not any(
            _claim_references_text(c, start, end) for c in claims
        ):
            continue

        seen_spans.add(span_key)
        concepts.append((term, start, end, "domain_concept"))

    # Strategy 3: Significant multi-word noun phrases
    # Extract 2-3 word phrases (non-stop-word sequences) referenced by claims
    phrase_pattern = re.compile(
        r'\b((?:[A-Za-z][a-z]+\s+){1,2}[A-Za-z][a-z]+)\b'
    )
    phrase_counts: dict[tuple[str, int, int], int] = {}
    for match in phrase_pattern.finditer(text):
        start = match.start()
        end = match.end()
        span_key = (start, end)
        if span_key in seen_spans:
            continue
        if _span_overlaps_entities(start, end, named_entities):
            continue

        phrase = match.group(0).strip()
        words_in_phrase = phrase.split()
        # Skip if any word is a stop word at the start
        if _is_stop_word(words_in_phrase[0]):
            continue
        # Skip if more than half the words are stop words
        stop_count = sum(1 for w in words_in_phrase if _is_stop_word(w))
        if stop_count >= len(words_in_phrase) / 2:
            continue
        # Must be referenced by at least one claim
        if not any(
            _claim_references_text(c, start, end) for c in claims
        ):
            continue

        if span_key not in phrase_counts:
            phrase_counts[span_key] = (start, end, phrase)

    # Keep phrases that have technical content and are claim-referenced.
    # A phrase is significant if it contains technical vocabulary or is long
    # enough to carry specific meaning (3+ content words).
    for (start, end), (s, e, phrase) in phrase_counts.items():
        span_key = (start, end)
        if span_key in seen_spans:
            continue
        # Count how many claims reference this phrase
        referencing_claims = sum(
            1 for c in claims if _claim_references_text(c, start, end)
        )
        # Include if referenced by claims AND has technical content
        if referencing_claims >= 1 and (
            any(_is_technical_term(w) for w in phrase.split())
            or len(phrase.split()) >= 3
        ):
            seen_spans.add(span_key)
            concepts.append((phrase, start, end, "domain_concept"))

    return concepts


# ---------------------------------------------------------------------------
# Concept assembly -- combining all entity types
# ---------------------------------------------------------------------------


def _claim_references_text(claim: Claim, char_start: int, char_end: int) -> bool:
    """Check if a claim's text span overlaps with a concept mention."""
    # Concept is referenced by a claim if its position overlaps with the claim's span
    return not (char_end <= claim.start_char or char_start >= claim.end_char)


def extract_concepts(
    normalized_text: NormalizedText,
    claims: list[Claim],
) -> list[Concept]:
    """Extract concepts from normalized text, filtered by claim significance.

    Phase 2.1: Named entities only (persons, organizations, locations, works).
    Each extracted entity becomes a Concept with referencing claim IDs.

    Args:
        normalized_text: The NormalizedText from A1.
        claims: The ClaimSet from A2 -- used for significance filtering.

    Returns:
        List of Concept objects (named entities only in Phase 2.1).
    """
    text = normalized_text.text

    # Phase 2.1: Extract all named entities
    persons = extract_persons(text)
    organizations = extract_organizations(text)
    locations = extract_locations(text)
    works = extract_works(text)

    # Collect named entities for overlap detection
    named_entity_spans: list[tuple[str, int, int]] = []
    named_entity_spans.extend(persons)
    named_entity_spans.extend(organizations)
    named_entity_spans.extend(locations)
    named_entity_spans.extend(works)

    # Phase 2.2: Extract domain and common concepts
    domain_concepts = extract_domain_concepts(
        text, claims, named_entity_spans,
    )

    # Build concepts
    concepts: list[Concept] = []
    concept_index = 0

    # Map entity type to concept type
    entity_groups: list[tuple[str, list[tuple[str, int, int]]]] = [
        ("named_entity_person", persons),
        ("named_entity_organization", organizations),
        ("named_entity_location", locations),
        ("named_entity_work", works),
    ]

    for concept_type, entities in entity_groups:
        for name, start, end in entities:
            # Find which claims reference this entity
            referencing_ids: list[str] = []
            for claim in claims:
                if _claim_references_text(claim, start, end):
                    referencing_ids.append(claim.id)

            # Only include if referenced by at least one claim (significance filter)
            if not referencing_ids:
                continue

            concept_index += 1
            surface_form = ConceptSurfaceForm(
                text=name,
                start_char=start,
                end_char=end,
            )

            concept = Concept(
                id=_make_concept_id(concept_index),
                canonical_name=name,
                concept_type=concept_type,
                surface_forms=(surface_form,),
                referencing_claim_ids=tuple(referencing_ids),
                domain_associations={},
                definition_provided=False,
                definition_claim_id=None,
            )
            concepts.append(concept)

    # Phase 2.2: Add domain concepts (already filtered by claim significance)
    for name, start, end, concept_type in domain_concepts:
        referencing_ids: list[str] = []
        for claim in claims:
            if _claim_references_text(claim, start, end):
                referencing_ids.append(claim.id)

        if not referencing_ids:
            continue

        concept_index += 1
        surface_form = ConceptSurfaceForm(
            text=name,
            start_char=start,
            end_char=end,
        )

        concept = Concept(
            id=_make_concept_id(concept_index),
            canonical_name=name,
            concept_type=concept_type,
            surface_forms=(surface_form,),
            referencing_claim_ids=tuple(referencing_ids),
            domain_associations={},
            definition_provided=False,
            definition_claim_id=None,
        )
        concepts.append(concept)

    # Phase 2.3: Resolve coreferences (pronouns, definite NPs)
    concepts = _resolve_coreferences(concepts, text)

    # Phase 2.4: Domain association and definition detection
    concepts = _associate_domains(concepts)
    concepts = _detect_definitions(concepts, claims)

    return concepts


# ---------------------------------------------------------------------------
# Phase 2.3: Coreference Resolution
# ---------------------------------------------------------------------------

# Third-person pronouns and their gender/number categories
_PRONOUNS_MASCULINE: frozenset[str] = frozenset({"he", "him", "his"})
_PRONOUNS_FEMININE: frozenset[str] = frozenset({"she", "her", "hers"})
_PRONOUNS_NEUTRAL: frozenset[str] = frozenset({"it", "its"})
_PRONOUNS_PLURAL: frozenset[str] = frozenset({"they", "them", "their", "theirs"})
_ALL_PRONOUNS: frozenset[str] = (
    _PRONOUNS_MASCULINE | _PRONOUNS_FEMININE | _PRONOUNS_NEUTRAL | _PRONOUNS_PLURAL
)

# Pronoun regex -- matches third-person pronouns as whole words
_PRONOUN_PATTERN = re.compile(
    r'\b(he|him|his|she|her|hers|it|its|they|them|their|theirs)\b',
    re.IGNORECASE,
)

# Definite NP pattern: "the <noun>" -- captures the head noun after "the".
# Matches single word only to avoid over-capturing verbs/adjectives.
_DEFINITE_NP_PATTERN = re.compile(
    r'\bthe\s+([A-Za-z][a-z]+)\b',
    re.IGNORECASE,
)


def _pronoun_gender(pronoun: str) -> str:
    """Return the gender/number category of a pronoun."""
    lower = pronoun.lower()
    if lower in _PRONOUNS_MASCULINE:
        return "masculine"
    if lower in _PRONOUNS_FEMININE:
        return "feminine"
    if lower in _PRONOUNS_NEUTRAL:
        return "neutral"
    return "plural"


def _concept_matches_gender(concept: Concept, gender: str) -> bool:
    """Check if a concept's type is compatible with a pronoun's gender."""
    if gender == "masculine" or gender == "feminine":
        return concept.concept_type == "named_entity_person"
    if gender == "neutral":
        # "it" → organizations, domain concepts, works
        return concept.concept_type in (
            "named_entity_organization", "domain_concept",
            "named_entity_work",
        )
    # Plural → any concept type
    return True


def _find_antecedent(
    concepts: list[Concept],
    pronoun_gender: str,
    pronoun_pos: int,
) -> Concept | None:
    """Find the nearest preceding concept that matches the pronoun's gender.

    Only considers concepts whose last surface form appears before the pronoun.
    """
    best: Concept | None = None
    best_pos = -1

    for concept in concepts:
        if not _concept_matches_gender(concept, pronoun_gender):
            continue
        # Find the latest surface form position that precedes the pronoun
        for sf in concept.surface_forms:
            if sf.end_char <= pronoun_pos and sf.start_char > best_pos:
                best = concept
                best_pos = sf.start_char

    return best


def _resolve_coreferences(
    concepts: list[Concept],
    text: str,
) -> list[Concept]:
    """Resolve pronoun and definite-NP coreferences within concepts.

    Phase 2.3: Conservative within-segment resolution.
    - Third-person pronouns → nearest matching named entity
    - Definite NPs → matching concept by canonical name

    Returns a new list of concepts with merged surface forms.
    Concept count may decrease as coreferring mentions are merged.
    """
    if not concepts:
        return concepts

    # Build mutable working copies keyed by concept id
    concept_map: dict[str, dict] = {}
    for c in concepts:
        concept_map[c.id] = {
            "canonical_name": c.canonical_name,
            "concept_type": c.concept_type,
            "surface_forms": list(c.surface_forms),
            "referencing_claim_ids": set(c.referencing_claim_ids),
        }

    # Pass 1: Pronoun resolution
    for match in _PRONOUN_PATTERN.finditer(text):
        pronoun = match.group(0)
        pronoun_pos = match.start()
        gender = _pronoun_gender(pronoun)

        antecedent = _find_antecedent(concepts, gender, pronoun_pos)
        if antecedent is None:
            continue

        # Add pronoun as a surface form of the antecedent
        sf = ConceptSurfaceForm(
            text=pronoun,
            start_char=match.start(),
            end_char=match.end(),
        )
        if antecedent.id in concept_map:
            concept_map[antecedent.id]["surface_forms"].append(sf)

    # Pass 2: Definite NP resolution via role-to-type matching.
    # "the physicist" → person, "the company" → organization, "the theory" → domain concept
    _ROLE_TO_TYPE: dict[str, str] = {
        # Person roles
        "physicist": "named_entity_person",
        "mathematician": "named_entity_person",
        "scientist": "named_entity_person",
        "researcher": "named_entity_person",
        "chemist": "named_entity_person",
        "biologist": "named_entity_person",
        "engineer": "named_entity_person",
        "professor": "named_entity_person",
        "economist": "named_entity_person",
        "philosopher": "named_entity_person",
        "historian": "named_entity_person",
        "author": "named_entity_person",
        "founder": "named_entity_person",
        "ceo": "named_entity_person",
        "leader": "named_entity_person",
        # Organization roles
        "company": "named_entity_organization",
        "corporation": "named_entity_organization",
        "organization": "named_entity_organization",
        "institution": "named_entity_organization",
        "university": "named_entity_organization",
        "firm": "named_entity_organization",
        "startup": "named_entity_organization",
        "agency": "named_entity_organization",
        "lab": "named_entity_organization",
        "laboratory": "named_entity_organization",
        # Concept roles
        "theory": "domain_concept",
        "approach": "domain_concept",
        "method": "domain_concept",
        "technique": "domain_concept",
        "algorithm": "domain_concept",
        "model": "domain_concept",
        "framework": "domain_concept",
        "phenomenon": "domain_concept",
        "principle": "domain_concept",
    }

    for match in _DEFINITE_NP_PATTERN.finditer(text):
        head_noun = match.group(1).lower()
        np_start = match.start()
        np_end = match.end()
        target_type = _ROLE_TO_TYPE.get(head_noun)

        if target_type is None:
            continue

        # Find the nearest preceding concept of the matching type
        best: Concept | None = None
        best_pos = -1
        for concept in concepts:
            if concept.concept_type != target_type:
                continue
            for sf in concept.surface_forms:
                if sf.end_char <= np_start and sf.start_char > best_pos:
                    best = concept
                    best_pos = sf.start_char

        if best is not None and best.id in concept_map:
            sf = ConceptSurfaceForm(
                text=match.group(0),
                start_char=np_start,
                end_char=np_end,
            )
            concept_map[best.id]["surface_forms"].append(sf)

    # Rebuild concepts from the map, preserving original IDs
    result: list[Concept] = []
    for c in concepts:
        if c.id not in concept_map:
            result.append(c)
            continue
        data = concept_map[c.id]
        result.append(Concept(
            id=c.id,
            canonical_name=data["canonical_name"],
            concept_type=data["concept_type"],
            surface_forms=tuple(data["surface_forms"]),
            referencing_claim_ids=tuple(data["referencing_claim_ids"]),
            domain_associations=c.domain_associations,
            definition_provided=c.definition_provided,
            definition_claim_id=c.definition_claim_id,
        ))

    return result


# ---------------------------------------------------------------------------
# Phase 2.4: Domain Association and Definition Detection
# ---------------------------------------------------------------------------

# Domain keyword mapping -- curated keywords → domain labels with weights.
# A concept's domain_associations is the union of all keywords it matches.
_DOMAIN_KEYWORDS: dict[str, dict[str, float]] = {
    # Physics
    "quantum": {"physics": 0.9},
    "entanglement": {"physics": 0.9},
    "particle": {"physics": 0.8},
    "photon": {"physics": 0.9},
    "electron": {"physics": 0.9},
    "relativity": {"physics": 0.9},
    "wave function": {"physics": 0.9},
    "superposition": {"physics": 0.9},
    "thermodynamics": {"physics": 0.9},
    "electromagnetic": {"physics": 0.9},
    "gravitational": {"physics": 0.9},
    "nuclear": {"physics": 0.8},
    "atomic": {"physics": 0.8},
    "newtonian": {"physics": 0.9},
    # Computer Science / AI
    "algorithm": {"computer_science": 0.8, "mathematics": 0.5},
    "machine learning": {"computer_science": 0.9, "artificial_intelligence": 0.9},
    "deep learning": {"computer_science": 0.9, "artificial_intelligence": 0.9},
    "neural network": {"computer_science": 0.9, "artificial_intelligence": 0.9},
    "transformer": {"computer_science": 0.8, "artificial_intelligence": 0.8},
    "artificial intelligence": {"computer_science": 0.9, "artificial_intelligence": 0.9},
    "natural language": {"computer_science": 0.8, "artificial_intelligence": 0.8},
    "programming": {"computer_science": 0.9},
    "software": {"computer_science": 0.8},
    "hardware": {"computer_science": 0.8},
    "database": {"computer_science": 0.9},
    "compiler": {"computer_science": 0.9},
    "computation": {"computer_science": 0.8, "mathematics": 0.6},
    "cryptography": {"computer_science": 0.9, "mathematics": 0.7},
    # Biology
    "dna": {"biology": 0.9},
    "rna": {"biology": 0.9},
    "protein": {"biology": 0.9},
    "gene": {"biology": 0.9},
    "genetic": {"biology": 0.9},
    "genome": {"biology": 0.9},
    "cell": {"biology": 0.7},
    "organism": {"biology": 0.8},
    "species": {"biology": 0.8},
    "evolution": {"biology": 0.8},
    "mutation": {"biology": 0.9},
    "enzyme": {"biology": 0.9},
    # Medicine
    "disease": {"medicine": 0.8},
    "diagnosis": {"medicine": 0.9},
    "treatment": {"medicine": 0.7},
    "clinical": {"medicine": 0.8},
    "patient": {"medicine": 0.8},
    "symptom": {"medicine": 0.9},
    "therapy": {"medicine": 0.8},
    "surgical": {"medicine": 0.9},
    "pharmaceutical": {"medicine": 0.9},
    "vaccine": {"medicine": 0.9},
    # Economics
    "inflation": {"economics": 0.9},
    "gdp": {"economics": 0.9},
    "market": {"economics": 0.6},
    "trade": {"economics": 0.6},
    "investment": {"economics": 0.8},
    "monetary": {"economics": 0.9},
    "fiscal": {"economics": 0.9},
    "recession": {"economics": 0.9},
    # Mathematics
    "theorem": {"mathematics": 0.9},
    "equation": {"mathematics": 0.8},
    "calculus": {"mathematics": 0.9},
    "algebra": {"mathematics": 0.9},
    "geometry": {"mathematics": 0.9},
    "topology": {"mathematics": 0.9},
    "probability": {"mathematics": 0.8},
    "statistics": {"mathematics": 0.8},
    "optimization": {"mathematics": 0.7, "computer_science": 0.6},
    # Law
    "legislation": {"law": 0.9},
    "constitutional": {"law": 0.9},
    "judicial": {"law": 0.9},
    "statute": {"law": 0.9},
    "regulation": {"law": 0.8},
    "compliance": {"law": 0.7},
    "liability": {"law": 0.9},
    "jurisdiction": {"law": 0.9},
    # Philosophy
    "ethics": {"philosophy": 0.8},
    "epistemology": {"philosophy": 0.9},
    "metaphysics": {"philosophy": 0.9},
    "consciousness": {"philosophy": 0.8},
    "existentialism": {"philosophy": 0.9},
    "stoicism": {"philosophy": 0.9},
}


def _associate_domains(concepts: list[Concept]) -> list[Concept]:
    """Associate each concept with likely domains via keyword matching.

    Phase 2.4: Keyword-based domain mapping. A concept's canonical name is
    matched against curated domain keywords. Multiple domains may be
    associated with different weights.

    Returns updated concepts with domain_associations populated.
    """
    result: list[Concept] = []
    for concept in concepts:
        domains: dict[str, float] = {}
        name_lower = concept.canonical_name.lower()

        for keyword, domain_weights in _DOMAIN_KEYWORDS.items():
            if keyword in name_lower:
                for domain, weight in domain_weights.items():
                    domains[domain] = max(domains.get(domain, 0.0), weight)

        result.append(Concept(
            id=concept.id,
            canonical_name=concept.canonical_name,
            concept_type=concept.concept_type,
            surface_forms=concept.surface_forms,
            referencing_claim_ids=concept.referencing_claim_ids,
            domain_associations=domains,
            definition_provided=concept.definition_provided,
            definition_claim_id=concept.definition_claim_id,
        ))

    return result


# Patterns for definition detection in claim text
_DEFINITION_PATTERNS = [
    re.compile(r'\b(is\s+(?:a|an|the)\s+.+)', re.IGNORECASE),
    re.compile(r'\b(refers?\s+to\s+.+)', re.IGNORECASE),
    re.compile(r'\b(is\s+defined\s+as\s+.+)', re.IGNORECASE),
    re.compile(r'\b(,\s*or\s+.+,)', re.IGNORECASE),  # Appositive: "X, or Y,"
]


def _detect_definitions(
    concepts: list[Concept],
    claims: list[Claim],
) -> list[Concept]:
    """Detect which concepts are explicitly defined in the response.

    Phase 2.4: Pattern-based definition detection. If a claim referenced
    by a concept matches a definition pattern, the concept is marked as
    having a definition provided.

    Returns updated concepts with definition_provided and definition_claim_id.
    """
    result: list[Concept] = []
    for concept in concepts:
        def_provided = False
        def_claim_id: str | None = None

        for claim_id in concept.referencing_claim_ids:
            # Find the claim text
            claim = next((c for c in claims if c.id == claim_id), None)
            if claim is None:
                continue

            claim_text = claim.text.lower()
            # Check if the claim contains a definition pattern AND
            # references the concept name
            name_lower = concept.canonical_name.lower()
            if name_lower not in claim_text:
                continue

            for pattern in _DEFINITION_PATTERNS:
                if pattern.search(claim_text):
                    def_provided = True
                    def_claim_id = claim_id
                    break

            if def_provided:
                break

        result.append(Concept(
            id=concept.id,
            canonical_name=concept.canonical_name,
            concept_type=concept.concept_type,
            surface_forms=concept.surface_forms,
            referencing_claim_ids=concept.referencing_claim_ids,
            domain_associations=concept.domain_associations,
            definition_provided=def_provided,
            definition_claim_id=def_claim_id,
        ))

    return result


# ---------------------------------------------------------------------------
# Orchestration Analyzer wrapper
# ---------------------------------------------------------------------------


class ConceptExtractorAnalyzer(Analyzer):
    """A3: Extracts concepts from text via named entity recognition.

    Input: NormalizedText from A1, ClaimSet from A2
    Output: list[Concept]
    """

    declaration = AnalyzerDeclaration(
        id="a3",
        version="0.1.0",
        responsibility="Identify significant concepts in text: named entities "
        "(persons, organizations, locations, works) and domain concepts "
        "(technical terms, multi-word phrases) with claim-based "
        "significance filtering.",
        inputs=(
            AnalyzerInput("a1", "a1", required=True),
            AnalyzerInput("a2", "a2", required=True),
        ),
        output_type=list,
        layer="foundation",
    )

    def analyze(self, context: AnalysisContext) -> dict[str, Any]:
        """Execute concept extraction.

        Reads NormalizedText from A1 and ClaimSet from A2.
        """
        a1_output = context.get_output("a1", "a1")
        if a1_output is None:
            raise AnalyzerError(
                "A3 (Concept Extractor) requires A1 (Text Normalizer) output."
            )

        a2_output = context.get_output("a2", "a2")
        if a2_output is None:
            raise AnalyzerError(
                "A3 (Concept Extractor) requires A2 (Claim Extractor) output."
            )

        normalized_text = a1_output.get("normalized_text")
        if normalized_text is None or not isinstance(normalized_text, NormalizedText):
            raise AnalyzerError("A3 requires NormalizedText from A1 output.")

        claims = a2_output.get("claims")
        if claims is None or not isinstance(claims, list):
            raise AnalyzerError("A3 requires claims list from A2 output.")

        concepts = extract_concepts(normalized_text, claims)
        return {"concepts": concepts}


def register(registry: AnalyzerRegistry) -> None:
    """Register the A3 Concept Extractor analyzer."""
    registry.register(ConceptExtractorAnalyzer.declaration, lambda: ConceptExtractorAnalyzer())
