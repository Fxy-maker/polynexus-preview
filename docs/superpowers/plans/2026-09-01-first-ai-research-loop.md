# First AI-Native Research Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one documented Codex-facing entry point run a selected mixed-technique project from canonical conversion through deterministic results, figures, evidence, ARS writing input, and an evidence-grounded manuscript draft.

**Architecture:** Reuse `ProjectWorkflowService.analyze_project`, existing `ComputeRun`/metric manifests, package builders, and Suite paper contracts. Add only a thin first-loop orchestration projection and CLI operation; do not create a second scientific result store. Extend the existing `ProjectAnalysisSummary` projection with package-relative writing/manuscript outputs so CLI, Codex, and GUI adapters consume the same objects.

**Tech Stack:** Python 3.14, dataclasses/JSON contracts, existing project workflow and Suite services, pytest, Ruff, `scripts/verify.py`.

---

## File map

- Modify `polynexus/core/project_workflow/evidence.py` to expose optional writing-input, manuscript, and preflight projections on the existing summary DTO.
- Modify `polynexus/core/project_workflow/service.py` to add one `close_first_loop()` facade that composes existing deterministic project, package, figure, and Suite paper services without recalculation.
- Modify `polynexus/cli/parser.py` and `polynexus/cli/run_project_workflow_service.py` to expose `project-workflow close-loop` as the single machine-readable entry point.
- Modify `polynexus/suite/paper_source.py` and `polynexus/suite/paper_pipeline.py` only where package-relative source or draft projection is missing; preserve existing contracts and hard gates.
- Create `tests/fixtures/first_ai_loop/raw/` with small public CSV fixtures for IR, WAXS, SAXS, and DSC; do not place real user data there.
- Create `tests/test_first_ai_research_loop.py` for the end-to-end contract and failure cases.
- Extend `tests/test_ai_native_project_entrypoint.py`, `tests/test_project_workflow_cli.py`, and `tests/test_project_ars_writing_handoff.py` for cross-entry projections.
- Add `docs/acceptance/2026-09-01-first-ai-research-loop.md` after the fixture and read-only real-project replay pass.

## Task 1: Add the public fixture and red end-to-end contract

**Files:**
- Create: `tests/fixtures/first_ai_loop/raw/IR/PA6-JW-180.csv`
- Create: `tests/fixtures/first_ai_loop/raw/WAXS/PA6-JW-180.dat`
- Create: `tests/fixtures/first_ai_loop/raw/SAXS/PA6-JW-180.csv`
- Create: `tests/fixtures/first_ai_loop/raw/DSC/PA6-JW-180.txt`
- Create: `tests/test_first_ai_research_loop.py`

- [ ] **Step 1: Write the failing CLI contract test**

```python
def test_close_loop_emits_package_writing_input_and_draft(tmp_path: Path, capsys) -> None:
    fixture = copy_fixture(tmp_path)
    args = build_parser().parse_args([
        "project-workflow", "close-loop",
        "--project-root", str(fixture),
        "--paths", "raw/IR/PA6-JW-180.csv", "raw/WAXS/PA6-JW-180.dat",
        "--paths", "raw/SAXS/PA6-JW-180.csv", "raw/DSC/PA6-JW-180.txt",
        "--question", "Compare the thermal and structural response of PA6 JW.",
        "--package-id", "first-loop-fixture",
    ])
    code = run_project_workflow(args)
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["operation"] == "close-loop"
    assert payload["analysis"]["package"]["path"]
    assert payload["analysis"]["writing_input"]["package_id"] == "first-loop-fixture"
    assert payload["analysis"]["manuscript"]["package_id"] == "first-loop-fixture"
```

- [ ] **Step 2: Add fixture writers and run the test**

Run: `python -m pytest -p no:cacheprovider -q tests/test_first_ai_research_loop.py::test_close_loop_emits_package_writing_input_and_draft`

Expected: FAIL because `close-loop` is not a parser operation and the summary has no writing/manuscript projection.

- [ ] **Step 3: Add explicit failure tests before implementation**

```python
def test_close_loop_keeps_missing_technique_explicit(tmp_path: Path) -> None:
    fixture = copy_fixture(tmp_path, include_nmr=False)
    summary = ProjectWorkflowService.open(fixture).close_first_loop(
        question="Prepare mixed evidence", data_scope=selected_paths(fixture)
    )
    assert summary.package is not None
    assert summary.reason_codes
    assert summary.to_dict()["missing_techniques"] == ["nmr"]
```

