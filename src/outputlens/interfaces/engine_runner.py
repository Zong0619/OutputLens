"""Shared engine runner for OutputLens interfaces.

Provides a single function, run_analysis(), that all interfaces use to invoke
the engine. This ensures consistent engine invocation across CLI, API, Web,
and future interfaces. Interfaces remain thin rendering layers -- all
analytical logic is in the engine.

Per M7-001: This module orchestrates the engine; it does not perform analysis.
"""

from __future__ import annotations

from outputlens.analysis.document import AnalysisDocument
from outputlens.orchestration.analyzer import AnalysisContext
from outputlens.orchestration.engine import AnalyzerRegistry, OrchestrationEngine
from outputlens.runtime.model import Metadata, RawInput


def run_analysis(
    text: str,
    prompt: str | None = None,
    model: str | None = None,
    domain: str | None = None,
    analyzers: frozenset[str] | None = None,
) -> AnalysisDocument:
    """Run the OutputLens analysis pipeline and return an AnalysisDocument.

    Args:
        text: The AI-generated text to analyze.
        prompt: Optional prompt that generated the text.
        model: Optional model identifier (for metadata only).
        domain: Optional domain hint.
        analyzers: Optional set of analyzer IDs to run. If None, runs all
                   registered analyzers.

    Returns:
        A finalized AnalysisDocument.
    """
    from outputlens.analyzers import register_all

    registry = AnalyzerRegistry()
    register_all(registry)

    engine = OrchestrationEngine(registry)
    context = AnalysisContext()

    raw_input = RawInput(text=text, prompt=prompt)
    context.set_output("_bootstrap", "raw_input", raw_input)

    targets = analyzers if analyzers else frozenset(registry.analyzer_ids)
    engine.execute(targets, context)

    doc = AnalysisDocument()
    doc.metadata = Metadata.create(
        engine_version="0.1.0",
        prompt=prompt,
        model_identifier=model,
        domain_hint=domain,
    )
    doc.raw_input = raw_input

    # Runtime
    a1 = context.get_output("a1", "a1") or {}
    doc.normalized_text = a1.get("normalized_text")
    doc.position_index = a1.get("position_index")

    # Foundation
    for c in (context.get_output("a2", "a2") or {}).get("claims", []):
        doc.set_claim(c)
    if (concepts := (context.get_output("a3", "a3") or {}).get("concepts")):
        doc.set_concepts(concepts)

    # Classification
    for (getter, setter) in [
        ("a4", "establishedness_annotations"),
        ("a5", "evidence_annotations"),
        ("a6", "novelty_annotations"),
    ]:
        out = context.get_output(getter, getter) or {}
        if anns := out.get(setter):
            getattr(doc, f"set_{setter}")(anns)

    # Structure
    for (getter, attr) in [("a7", "claim_graph"), ("a8", "concept_graph")]:
        out = context.get_output(getter, getter) or {}
        if val := out.get(attr):
            getattr(doc, f"set_{attr}")(val)

    # Synthesis
    for (getter, attr) in [
        ("a9", "trust_profile"), ("a10", "evidence_gap_report"),
        ("a11", "novelty_index"), ("a12", "overconfidence_report"),
        ("a13", "structural_integrity_report"), ("a14", "coherence_report"),
        ("a15", "response_narrative"),
    ]:
        out = context.get_output(getter, getter) or {}
        if val := out.get(attr):
            getattr(doc, f"set_{attr}")(val)

    # Terminal
    a16 = context.get_output("a16", "a16") or {}
    if pl := a16.get("verification_punchlist"):
        doc.set_verification_punchlist(pl)

    doc.finalize()
    return doc
