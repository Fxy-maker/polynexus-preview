---
task_id: 2026-07-31-restarted-gui-all-mode-evidence-refresh
status: accepted-automated-visual-evidence
date: 2026-07-31
---

# Restarted GUI All-Mode Evidence Acceptance

## Verification result

The current checkout ran the native Windows route harness with a fresh Qt
process and external D-drive pytest/capture roots:

```text
17 passed, 15 warnings in 521.92s (0:08:41), exit code 0
```

The capture directory contains `68` PNGs totaling `14,567,314` bytes. The 17
mode groups each contain Results, Gallery, History, and Editor captures. The
real Editor Export action was exercised and its PackageExporter fallback
artifacts were asserted for each route.

## Visual observations

- DSC Results contains populated metrics and review/risk text.
- IR mapping Results shows `Review required`, `review_missing`, source
  identity, and the official X/Y mapping provenance; it is not vendor approval.
- NMR solid-C Results shows `assignment_limited`, default/unconfirmed axis
  calibration, and blocked Xc promotion.
- Joint Results shows populated diagnostics with `2 errors`, `2 warnings`,
  and a blocked conflict conclusion; no scientific precedence is inferred.
- The SAXS Editor capture is nonblank, with two plotted panels, object tree,
  style controls, and export controls.

## Limitations

The 15 warnings include DSC polynomial-fit/font-glyph/constrained-layout
warnings. Long NMR evidence rows remain visually dense. This is route and
visual evidence from fresh native test windows, not final owner acceptance,
IR vendor mapping approval, NMR assignment truth, Joint conflict resolution,
or publication authorization.

## Checks

- `python scripts/boundary_audit.py --root D:\PolyNexus --json` exited `0`.
- The task-scoped verifier exited `0`; quality `297 passed`, preprocessing
  `106 passed`, task/memory, Ruff, compile, type baseline, and whitespace all
  passed.
- `git diff --check` exited `0`.

These checks cover the documentation/evidence boundary only. They do not
convert the remaining scientific or owner review items into approval.
