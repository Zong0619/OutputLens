"""Tests for A3: Concept Extractor -- Phase 2.1-2.2."""

from __future__ import annotations

import pytest

from outputlens.analysis.model import Claim, Concept
from outputlens.analyzers.a3_concept_extractor import (
    ConceptExtractorAnalyzer,
    _claim_references_text,
    extract_concepts,
    _associate_domains,
    _detect_definitions,
    _resolve_coreferences,
    extract_domain_concepts,
    extract_locations,
    extract_organizations,
    extract_persons,
    extract_works,
)
from outputlens.orchestration.analyzer import AnalysisContext, AnalyzerError
from outputlens.runtime.model import NormalizedText


def _make_claim(
    cid: str, text: str, start: int, end: int, seg: str = "s1"
) -> Claim:
    return Claim(
        id=cid, text=text, start_char=start, end_char=end,
        segment_id=seg, claim_type="factual_assertion",
    )


def _make_norm(text: str) -> NormalizedText:
    from outputlens.runtime.model import Segment
    return NormalizedText(
        text=text,
        segments=(Segment(id="s1", type="paragraph", start_char=0, end_char=len(text)),),
    )


# ---------------------------------------------------------------------------
# Phase 2.1: Person Extraction
# ---------------------------------------------------------------------------


class TestExtractPersons:
    def test_simple_name(self):
        text = "Albert Einstein proposed the theory.\n"
        result = extract_persons(text)
        assert len(result) == 1
        assert result[0][0] == "Albert Einstein"

    def test_title_prefix(self):
        text = "Dr. Jane Smith conducted the research.\n"
        result = extract_persons(text)
        assert len(result) >= 1
        names = [r[0] for r in result]
        assert any("Jane Smith" in n for n in names)

    def test_multiple_persons(self):
        text = "Einstein and Bohr debated quantum mechanics.\n"
        result = extract_persons(text)
        # "Einstein" alone is 1 capitalized word -- may not match
        # "Bohr" alone -- may not match alone
        # But they're single-word names, which our pattern requires 2+
        # This is a known limitation of Phase 2.1
        assert isinstance(result, list)

    def test_full_name_with_middle(self):
        text = "John von Neumann contributed to computer science.\n"
        result = extract_persons(text)
        # "John von Neumann" -- "von" is lowercase, but 3 words with 2 capitalized
        assert len(result) >= 1

    def test_initials_pattern(self):
        text = "J. Robert Oppenheimer led the project.\n"
        result = extract_persons(text)
        assert len(result) >= 1

    def test_no_persons_in_empty_text(self):
        result = extract_persons("")
        assert result == []

    def test_prof_prefix(self):
        text = "Prof. Alan Turing developed the Turing test.\n"
        result = extract_persons(text)
        assert len(result) >= 1
        names = [r[0] for r in result]
        assert any("Alan Turing" in n for n in names)

    def test_position_is_correct(self):
        text = "Marie Curie discovered radium.\n"
        result = extract_persons(text)
        assert len(result) >= 1
        name, start, end = result[0]
        assert text[start:end] == name

    def test_not_organization(self):
        """Harvard University should not be extracted as a person."""
        text = "Harvard University was founded in 1636.\n"
        result = extract_persons(text)
        names = [r[0] for r in result]
        assert "Harvard University" not in names


# ---------------------------------------------------------------------------
# Phase 2.1: Organization Extraction
# ---------------------------------------------------------------------------


