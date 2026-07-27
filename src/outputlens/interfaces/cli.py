"""OutputLens CLI -- reference command-line interface.

Consumes the analysis engine via AnalysisDocument. Per M7-001: rendering
layer only. No analytical logic.

Usage:
    outputlens analyze --text "AI response text..."
    echo "AI response..." | outputlens analyze
    outputlens analyze --file response.txt --summary
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from outputlens.analysis.document import AnalysisDocument
from outputlens.interfaces.engine_runner import run_analysis


def _format_summary(doc: AnalysisDocument) -> str:
    """Format a human-readable summary from an AnalysisDocument.

    Per M7-001: Rendering only. No analytical logic.
    """
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("OUTPUTLENS ANALYSIS")
    lines.append("=" * 60)

    # Trust Profile
    tp = doc.trust_profile
    if tp:
        lines.append(f"\nTrust Profile:")
        lines.append(f"  Established:        {tp.established_pct:5.1f}%")
        lines.append(f"  Plausible/Inferred: {tp.plausible_pct:5.1f}%")
        lines.append(f"  Needs Verification: {tp.needs_verification_pct:5.1f}%")
        lines.append(f"  ({TrustProfile_caveat()})")

    # Evidence Gap
    eg = doc.evidence_gap_report
    if eg:
        lines.append(f"\nEvidence Gap: {eg.gap_ratio:.0%} of claims lack supporting evidence")
        lines.append(f"  R3 (Expected but missing): {eg.r3_count}")
        lines.append(f"  R4 (Essential but absent): {eg.r4_count}")

    # Narrative
    narr = doc.response_narrative
    if narr and narr.narrative_text:
        lines.append(f"\nSummary: {narr.narrative_text}")

    # Claims
    lines.append(f"\nClaims: {len(doc.claims)} extracted")
    if doc.claims:
        for c in doc.claims[:10]:
            e_level = _find_annotation_level(doc.establishedness_annotations, c.id)
            ev_level = _find_annotation_level(doc.evidence_annotations, c.id)
            lines.append(f"  [{c.id}] {e_level}/{ev_level} {c.text[:100]}")

    # Punchlist
    pl = doc.verification_punchlist
    if pl and pl.entries:
        lines.append(f"\n--- Claims to Verify ({pl.overall_severity}) ---")
        for entry in pl.entries[:5]:
            lines.append(f"  #{entry.rank} [{entry.attention_trigger}] {entry.claim_text[:120]}")
            lines.append(f"      → {entry.suggested_verification[:120]}")

    lines.append("")
    return "\n".join(lines)


def TrustProfile_caveat() -> str:
    return "This is not a reliability score. Different contexts need different standards."


def _find_annotation_level(annotations: list | None, claim_id: str) -> str:
    if not annotations:
        return "--"
    for a in annotations:
        if a.claim_id == claim_id:
            return a.level
    return "--"


def _format_claims_table(doc: AnalysisDocument) -> str:
    """Format a claims table from an AnalysisDocument.

    Per M7-001: Rendering only. No analytical logic.
    """
    lines: list[str] = []
    lines.append(f"{'ID':<6} {'E':<4} {'R':<4} {'N':<4} {'Type':<24} Text")
    lines.append("-" * 100)
    for c in doc.claims:
        e = _find_annotation_level(doc.establishedness_annotations, c.id)
        r = _find_annotation_level(doc.evidence_annotations, c.id)
        n = _find_annotation_level(doc.novelty_annotations, c.id)
        ctype = c.claim_type[:22]
        text = c.text[:60]
        lines.append(f"{c.id:<6} {e:<4} {r:<4} {n:<4} {ctype:<24} {text}")
    return "\n".join(lines)


def main() -> None:
    """Entry point for the `outputlens` CLI command."""
    parser = argparse.ArgumentParser(
        prog="outputlens",
        description="Analyze AI-generated text for claims, evidence, and epistemological structure.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # analyze subcommand
    analyze = subparsers.add_parser("analyze", help="Analyze text")
    analyze.add_argument("--text", "-t", type=str, help="Text to analyze")
    analyze.add_argument("--file", "-f", type=str, help="File containing text to analyze")
    analyze.add_argument("--prompt", "-p", type=str, help="Prompt that generated the text")
    analyze.add_argument("--model", "-m", type=str, help="AI model identifier")
    analyze.add_argument("--domain", "-d", type=str, help="Domain context hint")
    analyze.add_argument("--json", "-j", action="store_true", help="Output full AnalysisDocument as JSON")
    analyze.add_argument("--summary", "-s", action="store_true", help="Output human-readable summary")
    analyze.add_argument("--claims", "-c", action="store_true", help="Output claims table")

    args = parser.parse_args()

    if args.command != "analyze":
        parser.print_help()
        sys.exit(0)

    # Get input text
    text: str | None = None
    if args.text:
        text = args.text
    elif args.file:
        try:
            with open(args.file) as f:
                text = f.read()
        except FileNotFoundError:
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(2)
        except OSError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(2)
    elif not sys.stdin.isatty():
        text = sys.stdin.read()

    if not text or not text.strip():
        print("Error: no text provided. Use --text, --file, or pipe text to stdin.",
              file=sys.stderr)
        sys.exit(2)

    # Run analysis
    try:
        doc = run_analysis(
            text=text,
            prompt=args.prompt,
            model=args.model,
            domain=args.domain,
        )
    except Exception as e:
        print(f"Error: analysis failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.json:
        print(json.dumps(doc.to_dict(), indent=2, default=str))
    elif args.claims:
        print(_format_claims_table(doc))
    else:
        # Default: summary
        print(_format_summary(doc))


if __name__ == "__main__":
    main()
