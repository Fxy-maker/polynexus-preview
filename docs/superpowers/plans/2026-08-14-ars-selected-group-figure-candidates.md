# ARS-Selected Group Figure Candidates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate at most two traceable FTIR manuscript figure candidates from groups selected by ARS before project analysis.

**Architecture:** Keep group selection, rendering, and evidence projection separate. `selection.py` validates ARS group IDs against the current inventory; `ir_group_figures.py` reads and preprocesses only selected FTIR sources then renders conservative overlays/trends; `service.py` coordinates existing provider runs and attaches a JSON-safe figure manifest to the project summary and evidence package.

**Tech Stack:** Python dataclasses, existing project workflow contracts, NumPy, Matplotlib, IR reader/preprocessor, pytest.

---

## File Structure

- Create `polynexus/core/project_workflow/selection.py`: immutable ARS selection request and candidate-figure DTOs, request validation, deterministic selection ID.
- Create `polynexus/core/project_workflow/ir_group_figures.py`: FTIR-only group data loading, shared-grid overlay render, shared metric-trend render, local manifest writing.
- Modify `polynexus/core/project_workflow/service.py`: accept an optional selection request, run selected artifact paths only, invoke FTIR candidate rendering after validated project runs.
- Modify `polynexus/core/project_workflow/evidence.py`: expose candidate figures and omissions through `ProjectAnalysisSummary`.
- Modify `polynexus/core/project_workflow/package.py`: copy the candidate manifest/assets and name the selected main figures in writing input.
- Modify `polynexus/cli/parser.py` and `polynexus/cli/run_project_workflow_service.py`: accept `--figure-selection <json>` for `analyze-project`.
- Create `tests/test_ars_group_figure_candidates.py`: selection, render, suppression, package, and CLI contracts.
- Create task acceptance and update active-work memory after verification.

### Task 1: Immutable ARS Selection Contract

**Files:**
- Create: `polynexus/core/project_workflow/selection.py`
- Modify: `polynexus/core/project_workflow/__init__.py`
- Test: `tests/test_ars_group_figure_candidates.py`

- [ ] **Step 1: Write the failing request-validation tests**

```python
def test_figure_selection_requires_unique_known_groups() -> None:
    request = FigureSelectionRequest.create(
        question="Compare PA6 series",
        selected_groups=("ir:pa6-jw:temperature_C", "ir:pa6-jw:temperature_C"),
        figure_intent="compare_groups",
    )
    assert request.reason_codes == ("selected_groups_duplicate",)

def test_figure_selection_blocks_mixed_condition_kinds() -> None:
    result = resolve_figure_selection(request, candidates)
    assert result.status == "blocked"
    assert "selected_groups_condition_kind_mismatch" in result.reason_codes
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `python -m pytest tests/test_ars_group_figure_candidates.py -q`

Expected: FAIL because `FigureSelectionRequest` and `resolve_figure_selection` do not exist.

- [ ] **Step 3: Implement JSON-safe selection DTOs**

```python
@dataclass(frozen=True)
class FigureSelectionRequest:
    question: str
    selected_groups: tuple[str, ...]
    figure_intent: str = "describe_group"
    main_figure_limit: int = 2

    @classmethod
    def create(cls, **values: object) -> "FigureSelectionRequest": ...

@dataclass(frozen=True)
class ResolvedFigureSelection:
    selection_id: str
    status: str
    groups: tuple[CandidateExperimentGroup, ...]
    reason_codes: tuple[str, ...] = ()
