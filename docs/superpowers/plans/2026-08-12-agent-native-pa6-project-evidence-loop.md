# Agent-Native PA6 Project Evidence Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Each step is tracked with a checkbox and must be verified before the next checkpoint.

**Goal:** Add a project-local, Codex-callable workflow that turns a PA6 paper folder into replayable DSC evidence and an ARS-readable `ResearchEvidencePackage`, while leaving raw files and existing GUI/database workflows untouched.

**Architecture:** Add a thin project-workflow layer above the existing agent-workflow contracts and canonical DSC provider. The layer owns `.polynexus/` workspace paths, a multi-formulation research index, analysis requests, and immutable package snapshots; it delegates conversion, calculation, plotting, and evidence limits to existing provider boundaries. Unsupported techniques remain explicit inventory/package blockers until separate adapter tasks are approved.

**Tech Stack:** Python 3.12+, frozen dataclasses, JSON-safe canonical serialization, SHA-256 identities, existing `AgentWorkflowService`, existing `CanonicalExperiment`/DSC converter, argparse CLI, pytest.

---

## Scope Map

Create these focused modules:

- `polynexus/core/project_workflow/models.py`: frozen JSON-safe contracts for project artifacts, research graph nodes/links, source-priority facts, `AnalysisRequest`, project plans, and package evidence items.
- `polynexus/core/project_workflow/workspace.py`: root validation, `.polynexus/` directory layout, safe derived-path checks, and atomic JSON read/write helpers.
- `polynexus/core/project_workflow/index.py`: deterministic inspection projection that merges artifacts without overwriting authoritative raw facts and records lower-priority discrepancies.
- `polynexus/core/project_workflow/package.py`: immutable `ResearchEvidencePackage` materialization and ARS `writing-input.md` projection.
- `polynexus/core/project_workflow/service.py`: public `inspect`, `plan`, `run`, and `package` facade delegating execution to `AgentWorkflowService`.
- `polynexus/core/project_workflow/__init__.py`: public exports only.
- `polynexus/cli/run_project_workflow_service.py`: one-JSON-envelope CLI adapter for project operations.

Modify only these existing entry points in the first slice:

- `polynexus/cli/parser.py`: add `project-workflow` subcommand and arguments.
- `polynexus/__main__.py`: route the new subcommand to the CLI adapter.

Add focused tests:

- `tests/test_project_workflow_models.py`
- `tests/test_project_workflow_workspace.py`
- `tests/test_project_workflow_index.py`
- `tests/test_project_workflow_service.py`
- `tests/test_project_workflow_package.py`
- `tests/test_project_workflow_cli.py`

Do not modify technique engines, GUI modules, SQLite schema, or external PA6
raw data in this plan.

## Task 1: Establish JSON-Safe Project Contracts

**Files:**

- Create: `polynexus/core/project_workflow/models.py`
- Create: `polynexus/core/project_workflow/__init__.py`
- Test: `tests/test_project_workflow_models.py`

- [ ] **Step 1: Write failing contract tests**

Add tests that require:

```python
def test_project_artifact_identity_is_stable_and_json_safe(tmp_path):
    artifact = ProjectArtifact.create(
        project_root=tmp_path,
        path=tmp_path / "raw" / "DSC_180.txt",
        technique="dsc",
        sha256="abc123",
        observed_facts={"setpoint_C": 180.0},
    )
    assert artifact.artifact_id == ProjectArtifact.create(
        project_root=tmp_path,
        path=tmp_path / "raw" / "DSC_180.txt",
        technique="dsc",
        sha256="abc123",
        observed_facts={"setpoint_C": 180.0},
    ).artifact_id
    assert json.loads(json.dumps(artifact.to_dict()))["technique"] == "dsc"

def test_raw_fact_wins_over_filename_label_and_records_discrepancy():
    fact = ProjectFact.from_sources(
        key="condition.setpoint_C",
        raw_value=185.0,
        filename_value=180.0,
    )
    assert fact.value == 185.0
    assert fact.status == "verified_from_raw"
    assert fact.discrepancies == ("filename_value_disagrees",)

def test_research_graph_supports_multiple_formulations_batches_and_measurements():
    graph = ResearchGraph.create(
        study_id="pa6-study",
        formulations=(Formulation("pa6", "PA6"), Formulation("blend", "PA6+additive")),
        batches=(PreparationBatch("b1", "pa6"), PreparationBatch("b2", "pa6")),
        conditions=(Condition("c180", "b1", {"temperature_C": 180.0}),),
        measurements=(Measurement("m-dsc", "c180", "dsc", "artifact-1"),),
    )
    assert len(graph.formulations) == 2
    assert graph.measurements[0].artifact_id == "artifact-1"

def test_analysis_request_round_trips_and_has_content_hash():
    request = AnalysisRequest.create(
        question="Compare 180-185 C kinetics",
        purpose="results_support",
        requested_outputs=("avrami_parameter_table",),
    )
    assert AnalysisRequest.from_dict(request.to_dict()).request_hash == request.request_hash
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
pytest tests/test_project_workflow_models.py -q
```