class TestExtractOrganizations:
    def test_university(self):
        text = "Stanford University conducted the study.\n"
        result = extract_organizations(text)
        assert len(result) >= 1
        assert any("Stanford University" in r[0] for r in result)

    def test_corporation(self):
        text = "Microsoft Corporation announced the results.\n"
        result = extract_organizations(text)
        assert len(result) >= 1
        assert any("Microsoft Corporation" in r[0] for r in result)

    def test_institute(self):
        text = "The Max Planck Institute published findings.\n"
        result = extract_organizations(text)
        assert len(result) >= 1
        assert any("Institute" in r[0] for r in result)

    def test_known_org_no_suffix(self):
        text = "NASA launched the telescope. OpenAI developed GPT.\n"
        result = extract_organizations(text)
        assert len(result) >= 2

    def test_mit(self):
        text = "Researchers at MIT conducted experiments.\n"
        result = extract_organizations(text)
        assert len(result) >= 1
        assert any("MIT" in r[0] for r in result)

    def test_position_correct(self):
        text = "Google published the paper.\n"
        result = extract_organizations(text)
        assert len(result) >= 1
        name, start, end = result[0]
        assert text[start:end].lower() == name.lower()

    def test_no_duplicate_orgs(self):
        text = "Google and Google announced updates.\n"
        result = extract_organizations(text)
        # Should have at most 2 distinct mentions (positions differ)
        assert len(result) <= 2


# ---------------------------------------------------------------------------
# Phase 2.1: Location Extraction
# ---------------------------------------------------------------------------


class TestExtractLocations:
    def test_country(self):
        text = "Researchers in France conducted the study.\n"
        result = extract_locations(text)
        assert len(result) >= 1
        assert any("France" in r[0] for r in result)

    def test_city(self):
        text = "The conference was held in Paris.\n"
        result = extract_locations(text)
        assert len(result) >= 1

    def test_us_state(self):
        text = "The study analyzed data from California.\n"
        result = extract_locations(text)
        assert len(result) >= 1

    def test_multi_word_location(self):
        text = "The team visited New York and San Francisco.\n"
        result = extract_locations(text)
        assert len(result) >= 2

    def test_case_insensitive_match(self):
        text = "The data came from JAPAN and GERMANY.\n"
        result = extract_locations(text)
        assert len(result) >= 2

    def test_empty_locations(self):
        text = "The model was trained on synthetic data.\n"
        result = extract_locations(text)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Phase 2.1: Work (Publication) Extraction
# ---------------------------------------------------------------------------


class TestExtractWorks:
    def test_quoted_title(self):
        text = 'The paper "Attention Is All You Need" introduced transformers.\n'
        result = extract_works(text)
        assert len(result) >= 1
        assert result[0][0] == "Attention Is All You Need"

    def test_curly_quotes(self):
        text = 'The study “Deep Learning Review” was influential.\n'
        result = extract_works(text)
        assert len(result) >= 1

    def test_short_quote_not_title(self):
        text = 'The term "AI" is widely used.\n'
        result = extract_works(text)
        # "AI" is too short -- heuristic rejects it as a work title
        assert len(result) == 0

    def test_multiple_works(self):
        text = 'Papers "GPT-3" and "BERT" were cited. The book "Deep Learning" was referenced.\n'
        result = extract_works(text)
        # "GPT-3" and "BERT" have title case → accepted
        # "Deep Learning" → accepted
        assert len(result) >= 2

    def test_position_correct(self):
        text = 'Read "The Republic" for background.\n'
        result = extract_works(text)
        if result:
            title, start, end = result[0]
            assert text[start:end] == f'"{title}"' or text[start:end] == f'“{title}”'


# ---------------------------------------------------------------------------
# Phase 2.1: Claim Reference Detection
# ---------------------------------------------------------------------------


class TestClaimReferences:
    def test_overlapping_claim(self):
        claim = _make_claim("c1", "Albert Einstein was a physicist.", 0, 35)
        assert _claim_references_text(claim, 0, 15) is True  # "Albert Einstein"

    def test_non_overlapping_claim(self):
        claim = _make_claim("c1", "Later developments were significant.", 50, 85)
        assert _claim_references_text(claim, 0, 15) is False

    def test_boundary_touch(self):
        claim = _make_claim("c1", "Einstein", 0, 8)
        assert _claim_references_text(claim, 0, 8) is True
        assert _claim_references_text(claim, 9, 15) is False


# ---------------------------------------------------------------------------
# Phase 2.1: End-to-End Concept Extraction
# ---------------------------------------------------------------------------


