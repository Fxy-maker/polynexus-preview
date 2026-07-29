# Test-storage apply fail-soft design

## Goal

Make the explicit test-storage `clean --apply` operation continue across
independent eligible directories when one directory cannot be removed, while
making partial success and remaining failures machine-readable and visible to
the caller.

## Scope and non-goals

- Keep all existing eligibility, approved-root, Git-tracked, protected-path,
  active-process, symlink, and retention checks unchanged.
- Never change ACLs, elevate privileges, retry indefinitely, or remove a path
  outside the approved roots.
- Keep the existing `apply_cleanup(...) -> list[Path]` helper contract for
  library callers; add a detailed result for the CLI rather than breaking the
  existing API.
- Dry-run behavior remains non-mutating and returns no failures because no
  deletion is attempted.

## Design

Add two immutable result types in `scripts/test_storage.py`:

- `CleanupFailure(path, error_type, message)` records one failed deletion.
- `CleanupApplyResult(removed, failures)` records all successful removals and
  deletion failures; `success` is true only when `failures` is empty.

Implement `apply_cleanup_detailed(...)` as the fail-soft operation. It iterates
the already-built plan in deterministic order, applies the existing root and
symlink safety gate, attempts each eligible path independently, appends an
`OSError` failure, and continues to the next path. The compatibility wrapper
`apply_cleanup(...)` delegates to it and returns only `list(result.removed)`.

The CLI consumes the detailed result, emits removed entries exactly as before,
adds a JSON `failures` array and a human-readable failure line for each failed
path, and returns exit code `1` when any deletion failed. A partial apply thus
does useful safe work but cannot be mistaken for a complete cleanup.

## Verification boundary

Regression tests will simulate one `PermissionError` followed by a successful
deletion without changing real ACLs. They will assert that the later eligible
path is removed, the failed path is retained and reported, dry-run remains
non-mutating, and existing safety tests remain green. The task verifier,
changed-file diff check, and storage report/dry-run will run before the
allowlist checkpoint.
