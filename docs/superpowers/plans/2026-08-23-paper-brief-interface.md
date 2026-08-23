# Paper-brief Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic `PaperBrief -> ManuscriptPlan` interface that pins one ARS/Codex writing plan to one immutable evidence-package snapshot, without modifying analysis, raw data, or package contents.

**Architecture:** A focused core module parses a versioned brief, loads the existing technique-neutral evidence view, validates every requested item against that view, and emits a hashable plan DTO. The existing `project-workflow` CLI will call exactly that core builder and write a separate JSON export through an atomic file replacement.

**Tech Stack:** Python 3.10+, frozen dataclasses, JSON, SHA-256, argparse, pytest, existing `EvidencePackageView`.

---

## File structure

- Create `polynexus/core/project_workflow/manuscript_plan.py`: `PaperBrief`, `ManuscriptPlan`, strict package pin validation, and the deterministic plan builder.
- Modify `polynexus/core/project_workflow/__init__.py`: re-export the shared core DTOs and builder.
- Modify `polynexus/cli/parser.py`: add the `manuscript-plan` project-workflow operation with its three inputs.
- Modify `polynexus/cli/run_project_workflow_service.py`: read JSON, call the core builder, atomically export JSON, and return one normal CLI envelope.
- Create `tests/test_manuscript_plan.py`: core behavior and failure-boundary tests with an actual minimal evidence-package directory.
- Modify `tests/test_project_workflow_cli.py`: parser and JSON-only CLI export tests.
- Modify `docs/agent/tasks/2026-08-23-paper-brief-interface.md` and `docs/agent/memory/active-work.md`: durable status and verification evidence.

### Task 1: Core plan contract and happy path

**Files:**

- Create: `polynexus/core/project_workflow/manuscript_plan.py`
- Create: `tests/test_manuscript_plan.py`
- Modify: `polynexus/core/project_workflow/__init__.py`

- [ ] **Step 1: Write a failing core selection test**

Create a package fixture that satisfies `load_evidence_package_view`, includes a `figure-index.json` entry `dsc`, a results candidate `metric-dsc`, a diagnostic `metric-diagnostic`, and an `ars-writing-input.json` human review action. Calculate and store `manifest["package_hash"]` as the SHA-256 of canonical manifest JSON without the `package_hash` field. Then add:

```python
def test_build_manuscript_plan_pins_package_and_inherits_boundaries(tmp_path: Path) -> None:
    plan = build_manuscript_plan(
        _package(tmp_path),
        PaperBrief.from_dict({
            "version": 1,
            "research_question": "Compare PA6 crystallization kinetics.",
            "comparison_scope": {
                "selected_techniques": ["dsc"],
                "selected_evidence_ids": ["run-dsc:step"],
                "selected_metric_ids": ["metric-dsc", "metric-diagnostic"],
            },
            "figure_budget": {"main_max": 1, "supporting_max": 1},
            "figure_intent": {"dsc": "main"},
            "technique_roles": {"dsc": "observed_result"},
        }),
    )

    assert plan.status == "draft"
    assert plan.package["package_id"] == "pa6"
    assert plan.selection["results_metric_ids"] == ("metric-dsc",)
    assert plan.selection["discussion_metric_ids"] == ("metric-diagnostic",)
    assert plan.selection["main_figure_ids"] == ("dsc",)
    assert plan.writing_boundaries["limitations"] == ("background_review",)
    assert plan.writing_boundaries["human_review"][0]["action"] == "human_scientific_review"
```

- [ ] **Step 2: Run the test and observe red**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_manuscript_plan.py::test_build_manuscript_plan_pins_package_and_inherits_boundaries
```

Expected: collection fails because `polynexus.core.project_workflow.manuscript_plan` does not exist.

- [ ] **Step 3: Add the minimal public DTOs and builder**

Create `manuscript_plan.py` with these exact public entry points:

```python
@dataclass(frozen=True)
class PaperBrief:
    version: int
    title_hint: str | None
    research_question: str
    selected_techniques: tuple[str, ...]
    selected_evidence_ids: tuple[str, ...]
    selected_metric_ids: tuple[str, ...]
    main_max: int
    supporting_max: int
    figure_intent: Mapping[str, str]
    technique_roles: Mapping[str, str]
    notes: str | None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PaperBrief": ...

@dataclass(frozen=True)
class ManuscriptPlan:
    version: int
    plan_id: str
    plan_hash: str
    package: Mapping[str, Any]
    brief: Mapping[str, Any]
    selection: Mapping[str, tuple[str, ...]]
    writing_boundaries: Mapping[str, Any]
    status: str = "draft"

    def to_dict(self) -> dict[str, Any]: ...