- [ ] **Step 4: Run both tests and record the expected red state**

Run: `python -m pytest -p no:cacheprovider -q tests/test_first_ai_research_loop.py`

Expected: FAIL only at the not-yet-defined `close-loop` contract, with no changes to provider algorithms.

## Task 2: Complete the shared first-loop summary projection

**Files:**
- Modify: `polynexus/core/project_workflow/evidence.py:ProjectAnalysisSummary`
- Modify: `polynexus/core/project_workflow/service.py:ProjectWorkflowService`
- Test: `tests/test_first_ai_research_loop.py`

- [ ] **Step 1: Extend the existing summary DTO without copying scientific values**

Add optional fields and serialize them as package-relative projections:

```python
writing_input: Mapping[str, Any] | None = None
manuscript: Mapping[str, Any] | None = None
preflight: Mapping[str, Any] | None = None
missing_techniques: tuple[str, ...] = ()
```

`to_dict()` must emit `writing_input`, `manuscript`, `preflight`, and sorted `missing_techniques`; existing callers must keep their current fields unchanged.

- [ ] **Step 2: Implement `close_first_loop()` as a composition facade**

The method must:

1. Call `analyze_project()` once with the caller's explicit paths.
2. Return the summary unchanged when computation is blocked or no package exists.
3. Load the package through `build_manuscript_source()`.
4. Build the draft through `assemble_manuscript()` using package projections; never call a provider or reparse raw files.
5. Run structural `preflight_manuscript()` for the internal draft and store its DTO.
6. Preserve `review_required`/warnings as status information instead of discarding finite results.

The implementation must use an output directory outside the immutable evidence package, such as `.polynexus/manuscript/{package_id}`, and write only package-relative references into the summary.

- [ ] **Step 3: Make the end-to-end test pass**

Run: `python -m pytest -p no:cacheprovider -q tests/test_first_ai_research_loop.py::test_close_loop_emits_package_writing_input_and_draft tests/test_first_ai_research_loop.py::test_close_loop_keeps_missing_technique_explicit`

Expected: PASS; the fixture package contains runs, result tables, figures, writing evidence, and the draft projection.

- [ ] **Step 4: Commit the DTO/facade slice**

Run `scripts/auto_commit.py` with message `feat(research-loop): compose shared first-loop summary` and an explicit allowlist containing only the changed DTO/service file and the focused test.

## Task 3: Expose one Codex/CLI entry point and preserve all existing routes

**Files:**
- Modify: `polynexus/cli/parser.py`
- Modify: `polynexus/cli/run_project_workflow_service.py`
- Modify: `tests/test_project_workflow_cli.py`
- Modify: `tests/test_ai_native_project_entrypoint.py`

- [ ] **Step 1: Add the parser operation and arguments**

Add `close-loop` to the `project-workflow` operation choices and add:

```python
ppw.add_argument("--manuscript-output", default=None)
```

The existing `--paths`, `--question`, and `--package-id` arguments remain the source of scope and project identity.

- [ ] **Step 2: Route the operation through the shared service**

The CLI handler must call `workflow.close_first_loop(...)` inside the existing stdout isolation context and emit exactly one JSON envelope with `operation`, `status`, `reason_codes`, and `analysis`. It must return exit code `0` for `completed` or `review_required` computation and `2` for blocked input.

- [ ] **Step 3: Add cross-entry assertions**

```python
def test_close_loop_cli_and_summary_share_run_ids(tmp_path: Path, capsys) -> None:
    fixture = copy_fixture(tmp_path)
    args = _args("close-loop", fixture, paths=selected_paths(fixture), question="Prepare evidence")
    assert run_project_workflow(args) == 0
    payload = _one_envelope(capsys)
    analysis = payload["analysis"]
    assert {run["run_id"] for run in analysis["runs"]}
    assert analysis["package"]["run_ids"] == [run["run_id"] for run in analysis["runs"]]
    assert analysis["writing_input"]["package_id"] == analysis["package"]["package_id"]
```

- [ ] **Step 4: Run the affected CLI and AI matrices**

Run: `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_cli.py tests/test_ai_native_project_entrypoint.py tests/test_first_ai_research_loop.py`

