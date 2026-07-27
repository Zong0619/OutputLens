"""AnalysisDocument and golden dataset loading with validation.

Loads serialized JSON documents. Implementation-agnostic -- does not
depend on the Python reference implementation's internal objects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_analysis_document(path: str | Path) -> dict[str, Any]:
    """Load and validate an AnalysisDocument from a JSON file.

    Args:
        path: Path to the AnalysisDocument JSON file.

    Returns:
        The parsed AnalysisDocument as a dict.

    Raises:
        ValueError: If the document fails schema validation.
        FileNotFoundError: If the path does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with open(path) as f:
        doc = json.load(f)

    errors = validate_analysis_document(doc)
    if errors:
        raise ValueError(
            f"Invalid AnalysisDocument at {path}:\n" + "\n".join(f"  - {e}" for e in errors)
        )
    return doc


def validate_analysis_document(doc: dict[str, Any]) -> list[str]:
    """Validate an AnalysisDocument against structural invariants.

    Checks required fields, schema version, and cross-reference integrity.
    Does NOT check classification accuracy -- that's what evaluation measures.
    """
    errors: list[str] = []

    if "schema_version" not in doc:
        errors.append("Missing required field: schema_version")
    elif doc["schema_version"] != "1.0.0":
        errors.append(f"Unsupported schema version: {doc['schema_version']}")

    if "metadata" not in doc:
        errors.append("Missing required field: metadata")

    if "analysis_objects" not in doc:
        errors.append("Missing required field: analysis_objects")
    else:
        ao = doc["analysis_objects"]
        if "claims" not in ao or not isinstance(ao["claims"], list):
            errors.append("analysis_objects.claims must be a non-empty list")

    return errors


def load_golden_dataset(path: str | Path) -> dict[str, Any]:
    """Load a golden dataset from a JSON file.

    Args:
        path: Path to the golden dataset JSON file.

    Returns:
        The parsed dataset dict with dataset_id, version, items, etc.
    """
    with open(path) as f:
        dataset = json.load(f)

    if "dataset_id" not in dataset:
        raise ValueError("Golden dataset missing dataset_id")
    if "version" not in dataset:
        raise ValueError("Golden dataset missing version")
    if "items" not in dataset:
        raise ValueError("Golden dataset missing items array")

    return dataset


def get_claims(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract claims from an AnalysisDocument."""
    return doc.get("analysis_objects", {}).get("claims", [])


def get_annotations(doc: dict[str, Any], annotation_key: str) -> list[dict[str, Any]]:
    """Extract annotations from an AnalysisDocument by key."""
    return doc.get("analysis_objects", {}).get(annotation_key, [])


def get_synthesis(doc: dict[str, Any], key: str) -> dict[str, Any] | None:
    """Extract a synthesis object from an AnalysisDocument."""
    return doc.get("analysis_objects", {}).get(key)
