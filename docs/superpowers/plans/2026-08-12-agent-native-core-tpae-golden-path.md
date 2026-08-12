# Agent-Native Core and TPAE Golden Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a stable, replayable, JSON-safe agent workflow boundary and use it to run the first TPAE characterization golden path without replacing existing technique engines.

**Architecture:** A new `polynexus.core.agent_workflow` package owns immutable contract models, artifact inspection, recipe proposal/replay, workflow registry, validation, and export. The TPAE adapter is manifest-driven and invokes existing engine `run_pipeline()` boundaries through injected provider functions; it aggregates their public `AnalysisResult.to_dict()` and `analysis_evidence`, never their private arrays. A dedicated CLI command exposes one JSON envelope per operation.

**Tech Stack:** Python 3.10+, dataclasses, stdlib JSON/hashlib/pathlib, existing `AnalysisResult`, pytest, argparse.

---

## File Structure

- Create: `polynexus/core/agent_workflow/models.py` — frozen JSON-safe contracts and canonical hashing.
- Create: `polynexus/core/agent_workflow/inspection.py` — hashing, technique/format checks, EDF header facts, expected error conversion.
- Create: `polynexus/core/agent_workflow/evidence.py` — public evidence normalization and observed/support/disallowed scopes.
- Create: `polynexus/core/agent_workflow/registry.py` — workflow adapter protocol and registration.
- Create: `polynexus/core/agent_workflow/service.py` — public inspect/propose/run/validate/export operations.
- Create: `polynexus/core/agent_workflow/tpae.py` — `tpae.characterization.v1` manifest adapter.
- Create: `polynexus/core/agent_workflow/__init__.py` — limited public exports and TPAE registration.
- Create: `polynexus/cli/run_agent_workflow_service.py` — JSON-only CLI orchestration.
- Modify: `polynexus/cli/parser.py` — `agent-workflow` parser and operation arguments.
- Modify: `polynexus/__main__.py` — route `agent-workflow` before single-technique analysis.
- Create: `tests/test_agent_workflow_contracts.py` — contracts, inspection, deterministic recipes, replay gate.
- Create: `tests/test_tpae_golden_workflow.py` — manifest, steps, evidence status, export bundle.
- Create: `tests/test_agent_workflow_cli.py` — parser and one-envelope CLI behavior.
- Modify: `docs/agent/memory/active-work.md` — implementation status/evidence.
- Modify: `docs/agent/tasks/2026-08-12-agent-native-core-tpae-golden-path.md` — completion evidence.

### Task 1: Contract Models and Canonical Recipe Hash

**Files:**
- Create: `tests/test_agent_workflow_contracts.py`
- Create: `polynexus/core/agent_workflow/models.py`
- Create: `polynexus/core/agent_workflow/__init__.py`

- [ ] **Step 1: Write the failing contract tests**

```python
from polynexus.core.agent_workflow import AnalysisRecipe, InputArtifact, RecipeStep


def test_recipe_hash_is_stable_for_same_json_safe_content() -> None:
    artifact = InputArtifact.ready(
        path="C:/data/sample.csv", technique="dsc", sha256="a" * 64
    )
    recipe = AnalysisRecipe.create(
        workflow_id="tpae.characterization.v1",
        artifacts=[artifact],
        steps=[RecipeStep(step_id="dsc_isothermal", technique="dsc")],
    )

    assert recipe.recipe_hash == AnalysisRecipe.from_dict(recipe.to_dict()).recipe_hash
    assert recipe.to_dict()["artifacts"][0]["sha256"] == "a" * 64
```

- [ ] **Step 2: Run the failing test**

Run: `python -m pytest -p no:cacheprovider -q tests/test_agent_workflow_contracts.py::test_recipe_hash_is_stable_for_same_json_safe_content`

Expected: FAIL because `polynexus.core.agent_workflow` does not exist.

- [ ] **Step 3: Implement minimal immutable models**

```python
@dataclass(frozen=True)
class RecipeStep:
    step_id: str
    technique: str
    parameters: Mapping[str, JSONValue] = field(default_factory=dict)
    parameter_sources: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AnalysisRecipe:
    workflow_id: str
    contract_version: str
    artifacts: tuple[InputArtifact, ...]
    steps: tuple[RecipeStep, ...]
    recipe_hash: str
```

Canonicalize recursively, reject non-finite float values, serialize with sorted
keys and compact separators, then hash UTF-8 JSON with SHA-256. `from_dict()`
recomputes and validates the supplied hash rather than trusting it.

- [ ] **Step 4: Run the contract test**

Run: `python -m pytest -p no:cacheprovider -q tests/test_agent_workflow_contracts.py::test_recipe_hash_is_stable_for_same_json_safe_content`

Expected: PASS.