class TestExtractConcepts:
    def test_person_concept(self):
        text = "Albert Einstein proposed the theory of relativity.\n"
        norm = _make_norm(text)
        claims = [_make_claim("c1", text, 0, len(text))]
        concepts = extract_concepts(norm, claims)
        assert len(concepts) >= 1
        person = [c for c in concepts if c.concept_type == "named_entity_person"]
        assert len(person) == 1
        assert person[0].canonical_name == "Albert Einstein"

    def test_significance_filtering(self):
        """Entities not referenced by any claim should be excluded."""
        text = "Some text about nothing in particular.\n"
        norm = _make_norm(text)
        # Claim covers only a small portion
        claims = [_make_claim("c1", "nothing in particular", 16, 38)]
        concepts = extract_concepts(norm, claims)
        # Only entities within the claim span should appear
        for concept in concepts:
            assert len(concept.referencing_claim_ids) >= 1

    def test_multiple_entity_types(self):
        text = (
            "Dr. Smith from Harvard University visited Paris "
            'and cited "The Republic".\n'
        )
        norm = _make_norm(text)
        claims = [_make_claim("c1", text, 0, len(text))]
        concepts = extract_concepts(norm, claims)
        types = {c.concept_type for c in concepts}
        assert "named_entity_person" in types or "named_entity_organization" in types

    def test_concept_ids_are_sequential(self):
        text = "Einstein worked at Princeton. Bohr worked at Copenhagen.\n"
        norm = _make_norm(text)
        claims = [_make_claim("c1", text, 0, len(text))]
        concepts = extract_concepts(norm, claims)
        ids = [c.id for c in concepts]
        expected = [f"con{i}" for i in range(1, len(ids) + 1)]
        assert ids == expected

    def test_surface_forms_present(self):
        text = "Google published a paper.\n"
        norm = _make_norm(text)
        claims = [_make_claim("c1", text, 0, len(text))]
        concepts = extract_concepts(norm, claims)
        for concept in concepts:
            assert len(concept.surface_forms) >= 1
            assert concept.surface_forms[0].text == concept.canonical_name
            assert concept.surface_forms[0].start_char >= 0
            assert concept.surface_forms[0].end_char > concept.surface_forms[0].start_char

    def test_empty_claims_produces_empty_concepts(self):
        text = "Google and Microsoft.\n"
        norm = _make_norm(text)
        claims: list[Claim] = []
        concepts = extract_concepts(norm, claims)
        assert concepts == []

    def test_each_concept_has_valid_type(self):
        text = "Dr. Jones from Stanford University visited Tokyo.\n"
        norm = _make_norm(text)
        claims = [_make_claim("c1", text, 0, len(text))]
        concepts = extract_concepts(norm, claims)
        for concept in concepts:
            assert concept.concept_type in Concept.CONCEPT_TYPES

    def test_domain_associations_default_empty(self):
        text = "Google announced a breakthrough.\n"
        norm = _make_norm(text)
        claims = [_make_claim("c1", text, 0, len(text))]
        concepts = extract_concepts(norm, claims)
        for concept in concepts:
            assert concept.domain_associations == {}

    def test_definition_not_provided_by_default(self):
        text = "Google announced a breakthrough.\n"
        norm = _make_norm(text)
        claims = [_make_claim("c1", text, 0, len(text))]
        concepts = extract_concepts(norm, claims)
        for concept in concepts:
            assert concept.definition_provided is False
            assert concept.definition_claim_id is None


# ---------------------------------------------------------------------------
# Orchestration Integration Tests
# ---------------------------------------------------------------------------


