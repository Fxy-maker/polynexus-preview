# AI-First Core Foundation and Direct-Run Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish one small, shared direct-run contract so CLI/AI and Quick
Analysis invoke the same deterministic engine path without evidence-package or
paper-review gating.

**Architecture:** Add a new `polynexus.core.compute` façade that wraps existing
technique engines without changing their scientific algorithms.  It creates a
hash-addressed raw artifact, a direct canonical envelope, a frozen plan, and a
completed/needs-input/failed run.  The existing CLI and GUI worker route
through this façade; a short-lived GUI compatibility projection lets the
current result table and persistence keep consuming the legacy engine result
until their own migration task.

**Tech Stack:** Python 3.12, frozen dataclasses, existing technique registry,
PySide6 worker signals, pytest, Ruff.

---

## Scope and protected boundaries

This is the first migration slice, not the deletion program.  It introduces no
new scientific calculation, changes no numerical engine result, and deletes no
workflow, review, figure, RAG, or Joint module.  It makes the first shared run
object observable and verifies that a legacy validation warning does not block
a calculation.

The temporary `ComputeResult` name avoids colliding with the existing
`polynexus.core.engine.AnalysisResult`.  It is the new contract's result
projection; it must not import `analysis_evidence` or publish writing
eligibility.  The legacy engine result stays attached only in-memory to bridge
the existing GUI during the migration and is deliberately absent from JSON.

## Planned file structure

| File | Responsibility |
| --- | --- |
| `docs/agent/tasks/2026-08-24-core-foundation-direct-run.md` | Atomic task card and validation commands for this slice. |
| `docs/agent/inventories/2026-08-24-core-simplification-import-inventory.md` | Checked import/entry-point inventory before future deletion tasks. |
| `polynexus/core/compute/__init__.py` | Small public surface for the new compute contracts and service. |
| `polynexus/core/compute/models.py` | JSON-safe artifact, envelope, plan, result, and run dataclasses. |
| `polynexus/core/compute/service.py` | Only place that instantiates a legacy engine and projects its result. |
| `polynexus/cli/run_single_service.py` | Existing `dsc`, `ir`, `saxs`, `waxs`, and `nmr` commands use the service. |
| `polynexus/cli/parser.py` | Adds an optional machine-readable direct-run result to existing technique commands. |
| `polynexus/gui/main_window_workers.py` | Quick Analysis invokes `ComputeRunService` rather than `engine.run_pipeline` directly. |
| `polynexus/gui/main_window_run_mixin.py` | Stores the shared run and explicitly projects its legacy result for existing widgets. |
| `tests/test_compute_models.py` | Contract immutability, hashing, and JSON projection tests. |
| `tests/test_compute_service.py` | Status, warning, engine, and option-forwarding service tests. |
| `tests/test_cli_run_single_service.py` | Human output and JSON direct-run CLI tests. |
| `tests/test_main_window_workers.py` | Worker service-routing and completion-payload tests. |

## Task 1: Record the protected migration boundary

**Files:**
- Create: `docs/agent/tasks/2026-08-24-core-foundation-direct-run.md`
- Create: `docs/agent/inventories/2026-08-24-core-simplification-import-inventory.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Create the architecture task card before source changes**

Create a card with `kind: architecture`, `status: active`, and these exact
acceptance conditions:

```markdown
## Affected boundaries

- Analysis engine: adds a façade only; DSC, IR, SAXS, WAXS, and NMR algorithms remain unchanged.
- Result/schema contract: creates the new compute contracts while legacy `AnalysisResult` remains a compatibility projection.
- CLI/AI: existing single-technique commands return the direct-run record when `--json` is requested.
- GUI: `AnalysisWorker` invokes the same service and retains the received `ComputeRun` in memory.
- Persistence/export: unchanged database schema; legacy result persistence is an explicit temporary adapter.

## Acceptance criteria

