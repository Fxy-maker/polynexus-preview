# Latest full/boundary evidence capture

The current checkout completed a captured full/boundary process tree with:

```text
stdout: D:\PolyNexus_full_boundary_async_20260730_2\stdout.log
stderr: D:\PolyNexus_full_boundary_async_20260730_2\stderr.log (empty)
pytest: 2986 passed, 17 skipped, 12 warnings in 1907.60s (0:31:47)
quality: 287 passed
preprocessing: 106 passed
verify stdout: [verify] all selected checks passed
```

The background launcher did not persist a separate wrapper exit-code file, so
the wrapper exit code is intentionally not asserted. A fresh direct
`scripts/boundary_audit.py --root D:\PolyNexus --json` run returned
`BOUNDARY_EXIT_CODE=0`.

This is fresh automated evidence, not scientific or release approval.
Restarted-GUI visual review, IR vendor/ROI semantics, NMR solid-C assignment,
Joint conflict interpretation, and final human scientific/release approval
remain open. Test-storage cleanup remained dry-run only; no test data was
deleted or migrated.

## Current-HEAD recheck

After the Gallery missing-asset checkpoint, a fresh D:-isolated rerun with the
pre-existing untracked `tests/_tmp_phase3/test_visual_audit_capture.py`
explicitly excluded returned:

```text
pytest: 3100 passed, 18 skipped, 12 warnings in 2280.40s (0:38:00)
quality: 290 passed
preprocessing: 106 passed
wrapper exit: 0
boundary audit exit: 0
```

The default collection was also run and returned one failure in that same
pre-existing scratch test because its old capture directory was not present;
it is retained as a limitation rather than hidden. No scratch, source, real
dataset, or test-storage directory was modified or cleaned with `--apply`.

## Follow-up after checkpoint `765bda3`

The fresh command with the same scratch exclusion and a new external basetemp
timed out after `1504.1s` with wrapper exit code `124`. No final pytest,
quality, preprocessing, or boundary summary was emitted. The verification
process tree was explicitly reaped after the timeout. This is not evidence of
a pass; the previous complete current-HEAD result remains the last complete
automated full/boundary evidence, but it predates `765bda3`.