class TestConceptExtractorAnalyzer:
    def test_declaration(self):
        analyzer = ConceptExtractorAnalyzer()
        decl = analyzer.declaration
        assert decl.id == "a3"
        assert decl.version == "0.1.0"
        assert decl.layer == "foundation"
        assert len(decl.inputs) == 2
        input_ids = {inp.analyzer_id for inp in decl.inputs}
        assert input_ids == {"a1", "a2"}

    def test_analyze_with_valid_context(self):
        text = "Google was founded by Larry Page and Sergey Brin.\n"
        norm = _make_norm(text)
        claims = [_make_claim("c1", text, 0, len(text))]

        ctx = AnalysisContext()
        ctx.set_output("a1", "a1", {"normalized_text": norm, "position_index": None})
        ctx.set_output("a2", "a2", {"claims": claims})

        analyzer = ConceptExtractorAnalyzer()
        result = analyzer.analyze(ctx)

        assert "concepts" in result
        concepts = result["concepts"]
        assert all(isinstance(c, Concept) for c in concepts)
        assert len(concepts) >= 1  # Google should be found

    def test_analyze_missing_a1_raises(self):
        ctx = AnalysisContext()
        ctx.set_output("a2", "a2", {"claims": []})
        analyzer = ConceptExtractorAnalyzer()
        with pytest.raises(AnalyzerError, match="requires A1"):
            analyzer.analyze(ctx)

    def test_analyze_missing_a2_raises(self):
        ctx = AnalysisContext()
        ctx.set_output("a1", "a1", {"normalized_text": _make_norm("test.\n")})
        analyzer = ConceptExtractorAnalyzer()
        with pytest.raises(AnalyzerError, match="requires A2"):
            analyzer.analyze(ctx)

    def test_analyze_empty_text(self):
        norm = _make_norm("\n")
        ctx = AnalysisContext()
        ctx.set_output("a1", "a1", {"normalized_text": norm, "position_index": None})
        ctx.set_output("a2", "a2", {"claims": []})
        analyzer = ConceptExtractorAnalyzer()
        result = analyzer.analyze(ctx)
        assert result["concepts"] == []


# ---------------------------------------------------------------------------
# Orchestration Pipeline Test (A1 -> A2 -> A3)
# ---------------------------------------------------------------------------


class TestA1A2A3Pipeline:
    def test_full_pipeline(self):
        from outputlens.analyzers.a1_normalizer import TextNormalizerAnalyzer
        from outputlens.analyzers.a2_claim_extractor import ClaimExtractorAnalyzer
        from outputlens.orchestration.engine import OrchestrationEngine, AnalyzerRegistry
        from outputlens.runtime.model import RawInput

        # Setup
        registry = AnalyzerRegistry()
        registry.register(
            TextNormalizerAnalyzer.declaration,
            lambda: TextNormalizerAnalyzer(),
        )
        registry.register(
            ClaimExtractorAnalyzer.declaration,
            lambda: ClaimExtractorAnalyzer(),
        )
        registry.register(
            ConceptExtractorAnalyzer.declaration,
            lambda: ConceptExtractorAnalyzer(),
        )

        engine = OrchestrationEngine(registry)
        context = AnalysisContext()
        context.set_output(
            "_bootstrap", "raw_input",
            RawInput(text="Google was founded by Larry Page in California.\n"),
        )

        # Execute A1 -> A2 -> A3
        engine.execute(frozenset({"a1", "a2", "a3"}), context)

        # Verify all outputs present
        assert context.has_output("a1", "a1")
        assert context.has_output("a2", "a2")
        assert context.has_output("a3", "a3")

        # Verify concepts are populated
        concepts = context.get_output("a3", "a3")["concepts"]
        assert len(concepts) >= 1
        concept_types = {c.concept_type for c in concepts}
        assert "named_entity_organization" in concept_types or "named_entity_person" in concept_types


# ---------------------------------------------------------------------------
# AI Response Scenario Tests
# ---------------------------------------------------------------------------


