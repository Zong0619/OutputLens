"""Documentation consistency and link validation tests."""

from __future__ import annotations

from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent.parent / "docs"


class TestDocumentationExists:
    def test_all_required_docs_present(self):
        required = [
            "PROJECT_CONTEXT.md", "PROJECT_STATE.md", "ARCHITECTURE.md",
            "IMPLEMENTATION_GUIDE.md", "IMPLEMENTATION_DECISIONS.md",
            "DEVELOPMENT_WORKFLOW.md", "ROADMAP.md",
            "ANALYZER_DEVELOPMENT.md", "INTERFACE_DEVELOPMENT.md",
            "EVALUATION_GUIDE.md", "CONTRIBUTOR_GUIDE.md",
        ]
        for doc in required:
            assert (DOCS_DIR / doc).exists(), f"Missing required doc: {doc}"

    def test_readme_exists(self):
        assert (Path(__file__).parent.parent.parent / "README.md").exists()

    def test_contributing_exists(self):
        assert (Path(__file__).parent.parent.parent / "CONTRIBUTING.md").exists()


class TestDocumentationBoundary:
    def test_analyzer_dev_doc_preserves_knowledge_boundary(self):
        content = (DOCS_DIR / "ANALYZER_DEVELOPMENT.md").read_text()
        assert "knowledge-agnostic" in content.lower() or "external knowledge" in content.lower()

    def test_interface_dev_doc_preserves_rendering_boundary(self):
        content = (DOCS_DIR / "INTERFACE_DEVELOPMENT.md").read_text()
        assert "do not perform analysis" in content.lower() or "not allowed" in content.lower()

    def test_evaluation_guide_preserves_m6_001(self):
        content = (DOCS_DIR / "EVALUATION_GUIDE.md").read_text()
        assert "does not define correctness" in content.lower()

    def test_contributor_guide_references_workflow(self):
        content = (DOCS_DIR / "CONTRIBUTOR_GUIDE.md").read_text()
        assert "DEVELOPMENT_WORKFLOW.md" in content
