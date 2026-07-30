---
kind: lesson
status: active
date: 2026-07-30
title: Keep SAXS route evidence current without rewriting history
---

# Keep SAXS route evidence current

Later SAXS atomic tasks can make an older route matrix stale while the older
task evidence remains valid. Add a dated reconciliation section instead of
rewriting historical results or claiming a broad release gate from narrow
tests. Keep automated-ready, contract-ready, and human/open classifications
separate, and exclude parallel memory files from an atomic checkpoint.

The current audit verifier reached the shared quality gate and recorded
`288 passed, 2 failed, 3 warnings`; the failures are unrelated NMR locale
expectations. A documentation audit must preserve that limitation rather than
turning it into a SAXS pass or changing parallel files.