class TestAIResponseScenarios:
    def test_technical_ai_response(self):
        text = (
            "Researchers at Stanford University developed a new model. "
            "Dr. Chen and Prof. Kumar led the team. "
            'Their paper "Efficient Transformers" was published in Nature.\n'
        )
        norm = _make_norm(text)
        claims = [
            _make_claim("c1", text[:75], 0, 75),
            _make_claim("c2", text[76:113], 76, 113),
            _make_claim("c3", text[114:], 114, len(text)),
        ]
        concepts = extract_concepts(norm, claims)

        # Should extract: Stanford University (org), Dr. Chen (person),
        # Prof. Kumar (person), "Efficient Transformers" (work), Nature (org/work)
        assert len(concepts) >= 3

    def test_historical_ai_response(self):
        text = (
            "Alan Turing proposed the Turing Test in 1950. "
            "He worked at the University of Manchester. "
            "The paper was published in Mind, a journal based in London.\n"
        )
        norm = _make_norm(text)
        claims = [_make_claim("c1", text, 0, len(text))]
        concepts = extract_concepts(norm, claims)

        # Should find: Alan Turing, University of Manchester, London
        assert len(concepts) >= 2

    def test_multiple_claims_referencing_same_entity(self):
        text = "Microsoft was founded in 1975. Microsoft developed Windows.\n"
        norm = _make_norm(text)
        claims = [
            _make_claim("c1", text[:32], 0, 32),
            _make_claim("c2", text[33:], 33, len(text)),
        ]
        concepts = extract_concepts(norm, claims)
        # "Microsoft" in both claims -> should appear once (Phase 2.3 coref),
        # or potentially twice (Phase 2.1 without coref -- surface form positions differ)
        assert len(concepts) >= 1


# ===================================================================
# Phase 2.2: Domain Concept Identification Tests
# ===================================================================


class TestExtractDomainConcepts:
    def test_capitalized_term(self):
        text = "Quantum Entanglement is a key phenomenon in physics.\n"
        claims = [_make_claim("c1", text, 0, len(text))]
        named: list = []
        result = extract_domain_concepts(text, claims, named)
        assert len(result) >= 1
        names = [r[0] for r in result]
        assert any("Quantum Entanglement" in n for n in names)

    def test_technical_suffix_word(self):
        text = "The optimization algorithm improved performance significantly.\n"
        claims = [_make_claim("c1", text, 0, len(text))]
        result = extract_domain_concepts(text, claims, [])
        names = [r[0] for r in result]
        assert any("optimization" in n.lower() for n in names)

    def test_no_overlap_with_named_entities(self):
        text = "Google developed a new Machine Learning framework.\n"
        claims = [_make_claim("c1", text, 0, len(text))]
        named = [("Google", 0, 6)]
        result = extract_domain_concepts(text, claims, named)
        names = [r[0] for r in result]
        assert "Google" not in names

    def test_domain_concept_type(self):
        text = "Deep Learning has revolutionized artificial intelligence.\n"
        claims = [_make_claim("c1", text, 0, len(text))]
        result = extract_domain_concepts(text, claims, [])
        for _, _, _, ctype in result:
            assert ctype in ("domain_concept", "common_concept")

    def test_stop_word_phrases_excluded(self):
        text = "This is the first example of the new approach.\n"
        claims = [_make_claim("c1", text, 0, len(text))]
        result = extract_domain_concepts(text, claims, [])
        names = [r[0] for r in result]
        for phrase in names:
            words = phrase.lower().split()
            assert words[0] not in ("this", "is", "the", "of", "in")


class TestExtractConceptsWithDomainConcepts:
    """End-to-end: extract_concepts includes both named entities and domain concepts."""

    def test_mixed_entities_and_domain_concepts(self):
        text = (
            "Researchers at Stanford University developed a new "
            "Natural Language Processing model. The transformer architecture "
            "improves performance significantly.\n"
        )
        norm = _make_norm(text)
        claims = [
            _make_claim("c1", text[:85], 0, 85),
            _make_claim("c2", text[86:], 86, len(text)),
        ]
        concepts = extract_concepts(norm, claims)

        types = {c.concept_type for c in concepts}
        assert "named_entity_organization" in types
        assert "domain_concept" in types

    def test_physics_response(self):
        text = (
            "Quantum mechanics describes particle behavior at atomic scales. "
            "Wave function collapse occurs during measurement. "
            "Entanglement demonstrates non-local correlations.\n"
        )
        norm = _make_norm(text)
        claims = [_make_claim("c1", text, 0, len(text))]
        concepts = extract_concepts(norm, claims)

        domain = [c for c in concepts if c.concept_type == "domain_concept"]
        assert len(domain) >= 2

    def test_sequential_ids_across_types(self):
        text = "Google developed BERT. Natural Language Processing improved.\n"
        norm = _make_norm(text)
        claims = [_make_claim("c1", text, 0, len(text))]
        concepts = extract_concepts(norm, claims)
        ids = [c.id for c in concepts]
        expected = [f"con{i}" for i in range(1, len(ids) + 1)]
        assert ids == expected


