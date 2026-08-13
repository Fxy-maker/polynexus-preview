---
kind: lesson
status: active
date: 2026-08-13
title: Explicitly scan historical pytest roots without protecting them by accident
---

## Lesson

Historical PolyNexus pytest runs may have been created directly under a drive
root with names such as `PolyNexus-test-runs-*`, `PolyNexus_full_*`,
`PolyNexus_joint_*`, or dated SAXS matrix roots. The default storage scan must
not recurse across a whole drive, so operators must supply the affected root
explicitly with `--legacy-root 'D:\'` and inspect the JSON report before
`clean --apply`.

The legacy-name classifier must protect `archive`, `evidence`, and `baseline`
names before recognizing temporary-root patterns. Generic `review` directories
also remain protected; only dated or explicitly named SAXS basetemps are
eligible. Process detection must identify an actual pytest executable or
`python -m pytest`, not any command line that happens to contain the word
`pytest`, otherwise maintenance-shell text falsely blocks cleanup.

On 2026-08-13, this recovered 22.66 GB of old SAXS basetemps from `D:\`.
Twenty-three zero-byte legacy directories remained because their Windows ACLs
returned `WinError 5`; they do not justify an ownership/ACL bypass.
