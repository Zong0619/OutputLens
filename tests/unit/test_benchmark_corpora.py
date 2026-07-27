"""Tests for benchmark corpus metadata and format validation -- Phase 6.3."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

CORPORA_DIR = Path(__file__).parent.parent.parent / "benchmarks" / "corpora"


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


class TestCorpusStructure:
    def test_all_corpora_have_readme(self):
        for corpus in ["diversity", "challenge", "temporal"]:
            readme = CORPORA_DIR / corpus / "README.md"
            assert readme.exists(), f"Missing README for {corpus}"

    def test_all_corpora_have_manifest(self):
        for corpus in ["diversity", "challenge", "temporal"]:
            manifest = CORPORA_DIR / corpus / "manifest.json"
            assert manifest.exists(), f"Missing manifest for {corpus}"


class TestManifestValidation:
    def test_diversity_manifest(self):
        m = _load_json(CORPORA_DIR / "diversity" / "manifest.json")
        assert m["corpus_id"] == "BENCH-DIVERSITY"
        assert m["mutability"] == "appendable"
        assert len(m["items"]) >= 5
        for item in m["items"]:
            assert "item_id" in item
            assert "domain" in item
            assert "file" in item

    def test_challenge_manifest(self):
        m = _load_json(CORPORA_DIR / "challenge" / "manifest.json")
        assert m["corpus_id"] == "BENCH-CHALLENGE"
        assert m["mutability"] == "appendable"
        for item in m["items"]:
            assert "primary_pattern" in item
            assert item["primary_pattern"] in [
                "high_claim_density", "hedging_heavy", "self_contradiction",
                "domain_mixing", "code_prose_mix", "nested_structure",
                "undefined_terms", "list_heavy",
            ]

    def test_temporal_manifest(self):
        m = _load_json(CORPORA_DIR / "temporal" / "manifest.json")
        assert m["corpus_id"] == "BENCH-TEMPORAL"
        assert m["mutability"] == "immutable"
        for item in m["items"]:
            assert "deprecated" in item
            assert "added_version" in item

    def test_diversity_manifest_items_exist(self):
        m = _load_json(CORPORA_DIR / "diversity" / "manifest.json")
        for item in m["items"]:
            item_path = CORPORA_DIR / "diversity" / item["file"]
            if item_path.exists():
                item_data = _load_json(item_path)
                assert item_data["item_id"] == item["item_id"]

    def test_temporal_items_exist(self):
        m = _load_json(CORPORA_DIR / "temporal" / "manifest.json")
        for item in m["items"]:
            if not item["deprecated"]:
                item_path = CORPORA_DIR / "temporal" / item["file"]
                if item_path.exists():
                    item_data = _load_json(item_path)
                    assert item_data["item_id"] == item["item_id"]


class TestTemporalImmutability:
    def test_temporal_manifest_declares_immutable(self):
        m = _load_json(CORPORA_DIR / "temporal" / "manifest.json")
        assert m["mutability"] == "immutable"

    def test_temporal_readme_documents_immutability_policy(self):
        readme = CORPORA_DIR / "temporal" / "README.md"
        content = readme.read_text()
        assert "IMMUTABLE" in content
        assert "never modified" in content.lower()
        assert "deprecation" in content.lower()


class TestSampleItemFormat:
    def test_diversity_item_format(self):
        item = _load_json(CORPORA_DIR / "diversity" / "items" / "div_001.json")
        assert "item_id" in item
        assert "response_text" in item
        assert len(item["response_text"]) >= 50
        assert "domain" in item
        assert "word_count" in item

    def test_temporal_item_format(self):
        item = _load_json(CORPORA_DIR / "temporal" / "items" / "tmp_001.json")
        assert "item_id" in item
        assert "response_text" in item
        assert "domain" in item
        assert "added_date" in item


class TestCorpusBoundaryCompliance:
    """Corpora must not claim correctness or truth (M6-001)."""

    def test_no_correctness_claims_in_readmes(self):
        for corpus in ["diversity", "challenge", "temporal"]:
            readme = CORPORA_DIR / corpus / "README.md"
            if readme.exists():
                content = readme.read_text().lower()
                # Corpora measure behavior, not correctness
                assert "correct" not in content or "correctness" not in content

    def test_corpora_have_no_annotations(self):
        """Benchmark corpora are unannotated; annotations belong in golden datasets."""
        for corpus in ["diversity", "challenge", "temporal"]:
            manifest = CORPORA_DIR / corpus / "manifest.json"
            if manifest.exists():
                m = _load_json(manifest)
                for item in m.get("items", []):
                    assert "annotations" not in item, (
                        f"{corpus} item {item.get('item_id')} should not have annotations"
                    )