Expected: PASS, with all pre-existing `inspect`, `plan`, `run`, `package`, and `analyze-project` behavior unchanged.

## Task 4: Verify evidence, figures, tables, and manuscript binding

**Files:**
- Modify: `polynexus/suite/paper_source.py` only if package-relative files are not exposed by the existing source DTO.
- Modify: `polynexus/suite/paper_pipeline.py` only if draft assembly drops existing evidence bindings.
- Modify: `tests/test_project_ars_writing_handoff.py`
- Modify: `tests/test_paper_pipeline.py`
- Test: `tests/test_first_ai_research_loop.py`

- [ ] **Step 1: Add binding tests**

```python
def test_first_loop_draft_claims_resolve_to_package_metrics(tmp_path: Path) -> None:
    summary = run_fixture_loop(tmp_path)
    source = summary.writing_input
    manuscript = summary.manuscript
    assert source and manuscript
    metric_ids = {item["metric_id"] for item in source["citation_metrics"]}
    for claim in manuscript["claims"]:
        assert set(claim["metric_ids"]).issubset(metric_ids)
    assert manuscript["package_id"] == source["package_id"]
```

- [ ] **Step 2: Assert figure and table provenance**

The fixture test must load `figure-index.json` and `result-tables.json`, assert every visible figure references an existing run, and assert every table row has a source path. It must not compare scientific values to hard-coded claims.

- [ ] **Step 3: Run the focused package/paper matrix**

Run: `python -m pytest -p no:cacheprovider -q tests/test_project_ars_writing_handoff.py tests/test_paper_pipeline.py tests/test_paper_bundle.py tests/test_first_ai_research_loop.py`

Expected: PASS; no manuscript function reads or recomputes raw inputs.

- [ ] **Step 4: Commit the package/ARS binding slice**

Run `scripts/auto_commit.py` with message `feat(research-loop): bind first-loop evidence to manuscript input` and an explicit allowlist for the changed Suite files and tests.

## Task 5: Real-project read-only replay and acceptance record

**Files:**
- Create: `docs/acceptance/2026-09-01-first-ai-research-loop.md`
- Modify: `docs/agent/tasks/2026-09-01-first-ai-research-loop.md`
- Do not modify: real raw data, old evidence packages, personal manuscripts, `active_run.json`, `runs/`, or `tests/_tmp_phase3/`.

- [ ] **Step 1: Run the public fixture in a clean temporary project**

Run the documented `project-workflow close-loop` command and save only the command summary, output paths, hashes, and test result in the acceptance note.

- [ ] **Step 2: Replay one real mixed-technique project read-only**

Use explicit `--paths` for the selected group. Record source SHA-256 values before and after. The replay may remain `review_required`; that is not a failure if every finite deterministic result is preserved and all missing/failed inputs are explicit.

- [ ] **Step 3: Inspect the complete output contract**

Check run count, result-table count, figure index, writing input, manuscript JSON, and preflight. Confirm all paths in the package and writing input are package-relative and all source hashes match.

- [ ] **Step 4: Write the acceptance note**

Record exact command outcomes, real-project limitations, absent techniques such as NMR when absent, and the fact that no raw file was changed. Do not describe the result as publication-ready or release-green.

## Task 6: Full verification and handoff to open-source preparation

**Files:**
- Modify: `docs/agent/tasks/2026-09-01-first-ai-research-loop.md`
- Modify: `docs/agent/memory/current-state.md` and `docs/agent/memory/active-work.md` only with durable status and links to the acceptance note.

- [ ] **Step 1: Run task-scoped verification**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-09-01-first-ai-research-loop.md --changed --types
```

Expected: the task-scoped quality and type checks pass.

- [ ] **Step 2: Run release-boundary verification**

```powershell
python scripts/verify.py --changed --types --full --boundary
git diff --check
```

Expected: the first-loop changes pass; unrelated historical failures remain listed rather than hidden.

- [ ] **Step 3: Create the final allowlisted checkpoint**

Run `scripts/auto_commit.py` with message `feat(research-loop): complete first mixed-technique AI path` and an explicit allowlist containing only task-scoped source files, tests, task/acceptance/memory records. Never include fixture-generated outputs or real data.

- [ ] **Step 4: Mark open-source preparation as the next separate task**

Do not start license/dependency/release edits in this task. The completion report must link the open-source follow-up and state the remaining historical full-suite failures and human scientific review boundary.
