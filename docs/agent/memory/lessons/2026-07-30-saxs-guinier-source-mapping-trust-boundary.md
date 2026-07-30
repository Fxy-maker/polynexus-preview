---
kind: lesson
status: active
date: 2026-07-30
title: Preserve the Guinier source-mapping trust boundary
---

# Guinier source-mapping trust boundary

For temperature sequence evidence, a source-index defect can be recorded as a
diagnostic fact without making the supplied indices safe for downstream pair
binding. Keep diagnostic position lists separate from the trusted mapping:
only a complete, finite, non-negative, integral, duplicate-free mapping may
populate frame or pair source identities. This preserves the conservative
Guinier sequence contract without interpolation, source repair, or scientific
promotion.

This task intentionally does not modify `active-work.md` or `current-state.md`
because both contain parallel uncommitted work. Its task card and acceptance
note are the durable execution record.

Verification lesson: the focused SAXS matrix is the reliable acceptance signal
for this narrow contract (`33 passed, 1 warning`). The repository verifier can
also include unrelated changed-worktree tests; here its quality gate reached
`288 passed, 2 failed, 3 warnings` on parallel NMR label expectations. Record
that limitation explicitly instead of changing or committing the parallel NMR
files to make a SAXS checkpoint appear green.