- [ ] A missing path produces `needs_input`, not a review state.
- [ ] An engine validation warning produces a `completed` run with warnings.
- [ ] CLI and GUI worker both invoke `ComputeRunService.run_direct`.
- [ ] The public compute JSON contains no `analysis_evidence`, writing eligibility, or manuscript role fields.
```

- [ ] **Step 2: Create the dependency inventory from current imports**

Record, with source paths and symbol names, the current producer/consumer
boundaries that future deletion tasks must drain:

```markdown
| Area | Current producer | Current consumers | First migration action |
| --- | --- | --- | --- |
| Single run | `core.engine.BaseEngine.run_pipeline` | `cli.run_single_service`, `gui.main_window_workers` | Route both through `ComputeRunService`. |
| Canonical conversion | `core.canonical_experiments` | `agent_workflow`, `project_workflow` | Keep unchanged in this slice; replace status model in conversion task. |
| Evidence/review | `core.analysis_evidence*` | engine result, project/agent workflow, GUI review panels | Do not import from `core.compute`; drain in a later deletion batch. |
| Paper workflow | `core.project_workflow` | CLI, evidence dialog, gallery | Do not modify in this slice. |
| Agent workflow | `core.agent_workflow` | agent CLI | Do not modify in this slice. |
| Joint/RAG | `core.joint`, `rag` | main-window workers and tuning/advisory paths | Do not modify in this slice. |
```

Use `rg -l` to enumerate imports and include the command and date in the
inventory.  Do not copy generated test directories or external data paths.

- [ ] **Step 3: Record the active architecture work**

Add one concise `active-work.md` entry stating that this slice is a temporary
compatibility bridge, that no legacy code has been removed, and that deletion
depends on focused Quick Analysis plus CLI/AI contract tests.

- [ ] **Step 4: Validate documentation contracts**

Run:

```powershell
python scripts/task_check.py --task docs/agent/tasks/2026-08-24-core-foundation-direct-run.md
git diff --check
```

Expected: task card is valid and whitespace check exits `0`.

- [ ] **Step 5: Commit the documentation boundary**

```powershell
python scripts/auto_commit.py `
  --message "docs(core): define direct-run migration boundary" `
  --files docs/agent/tasks/2026-08-24-core-foundation-direct-run.md docs/agent/inventories/2026-08-24-core-simplification-import-inventory.md docs/agent/memory/active-work.md
```

Expected: one local commit containing only the three named files.

## Task 2: Add JSON-safe compute contracts with a failing-test-first loop

**Files:**
- Create: `polynexus/core/compute/__init__.py`
- Create: `polynexus/core/compute/models.py`
- Create: `tests/test_compute_models.py`

- [ ] **Step 1: Write the contract tests before the package exists**

Create `tests/test_compute_models.py` with tests equivalent to the following:

```python
from pathlib import Path

import pytest

from polynexus.core.compute.models import (
    AnalysisPlan,
    CanonicalDataset,
    ComputeResult,
    ComputeRun,
    RawArtifact,
)


