# BENCH-TEMPORAL

**Purpose**: Detect unintended behavioral changes across analyzer versions.
A fixed, immutable set of responses that must produce identical output when
processed by the same analyzer versions.

**Mutability**: **IMMUTABLE**. Items in this corpus are never modified, updated,
or removed. If a response is found to be problematic for any reason, it is
deprecated in the manifest with an explanatory note but the item file itself
is preserved unchanged.

**Target size**: 20+ responses, fixed.

## Immutability Policy

1. **Items are never modified.** Once an item is added to BENCH-TEMPORAL, its
   content is frozen. Any change would invalidate cross-version comparisons.
2. **Items are never removed.** Removal would create gaps in historical
   comparison data.
3. **Deprecation**: If an item is found to be problematic (e.g., contains
   personal data, copyrighted content, or was incorrectly included), it is
   marked `deprecated: true` in the manifest with a `deprecation_reason`.
   The item file is preserved for historical completeness.
4. **Additions**: New items may be added in future corpus versions. Existing
   items remain unchanged.
5. **Versioning**: The corpus version changes when items are added or
   deprecated. Each version is a superset of the previous version's items.

## Change Approval Process

- **Adding items**: Requires review by at least one project maintainer.
  New items must represent stable, non-controversial AI response patterns.
- **Deprecating items**: Requires review by at least two project maintainers.
  Must include a written deprecation reason.
- **Modifying items**: Not permitted under any circumstances. Create a new
  item instead and deprecate the old one.

## Usage

Run the same analyzer versions against BENCH-TEMPORAL and compare:
- Must produce byte-identical AnalysisDocuments (same engine version, same input)
- Distribution shifts across engine versions indicate intentional behavioral changes
- Unexpected distribution shifts may indicate regressions

## Manifest Format

See `manifest.json`. Each entry references an immutable item file with
version history and deprecation status.
