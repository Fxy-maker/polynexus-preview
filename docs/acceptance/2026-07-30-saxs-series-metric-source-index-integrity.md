# SAXS series metric source-index integrity

Status: implementation verified; checkpoint pending.

The source-index boundary is now verified. Initial RED was `8 failed, 2
warnings`; the non-finite boundary RED was `1 failed, 6 passed, 4 deselected,
2 warnings`; GREEN was `21 passed, 1 warning`. The consumer matrix passed `110
tests`, and the fresh SAXS matrix passed `605 passed, 8 warnings in 424.90s`
with exit code `0`.

The task verifier passed task-card, memory, Ruff, compile, and type-baseline
checks but its focused quality gate returned `288 passed, 2 failed, 3
warnings`, exit code `1`, due to pre-existing English-vs-Chinese locale
expectations in `tests/test_history_table_service.py`. This does not implicate
the SAXS change. `git diff --check` passed.

Storage remained non-destructive: `54` artifacts, `6` eligible,
`eligible_bytes=13390550`, `removed=0`; no `test_storage.py --apply` was run.
The task is limited to source-index evidence integrity and does not change
SAXS metric values, physical gates, rescue, AI, or publication roles.

The explicit allowlist is recorded in
`docs/agent/tasks/2026-07-30-saxs-series-metric-source-index-integrity.md`.