Expected: collection or import failures because the new contracts do not yet
exist.

- [ ] **Step 3: Implement the minimal contracts**

Implement frozen dataclasses with `to_dict`/`from_dict`, recursive JSON-safe
normalization, and canonical SHA-256 hashes. Use these exact public concepts:

```python
class ProjectArtifact: ...
class ProjectFact: ...
class Formulation: ...
class PreparationBatch: ...
class Condition: ...
class Measurement: ...
class ResearchGraph: ...
class AnalysisRequest: ...
class ProjectPlan: ...
class EvidenceItem: ...
```

`ProjectFact.from_sources` must implement raw > record > directory > filename >
inference authority and retain discrepancy codes. It must never expose a
probabilistic confidence field in the public contract. Reject non-finite
numbers and mutable payloads at construction.

- [ ] **Step 4: Run GREEN and checkpoint**

Run the focused test command again; expected `4 passed`. Then run:

```powershell
python scripts/verify.py --changed --types
```

Commit only the new model module, package export, and model test with:

```powershell
python scripts/auto_commit.py --message "feat(project): add agent-native project contracts" --files polynexus/core/project_workflow/models.py polynexus/core/project_workflow/__init__.py tests/test_project_workflow_models.py
```

## Task 2: Add Safe Project Workspace And Index Projection

**Files:**

- Create: `polynexus/core/project_workflow/workspace.py`
- Create: `polynexus/core/project_workflow/index.py`
- Test: `tests/test_project_workflow_workspace.py`
- Test: `tests/test_project_workflow_index.py`

- [ ] **Step 1: Write failing isolation and authority tests**

Cover root creation, derived-only writes, path traversal rejection, raw hash
inventory, directory/file label discrepancy, and repeated inspection stability:

```python
def test_workspace_creates_only_polynexus_children(tmp_path):
    workspace = ProjectWorkspace.open(tmp_path)
    assert workspace.root == tmp_path.resolve()
    assert workspace.inventory_dir.parent == tmp_path / ".polynexus"
    assert not (tmp_path / "raw").exists()

def test_workspace_rejects_output_outside_project_root(tmp_path):
    workspace = ProjectWorkspace.open(tmp_path)
    with pytest.raises(ValueError, match="project root"):
        workspace.require_derived_path(tmp_path.parent / "escape.json")

def test_index_preserves_raw_condition_when_filename_disagrees(tmp_path):
    source = tmp_path / "raw" / "WAXS_180C.raw"
    source.parent.mkdir()
    source.write_text("method_temperature_C=185\n", encoding="utf-8")
    index = ProjectIndexer(ProjectWorkspace.open(tmp_path)).inspect([source])
    assert index.artifacts[0].facts["condition.setpoint_C"].value == 185.0
    assert "filename_value_disagrees" in index.artifacts[0].discrepancies
```

- [ ] **Step 2: Run RED**

Run:

```powershell
pytest tests/test_project_workflow_workspace.py tests/test_project_workflow_index.py -q
```

Expected: import failures for the new workspace/index classes.

