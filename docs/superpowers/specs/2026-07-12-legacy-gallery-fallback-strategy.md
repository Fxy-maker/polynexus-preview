# Legacy Gallery Fallback Strategy

**Date:** 2026-07-12

## Decision

Keep the normal gallery manifest-only. Do not re-enable automatic fallback from
the active gallery to recursive legacy file discovery when `active_run.json` or
the active run manifest is missing or invalid.

Historical files remain recoverable through the separate, explicit Historical
Figure Recovery view. That view may scan legacy output, but its entries must not
be mixed into the active gallery, silently activate a run, or claim publication
and object-editing capabilities that were not proven from stored evidence.

## Current evidence

- `MainWindowFigureMixin._populate_plots()` calls
  `build_active_manifest_gallery_entries()` only.
- `build_active_manifest_gallery_entries()` returns an empty gallery when the
  active pointer or manifest cannot be read.
- Recursive discovery is owned by `polynexus/core/figures/legacy_recovery.py`.
- `MainWindowFigureMixin._open_legacy_recovery_view()` opens a separate
  `ChartViewer` and leaves the active gallery selection unchanged.
- `LegacyFigureRecoveryService` classifies candidates as `rebuildable`,
  `partially_repairable`, or `static_only` using recipe, document, and data
  evidence.
- Recovery tests verify that discovery does not change the active manifest or
  active-run pointer.

## Options considered

### Option A: Automatic fallback in the normal gallery

If the active manifest is absent, scan `figures/`, `summary/`, `per_frame/`, and
root-level exports and show the result as if it were the current run.

Rejected because it creates competing sources of truth, can mix historical and
current assets, cannot reliably reconstruct figure identity or publication
status, and makes an incomplete run look valid.

### Option B: Manifest-only normal gallery plus explicit recovery view

The active gallery shows only the active manifest. A user explicitly opens the
recovery view to inspect historical candidates; recovery actions create a new
portable package or a new run and never mutate the active run implicitly.

Selected because it preserves a predictable production workflow while retaining
an honest path for old data.

### Option C: Temporary dual-mode fallback with warnings

Show legacy files in the normal gallery with warning badges and attempt to infer
categories and editing capability.

Deferred because warnings do not solve identity, lineage, and publication-status
ambiguity. It may be reconsidered only after migration telemetry or a concrete
user-data loss case demonstrates that explicit recovery is insufficient.

## Policy boundary

| Surface | Source of truth | Legacy scan | Can activate a run? |
| --- | --- | --- | --- |
| Normal result gallery | Active `RunFigureManifest` | No | No |
| Historical Figure Recovery | Explicit recovery service | Yes | No, not implicitly |
| Recovery import/rebuild | New package or new pipeline run | Candidate-specific | Only through an explicit new-run operation |
| ChartEditor entry from normal gallery | Manifest entry and capability report | No | No |

## Risks and mitigations

- Older output may appear absent from the normal gallery. Mitigation: keep the
  recovery action visible and label the empty normal gallery honestly.
- Users may confuse a recovery candidate with a current result. Mitigation: use
  a separate window, `legacy` category, classification labels, and no active-run
  metadata on recovery entries.
- Some legacy figures cannot be reconstructed. Mitigation: classify them as
  static-only instead of promising object editing or scientific rebuild.
- A future contributor may reintroduce recursive discovery into the normal
  gallery. Mitigation: retain the quality-gate rule that reserves recursive
  discovery for `legacy_recovery.py` and keep manifest-only regression tests.

## Revisit triggers

Reconsider this decision only if one of these is demonstrated with evidence:

1. A supported legacy dataset cannot be recovered through the explicit recovery
   view and no migration path exists.
2. A measurable user workflow requires automatic discovery, with a stable legacy
   identity and provenance contract defined first.
3. A migration tool has converted the legacy candidate into a new manifest-backed
   run, making normal-gallery fallback unnecessary.

## Non-goals

- No production code change in this strategy task.
- No deletion or mass migration of old output directories.
- No restoration of the old gallery's silent recursive scan.
- No claim that every legacy figure is object-editable or publication-ready.

## Verification evidence

Focused gallery, recovery, main-window, and quality-gate tests:

```text
50 passed in 2.66s
```