- [ ] **Step 5: Commit the atomic contract slice**

```powershell
python scripts/auto_commit.py --message "feat(core): add agent workflow contracts" --files polynexus/core/agent_workflow/__init__.py polynexus/core/agent_workflow/models.py tests/test_agent_workflow_contracts.py
```

### Task 2: Artifact Inspection and Structured Failures

**Files:**
- Modify: `tests/test_agent_workflow_contracts.py`
- Create: `polynexus/core/agent_workflow/inspection.py`
- Modify: `polynexus/core/agent_workflow/__init__.py`

- [ ] **Step 1: Write failing artifact inspection tests**

```python
def test_inspect_edf_preserves_geometry_and_background_limit(tmp_path: Path) -> None:
    source = tmp_path / "sample.edf"
    source.write_bytes(EDF_HEADER_WITH_GEOMETRY)

    artifact = inspect_artifact(source, technique="saxs")

    assert artifact.inspection_status == "review_required"
    assert artifact.header_facts["geometry_calibrated"] is True
    assert "background_unknown" in artifact.reason_codes


def test_inspect_missing_file_returns_blocked_artifact(tmp_path: Path) -> None:
    artifact = inspect_artifact(tmp_path / "missing.csv", technique="dsc")

    assert artifact.inspection_status == "blocked"
    assert artifact.reason_codes == ("file_missing",)
```

- [ ] **Step 2: Run the failing tests**

Run: `python -m pytest -p no:cacheprovider -q tests/test_agent_workflow_contracts.py -k "inspect"`

Expected: FAIL because `inspect_artifact` is unavailable.

- [ ] **Step 3: Implement inspection using source facts only**

`inspect_artifact()` must hash files in chunks, call existing
`check_file_format()` for declared techniques, and parse only EDF header values
needed to report observed geometry. Do not import pyFAI/fabio, load detector
arrays, infer missing calibration, or create output files. Convert missing path,
unsupported format, unreadable file, and malformed EDF header into `InputArtifact`
statuses/reason codes.

- [ ] **Step 4: Run the inspection tests**

Run: `python -m pytest -p no:cacheprovider -q tests/test_agent_workflow_contracts.py -k "inspect"`

Expected: PASS.

- [ ] **Step 5: Commit the inspection slice**

```powershell
python scripts/auto_commit.py --message "feat(core): inspect agent workflow artifacts" --files polynexus/core/agent_workflow/__init__.py polynexus/core/agent_workflow/inspection.py tests/test_agent_workflow_contracts.py
```

### Task 3: Workflow Registry, TPAE Manifest Proposal, and Replay Gate

**Files:**
- Create: `polynexus/core/agent_workflow/registry.py`
- Create: `polynexus/core/agent_workflow/tpae.py`
- Create: `polynexus/core/agent_workflow/service.py`
- Create: `tests/test_tpae_golden_workflow.py`
- Modify: `tests/test_agent_workflow_contracts.py`
- Modify: `polynexus/core/agent_workflow/__init__.py`

- [ ] **Step 1: Write failing TPAE recipe tests**

```python
def test_tpae_proposal_requires_dsc_and_orders_available_steps(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path, dsc=True, ftir=True, waxs=False, saxs=True)
    service = AgentWorkflowService()

    recipe = service.propose_recipe("tpae.characterization.v1", manifest)

    assert [step.step_id for step in recipe.steps] == [
        "dsc_isothermal", "ftir_temperature", "saxs_profile"
    ]
    assert recipe.steps[0].evidence_role == "primary"


def test_tpae_proposal_blocks_when_required_dsc_is_missing(tmp_path: Path) -> None:
    service = AgentWorkflowService()

    proposal = service.propose_recipe("tpae.characterization.v1", write_manifest(tmp_path, dsc=False))

    assert proposal.status == "blocked"
    assert "required_artifact_missing:dsc_isothermal" in proposal.reason_codes
```

- [ ] **Step 2: Run the failing TPAE proposal tests**

Run: `python -m pytest -p no:cacheprovider -q tests/test_tpae_golden_workflow.py -k "proposal"`

Expected: FAIL because no workflow registry/service exists.

- [ ] **Step 3: Implement the registry and manifest proposal**

Define a small `WorkflowAdapter` protocol with `inspect_manifest()` and
`propose_recipe()`. `TpaeCharacterizationWorkflow` accepts versioned JSON
manifests with `workflow_id`, `artifacts`, optional qualitative `intent`, and
no embedded raw arrays. Require `dsc_isothermal`; add available optional steps
in fixed order `ftir_temperature`, `waxs_profile`, `saxs_profile`. Bind each
step to an existing technique name and evidence role only; do not introduce
scientific parameters.

- [ ] **Step 4: Write and run the failing replay gate test**