def build_manuscript_plan(package_path: str | Path, brief: PaperBrief) -> ManuscriptPlan: ...
```

Use `load_evidence_package_view(package_path)` as the source for all selection values. For an empty scope list, select all existing package values. Split metrics by their existing `writing_eligibility`; never change eligibility. Copy limitations and human-review items unchanged. Create `plan_id` and `plan_hash` from a canonical JSON object that includes the exact package ID, version, hash, normalized brief, selection, and boundaries. Re-export all three symbols from `project_workflow/__init__.py`.

- [ ] **Step 4: Run the happy-path test and observe green**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_manuscript_plan.py::test_build_manuscript_plan_pins_package_and_inherits_boundaries
```

Expected: PASS.

- [ ] **Step 5: Create the first local checkpoint**

Run:

```powershell
python scripts/auto_commit.py --message "feat(workflow): add manuscript plan builder" --files polynexus/core/project_workflow/manuscript_plan.py polynexus/core/project_workflow/__init__.py tests/test_manuscript_plan.py
```

Expected: one local commit with only the listed files; no push.

### Task 2: Fail-closed paper-brief validation

**Files:**

- Modify: `tests/test_manuscript_plan.py`
- Modify: `polynexus/core/project_workflow/manuscript_plan.py`

- [ ] **Step 1: Write failing validation tests**

Add separate tests that prove the contract rejects a tampered package pin, missing metric, promotion of a diagnostic metric to Results, missing figure, and figure-budget overflow:

```python
def test_builder_rejects_a_tampered_package_hash(tmp_path: Path) -> None:
    package = _package(tmp_path)
    manifest = _read_json(package / "manifest.json")
    manifest["package_hash"] = "tampered"
    _write_json(package / "manifest.json", manifest)
    with pytest.raises(ValueError, match="package hash"):
        build_manuscript_plan(package, _brief())

def test_builder_rejects_unknown_and_promoted_metric_references(tmp_path: Path) -> None:
    package = _package(tmp_path)
    with pytest.raises(ValueError, match="metric"):
        build_manuscript_plan(package, _brief(selected_metric_ids=("missing",)))
    with pytest.raises(ValueError, match="Results"):
        build_manuscript_plan(package, _brief(results_metric_ids=("metric-diagnostic",)))

def test_builder_rejects_missing_figure_and_figure_budget_overflow(tmp_path: Path) -> None:
    package = _package(tmp_path)
    with pytest.raises(ValueError, match="figure"):
        build_manuscript_plan(package, _brief(figure_intent={"missing": "main"}))
    with pytest.raises(ValueError, match="budget"):
        build_manuscript_plan(package, _brief(main_max=0, figure_intent={"dsc": "main"}))
```

- [ ] **Step 2: Run validation tests and observe red**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_manuscript_plan.py -k rejects
```

Expected: FAIL because the Task 1 builder has no strict package, reference, promotion, or budget validation.

- [ ] **Step 3: Implement only the required validation**

Add helpers equivalent to:

```python
def _validate_package_pin(root: Path, manifest: Mapping[str, Any]) -> str:
    expected = str(manifest.get("package_hash", ""))
    unsigned = {key: value for key, value in manifest.items() if key != "package_hash"}
    actual = sha256(canonical_json(unsigned).encode("utf-8")).hexdigest()
    if not expected or not hmac.compare_digest(expected, actual):
        raise ValueError("evidence package hash is invalid")
    return expected

def _require_known(requested: Iterable[str], known: Collection[str], kind: str) -> tuple[str, ...]: ...
```

`PaperBrief.from_dict` must reject empty research questions, versions other than `1`, negative budgets, non-string selections, unsupported roles, unsupported figure intents, source/raw-data paths, analysis parameters, and a supplied `status`. Validate requested techniques, evidence IDs, metric IDs, explicit results metric IDs, explicit discussion metric IDs, and figure IDs against the package view. Results references must have `results_candidate` eligibility; Discussion references must not. Permit only `main` and `supporting` figure roles and reject counts beyond either budget.

- [ ] **Step 4: Run the core suite and observe green**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_manuscript_plan.py
```

Expected: PASS.

- [ ] **Step 5: Checkpoint the validation boundary**

Run:

```powershell
python scripts/auto_commit.py --message "feat(workflow): validate paper brief selections" --files polynexus/core/project_workflow/manuscript_plan.py tests/test_manuscript_plan.py
```

Expected: one local commit with only the listed files; no push.

### Task 3: JSON-only project-workflow export

**Files:**

- Modify: `polynexus/cli/parser.py`
- Modify: `polynexus/cli/run_project_workflow_service.py`
- Modify: `tests/test_project_workflow_cli.py`

- [ ] **Step 1: Write failing parser and export tests**

Add `"manuscript-plan"` to the parser-operation parametrization. Add this test using the Task 1 package helper and brief helper:

```python
def test_project_workflow_cli_exports_plan_outside_the_package(capsys, tmp_path: Path) -> None:
    package = _package(tmp_path)
    brief = _write_brief(tmp_path / "brief.json")
    output = tmp_path / "exports" / "manuscript-plan.json"

    assert run_project_workflow(_args(
        "manuscript-plan", tmp_path, package=str(package), brief=str(brief), output=str(output)
    )) == 0

    payload = _one_envelope(capsys)
    assert payload["operation"] == "manuscript-plan"
    assert payload["status"] == "completed"
    assert Path(payload["manuscript_plan"]["path"]) == output
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "draft"
    assert not (package / "manuscript-plan.json").exists()

def test_project_workflow_cli_blocks_missing_paper_brief(capsys, tmp_path: Path) -> None:
    assert run_project_workflow(_args("manuscript-plan", tmp_path, package=str(_package(tmp_path)))) == 2
    assert _one_envelope(capsys)["reason_codes"] == ["paper_brief_invalid"]
```

- [ ] **Step 2: Run the CLI tests and observe red**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_workflow_cli.py -k manuscript_plan
```

Expected: FAIL because argparse rejects the operation and the service has no branch for it.

- [ ] **Step 3: Implement the thin CLI adapter**

In `parser.py`, add the operation and these arguments:

```python
"manuscript-plan"
ppw.add_argument("--package", default=None, help="Immutable evidence package directory for manuscript-plan")
ppw.add_argument("--brief", default=None, help="PaperBrief JSON path for manuscript-plan")
ppw.add_argument("--output", default=None, help="Destination JSON path for manuscript-plan")
```

In `run_project_workflow_service.py`, handle this operation before opening `ProjectWorkflowService`, because it is package-scoped rather than project-scoped. Read `--brief` with `_read_object`, call `PaperBrief.from_dict`, call `build_manuscript_plan`, and write exactly `plan.to_dict()` to `--output`. Reject an empty output path or a resolved output path inside the resolved package root. Write to a temporary sibling, then `Path.replace` it. Emit a single completed envelope:

```python
return _emit(operation, "completed", manuscript_plan={"path": str(output), **plan.to_dict()})
```

Return only `paper_brief_invalid`, `evidence_package_invalid`, or `manuscript_plan_output_invalid` for validation errors. Do not create a workspace, run an analysis provider, or mutate package files.

- [ ] **Step 4: Run the CLI tests and observe green**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_workflow_cli.py -k manuscript_plan
```

Expected: PASS.

- [ ] **Step 5: Checkpoint the CLI boundary**

Run:

```powershell
python scripts/auto_commit.py --message "feat(cli): export manuscript plans" --files polynexus/cli/parser.py polynexus/cli/run_project_workflow_service.py tests/test_project_workflow_cli.py
```

Expected: one local commit with only the listed files; no push.

### Task 4: Shared-contract verification and durable record

**Files:**

- Modify: `docs/agent/tasks/2026-08-23-paper-brief-interface.md`
- Modify: `docs/agent/memory/active-work.md`
- Test: `tests/test_manuscript_plan.py`
- Test: `tests/test_project_workflow_cli.py`
- Test: `tests/test_project_ars_writing_handoff.py`
- Test: `tests/test_evidence_package_view.py`

- [ ] **Step 1: Run the focused shared-contract matrix**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_manuscript_plan.py tests/test_project_workflow_cli.py tests/test_project_ars_writing_handoff.py tests/test_evidence_package_view.py
```

Expected: PASS. The new interface must not weaken old package readers; old package fixtures outside `test_manuscript_plan.py` do not need a package hash merely because they do not use the new interface.

- [ ] **Step 2: Update task and project memory**

Set the task status to `implementation_complete_review_required`. Under Completion evidence record the exact focused-test count, structured verifier result, and the fact that no real data was changed. Add this concise durable active-work entry:

```text
PaperBrief/ManuscriptPlan is a separate ARS/CLI export pinned to immutable package hash. V1 does not mutate packages, rerun analysis, generate prose, or provide GUI editing. Architecture and scientific-boundary review remain required before merge.
```

- [ ] **Step 3: Run structured checks**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-23-paper-brief-interface.md --changed --types
git diff --check
```

Expected: task-scoped quality, preprocessing, compilation, and whitespace checks pass.

- [ ] **Step 4: Checkpoint documentation and verification evidence**

Run:

```powershell
python scripts/auto_commit.py --message "docs(workflow): record paper brief verification" --files docs/agent/tasks/2026-08-23-paper-brief-interface.md docs/agent/memory/active-work.md
```

Expected: one local commit with only the listed files; no push.

## Plan self-review

- Spec coverage: Tasks 1–2 implement package pinning, scoped selection, inherited limitations, eligibility preservation, review retention, and every fail-closed rule. Task 3 provides the same shared core contract to AI/CLI. Task 4 verifies the package/ARS producer contracts and documents the review boundary.
- Scope: GUI editing, ARS prose generation, human approval persistence, and new figure production remain explicitly deferred.
- Type consistency: every route uses `PaperBrief.from_dict`, `build_manuscript_plan`, and `ManuscriptPlan.to_dict`; the CLI has no independent selection logic.
- Placeholder scan: no open requirements, broad cleanup, or implementation placeholders remain.