```

`resolve_figure_selection()` must reject unknown IDs, duplicate IDs, an intent
outside `describe_group|compare_groups|show_trend`, a limit outside `1|2`,
mixed techniques, mixed condition kinds, and intent/count mismatch. It returns
group artifact paths without relying on labels.

- [ ] **Step 4: Run the contract tests to verify GREEN**

Run: `python -m pytest tests/test_ars_group_figure_candidates.py -q`

Expected: PASS for request validation and deterministic selection IDs.

- [ ] **Step 5: Commit the selection contract**

```powershell
python scripts/auto_commit.py --message "feat(project): add ARS figure selection contract" --files polynexus/core/project_workflow/selection.py polynexus/core/project_workflow/__init__.py tests/test_ars_group_figure_candidates.py
```

### Task 2: FTIR Group Overlay Renderer

**Files:**
- Create: `polynexus/core/project_workflow/ir_group_figures.py`
- Test: `tests/test_ars_group_figure_candidates.py`

- [ ] **Step 1: Write the failing overlay test**

```python
def test_render_ftir_group_overlay_uses_only_selected_sources(tmp_path: Path) -> None:
    result = render_ftir_group_candidates(
        selection=resolved_jw,
        output_dir=tmp_path / "figures",
        source_runs=(),
    )
    assert result.main_candidates[0].kind == "group_overlay"
    assert Path(result.main_candidates[0].paths[0]).is_file()
    assert result.main_candidates[0].source_artifacts == (
        "raw/PA6-JW-30.csv", "raw/PA6-JW-40.csv",
    )
```

- [ ] **Step 2: Run the test to verify RED**

Run: `python -m pytest tests/test_ars_group_figure_candidates.py::test_render_ftir_group_overlay_uses_only_selected_sources -q`

Expected: FAIL because the renderer does not exist.

- [ ] **Step 3: Implement loading, preprocessing, and overlay rendering**

```python
def render_ftir_group_candidates(
    *, selection: ResolvedFigureSelection, output_dir: Path,
    source_runs: tuple[ProjectWorkflowRun, ...],
) -> FigureCandidateSet:
    spectra = _load_selected_ftir_spectra(selection.groups)
    overlay = _render_overlay(spectra, selection, output_dir / "main")
    return FigureCandidateSet.create(selection, main_candidates=(overlay,))
```

Load each source with `load_spectrum`, normalize to absorbance only when the
reader supplies it, apply the existing `preprocess_pipeline`, sort by the
candidate condition values, interpolate only onto the overlap grid, invert the
wavenumber axis, and write PNG plus SVG below `.polynexus/figures/<selection-id>/main`.
Return `group_overlay_insufficient_usable_spectra` instead of a figure when
fewer than two valid spectra remain.

- [ ] **Step 4: Run overlay and existing project tests to verify GREEN**

Run: `python -m pytest tests/test_ars_group_figure_candidates.py tests/test_ai_project_candidate_groups.py -q`

Expected: PASS; unselected source data is absent from overlay provenance.

- [ ] **Step 5: Commit the overlay renderer**

```powershell
python scripts/auto_commit.py --message "feat(project): render selected FTIR group overlays" --files polynexus/core/project_workflow/ir_group_figures.py tests/test_ars_group_figure_candidates.py
```

### Task 3: Conservative Metric Trend

**Files:**
- Modify: `polynexus/core/project_workflow/ir_group_figures.py`
- Test: `tests/test_ars_group_figure_candidates.py`

- [ ] **Step 1: Write the failing trend and suppression tests**

```python
def test_render_ftir_trend_requires_common_finite_xc_metric(tmp_path: Path) -> None:
    figures = render_ftir_group_candidates(selection=resolved_jw, output_dir=tmp_path, source_runs=runs_with_xc)
    assert [candidate.kind for candidate in figures.main_candidates] == ["group_overlay", "metric_trend"]

def test_render_ftir_trend_is_suppressed_for_missing_metric(tmp_path: Path) -> None:
    figures = render_ftir_group_candidates(selection=resolved_jw, output_dir=tmp_path, source_runs=runs_without_xc)
    assert "metric_trend_metric_unavailable" in figures.omission_reasons
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `python -m pytest tests/test_ars_group_figure_candidates.py -q`

Expected: FAIL because no metric trend is emitted or suppression recorded.

- [ ] **Step 3: Implement a strict metric extractor and trend renderer**