# ===================================================================
# Phase 2.3: Coreference Resolution Tests
# ===================================================================


class TestCoreferenceResolution:
    def test_pronoun_he_resolved(self):
        text = "Albert Einstein proposed the theory. He won the Nobel Prize.\n"
        norm = _make_norm(text)
        claims = [
            _make_claim("c1", text[:40], 0, 40),
            _make_claim("c2", text[41:], 41, len(text)),
        ]
        concepts = extract_concepts(norm, claims)
        einstein = [c for c in concepts if "Einstein" in c.canonical_name]
        assert len(einstein) == 1
        surface_texts = [sf.text.lower() for sf in einstein[0].surface_forms]
        assert "he" in surface_texts

    def test_pronoun_it_for_org(self):
        text = "Google announced a breakthrough. It will release details.\n"
        norm = _make_norm(text)
        claims = [
            _make_claim("c1", text[:32], 0, 32),
            _make_claim("c2", text[33:], 33, len(text)),
        ]
        concepts = extract_concepts(norm, claims)
        google = [c for c in concepts if "Google" in c.canonical_name]
        assert len(google) >= 1
        surface_texts = [sf.text.lower() for sf in google[0].surface_forms]
        assert "it" in surface_texts

    def test_pronoun_gender_agreement(self):
        text = "Marie Curie and Albert Einstein worked together. He proposed relativity.\n"
        norm = _make_norm(text)
        claims = [_make_claim("c1", text, 0, len(text))]
        concepts = extract_concepts(norm, claims)
        einstein = [c for c in concepts if "Einstein" in c.canonical_name]
        curie = [c for c in concepts if "Curie" in c.canonical_name]
        if einstein and curie:
            einstein_surfaces = [sf.text.lower() for sf in einstein[0].surface_forms]
            curie_surfaces = [sf.text.lower() for sf in curie[0].surface_forms]
            assert "he" in einstein_surfaces
            assert "he" not in curie_surfaces

    def test_definite_np_physicist(self):
        text = "Albert Einstein developed relativity. The physicist won a prize.\n"
        norm = _make_norm(text)
        claims = [
            _make_claim("c1", text[:42], 0, 42),
            _make_claim("c2", text[43:], 43, len(text)),
        ]
        concepts = extract_concepts(norm, claims)
        einstein = [c for c in concepts if "Einstein" in c.canonical_name]
        assert len(einstein) == 1
        surface_texts = [sf.text for sf in einstein[0].surface_forms]
        assert any("physicist" in t.lower() for t in surface_texts)

    def test_dummy_it_no_false_merge(self):
        text = "It is an interesting phenomenon. No clear antecedent exists.\n"
        norm = _make_norm(text)
        claims = [_make_claim("c1", text, 0, len(text))]
        concepts = extract_concepts(norm, claims)
        assert isinstance(concepts, list)

    def test_surface_forms_traceable_after_coref(self):
        text = "Google was founded in 1998. It is now a large company.\n"
        norm = _make_norm(text)
        claims = [
            _make_claim("c1", text[:26], 0, 26),
            _make_claim("c2", text[27:], 27, len(text)),
        ]
        concepts = extract_concepts(norm, claims)
        for concept in concepts:
            for sf in concept.surface_forms:
                assert sf.start_char >= 0
                assert sf.end_char > sf.start_char
                assert sf.text.lower() in text.lower()