```python
def test_run_blocks_before_provider_when_artifact_hash_changes(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path, dsc=True)
    service = AgentWorkflowService(provider_runner=pytest.fail)
    recipe = service.propose_recipe("tpae.characterization.v1", manifest).recipe
    Path(manifest["artifacts"]["dsc_isothermal"]["path"]).write_text("changed")

    run = service.run_recipe(recipe, tmp_path / "out")

    assert run.status == "blocked"
    assert run.reason_codes == ("artifact_hash_mismatch",)
```

Run: `python -m pytest -p no:cacheprovider -q tests/test_agent_workflow_contracts.py -k "hash_changes"`

Expected: FAIL because `run_recipe()` does not check hash identity.

- [ ] **Step 5: Implement replay preconditions, then run tests**

Before a provider is resolved or invoked, re-inspect every recipe artifact and
compare hashes. Return a structured blocked `AnalysisRun` on any mismatch. The
provider runner receives only a `RecipeStep`, its `InputArtifact`, and an output
directory; it cannot mutate recipe contents.

Run: `python -m pytest -p no:cacheprovider -q tests/test_tpae_golden_workflow.py -k "proposal"; python -m pytest -p no:cacheprovider -q tests/test_agent_workflow_contracts.py -k "hash_changes"`

Expected: PASS.

- [ ] **Step 6: Commit manifest/registry/replay behavior**

```powershell
python scripts/auto_commit.py --message "feat(core): add TPAE agent workflow proposal" --files polynexus/core/agent_workflow/__init__.py polynexus/core/agent_workflow/registry.py polynexus/core/agent_workflow/service.py polynexus/core/agent_workflow/tpae.py tests/test_agent_workflow_contracts.py tests/test_tpae_golden_workflow.py
```

### Task 4: Public Result Adaptation, Validation, and Export Bundle

**Files:**
- Create: `polynexus/core/agent_workflow/evidence.py`
- Modify: `polynexus/core/agent_workflow/models.py`
- Modify: `polynexus/core/agent_workflow/service.py`
- Modify: `tests/test_tpae_golden_workflow.py`

- [ ] **Step 1: Write failing run/evidence/export tests**

```python
def test_run_normalizes_public_result_and_preserves_conclusion_limits(tmp_path: Path) -> None:
    service = AgentWorkflowService(provider_runner=qualified_provider)
    recipe = service.propose_recipe("tpae.characterization.v1", write_manifest(tmp_path, dsc=True)).recipe

    run = service.run_recipe(recipe, tmp_path / "run")
    validated = service.validate_run(run)

    assert validated.status == "review_required"
    assert validated.steps[0].result_summary["technique"] == "dsc"
    assert "unique_hydrogen_bond_species" in validated.evidence.disallowed_conclusions


def test_export_writes_replay_bundle_without_copying_raw_artifact(tmp_path: Path) -> None:
    run = completed_run(tmp_path)

    bundle = AgentWorkflowService().export_run(run, tmp_path / "bundle")

    assert (bundle / "recipe.json").is_file()
    assert (bundle / "artifacts.json").is_file()
    assert not any(path.name == "source.csv" for path in bundle.rglob("*"))
```

- [ ] **Step 2: Run the failing validation/export tests**

Run: `python -m pytest -p no:cacheprovider -q tests/test_tpae_golden_workflow.py -k "normalizes or export"`

Expected: FAIL because public run/evidence/export structures are absent.

- [ ] **Step 3: Implement evidence normalization and provider adaptation**

Accept only an `AnalysisResult` or equivalent public mapping from a provider.
For `AnalysisResult`, use `to_dict()`, public figures, and `analysis_evidence`.
Derive status from `validation_passed`, warnings, and workflow role. Add fixed
workflow conclusion limits including `unique_hydrogen_bond_species` for 2D-COS
and `absolute_scattering_quantity_without_background` for scattering steps;
never remove technique-provided warnings.

- [ ] **Step 4: Implement export and run validation**

`validate_run()` aggregates step statuses and evidence. `export_run()` requires
a validated run, writes only canonical JSON summaries, recipe/artifact hashes,
and references to existing figure assets/manifests. Reject destinations that
equal or reside inside any raw input parent path.

- [ ] **Step 5: Run validation/export tests**

Run: `python -m pytest -p no:cacheprovider -q tests/test_tpae_golden_workflow.py -k "normalizes or export"`

Expected: PASS.

- [ ] **Step 6: Commit the public result/export slice**

```powershell
python scripts/auto_commit.py --message "feat(core): export validated agent workflow runs" --files polynexus/core/agent_workflow/evidence.py polynexus/core/agent_workflow/models.py polynexus/core/agent_workflow/service.py tests/test_tpae_golden_workflow.py
```

### Task 5: CLI Entry Point and Compatibility Tests