```python
def _common_ftir_metric(selection: ResolvedFigureSelection, runs: tuple[ProjectWorkflowRun, ...]) -> MetricSeries | None:
    # V1 accepts only finite per-artifact IR Xc_pct with one value per condition.
    ...
```

Map source artifacts to provider step summaries. Accept only finite `Xc_pct`
values with a recorded method and exactly one value for every selected
condition. Suppress for duplicate/missing conditions, missing/non-finite
metrics, or a source run that is not validated. The trend is always
`review_required` when IR source runs are review-bound and never changes their
scientific limitations.

- [ ] **Step 4: Run trend tests to verify GREEN**

Run: `python -m pytest tests/test_ars_group_figure_candidates.py -q`

Expected: PASS for valid `Xc_pct` trends and each suppression path.

- [ ] **Step 5: Commit the trend renderer**

```powershell
python scripts/auto_commit.py --message "feat(project): add conservative FTIR trends" --files polynexus/core/project_workflow/ir_group_figures.py tests/test_ars_group_figure_candidates.py
```

### Task 4: Project Workflow and Candidate Manifest

**Files:**
- Modify: `polynexus/core/project_workflow/service.py`
- Modify: `polynexus/core/project_workflow/evidence.py`
- Test: `tests/test_ars_group_figure_candidates.py`

- [ ] **Step 1: Write the failing orchestration test**

```python
def test_analyze_project_with_ars_selection_runs_selected_group_and_limits_main_figures(tmp_path: Path) -> None:
    summary = service.analyze_project(question="Compare JW", figure_selection=request)
    payload = summary.to_dict()
    assert payload["selected_groups"] == ["ir:pa6-jw:temperature_C"]
    assert len(payload["figure_candidates"]["main_candidates"]) <= 2
    assert calls == ["PA6-JW-30.csv", "PA6-JW-40.csv"]
```

- [ ] **Step 2: Run the test to verify RED**

Run: `python -m pytest tests/test_ars_group_figure_candidates.py::test_analyze_project_with_ars_selection_runs_selected_group_and_limits_main_figures -q`

Expected: FAIL because `analyze_project` lacks `figure_selection`.

- [ ] **Step 3: Coordinate selection and manifest persistence**

```python
def analyze_project(..., figure_selection: FigureSelectionRequest | None = None) -> ProjectAnalysisSummary:
    candidates = candidate_groups(graph.artifacts)
    resolved = resolve_figure_selection(figure_selection, candidates) if figure_selection else None
    if resolved and resolved.status == "blocked": return self._blocked_selection_summary(resolved)
    graph = self._graph_for_selected_groups(graph, resolved) if resolved else graph
    runs = self._run_grouped_artifacts(...)
    figure_candidates = self._render_selected_group_figures(resolved, runs) if resolved else None
```

Persist a canonical `manifest.json` through `ProjectWorkspace.write_json`,
include source artifact paths, group status, candidate roles, source run IDs,
limits, and omission reasons. `ProjectAnalysisSummary.to_dict()` must include
`selected_groups` and `figure_candidates`; no selection means these fields are
empty/null and preserves existing behavior.

- [ ] **Step 4: Run the workflow matrix to verify GREEN**

Run: `python -m pytest tests/test_ars_group_figure_candidates.py tests/test_ai_project_candidate_groups.py tests/test_ai_native_project_entrypoint.py tests/test_project_workflow_service.py -q`

Expected: PASS; invalid selection has no provider call and main candidates are
bounded by the requested limit.

- [ ] **Step 5: Commit orchestration and manifest**

```powershell
python scripts/auto_commit.py --message "feat(project): orchestrate ARS group figures" --files polynexus/core/project_workflow/service.py polynexus/core/project_workflow/evidence.py tests/test_ars_group_figure_candidates.py
```

### Task 5: Evidence Package and CLI Projection

**Files:**
- Modify: `polynexus/core/project_workflow/package.py`
- Modify: `polynexus/cli/parser.py`
- Modify: `polynexus/cli/run_project_workflow_service.py`
- Test: `tests/test_ars_group_figure_candidates.py`