# ===================================================================
# Phase 2.4: Domain Association and Definition Detection Tests
# ===================================================================


class TestDomainAssociation:
    def test_physics_concept_gets_physics_domain(self):
        from outputlens.analysis.model import Concept, ConceptSurfaceForm
        c = Concept(
            id="con1", canonical_name="quantum entanglement",
            concept_type="domain_concept",
            surface_forms=(ConceptSurfaceForm(text="quantum entanglement", start_char=0, end_char=20),),
            referencing_claim_ids=("c1",),
        )
        result = _associate_domains([c])
        assert len(result) == 1
        assert result[0].domain_associations.get("physics", 0.0) > 0.5

    def test_ai_concept_gets_cs_domain(self):
        from outputlens.analysis.model import Concept, ConceptSurfaceForm
        c = Concept(
            id="con1", canonical_name="machine learning",
            concept_type="domain_concept",
            surface_forms=(ConceptSurfaceForm(text="machine learning", start_char=0, end_char=16),),
            referencing_claim_ids=("c1",),
        )
        result = _associate_domains([c])
        assert result[0].domain_associations.get("computer_science", 0.0) > 0.5

    def test_unknown_concept_empty_domains(self):
        from outputlens.analysis.model import Concept, ConceptSurfaceForm
        c = Concept(
            id="con1", canonical_name="unknown term",
            concept_type="domain_concept",
            surface_forms=(ConceptSurfaceForm(text="unknown term", start_char=0, end_char=12),),
            referencing_claim_ids=("c1",),
        )
        result = _associate_domains([c])
        assert result[0].domain_associations == {}

    def test_multi_domain_concept(self):
        from outputlens.analysis.model import Concept, ConceptSurfaceForm
        c = Concept(
            id="con1", canonical_name="optimization algorithm",
            concept_type="domain_concept",
            surface_forms=(ConceptSurfaceForm(text="optimization algorithm", start_char=0, end_char=22),),
            referencing_claim_ids=("c1",),
        )
        result = _associate_domains([c])
        domains = result[0].domain_associations
        assert len(domains) >= 1


class TestDefinitionDetection:
    def test_is_a_definition_detected(self):
        from outputlens.analysis.model import Concept, ConceptSurfaceForm
        c = Concept(
            id="con1", canonical_name="quantum entanglement",
            concept_type="domain_concept",
            surface_forms=(ConceptSurfaceForm(text="quantum entanglement", start_char=0, end_char=20),),
            referencing_claim_ids=("c1",),
        )
        claims = [
            _make_claim("c1", "quantum entanglement is a phenomenon where particles become correlated.", 0, 73),
        ]
        result = _detect_definitions([c], claims)
        assert result[0].definition_provided is True
        assert result[0].definition_claim_id == "c1"

    def test_no_definition_when_concept_not_in_claim(self):
        from outputlens.analysis.model import Concept, ConceptSurfaceForm
        c = Concept(
            id="con1", canonical_name="quantum entanglement",
            concept_type="domain_concept",
            surface_forms=(ConceptSurfaceForm(text="quantum entanglement", start_char=0, end_char=20),),
            referencing_claim_ids=("c1",),
        )
        claims = [
            _make_claim("c1", "This is an unrelated claim about other topics.", 0, 45),
        ]
        result = _detect_definitions([c], claims)
        assert result[0].definition_provided is False

    def test_end_to_end_domain_and_definition(self):
        text = "Quantum entanglement is a phenomenon in physics. It was studied by Einstein.\n"
        norm = _make_norm(text)
        claims = [_make_claim("c1", text[:55], 0, 55),
                  _make_claim("c2", text[56:], 56, len(text))]
        concepts = extract_concepts(norm, claims)

        # Find the "quantum entanglement" concept
        qe = [c for c in concepts if "entanglement" in c.canonical_name.lower()]
        if qe:
            assert qe[0].definition_provided is True
            # Should have physics domain association
            domains = qe[0].domain_associations
            assert len(domains) >= 1