**Files:**
- Create: `polynexus/cli/run_agent_workflow_service.py`
- Modify: `polynexus/cli/parser.py`
- Modify: `polynexus/__main__.py`
- Create: `tests/test_agent_workflow_cli.py`
- Modify: `tests/test_cli_parser.py`

- [ ] **Step 1: Write failing parser and CLI output tests**

```python
def test_agent_workflow_parser_accepts_inspect_operation() -> None:
    args = parse_args(["agent-workflow", "inspect", "--manifest", "tpae.json"])

    assert args.cmd == "agent-workflow"
    assert args.operation == "inspect"


def test_agent_workflow_cli_prints_exactly_one_json_envelope(capsys, tmp_path: Path) -> None:
    code = run_agent_workflow(make_args("inspect", tmp_path / "manifest.json"), service=StubService())

    assert code == 0
    assert len(capsys.readouterr().out.splitlines()) == 1
```

- [ ] **Step 2: Run the failing CLI tests**

Run: `python -m pytest -p no:cacheprovider -q tests/test_agent_workflow_cli.py tests/test_cli_parser.py -k "agent_workflow"`

Expected: FAIL because the parser and route are absent.

- [ ] **Step 3: Implement CLI routing and JSON envelope**

Add `polynexus agent-workflow {inspect,propose,run,validate,export}` with a
manifest path, recipe/run path as applicable, output directory, and optional
intent file. `run_agent_workflow()` loads/saves only canonical JSON, delegates
to `AgentWorkflowService`, prints one `json.dumps(..., ensure_ascii=False,
allow_nan=False)` line, and returns a nonzero code only for `blocked`/`failed`.
Route it in `__main__.main()` before `_run_single()`.

- [ ] **Step 4: Run CLI and legacy parser tests**

Run: `python -m pytest -p no:cacheprovider -q tests/test_agent_workflow_cli.py tests/test_cli_parser.py tests/test_cli_wrappers.py`

Expected: PASS.

- [ ] **Step 5: Commit the CLI slice**

```powershell
python scripts/auto_commit.py --message "feat(cli): expose agent workflow operations" --files polynexus/cli/run_agent_workflow_service.py polynexus/cli/parser.py polynexus/__main__.py tests/test_agent_workflow_cli.py tests/test_cli_parser.py
```

### Task 6: Integration Verification and Durable Records

**Files:**
- Modify: `docs/agent/tasks/2026-08-12-agent-native-core-tpae-golden-path.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Run the focused contract and golden-path suite**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_agent_workflow_contracts.py tests/test_tpae_golden_workflow.py tests/test_agent_workflow_cli.py tests/test_engine_result.py tests/test_cli_parser.py tests/test_cli_wrappers.py
```

Expected: PASS with no real TPAE data requirement.

- [ ] **Step 2: Run the structured verifier and whitespace audit**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-12-agent-native-core-tpae-golden-path.md --changed --types
git diff --check
```

Expected: selected checks pass.

- [ ] **Step 3: Record implementation evidence**

Add exact test counts, verifier output, known adapter limitations, and the
checkpoint hash to the task card and active-work record. Do not claim real TPAE
scientific acceptance unless a separate read-only external-data audit has run.

- [ ] **Step 4: Create the final atomic checkpoint**

```powershell
python scripts/auto_commit.py --message "feat(core): establish TPAE agent workflow golden path" --files polynexus/core/agent_workflow/__init__.py polynexus/core/agent_workflow/models.py polynexus/core/agent_workflow/inspection.py polynexus/core/agent_workflow/evidence.py polynexus/core/agent_workflow/registry.py polynexus/core/agent_workflow/service.py polynexus/core/agent_workflow/tpae.py polynexus/cli/run_agent_workflow_service.py polynexus/cli/parser.py polynexus/__main__.py tests/test_agent_workflow_contracts.py tests/test_tpae_golden_workflow.py tests/test_agent_workflow_cli.py tests/test_cli_parser.py docs/agent/tasks/2026-08-12-agent-native-core-tpae-golden-path.md docs/agent/memory/active-work.md
```

## Plan Self-Review

- Spec coverage: Tasks 1-2 cover contract/inspection; Task 3 covers registry,
  manifest and replay; Task 4 covers provider adaptation, validation, and
  export; Task 5 covers machine-facing CLI; Task 6 records and verifies the
  full task.
- Scope: no task changes technique algorithms, GUI behavior, external datasets,
  or the existing `AnalysisResult` schema.
- Naming: public operation names and status vocabulary match the approved
  design; every later task uses the contract types established in Task 1.
- Placeholder scan: no implementation step defers behavior to an unspecified
  future component; WAXS/SAXS provider binding remains bounded by existing
  public evidence and returns structured blockers when unavailable.
