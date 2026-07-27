"""Tests for the CLI interface -- Phase 7.1."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def _run_cli(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess:
    """Run the outputlens CLI and return the result."""
    cmd = [sys.executable, "-m", "outputlens.interfaces.cli", "analyze", *args]
    return subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=30,
        env={**__import__("os").environ, "PYTHONPATH": "src"},
    )


class TestCLIBasic:
    def test_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "outputlens.interfaces.cli", "--help"],
            capture_output=True, text=True, timeout=10,
            env={**__import__("os").environ, "PYTHONPATH": "src"},
        )
        assert result.returncode == 0
        assert "analyze" in result.stdout

    def test_text_flag(self):
        result = _run_cli("--text", "AI is transforming society. It has limitations.")
        assert result.returncode == 0
        assert "OUTPUTLENS ANALYSIS" in result.stdout

    def test_json_output(self):
        result = _run_cli("--text", "Water freezes at 0 degrees Celsius.", "--json")
        assert result.returncode == 0
        doc = json.loads(result.stdout)
        assert doc["schema_version"] == "1.0.0"
        assert len(doc["analysis_objects"]["claims"]) >= 1

    def test_summary_output(self):
        result = _run_cli("--text", "AI is powerful, but it has limitations.", "--summary")
        assert result.returncode == 0
        assert "Trust Profile" in result.stdout

    def test_claims_output(self):
        result = _run_cli("--text", "First claim. Second claim.", "--claims")
        assert result.returncode == 0
        assert "c1" in result.stdout
        assert "c2" in result.stdout

    def test_stdin_input(self):
        result = _run_cli(input_text="AI is a technology. It evolves rapidly.")
        assert result.returncode == 0
        assert "OUTPUTLENS ANALYSIS" in result.stdout

    def test_file_input(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Quantum computing uses qubits. It promises speedups.")
            tmp = f.name
        try:
            result = _run_cli("--file", tmp)
            assert result.returncode == 0
            assert "OUTPUTLENS ANALYSIS" in result.stdout
        finally:
            Path(tmp).unlink()

    def test_empty_input_errors(self):
        result = _run_cli("--text", "   ")
        assert result.returncode == 2

    def test_file_not_found_errors(self):
        result = _run_cli("--file", "/nonexistent/path.txt")
        assert result.returncode == 2

    def test_prompt_flag(self):
        result = _run_cli("--text", "AI is useful.", "--prompt", "Is AI useful?")
        assert result.returncode == 0

    def test_model_flag(self):
        result = _run_cli("--text", "AI is useful.", "--model", "claude-opus-4-8")
        assert result.returncode == 0

    def test_json_output_is_valid(self):
        result = _run_cli("--text", "A test claim.", "--json")
        doc = json.loads(result.stdout)
        assert "metadata" in doc
        assert "runtime_objects" in doc
        assert "analysis_objects" in doc
        assert len(doc["analysis_objects"]["claims"]) >= 1

    def test_caveat_in_summary(self):
        result = _run_cli("--text", "Test.", "--summary")
        assert "not a reliability score" in result.stdout.lower()


class TestCLIInterfaceBoundary:
    """Per M7-001: CLI is a rendering layer. No analytical logic."""

    def test_cli_does_not_contain_classification(self):
        """CLI module must not import classification functions."""
        cli_source = Path(__file__).parent.parent.parent / "src" / "outputlens" / "interfaces" / "cli.py"
        content = cli_source.read_text()
        # CLI may import analyzers for registration, but must not call
        # classification functions directly
        assert "classify_evidence" not in content
        assert "classify_establishedness" not in content
        assert "classify_novelty" not in content
