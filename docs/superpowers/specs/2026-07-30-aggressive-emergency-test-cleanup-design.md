# Aggressive Emergency Test Cleanup Design

## Goal

Prevent a nearly-full test volume from being consumed by known disposable
pytest output while preserving review evidence, active work, source data, and
recoverability. When the target volume falls below 10% free space, the janitor
may clean known test-class legacy directories after a two-hour cooling period.

## Context and root cause

The current retention implementation is safe in normal conditions but too
conservative during disk pressure:

- emergency pressure is evaluated when a pytest run is finalized, not when a
  later janitor plan is built;
- a failed run can therefore retain an already-expired 24-hour deadline in its
  manifest while the volume is currently nearly full;
- discovery recognizes only a small set of historical names, so large
  directories such as `PolyNexus_*_matrix*` are invisible to the report;
- a `running` manifest is not reconciled during discovery when its recorded
  process has already exited.

Recent evidence showed an 11+ GB failed managed run, multiple multi-GB matrix
directories, and a live pytest process while cleanup was attempted. The
solution must address both the policy timing and the discovery/lifecycle gaps.

## Approved policy

Normal profiles remain unchanged:

| Profile | Normal cleanup |
| --- | --- |
| `ephemeral` | successful owned runs delete at pytest teardown; failures/interruption retain 24 hours |
| `review` | retain 7 days |
| `evidence` | retain permanently |
| `legacy` | retain 24 hours after discovery/modified time |

Emergency mode is active when the volume containing the approved test root has
less than 10% free space. It changes only the following decisions:

- failed or interrupted managed `ephemeral` runs become eligible after two
  hours;
- known test-class `legacy` directories become eligible after two hours;
- `review`, `evidence`, active, tracked, protected, symlinked, invalid, and
  unknown paths retain their normal protections.

The two-hour emergency rule is evaluated during every cleanup-plan build. It
is not limited to the moment a test process exits. A passed `ephemeral` run
continues to use its owned terminal cleanup path and is not made broadly
deletable by the CLI.

## Known legacy discovery boundary

Emergency legacy cleanup applies only to paths discovered through explicit
test-output patterns or the managed test root. The initial pattern set is:

- managed `.../PolyNexus-test-runs/pytest/run-*` directories;
- `PolyNexus_*_matrix*` directories at a configured legacy root;
- `PolyNexus_*_pytest*` directories at a configured legacy root;
- `PN_*_MATRIX*` directories at a configured legacy root;
- existing `TempPolyNexus*` and malformed historical temp names.

Names containing `archive`, `review`, `evidence`, `baseline`, or real-data
identifiers are not automatically treated as emergency-cleanable solely from
their name. Explicit user allowlists remain available for one-off cleanup.

## Lifecycle reconciliation

During discovery, each managed manifest is revalidated:

1. If its recorded PID is active, the run remains `running` and is protected.
2. If its recorded PID is no longer active, `running` becomes `interrupted`.
3. The interrupted run receives the normal failure deadline, or the two-hour
   emergency deadline for an `ephemeral` profile when pressure is active.
4. Malformed manifests remain protected with `manifest-invalid`.

The janitor must never infer that a process is dead from age alone. PID
reconciliation is a classification step; deletion still requires all other
gates immediately before `rmtree`.

## Shared deletion gates

Every deletion candidate must pass all applicable gates:

1. `--apply` is explicitly supplied for CLI cleanup, or the pytest-owned
   terminal path is handling its exact created run.
2. The candidate is under an approved managed/test root.
3. The resolved path is not a symlink and remains under that root.
4. No live process command line references the candidate.
5. The candidate is not Git-tracked, protected, review, evidence, invalid, or
   unknown.
6. The profile and normal/emergency age deadline have elapsed.
7. A deletion failure is recorded per path and does not cause unrelated
   candidates to be skipped.

The CLI remains dry-run by default. It reports ordinary eligible bytes,
emergency-only eligible bytes, protected reasons, and deletion failures. A
non-zero exit code is returned when `--apply` encounters one or more deletion
failures, even if other candidates were removed successfully.

## Data flow

```text
discover roots and manifests
        |
reconcile recorded process state
        |
measure current volume pressure
        |
build normal/emergency cleanup plan
        |
report or apply after root/process revalidation
```

The policy decision remains in `scripts/test_storage.py`; `conftest.py` keeps
only the owned pytest lifecycle behavior. No background service, forced ACL
takeover, branch deletion, or source/data cleanup is introduced.

## Verification strategy

Add focused regression coverage for:

- emergency legacy cleanup after two hours;
- emergency ephemeral failure cleanup after two hours;
- review/evidence and unknown paths remaining protected under pressure;
- pressure being evaluated during plan construction, not only finalization;
- live PID protection and dead-PID reconciliation to `interrupted`;
- the expanded known-test discovery patterns;
- active, tracked, protected, symlink, root-boundary, and ACL-failure behavior;
- report fields for emergency eligibility and per-path deletion failures.

Use temporary roots and mocked disk/process state in tests. No test may inspect
or delete real C: or D: data.

## Non-goals

- Do not automatically delete `review`, `evidence`, archive, baseline, or real
  scientific data directories.
- Do not bypass Windows ACLs with `takeown`, `icacls`, or administrator
  escalation automatically.
- Do not stop a live pytest process automatically.
- Do not change normal seven-day review or permanent evidence retention.
- Do not implement the autonomous coding loop or a background cleanup service.

## Acceptance criteria

- A D: volume below 10% free causes known test-class legacy and failed/
  interrupted ephemeral artifacts older than two hours to become eligible.
- A live pytest process, review/evidence path, protected path, tracked path,
  symlink, invalid manifest, and unknown legacy path remains ineligible.
- Stale `running` manifests are reconciled only after recorded processes are
  confirmed absent.
- The JSON and human reports explain normal versus emergency eligibility and
  every deletion failure.
- Focused tests, task-scoped verifier, and a real dry-run pass before any
  emergency `--apply` is attempted.
