# SAXS series metric evidence projection

Status: implementation verified; checkpoint is the final handoff action.

This task is limited to carrying three existing source-index integrity fields
through the Figure/Manifest projection. Export continues to use its existing
read-only quality payload path. No calculation, threshold, physical gate,
rescue, AI, or publication role changes are in scope.

The Figure/Manifest/Export projection now preserves
`duplicate_source_index_indices`, `invalid_source_index_indices`, and
`source_index_order_reordered` as detached, strict-JSON-safe fields. Focused
GREEN was `47 passed, 1 warning`; the consumer matrix was `71 passed, 1
warning`; and the fresh SAXS matrix was `608 passed, 8 warnings in 394.32s`,
exit code `0`.

The task verifier's quality gate remains limited by two pre-existing history
locale assertions (`288 passed, 2 failed, 3 warnings`, exit code `1`). Storage
report/clean remained dry-run only (`56` artifacts, `6` eligible,
`eligible_bytes=13390550`, `removed=0`). No test-storage `--apply`, full
software full/boundary pass claim, physical threshold, rescue, AI, or
publication-role change is part of this task.
