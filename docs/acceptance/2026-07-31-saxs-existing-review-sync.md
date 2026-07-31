# SAXS Existing Review Evidence Synchronization Acceptance

Date: 2026-07-31

## Result

Accepted as an atomic implementation with a documented full SAXS matrix
timeout limitation. Existing manifest-linked Figure documents now receive the
current Workbench review evidence through the SAXS core boundary.

## Functional evidence

- Source-matched accepted `saxs.1d` review updates an existing Figure document.
- Detector/orientation classification uses `saxs.2d`; a 1D review remains
  `scope_mismatch` and disallowed.
- Cancelled/bad reviews remain disallowed.
- Missing manifests are nonfatal no-ops.
- Parsed manifest structure and all non-review document provenance remain
  unchanged.
- Workbench routing calls the cached SAXS engine only for SAXS and preserves the
  already-persisted review if synchronization is unavailable.

## Verification evidence

| Check | Actual result |
|---|---|
| RED | Expected collection `ImportError` before the new API existed |
| Focused sync | `5 passed, 51 deselected in 4.88s` |
| Sync-only incl. engine | `5 passed, 33 deselected in 6.08s` |
| Figure/Export/Workbench | `69 passed in 14.03s` |
| Quality gate | `297 passed`; preprocessing `106 passed` |
| Pyright | `0 errors, 0 warnings, 0 informations` |
| Structured verifier with types | exit `0` |
| SAXS matrix | timeout exit `124` after about `603.6s`, no final summary; not a pass |
| Storage | report/dry-run clean exit `0`, no apply, no removals |

The changed-file verifier variant was blocked by 10 pre-existing Ruff errors
in `polynexus/core/saxs_engine/io.py`; that parallel file was intentionally
left untouched.

## Scientific boundary

The implementation does not recalculate SAXS metrics, change quality grades,
physical gates, AI rescue semantics, publication roles, or human approval
state. It only transports an existing source-linked review snapshot into an
existing Figure provenance subtree.