- [ ] **Step 3: Implement workspace and index**

`ProjectWorkspace.open(root)` resolves a directory and exposes only the
documented `.polynexus` subdirectories. `require_derived_path` must reject the
root itself, any path outside root, and any path inside `raw`, `notes`, or
`manuscript`. JSON writes use a temporary sibling and `replace` so interrupted
writes do not corrupt `project.json`.

`ProjectIndexer.inspect(paths)` calls the existing `inspect_artifact` for each
file/directory, hashes source artifacts, extracts only directly observed facts
available from current inspection, merges them into `ResearchGraph`, and writes
`inventory/index.json`. It may record inferred classification labels but must
not replace a raw fact. Repeating inspection with unchanged inputs must produce
the same index hash.

- [ ] **Step 4: Run GREEN and checkpoint**

Run the two focused test modules and `git diff --check`. Commit:

```powershell
python scripts/auto_commit.py --message "feat(project): add isolated workspace and index" --files polynexus/core/project_workflow/workspace.py polynexus/core/project_workflow/index.py tests/test_project_workflow_workspace.py tests/test_project_workflow_index.py
```

## Task 3: Introduce Analysis Request Planning

**Files:**

- Modify: `polynexus/core/project_workflow/service.py`
- Modify: `polynexus/core/project_workflow/models.py`
- Test: `tests/test_project_workflow_service.py`

- [ ] **Step 1: Write failing planning tests**

Require planning to work with a specific DSC scope and with no scope:

```python
def test_plan_resolves_dsc_request_without_requiring_batch_metadata(tmp_path):
    service = ProjectWorkflowService.open(tmp_path)
    request = AnalysisRequest.create(
        question="Compare PA6 kinetics",
        requested_outputs=("avrami_parameter_table",),
        data_scope=("raw/DSC-isothermal",),
    )
    plan = service.plan(request)
    assert plan.status in {"ready", "review_required"}
    assert plan.required_context == ()

def test_plan_reports_missing_converter_as_blocker_without_fabrication(tmp_path):
    service = ProjectWorkflowService.open(tmp_path)
    request = AnalysisRequest.create(
        question="Analyze WAXS",
        requested_outputs=("waxs_profile_figure",),
        data_scope=("raw/WAXS",),
    )
    plan = service.plan(request)
    assert "converter_unregistered" in plan.reason_codes
```

- [ ] **Step 2: Run RED**

Run `pytest tests/test_project_workflow_service.py -q`; expected failures for
the absent facade and plan implementation.

- [ ] **Step 3: Implement deterministic request planning**

Add `ProjectWorkflowService.open(root)`, `inspect(paths)`, and `plan(request)`.
Planning must resolve data scope against the persisted index, select only
registered provider/template IDs, preserve requested output names, and list
missing context separately from blockers. A missing batch relationship cannot
become a blocker for a DSC-only request. A technique with no registered
converter becomes `converter_unregistered`; do not fall back to ad-hoc code.

- [ ] **Step 4: Run GREEN and checkpoint**

Run the focused service tests and `python scripts/verify.py --changed --types`.
Commit:

```powershell
python scripts/auto_commit.py --message "feat(project): plan analysis requests" --files polynexus/core/project_workflow/service.py polynexus/core/project_workflow/models.py tests/test_project_workflow_service.py
```

## Task 4: Delegate DSC Execution And Emit Evidence Items

**Files:**

- Modify: `polynexus/core/project_workflow/service.py`
- Create: `polynexus/core/project_workflow/evidence.py`
- Test: `tests/test_project_workflow_service.py`

- [ ] **Step 1: Write failing execution tests**

Use a synthetic Mettler-style fixture and assert the existing converter and
provider are used without changing raw source files:

```python
def test_run_dsc_request_writes_derived_outputs_only(tmp_path):
    source = _write_mettler_fixture(tmp_path / "raw" / "PA6-DWJJ.txt")
    service = ProjectWorkflowService.open(tmp_path)
    request = AnalysisRequest.create(
        question="Compare PA6 kinetics",
        requested_outputs=("avrami_parameter_table",),
        data_scope=(str(source.relative_to(tmp_path)),),
    )
    result = service.run(request)
    assert result.status == "review_required"
    assert source.exists()
    assert all(Path(path).is_relative_to(tmp_path / ".polynexus") for path in result.outputs)
```

