# Colorbar figure-audit regression

## Goal

Keep Matplotlib colorbar helper axes out of the data-axis SCI checklist so a
valid heatmap is not rejected for lacking x/y labels on its auxiliary axis.

## Non-goals

- Non-goals: changing scientific labels, heatmap rendering, publication roles,
  or any engine validation decision.

## Affected boundaries

- `polynexus.plotting.figure_audit.audit_figure_sci` axis checklist.
- `tests/test_figure_audit.py` heatmap/colorbar regression coverage.
- SAXS temperature publication audit only as the real-data reproducer.

## Acceptance criteria

- [x] A heatmap with a colorbar and standard data-axis labels passes the SCI
  audit.
- [x] A normal data axis with missing or non-standard labels remains audited.
- [x] Focused regression and changed-file verification pass.

## Design

Matplotlib marks a colorbar axis with the private-but-stable `_colorbar`
reference. The audit skips that auxiliary axis only in the axis-label, line,
and annotation checks; the primary plotting axes retain the existing strict
checks. This avoids weakening publication checks for actual data axes.

## Implementation plan

1. Add a failing SCI-audit regression using a standard-labelled heatmap with a
   Matplotlib colorbar.
2. Skip only axes carrying Matplotlib's `_colorbar` marker in the shared audit
   loop, then rerun the focused regression and existing SAXS provider matrix.
3. Run `python scripts/verify.py --task docs/agent/tasks/2026-07-26-colorbar-audit-regression.md --changed --types` and checkpoint only the explicit allowlist.

## Verification

```powershell
python -m pytest --basetemp=C:\Temp\PolyNexus_colorbar_fix_focus tests\test_figure_audit.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_temperature_figure_panels.py tests/test_saxs_temperature_evidence_filtering.py -q

python scripts/verify.py --task docs/agent/tasks/2026-07-26-colorbar-audit-regression.md --changed --types
```

Result: 20 passed.

The real SAXS temperature run after the fix produced eight `ready` Manifest
entries. The run still reports scientific validation failure because the
fixture has contaminated Q* / unresolved lamellar evidence; that is preserved
as diagnostic state and is not treated as a figure-audit failure.

## Changed-file allowlist

- `polynexus/plotting/figure_audit.py`
- `tests/test_figure_audit.py`
- this task card
- release audit and memory files only when the new evidence is recorded
