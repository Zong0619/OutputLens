"""OutputLens REST API -- reference HTTP interface.

Thin transport layer over the analysis engine. Per M7-001: rendering layer
only. No analytical logic.

Usage:
    pip install outputlens[api]
    python -m outputlens.interfaces.api
    # or: outputlens serve

Endpoint:
    POST /analyze  -- JSON body {"text": "..."} → AnalysisDocument JSON
    GET /health     -- Health check
"""

from __future__ import annotations

import json
import sys
from typing import Any

from outputlens.interfaces.engine_runner import run_analysis


def create_app() -> Any:
    """Create the Flask application. Returns None if Flask is not installed."""
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        return None

    app = Flask(__name__)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "engine_version": "0.1.0"})

    @app.route("/analyze", methods=["POST"])
    def analyze():
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data: dict[str, Any] = request.get_json(silent=True) or {}
        text = data.get("text", "")

        if not text or not text.strip():
            return jsonify({"error": "Field 'text' is required and must not be empty"}), 400

        # Optional parameters
        prompt = data.get("prompt")
        model = data.get("model")
        domain = data.get("domain")

        # Optional analyzer subset
        analyzer_list = data.get("analyzers")
        analyzers: frozenset[str] | None = None
        if analyzer_list and isinstance(analyzer_list, list):
            analyzers = frozenset(str(a) for a in analyzer_list)

        try:
            doc = run_analysis(
                text=text,
                prompt=prompt,
                model=model,
                domain=domain,
                analyzers=analyzers,
            )
            return jsonify(doc.to_dict())

        except Exception as e:
            return jsonify({"error": f"Analysis failed: {e}"}), 500

    # Serve the web demo at the root path
    import os
    web_dir = os.path.join(os.path.dirname(__file__), "web")

    @app.route("/")
    def index():
        return __import__("flask").send_from_directory(web_dir, "index.html")

    @app.route("/<path:filename>")
    def static_files(filename):
        from flask import send_from_directory
        path = os.path.join(web_dir, filename)
        if os.path.isfile(path):
            return send_from_directory(web_dir, filename)
        return jsonify({"error": "Not found"}), 404

    # CORS support for web demo
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
        return response

    return app


def main() -> None:
    """Entry point: start the API server."""
    app = create_app()
    if app is None:
        print(
            "Error: Flask is required for the API server.\n"
            "Install with: pip install outputlens[api]",
            file=sys.stderr,
        )
        sys.exit(1)

    import argparse
    parser = argparse.ArgumentParser(description="OutputLens API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    print(f"OutputLens API server starting on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
