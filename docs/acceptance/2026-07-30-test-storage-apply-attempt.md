# Test storage apply attempt

Date: 2026-07-30

The user explicitly authorized `python scripts/test_storage.py clean
--older-than-hours 24 --apply` after all pytest processes had exited.

The apply partially removed eligible artifacts but returned exit code `1` on
`D:\PolyNexus\PolyNexusPolyNexus.pytest_tmp_metric_position_full` with
`WinError 5` access denied. No ACL bypass or broad manual deletion was done.

Post-apply dry-run report:

- `277` artifacts remain;
- `40` are eligible (`19128640281` bytes);
- `237` are protected;
- C: has `8` artifacts and `0` eligible entries.

The exact removed list was not emitted because the cleanup process stopped on
the permission error. The cleanup is therefore partially complete, not fully
complete.