- [ ] **Step 2: Run RED**

Run `pytest tests/test_project_workflow_service.py::test_run_dsc_request_writes_derived_outputs_only -q`; expected failure until delegation is wired.

- [ ] **Step 3: Implement delegation**

`ProjectWorkflowService.run(request_or_plan)` must:

1. resolve the plan and persist it under `requests/`;
2. build an existing `AnalysisRecipe` for the DSC canonical provider;
3. call `AgentWorkflowService.run_recipe` with output under `.polynexus/runs/`;
4. convert `AnalysisRun` step results to `EvidenceItem` records without
   copying raw input data;
5. persist a run manifest containing request hash, recipe hash, source hashes,
   canonical/conversion hashes, provider version, status, figures, tables, and
   limitations.

The service must preserve `review_required` from the current PA6 path and must
not call an LLM or rerun raw segmentation after canonical conversion.

- [ ] **Step 4: Run GREEN and checkpoint**

Run the focused service matrix plus existing DSC canonical tests. Commit:

```powershell
python scripts/auto_commit.py --message "feat(project): run DSC requests through canonical providers" --files polynexus/core/project_workflow/service.py polynexus/core/project_workflow/evidence.py tests/test_project_workflow_service.py
```

## Task 5: Materialize Immutable ARS Evidence Packages

**Files:**

- Create: `polynexus/core/project_workflow/package.py`
- Modify: `polynexus/core/project_workflow/service.py`
- Test: `tests/test_project_workflow_package.py`

- [ ] **Step 1: Write failing package tests**

Require package versioning, source pointers, supported/disallowed scopes, and
non-mutation of prior packages:

```python
def test_package_contains_ars_entrypoint_and_provenance(tmp_path):
    run = _run_dsc_request(tmp_path)
    package = ProjectEvidencePackager(ProjectWorkspace.open(tmp_path)).create((run,))
    assert (package.path / "writing-input.md").exists()
    payload = json.loads((package.path / "evidence.json").read_text())
    assert payload["items"][0]["source_runs"]
    assert payload["items"][0]["supported_interpretations"]
    assert payload["items"][0]["disallowed_conclusions"]

def test_new_package_version_does_not_replace_previous_snapshot(tmp_path):
    first = _create_package(tmp_path)
    second = _create_package(tmp_path)
    assert first.path != second.path
    assert first.path.exists()
```

- [ ] **Step 2: Run RED**

Run `pytest tests/test_project_workflow_package.py -q`; expected failures for
the absent packager.

- [ ] **Step 3: Implement package writer**

`ProjectEvidencePackager.create(runs, relations=())` chooses the next numeric
version, validates that referenced run manifests still exist and hashes match,
copies only derived figure/table assets into the package, and writes
`manifest.json`, `evidence.json`, `relations.json`, `limitations.json`, and
`writing-input.md` atomically. It must reject attempts to package blocked runs
as completed evidence while allowing `review_required` packages. Existing
packages are read-only snapshots.

- [ ] **Step 4: Run GREEN and checkpoint**

Run package tests, service tests, and `git diff --check`. Commit:

```powershell
python scripts/auto_commit.py --message "feat(project): emit immutable ARS evidence packages" --files polynexus/core/project_workflow/package.py polynexus/core/project_workflow/service.py tests/test_project_workflow_package.py
```

## Task 6: Add Project CLI Boundary

**Files:**

- Modify: `polynexus/cli/parser.py`
- Create: `polynexus/cli/run_project_workflow_service.py`
- Modify: `polynexus/__main__.py`
- Test: `tests/test_project_workflow_cli.py`

- [ ] **Step 1: Write failing parser/JSON envelope tests**

Cover `project-workflow inspect|plan|run|package`, one JSON object on stdout,
and a blocked response for invalid roots or missing requests.

