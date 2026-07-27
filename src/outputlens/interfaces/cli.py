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
from outputlens.orchestration.analyzer import AnalysisContext
from outputlens.orchestration.engine import AnalyzerRegistry, OrchestrationEngine
from outputlens.runtime.model import Metadata, RawInput


def _build_registry() -> AnalyzerRegistry:
    """Build and populate the analyzer registry."""
    from outputlens.analyzers import register_all
    registry = AnalyzerRegistry()
    register_all(registry)
    return registry


def _run_analysis(text: str, prompt: str | None = None,
                  model: str | None = None,
                  domain: str | None = None) -> AnalysisDocument:
    """Run the full analysis pipeline and return an AnalysisDocument.

    Per M7-001: This function orchestrates the engine. It does not perform
    analysis itself. All analytical logic is in the analyzers.
    """
    registry = _build_registry()
    engine = OrchestrationEngine(registry)
    context = AnalysisContext()

    raw_input = RawInput(text=text, prompt=prompt)
    context.set_output("_bootstrap", "raw_input", raw_input)

    # Run all 16 analyzers
    all_analyzers = frozenset(registry.analyzer_ids)
    engine.execute(all_analyzers, context)

    # Assemble AnalysisDocument from context outputs
    doc = AnalysisDocument()
    doc.metadata = Metadata.create(
        engine_version="0.1.0",
        prompt=prompt,
        model_identifier=model,
        domain_hint=domain,
    )
    doc.raw_input = raw_input

    # Runtime objects
    a1_out = context.get_output("a1", "a1") or {}
    doc.normalized_text = a1_out.get("normalized_text")
    doc.position_index = a1_out.get("position_index")

    # Foundation
    a2_out = context.get_output("a2", "a2") or {}
    claims = a2_out.get("claims", [])
    for c in claims:
        doc.set_claim(c)

    a3_out = context.get_output("a3", "a3") or {}
    if a3_out.get("concepts"):
        doc.set_concepts(a3_out["concepts"])

    # Classification
    a4_out = context.get_output("a4", "a4") or {}
    if a4_out.get("establishedness_annotations"):
        doc.set_establishedness_annotations(a4_out["establishedness_annotations"])
    a5_out = context.get_output("a5", "a5") or {}
    if a5_out.get("evidence_annotations"):
        doc.set_evidence_annotations(a5_out["evidence_annotations"])
    a6_out = context.get_output("a6", "a6") or {}
    if a6_out.get("novelty_annotations"):
        doc.set_novelty_annotations(a6_out["novelty_annotations"])

    # Structure
    a7_out = context.get_output("a7", "a7") or {}
    if a7_out.get("claim_graph"):
        doc.set_claim_graph(a7_out["claim_graph"])
    a8_out = context.get_output("a8", "a8") or {}
    if a8_out.get("concept_graph"):
        doc.set_concept_graph(a8_out["concept_graph"])

    # Synthesis
    a9_out = context.get_output("a9", "a9") or {}
    if a9_out.get("trust_profile"):
        doc.set_trust_profile(a9_out["trust_profile"])
    a10_out = context.get_output("a10", "a10") or {}
    if a10_out.get("evidence_gap_report"):
        doc.set_evidence_gap_report(a10_out["evidence_gap_report"])
    a11_out = context.get_output("a11", "a11") or {}
    if a11_out.get("novelty_index"):
        doc.set_novelty_index(a11_out["novelty_index"])
    a12_out = context.get_output("a12", "a12") or {}
    if a12_out.get("overconfidence_report"):
        doc.set_overconfidence_report(a12_out["overconfidence_report"])
    a13_out = context.get_output("a13", "a13") or {}
    if a13_out.get("structural_integrity_report"):
        doc.set_structural_integrity_report(a13_out["structural_integrity_report"])
    a14_out = context.get_output("a14", "a14") or {}
    if a14_out.get("coherence_report"):
        doc.set_coherence_report(a14_out["coherence_report"])
    a15_out = context.get_output("a15", "a15") or {}
    if a15_out.get("response_narrative"):
        doc.set_response_narrative(a15_out["response_narrative"])

    # Terminal
    a16_out = context.get_output("a16", "a16") or {}
    if a16_out.get("verification_punchlist"):
        doc.set_verification_punchlist(a16_out["verification_punchlist"])

    doc.finalize()
    return doc


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
        doc = _run_analysis(
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
