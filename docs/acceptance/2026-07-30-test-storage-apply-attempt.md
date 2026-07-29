# Test storage apply attempt

Date: 2026-07-30

The user explicitly authorized `python scripts/test_storage.py clean
--older-than-hours 24 --apply` after all pytest processes had exited.

The apply partially removed eligible artifacts and returned exit code `1` after
six old zero-byte D:\PolyNexus legacy directories reported `WinError 5`
access denied. No ACL bypass or broad manual deletion was done.

Six C: legacy test directories were removed successfully, including two large
background pytest roots. The removed paths were:

- `C:\TempPolyNexus_full_goal_recheck_20260730`
- `C:\TempPolyNexus_full_goal_recheck_20260730_bg_pytest`
- `C:\TempPolyNexus_pad8_acceptance_goal_recheck_20260730`
- `C:\TempPolyNexus_real_saxs_goal_recheck_20260730`
- `C:\TempPolyNexus_real_saxs_goal_recheck_20260730_bg_pytest`
- `C:\TempPolyNexus_saxs_quality_program_task_verify_20260730_bg_pytest`

Post-apply dry-run report:

- `41` artifacts remain;
- `35` are protected;
- `0` eligible bytes remain; six eligible paths are zero-byte D: legacy
  directories;
- C: has no eligible artifacts and reports `182.27 GB` free;
- D: reports `125.60 GB` free.

The cleanup is partially complete because the six zero-byte D: directories
remain ACL-protected; no additional disk space is recoverable from them.
