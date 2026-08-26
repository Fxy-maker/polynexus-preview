# Agent directory ComputeRun migration acceptance

Date: 2026-08-27
Task: `docs/agent/tasks/2026-08-27-agent-directory-compute-run-migration.md`

## Scope

This checkpoint routes non-DSC Agent/Codex directory inputs for IR, SAXS, and
WAXS through the shared `CanonicalTemplate -> CapabilityItems -> ComputeRun`
boundary. The canonical template is an opaque source-bound envelope for
provider-specific directory bytes; it does not invent measurements. DSC
directories remain on the existing provider route because their multi-segment
thermal semantics are not represented by a directory-aware
`thermal_program.v1` converter.

## Evidence

Focused verification:

```text
python -m pytest -q tests/test_agent_directory_compute_run.py
4 passed

python -m pytest -q tests/test_agent_directory_compute_run.py tests/test_agent_workflow_contracts.py tests/test_agent_prevalidated_template_reuse.py tests/test_project_workflow_adapters.py tests/test_project_workflow_package.py tests/test_compute_service.py tests/test_compute_models.py
115 passed, 4 skipped
```

The regression suite proves:

- custom non-DSC directory providers publish one completed `ComputeRun` and
  retain their legacy result projection;
- the default directory engine is invoked exactly once;
- IR/SAXS/WAXS directory templates use the expected technique envelope IDs;
- DSC directory execution remains provider-only;
- Agent inspection and ComputeRun share directory content hash and artifact
  identity;
- evidence packaging accepts the same directory manifest hash without copying
  raw inputs.

## Limits and follow-up

- NMR directory conversion is not registered and was not changed.
- DSC directory migration is intentionally deferred until a directory-aware
  `thermal_program.v1` representation exists.
- Full repository verification is not release-green because the known chart,
  GUI persistence/history, IR compatibility, and SAXS historical failures are
  outside this atomic migration.
- Architecture and scientific-boundary review are still required before any
  merge to a release branch.
