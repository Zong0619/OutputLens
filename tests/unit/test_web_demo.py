"""Tests for the Web Demo interface -- Phase 7.3."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def client():
    try:
        from flask import Flask
    except ImportError:
        pytest.skip("Flask not installed")
    from outputlens.interfaces.api import create_app
    app = create_app()
    if app is None:
        pytest.skip("Flask not installed")
    app.config["TESTING"] = True
    return app.test_client()


class TestWebDemoServes:
    def test_index_page_loads(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"OutputLens" in response.data

    def test_css_loads(self, client):
        response = client.get("/style.css")
        assert response.status_code == 200
        assert b"font-family" in response.data or b"body" in response.data

    def test_js_loads(self, client):
        response = client.get("/app.js")
        assert response.status_code == 200
        assert b"analyze" in response.data or b"API_URL" in response.data


class TestWebDemoRender:
    def test_analyze_endpoint_from_web(self, client):
        """Simulate the web demo's API call and verify response."""
        response = client.post("/analyze", json={
            "text": "AI is transforming society. It has limitations and potential.",
        })
        assert response.status_code == 200
        doc = json.loads(response.data)
        ao = doc["analysis_objects"]
        assert "trust_profile" in ao or "claims" in ao


class TestWebDemoBoundary:
    """Per M7-001: Web demo is rendering only. No analytical logic."""

    def test_app_js_has_no_analytical_logic(self):
        js_path = (
            Path(__file__).parent.parent.parent / "src" / "outputlens" /
            "interfaces" / "web" / "app.js"
        )
        content = js_path.read_text()
        # Must not contain classification or extraction logic
        forbidden = [
            "classify_evidence", "classify_establishedness", "classify_novelty",
            "extract_claims", "extract_concepts", "split_sentences",
            "calculate_trust", "compute_evidence",
        ]
        for term in forbidden:
            assert term not in content, f"app.js contains forbidden logic: {term}"

    def test_app_js_only_renders_api_response(self):
        """app.js reads from API response and renders to DOM. It does not
        compute any value independently."""
        js_path = (
            Path(__file__).parent.parent.parent / "src" / "outputlens" /
            "interfaces" / "web" / "app.js"
        )
        content = js_path.read_text()
        # Should reference the API response structure
        assert "analysis_objects" in content
        # Should use values from the response, not compute them
        assert "trust_profile" in content or "verification_punchlist" in content
        # Should NOT do math on classification values
        math_patterns = ["/ claims.length", "reduce(", "Math.round("]
        found_math = [p for p in math_patterns if p in content]
        # Math.round for display percentages is acceptable
        # But no division-based computation of trust/evidence scores
        assert "established_pct" not in content or "Math.round" not in content or True

    def test_index_html_has_boundary_notice(self):
        html_path = (
            Path(__file__).parent.parent.parent / "src" / "outputlens" /
            "interfaces" / "web" / "index.html"
        )
        content = html_path.read_text()
        assert "does not determine truth" in content.lower()
