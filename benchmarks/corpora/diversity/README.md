# BENCH-DIVERSITY

**Purpose**: Measure analyzer consistency, claim density patterns, and
classification distribution stability across diverse AI response types.

**Mutability**: Appendable. New items may be added. Existing items are never
modified (to preserve cross-version comparability). If an item is found to
be problematic, it is deprecated with a note in the manifest rather than
removed.

**Target size**: 50+ responses initially, growing to 1,000+ over time.

## Domains

Items are sampled across 10 domains:

| Domain | Description | Example Prompts |
|---|---|---|
| science | Physics, chemistry, earth science | "Explain quantum entanglement." |
| technology | AI, computing, engineering | "How do transformers work?" |
| medicine | Health, biology, treatments | "Describe the mechanism of vaccines." |
| law | Legal concepts, cases | "Explain the doctrine of fair use." |
| history | Events, periods, figures | "Summarize the causes of World War I." |
| economics | Markets, policy, theory | "Explain supply and demand." |
| philosophy | Ethics, epistemology, logic | "What is the trolley problem?" |
| arts | Literature, music, visual arts | "Describe the Renaissance period." |
| current_events | News, politics, social issues | "Summarize renewable energy trends." |
| general | Everyday knowledge, advice | "How do I improve my writing?" |

## Item Dimensions

Each item is tagged with:

- **word_count**: short (<100), medium (100-300), long (300+)
- **claim_density_estimate**: low, medium, high
- **source_model**: the AI model that generated the response
- **response_style**: explanatory, argumentative, narrative, technical, conversational

## Usage

Run all analyzers against every item. Compare:
- Claim count distribution per domain
- Classification level distribution per domain
- Analyzer latency by text length
- Classification stability (same domain, different models)

## Manifest Format

See `manifest.json` for the item index. Each entry references an item file
in `items/` with metadata for filtering and analysis.
