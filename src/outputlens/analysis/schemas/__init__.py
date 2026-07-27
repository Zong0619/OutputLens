"""JSON Schema loading and validation for the AnalysisDocument."""

import json
from pathlib import Path
from typing import Any

_SCHEMA_DIR = Path(__file__).parent
_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}


def load_schema(version: str = "1.0.0") -> dict[str, Any]:
    """Load an AnalysisDocument JSON Schema by version.

    Args:
        version: Schema version string (e.g., "1.0.0").

    Returns:
        The JSON Schema as a Python dict.

    Raises:
        FileNotFoundError: If the schema version does not exist.
    """
    if version in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[version]

    schema_path = _SCHEMA_DIR / f"analysis_document_v{version.split('.')[0]}.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema version {version} not found at {schema_path}")

    with open(schema_path) as f:
        schema = json.load(f)

    _SCHEMA_CACHE[version] = schema
    return schema


def get_current_schema() -> dict[str, Any]:
    """Get the current (latest) AnalysisDocument JSON Schema."""
    return load_schema("1.0.0")