- [ ] **Step 2: Run RED**

Run `pytest tests/test_project_workflow_cli.py -q`; expected parser/import
failures.

- [ ] **Step 3: Implement CLI adapter**

Add arguments `--project-root`, `--request`, `--paths`, `--plan`, `--runs`, and
`--output-dir` as applicable. The adapter must load JSON, call
`ProjectWorkflowService`, print one deterministic JSON envelope, and return
exit code 0 only for `ready`, `completed`, or `review_required`. It must not
print logs to stdout and must never write outside `.polynexus/` unless an
explicit derived export destination is within the project root.

- [ ] **Step 4: Run GREEN and checkpoint**

Run the focused CLI tests and existing agent-workflow CLI tests. Commit:

```powershell
python scripts/auto_commit.py --message "feat(cli): expose project evidence workflow" --files polynexus/cli/parser.py polynexus/cli/run_project_workflow_service.py polynexus/__main__.py tests/test_project_workflow_cli.py
```

## Task 7: PA6 External Read-Only Smoke And Final Verification

**Files:**

- Modify: `docs/agent/memory/active-work.md`
- Create: `docs/acceptance/2026-08-12-agent-native-pa6-project-evidence-loop.md`
- Test additions only if a focused regression is discovered.

- [ ] **Step 1: Run synthetic end-to-end matrix**

Run:

```powershell
pytest tests/test_project_workflow_models.py tests/test_project_workflow_workspace.py tests/test_project_workflow_index.py tests/test_project_workflow_service.py tests/test_project_workflow_package.py tests/test_project_workflow_cli.py tests/test_canonical_experiment_templates.py tests/test_dsc_canonical_isothermal_conversion.py -q
```

Expected: all focused tests pass and no raw source is copied into the package.

- [ ] **Step 2: Run the PA6 source read-only replay**

Use the existing external `PA6-DWJJ.txt` path and write only to a new external
derived output directory. Verify source hash, six holds at 180-185 C, package
status `review_required`, and package provenance. Do not place raw data or
derived bundle under the repository.

- [ ] **Step 3: Run structured verification**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-12-agent-native-pa6-project-evidence-loop.md --changed --types
git diff --check
```

Record exact quality/preprocessing counts and any scientific review limits in
the acceptance note and active-work memory.

- [ ] **Step 4: Create the final atomic checkpoint**

Derive the explicit changed-file allowlist and run:

```powershell
python scripts/auto_commit.py --message "feat(project): complete PA6 evidence loop" --files `
  polynexus/core/project_workflow/models.py `
  polynexus/core/project_workflow/workspace.py `
  polynexus/core/project_workflow/index.py `
  polynexus/core/project_workflow/evidence.py `
  polynexus/core/project_workflow/package.py `
  polynexus/core/project_workflow/service.py `
  polynexus/core/project_workflow/__init__.py `
  polynexus/cli/parser.py `
  polynexus/cli/run_project_workflow_service.py `
  polynexus/__main__.py `
  tests/test_project_workflow_models.py `
  tests/test_project_workflow_workspace.py `
  tests/test_project_workflow_index.py `
  tests/test_project_workflow_service.py `
  tests/test_project_workflow_package.py `
  tests/test_project_workflow_cli.py `
  docs/acceptance/2026-08-12-agent-native-pa6-project-evidence-loop.md `
  docs/agent/memory/active-work.md `
  docs/agent/tasks/2026-08-12-agent-native-pa6-project-evidence-loop.md `
  docs/superpowers/plans/2026-08-12-agent-native-pa6-project-evidence-loop.md
```

Do not push, merge, deploy, or modify the external source tree.

## Self-Review Checklist

- The plan covers every design requirement: project isolation, multiple
  entities, raw-fact priority, flexible entry, request operations, replay,
  package limits, GUI compatibility, and the PA6 vertical slice.
- No step creates a universal parser or bypasses a registered converter.
- The public types and method names are consistent across tasks.
- FTIR/SAXS/WAXS adapters are explicitly separate follow-up tasks; early package
  limitations are honest rather than fabricated completeness.