- [ ] **Step 1: Write failing package and CLI tests**

```python
def test_evidence_package_copies_figure_candidate_manifest(tmp_path: Path) -> None:
    package = service.package(runs, figure_candidates=figure_candidates)
    payload = json.loads((package.path / "figure-candidates.json").read_text())
    assert payload["main_candidates"][0]["role"] == "main_candidate"

def test_analyze_project_cli_reads_figure_selection_json(capsys, tmp_path: Path) -> None:
    code = run_project_workflow(args, service=service)
    assert json.loads(capsys.readouterr().out)["analysis"]["selected_groups"] == ["ir:pa6-jw:temperature_C"]
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `python -m pytest tests/test_ars_group_figure_candidates.py -q`

Expected: FAIL because package and CLI do not accept a figure selection.

- [ ] **Step 3: Add JSON request parsing and package projection**

```python
ppw.add_argument("--figure-selection", default=None, help="ARS figure-selection JSON path for analyze-project")

def _load_figure_selection(path: str | None) -> FigureSelectionRequest | None: ...
```

Read only a JSON object with the request contract. Invalid JSON emits
`figure_selection_invalid` before analysis. Copy main/supporting candidate
assets plus `figure-candidates.json` into the immutable package, include their
hashes in `manifest.json`, and append a “Manuscript figure candidates” section
to `writing-input.md`. Internal-only figures remain referenced in candidate
metadata but are not copied as manuscript assets.

- [ ] **Step 4: Run package and CLI tests to verify GREEN**

Run: `python -m pytest tests/test_ars_group_figure_candidates.py tests/test_project_workflow_package.py tests/test_project_workflow_cli.py -q`

Expected: PASS; the CLI emits exactly one JSON envelope and package hashes
include selected candidate assets.

- [ ] **Step 5: Commit package and CLI projection**

```powershell
python scripts/auto_commit.py --message "feat(project): package ARS figure candidates" --files polynexus/core/project_workflow/package.py polynexus/cli/parser.py polynexus/cli/run_project_workflow_service.py tests/test_ars_group_figure_candidates.py
```

### Task 6: Acceptance and Checkpoint

**Files:**
- Create: `docs/acceptance/2026-08-14-ars-selected-group-figure-candidates.md`
- Modify: `docs/agent/tasks/2026-08-14-ars-selected-group-figure-candidates.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Record a synthetic full workflow and PA6 read-only scope result**

Document the exact selected group IDs, candidate/omission output, validation
commands, and whether the real external PA6 rendering completed within the
bounded check. Do not claim a real figure smoke passed without its artifact and
manifest.

- [ ] **Step 2: Run the structured verifier**

Run: `python scripts/verify.py --task docs/agent/tasks/2026-08-14-ars-selected-group-figure-candidates.md --changed --types`

Expected: exit 0, including task card, memory, changed-file lint/compile, and
quality/preprocessing gates.

- [ ] **Step 3: Run whitespace verification**

Run: `git diff --check`

Expected: exit 0 with no output.

- [ ] **Step 4: Commit the acceptance checkpoint**

```powershell
python scripts/auto_commit.py --message "feat(project): generate ARS group figure candidates" --files docs/acceptance/2026-08-14-ars-selected-group-figure-candidates.md docs/agent/tasks/2026-08-14-ars-selected-group-figure-candidates.md docs/agent/memory/active-work.md
```

## Plan Self-Review

- The request contract, FTIR-only rendering, strict trend gate, project
  orchestration, package/CLI projection, and acceptance evidence each map to a
  specification section.
- The plan has no placeholder actions; every code-changing task names exact
  files, APIs, test examples, and commands.
- `FigureSelectionRequest`, `ResolvedFigureSelection`, `FigureCandidateSet`,
  `render_ftir_group_candidates`, and `figure_selection` use the same names in
  every task.