def test_direct_contract_hashes_are_stable_and_json_safe(tmp_path: Path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("x,y\\n1,2\\n", encoding="utf-8")

    artifact = RawArtifact.from_path(source, technique="ir")
    dataset = CanonicalDataset.direct_envelope(artifact)
    plan = AnalysisPlan.direct(dataset, output_dir=tmp_path / "out")
    run = ComputeRun.completed(
        artifact=artifact,
        dataset=dataset,
        plan=plan,
        result=ComputeResult(metrics={"peak_cm-1": 1630.0}, warnings=("auto_baseline",)),
    )

    payload = run.to_dict()
    assert payload["status"] == "completed"
    assert payload["artifact"]["sha256"] == artifact.sha256
    assert payload["dataset"]["source_artifact_id"] == artifact.artifact_id
    assert payload["plan"]["dataset_id"] == dataset.dataset_id
    assert payload["result"]["metrics"] == {"peak_cm-1": 1630.0}
    assert "analysis_evidence" not in str(payload)
    assert "writing_eligibility" not in str(payload)


def test_compute_run_accepts_only_ready_needs_input_failed_completed(tmp_path: Path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("x,y\\n1,2\\n", encoding="utf-8")
    artifact = RawArtifact.from_path(source, technique="ir")

    with pytest.raises(ValueError, match="Unsupported compute status"):
        ComputeRun(status="review_required", artifact=artifact, reasons=("legacy",))
```

- [ ] **Step 2: Run the tests and observe the missing-package failure**

Run:

```powershell
python -m pytest -q -p no:cacheprovider tests/test_compute_models.py
```

Expected: collection fails because `polynexus.core.compute` does not yet exist.

- [ ] **Step 3: Implement the compact dataclasses**

Create `models.py` with these public types and rules:

```python
COMPUTE_STATUSES = frozenset({"ready", "needs_input", "failed", "completed"})


@dataclass(frozen=True)
class RawArtifact:
    artifact_id: str
    path: str
    technique: str
    format: str
    sha256: str
    observed_facts: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_path(cls, path: str | Path, *, technique: str, observed_facts: Mapping[str, Any] | None = None) -> "RawArtifact": ...

    @classmethod
    def missing(cls, path: str | Path, *, technique: str) -> "RawArtifact": ...


@dataclass(frozen=True)
class CanonicalDataset:
    dataset_id: str
    source_artifact_id: str
    technique: str
    template_id: str
    payload: Mapping[str, Any]
    warnings: tuple[str, ...] = ()

    @classmethod
    def direct_envelope(cls, artifact: RawArtifact) -> "CanonicalDataset": ...


@dataclass(frozen=True)
class AnalysisPlan:
    plan_id: str
    dataset_id: str
    technique: str
    output_dir: str
    pipeline_options: Mapping[str, Any]
    parameter_sources: Mapping[str, str]

    @classmethod
    def direct(cls, dataset: CanonicalDataset, *, output_dir: str | Path, pipeline_options: Mapping[str, Any] | None = None) -> "AnalysisPlan": ...


@dataclass(frozen=True)
class ComputeResult:
    metrics: Mapping[str, Any] = field(default_factory=dict)
    figures: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @classmethod
    def from_legacy_result(cls, value: Any) -> "ComputeResult": ...


@dataclass(frozen=True)
class ComputeRun:
    status: str
    artifact: RawArtifact
    dataset: CanonicalDataset | None = None
    plan: AnalysisPlan | None = None
    result: ComputeResult | None = None
    reasons: tuple[str, ...] = ()
    legacy_result: Any = field(default=None, repr=False, compare=False)
```

Implement canonical JSON hashing with sorted keys and reject non-finite floats.
`RawArtifact.from_path` hashes files and deterministic directory manifests.
`RawArtifact.missing()` creates a JSON-safe reference from the resolved
candidate path, technique, and suffix without a content hash; it is used only
by a `needs_input` run and is never accepted by `CanonicalDataset.direct_envelope`.
`ComputeRun.__post_init__` rejects a status outside `COMPUTE_STATUSES`, rejects
a result on `needs_input` or `failed`, and requires a result on `completed`.
`ComputeRun.to_dict()` must exclude `legacy_result` and return only JSON-safe
values.

`ComputeResult.from_legacy_result()` projects `parameters` to `metrics`,
`figures`, `metadata`, `validation_warnings`, non-`OK` `quality_flags`, and a
non-empty non-success `validation_summary` to warnings.  It must not read,
copy, or expose `analysis_evidence`.

Export exactly `AnalysisPlan`, `CanonicalDataset`, `ComputeResult`,
`ComputeRun`, and `RawArtifact` from `polynexus/core/compute/__init__.py`.

- [ ] **Step 4: Run the contract tests after implementation**

Run:

```powershell
python -m pytest -q -p no:cacheprovider tests/test_compute_models.py
```

Expected: both tests pass.

- [ ] **Step 5: Commit the contract-only slice**

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add direct compute contracts" `
  --files polynexus/core/compute/__init__.py polynexus/core/compute/models.py tests/test_compute_models.py
```

Expected: one local commit with the models and their tests only.

## Task 3: Build and test the direct-run façade

**Files:**
- Create: `polynexus/core/compute/service.py`
- Modify: `polynexus/core/compute/__init__.py`
- Create: `tests/test_compute_service.py`

- [ ] **Step 1: Write service behavior tests**

Create `tests/test_compute_service.py` with the following core cases:

```python
from pathlib import Path
from types import SimpleNamespace

from polynexus.core.compute.service import ComputeRunService


class FakeEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def run_pipeline(self, path: str, output_dir: str, **options: object):
        self.calls.append((path, output_dir, options))
        return SimpleNamespace(
            parameters={"t_half_s": 12.5}, figures={"curve": "curve.svg"},
            metadata={"provider": "fake"}, validation_warnings=["no_background"],
            quality_flags={"fit": "WARN"}, validation_summary="fit needs inspection",
        )


def test_direct_run_completes_with_legacy_warnings(tmp_path: Path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("data", encoding="utf-8")
    engine = FakeEngine()

    run = ComputeRunService(lambda technique, config=None, submodule_id=None: engine).run_direct(
        technique="dsc", path=source, output_dir=tmp_path / "out", pipeline_options={"skip_to": None},
    )

    assert run.status == "completed"
    assert run.result is not None
    assert "no_background" in run.result.warnings
    assert engine.calls == [(str(source), str(tmp_path / "out"), {"skip_to": None})]


def test_direct_run_returns_needs_input_for_missing_path(tmp_path: Path) -> None:
    run = ComputeRunService(lambda *args, **kwargs: FakeEngine()).run_direct(
        technique="ir", path=tmp_path / "missing.csv", output_dir=tmp_path / "out",
    )

    assert run.status == "needs_input"
    assert run.reasons == ("raw_artifact_missing",)
```

- [ ] **Step 2: Run the service tests and observe the missing-service failure**

Run:

```powershell
python -m pytest -q -p no:cacheprovider tests/test_compute_service.py
```

Expected: collection fails because `ComputeRunService` is not yet exported.

- [ ] **Step 3: Implement `ComputeRunService` as the only legacy-engine adapter**

Implement this public method in `service.py`:

```python
class ComputeRunService:
    def __init__(self, engine_factory: Callable[..., Any] = get_engine) -> None: ...

    def run_direct(
        self,
        *,
        technique: str,
        path: str | Path,
        output_dir: str | Path,
        config: Any = None,
        submodule_id: str | None = None,
        engine: Any = None,
        pipeline_options: Mapping[str, Any] | None = None,
    ) -> ComputeRun: ...
```

The method must:

1. Create `RawArtifact`; return a `needs_input` `ComputeRun` built with
   `RawArtifact.missing()` and `raw_artifact_missing` when the path does not
   exist.
2. Build `CanonicalDataset.direct_envelope()` and `AnalysisPlan.direct()`;
   the envelope is explicitly `raw-file-envelope.v1` and contains only source
   identity/format until the conversion migration task replaces it.
3. Obtain `engine` or call `engine_factory(technique, config=config,
   submodule_id=submodule_id)`; return `needs_input` with `technique_unknown`
   if it is absent.
4. Call `engine.run_pipeline(str(path), str(output_dir), **pipeline_options)`
   exactly once.
5. Return `ComputeRun.completed(...)` with `ComputeResult.from_legacy_result`
   and the in-memory `legacy_result`, even if the legacy result contains
   warnings or `validation_passed is False`.
6. Catch unexpected provider exceptions and return `failed` with one opaque
   reason code `provider_execution_failed`; do not include a traceback in the
   public result.

Export `ComputeRunService` from `core.compute.__init__`.  Do not import any
module matching `analysis_evidence`, `project_workflow`, `agent_workflow`,
`rag`, or `joint` in the new package.

- [ ] **Step 4: Run focused service and contract tests**

Run:

```powershell
python -m pytest -q -p no:cacheprovider tests/test_compute_models.py tests/test_compute_service.py
```

Expected: all focused compute tests pass.

- [ ] **Step 5: Commit the service slice**

```powershell
python scripts/auto_commit.py `
  --message "feat(core): route direct analysis through compute service" `
  --files polynexus/core/compute/__init__.py polynexus/core/compute/service.py tests/test_compute_service.py
```

Expected: one local commit with only the direct-run service boundary.

## Task 4: Move the existing human and machine single-run entries onto the façade

**Files:**
- Modify: `polynexus/cli/parser.py`
- Modify: `polynexus/cli/run_single_service.py`
- Modify: `polynexus/gui/main_window_workers.py`
- Modify: `polynexus/gui/main_window_run_mixin.py`
- Modify: `tests/test_cli_parser.py`
- Modify: `tests/test_cli_run_single_service.py`
- Modify: `tests/test_main_window_workers.py`

- [ ] **Step 1: Add failing CLI/GUI route tests**

Add these focused assertions:

```python
def test_cli_parser_accepts_json_for_single_technique() -> None:
    args = build_parser().parse_args(["ir", "sample.csv", "--json"])
    assert args.cmd == "ir"
    assert args.json is True


def test_run_single_json_prints_the_shared_compute_run(tmp_path, capsys) -> None:
    args = SimpleNamespace(cmd="ir", input=str(tmp_path / "x.txt"), output=str(tmp_path / "out"), skip_to=None, json=True)
    (tmp_path / "x.txt").write_text("data", encoding="utf-8")

    code = run_single(args, compute_run_service_factory=FakeComputeRunService)

    assert code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "completed"


def test_analysis_worker_emits_compute_run_from_shared_service(qtbot, tmp_path) -> None:
    worker = AnalysisWorker("ir", str(tmp_path / "x.txt"), str(tmp_path / "out"), compute_service_factory=FakeComputeRunService)
    (tmp_path / "x.txt").write_text("data", encoding="utf-8")
    received: list[object] = []
    worker.finished.connect(received.append)

    worker.run()

    assert received[0].status == "completed"
```

Use a fake service whose `run_direct()` stores its keyword arguments and
returns a real `ComputeRun.completed(...)`.  Extend the existing non-JSON CLI
test to assert that the formatter receives `run.result.metrics`, preserving
the current human-readable output.

- [ ] **Step 2: Run the route tests and observe their intended failure**

Run:

```powershell
python -m pytest -q -p no:cacheprovider tests/test_cli_parser.py tests/test_cli_run_single_service.py tests/test_main_window_workers.py
```

Expected: parser rejects `--json` and worker does not yet emit a `ComputeRun`.

- [ ] **Step 3: Add optional machine-readable output without a duplicate CLI command**

In `parser.py`, add `--json` with `action="store_true"` to each existing
single-technique parser (`saxs`, `dsc`, `ir`, `waxs`, `nmr`).  Do not add a
parallel `compute` command.

In `run_single_service.py`, add a keyword-only dependency injection point:

```python
def run_single(
    args: Any,
    *,
    get_engine_fn: Callable[[str], Any] = get_engine,
    format_technique_result_lines_fn: Callable[[str, str, dict], list[str]] = format_technique_result_lines,
    compute_run_service_factory: Callable[..., ComputeRunService] = ComputeRunService,
) -> int: ...
```

Create the engine once so the existing `--type` configuration remains intact,
then pass that engine to `service.run_direct()`.  On `completed`, print
`json.dumps(run.to_dict(), ensure_ascii=False, sort_keys=True)` and return `0`
when `args.json` is true; otherwise retain the existing formatter over
`run.result.metrics`.  On `needs_input` or `failed`, print one concise status
line to stderr and return `1`.  The old function never prints an evidence
object or manuscript status.

- [ ] **Step 4: Route `AnalysisWorker` through the same service**

Add an optional `compute_service_factory=ComputeRunService` constructor
argument to `AnalysisWorker`.  Replace the direct `engine.run_pipeline(...)`
call with:

```python
service = self.compute_service_factory(
    lambda technique, config=None, submodule_id=None: main_window_module.get_engine(
        technique, config=config, submodule_id=submodule_id,
    )
)
compute_run = service.run_direct(
    technique=self.technique,
    path=self.filepath,
    output_dir=self.output_dir,
    config=self.config,
    submodule_id=self.submodule_id,
    engine=engine,
    pipeline_options=pipeline_kwargs,
)
self.compute_run = compute_run
if compute_run.status != "completed":
    self.error_msg.emit(", ".join(compute_run.reasons) or compute_run.status)
    return
self.finished.emit(compute_run)
```

Keep `self.engine` assigned to the exact engine used by the service so cached
replot behavior survives unchanged.

In `main_window_run_mixin.py`, add a private unwrapping helper that validates
the completed `ComputeRun`, saves it in `self._compute_runs[technique]`, and
returns `compute_run.legacy_result`.  Call it as the first line of
`_on_finished` and `_on_replot_finished`; all existing result-table, plot,
transaction, and persistence consumers continue to receive the legacy result
for this bridge slice.  A run with no `legacy_result` is a worker error and is
not silently published.

- [ ] **Step 5: Run the route tests after implementation**

Run:

```powershell
python -m pytest -q -p no:cacheprovider tests/test_cli_parser.py tests/test_cli_run_single_service.py tests/test_main_window_workers.py tests/test_compute_models.py tests/test_compute_service.py
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit the shared direct-run entries**

```powershell
python scripts/auto_commit.py `
  --message "feat(app): share direct analysis run contract" `
  --files polynexus/cli/parser.py polynexus/cli/run_single_service.py polynexus/gui/main_window_workers.py polynexus/gui/main_window_run_mixin.py tests/test_cli_parser.py tests/test_cli_run_single_service.py tests/test_main_window_workers.py
```

Expected: one local commit containing only direct-run entry-point routing.

## Task 5: Prove the first vertical slice and record its limitation

**Files:**
- Modify: `docs/agent/tasks/2026-08-24-core-foundation-direct-run.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Add an import-boundary regression test**

Extend `tests/test_compute_service.py` with:

```python
def test_compute_package_has_no_review_or_paper_runtime_imports() -> None:
    import sys

    import polynexus.core.compute as compute

    module_names = set(sys.modules)
    forbidden = (
        "polynexus.core.analysis_evidence",
        "polynexus.core.project_workflow",
        "polynexus.core.agent_workflow",
        "polynexus.core.joint",
        "rag",
    )

    assert compute.ComputeRunService
    assert not any(name == item or name.startswith(f"{item}.") for item in forbidden for name in module_names)
```

Run the test in a new Python/pytest process so unrelated earlier imports cannot
mask a forbidden dependency.

- [ ] **Step 2: Run the structured architecture verification**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-24-core-foundation-direct-run.md --changed --types
git diff --check
```

Expected: task/memory checks, changed-file lint/compile/type selection, quality
gate, preprocessing gate, and whitespace check all exit `0`.

- [ ] **Step 3: Record only durable facts**

Update the task card and `active-work.md` with the exact command outcomes,
commit hashes, and this limitation:

```markdown
The direct envelope is source identity plus format only.  It does not replace
the existing canonical conversion templates, and legacy GUI persistence still
stores the old engine result through the documented compatibility projection.
```

- [ ] **Step 4: Re-run the structured check after the documentation update**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-24-core-foundation-direct-run.md --changed --types
git diff --check
```

Expected: both commands exit `0`.

- [ ] **Step 5: Commit the acceptance record**

```powershell
python scripts/auto_commit.py `
  --message "docs(core): record direct-run foundation acceptance" `
  --files docs/agent/tasks/2026-08-24-core-foundation-direct-run.md docs/agent/memory/active-work.md tests/test_compute_service.py
```

Expected: one local commit containing the acceptance record and its import
boundary regression test; no push, merge, deployment, or data deletion.

## Final acceptance checklist

- [ ] `ComputeRunService` is the sole new façade calling a legacy engine.
- [ ] The first direct path has no import dependency on review, evidence,
  manuscript, Joint, or RAG modules.
- [ ] CLI human output is preserved and `--json` returns the same run object
  that the GUI worker receives.
- [ ] Missing files and unknown techniques are `needs_input`; provider crashes
  are `failed`; provider warnings still return `completed`.
- [ ] Existing algorithms, database schema, chart editor, Origin export,
  evidence workflow, and RAG code are untouched by this slice.
- [ ] Verification and atomic allowlisted commits are recorded before a later
  task starts canonical conversion or deletes legacy modules.

## Spec coverage review

This plan implements migration batch 1 and the protected part of batch 2 from
the approved design: dependency inventory, five-contract foundation, direct
run façade, one CLI/AI path, and Quick Analysis worker routing.  It explicitly
does not implement universal conversion, provider-by-provider numerical
migration, deletion of review/writing systems, or six-sample acceptance; each
needs a separate plan after this vertical slice passes.
