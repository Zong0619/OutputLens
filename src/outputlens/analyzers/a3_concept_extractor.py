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

    # Extract all named entities
    persons = extract_persons(text)
    organizations = extract_organizations(text)
    locations = extract_locations(text)
    works = extract_works(text)

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

    return concepts


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
        "(persons, organizations, locations, works) with claim-based "
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
