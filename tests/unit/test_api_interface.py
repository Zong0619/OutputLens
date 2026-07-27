"""Tests for the REST API interface -- Phase 7.2."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def client():
    """Create a Flask test client for the API."""
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


class TestAPIHealth:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ok"

    def test_health_has_engine_version(self, client):
        response = client.get("/health")
        data = json.loads(response.data)
        assert "engine_version" in data


class TestAPIAnalyze:
    def test_valid_request(self, client):
        response = client.post(
            "/analyze",
            json={"text": "AI is transforming society. It has limitations."},
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["schema_version"] == "1.0.0"
        assert len(data["analysis_objects"]["claims"]) >= 1

    def test_missing_text(self, client):
        response = client.post("/analyze", json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_empty_text(self, client):
        response = client.post("/analyze", json={"text": "   "})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_non_json_request(self, client):
        response = client.post("/analyze", data="not json")
        assert response.status_code == 400

    def test_with_prompt(self, client):
        response = client.post("/analyze", json={
            "text": "Water freezes at 0 degrees Celsius.",
            "prompt": "What is the freezing point of water?",
        })
        assert response.status_code == 200

    def test_with_model(self, client):
        response = client.post("/analyze", json={
            "text": "AI is useful.",
            "model": "claude-opus-4-8",
        })
        assert response.status_code == 200

    def test_json_structure_matches_schema(self, client):
        response = client.post("/analyze", json={"text": "A test claim."})
        doc = json.loads(response.data)
        assert "metadata" in doc
        assert "runtime_objects" in doc
        assert "analysis_objects" in doc
        assert "claims" in doc["analysis_objects"]

    def test_cors_headers(self, client):
        response = client.post("/analyze", json={"text": "Test."})
        assert "Access-Control-Allow-Origin" in response.headers

    def test_analyzer_subset(self, client):
        response = client.post("/analyze", json={
            "text": "A simple test claim for subset analysis.",
            "analyzers": ["a1", "a2"],
        })
        assert response.status_code == 200
        doc = json.loads(response.data)
        assert len(doc["analysis_objects"]["claims"]) >= 1

    def test_response_is_valid_analysis_document(self, client):
        response = client.post("/analyze", json={
            "text": "Quantum entanglement is a physical phenomenon. "
                   "According to Bell's theorem, it demonstrates non-locality.",
        })
        doc = json.loads(response.data)
        claims = doc["analysis_objects"]["claims"]
        assert len(claims) >= 1
        # Each claim should have required fields
        for claim in claims:
            assert "id" in claim
            assert "text" in claim
            assert "start_char" in claim


class TestAPIBoundary:
    """Per M7-001: API is a transport layer. No analytical logic."""

    def test_api_does_not_contain_classification(self):
        api_source = (
            Path(__file__).parent.parent.parent / "src" / "outputlens" /
            "interfaces" / "api.py"
        )
        content = api_source.read_text()
        assert "classify_evidence" not in content
        assert "classify_establishedness" not in content
        assert "classify_novelty" not in content
        assert "extract_claims" not in content
        assert "extract_concepts" not in content

    def test_api_uses_engine_runner(self):
        api_source = (
            Path(__file__).parent.parent.parent / "src" / "outputlens" /
            "interfaces" / "api.py"
        )
        content = api_source.read_text()
        assert "run_analysis" in content
        assert "from outputlens.interfaces.engine_runner" in content
