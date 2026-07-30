# Full-software goal requirements audit

The current evidence audit maps the full task as follows:

- Shared Workbench/Figure contracts: `57 passed`.
- Real published lifecycle: `15 passed, 11 warnings`, exit `0`.
- Golden preprocessing: `3 passed`, exit `0`.
- AI-off/failure/fallback: `25 passed`, exit `0`.
- Full repository/boundary: `2986 passed, 17 skipped, 12 warnings`; direct
  boundary exit `0`.
- Mode coverage: SAXS `3`, DSC `3`, WAXS `3` including strain/2D, IR `2`
  plus synthetic mapping, NMR `4`, and Joint transport/synthetic lifecycle.

The official Thermo/OMNIC Picta mapping profile is now documented for IR; the
reviewer confirmed that missing sample-level ROI, flattening order, detector
calibration, and source-matched payloads keep mapping diagnostic-only. NMR
JEOL axis calibration remains explicitly unconfirmed, and the reviewer
confirmed that solid-C assignment/Xc stays assignment-limited. Joint AI
fallback provenance and source/conflict preservation are covered; the
reviewer confirmed no automatic technique priority and diagnostic-only status
for unresolved conflicts.

The overall goal is not complete: current native route captures and an unlocked
canonical shell inspection provide route evidence, but they do not replace
complete human all-mode visual review. The three conservative scientific
dispositions are recorded, while source-specific IR/NMR evidence, final
release approval, and the separate SAXS decision remain conditions. No test
data was deleted or migrated.

## Current non-SAXS module recheck (2026-07-30)

The current checkout was re-run in three D:-isolated pytest shards, excluding
all SAXS test files:

```text
DSC/WAXS recursive test shard: 124 passed in 82.05s, exit code 0
IR recursive test shard: 55 passed in 46.51s, exit code 0
NMR/Joint recursive test shard: 65 passed in 412.97s, exit code 0
```

These counts strengthen the module-level regression evidence for the current
checkout. They do not alter the scientific/release boundaries above, and no
SAXS source, task card, or acceptance record was read for execution or
modified in this recheck.
