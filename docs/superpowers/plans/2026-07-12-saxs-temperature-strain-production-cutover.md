# SAXS Temperature/Strain Production Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lock SAXS temperature/time and strain plotting to the mainline shared publisher contract, with no ungated legacy fallback when definitions are empty.

**Architecture:** Validate the mainline SAXS route that already sends non-empty definitions through `BaseEngine.publish_figure_definitions()` and returns an explicit no-publication result for empty definitions. Add regression coverage for temperature/time, strain, unsupported mixed state, and static empty-definition behavior; do not reintroduce or rewrite legacy plotting helpers.

**Tech Stack:** Python 3.10+, NumPy, Matplotlib, pytest, existing `FigureProductionPublisher`/`RunFigureManifest` contracts.

---

## File map

- Modify: none — mainline already contains the strict shared-publisher route.
- Create: `tests/test_saxs_publication_cutover.py` — route, manifest, metadata, and empty-definition acceptance tests.
- Existing coverage: `tests/test_saxs_publication_temperature_provider.py` and `tests/test_saxs_strain_figure_provider.py` remain the provider contract suites and must stay green.

### Task 1: Lock the mode-routing and production-entry behavior with failing tests

**Files:**
- Create: `tests/test_saxs_publication_cutover.py`

- [ ] **Step 1: Add a minimal valid SAXS definition fixture and engine helpers**

Create a valid one-panel `FigureDefinition` in the new test file using the same
contract classes used by `tests/conftest.py`, but set `technique="saxs"`,
`publication_role="main"`, and a small two-point line source. Use a real
`SAXSEngine(SAXSConfig(...))` in the tests, set `_analysis` to a non-None
sentinel so `plot()` has analysis state, and set `_temperature_result` or
`_strain_result` to a non-None sentinel for series-mode routing. Monkeypatch
`engine.build_figure_definitions` only to isolate the production-entry contract;
provider-specific evidence is already covered by the existing provider suites.

- [ ] **Step 2: Add failing manifest-backed production tests**

Add these tests:

```python
def test_temperature_plot_publishes_shared_manifest_and_result_metadata(tmp_path, monkeypatch):
    engine = _series_engine("temperature")
    definition = _saxs_definition()
    monkeypatch.setattr(engine, "build_figure_definitions", lambda: (definition,))

    assets = engine.plot(str(tmp_path))

    manifest = Path(engine.result.metadata["figure_manifest"])
    assert manifest.is_file()
    assert assets == engine.result.figures
    assert assets[definition.figure_id].endswith(".svg")
    assert json.loads((tmp_path / "active_run.json").read_text("utf-8"))["run_id"]


def test_strain_plot_publishes_shared_manifest_and_result_metadata(tmp_path, monkeypatch):
    engine = _series_engine("strain")
    definition = _saxs_definition(figure_id="saxs.strain.evolution.1d")
    monkeypatch.setattr(engine, "build_figure_definitions", lambda: (definition,))

    assets = engine.plot(str(tmp_path))

    assert assets == engine.result.figures
    assert Path(engine.result.metadata["figure_manifest"]).is_file()
```

Run:

```powershell
python -m pytest tests/test_saxs_publication_cutover.py::test_temperature_plot_publishes_shared_manifest_and_result_metadata tests/test_saxs_publication_cutover.py::test_strain_plot_publishes_shared_manifest_and_result_metadata -q
```

Expected: the tests collect, then fail because the test helper does not yet
exist or because the current route still falls through to legacy behavior after
the new boundary cases are added. Fix only test setup errors before continuing;
the production assertion must not pass by accident.

- [ ] **Step 3: Add failing no-fallback and static-compatibility tests**

Add a parameterized test for `temperature` and `strain` that returns an empty
definition tuple and monkeypatches the corresponding legacy helper to raise if
called. The expected result is `{}`. Add an `unsupported` conflict case with
both series result sentinels and the same expectation. Add a static case whose
empty definitions call a monkeypatched `generate_all_figures` and return its
sentinel mapping, proving the compatibility path remains scoped to static mode.

Run:

```powershell
python -m pytest tests/test_saxs_publication_cutover.py -q
```

Expected: the new no-fallback tests fail against the current `SAXSEngine.plot()`
because it still invokes `fig_temperature_overview`, `fig_strain_overview`, or
`generate_all_figures` based only on result fields.

- [ ] **Step 4: Commit the RED tests**

```powershell
git add tests/test_saxs_publication_cutover.py
git commit -m "test(saxs): define temperature strain production cutover"
```

### Task 2: Verify the existing strict SAXS production routing

**Files:**
- Test: `tests/test_saxs_publication_cutover.py`

- [ ] **Step 1: Run the existing route contract before finalizing the test-only cutover**

Run:

```powershell
python -m pytest tests/test_saxs_static_figure_provider.py::test_provider_dispatch_is_deterministic_and_other_modes_are_safe tests/test_saxs_publication_temperature_provider.py::test_provider_prefers_completed_result_and_condition_state_over_static_config tests/test_saxs_strain_figure_provider.py::test_registry_dispatches_only_strain_and_definitions_validate -q
```

Expected: PASS, confirming the mainline provider and shared publisher contracts
are already intact.

- [ ] **Step 2: Confirm no production edit is needed**

Inspect `SAXSEngine.plot()` and keep this mainline contract unchanged:

```python
definitions = self.build_figure_definitions()
if definitions:
    return self.publish_figure_definitions(out, definitions=definitions)
```

```python
definitions = tuple(self.build_figure_definitions())
if not definitions:
    self.log("No figure definitions available")
    return {}
out = output_dir or self.cfg.output_dir or "saxs_output"
return self.publish_figure_definitions(out, definitions)
```

Do not add a legacy fallback branch. The provider and shared publisher already
own production output.

- [ ] **Step 3: Run the focused tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_saxs_publication_cutover.py tests/test_saxs_static_figure_provider.py tests/test_saxs_publication_temperature_provider.py tests/test_saxs_strain_figure_provider.py -q
```

Expected: all tests pass, including manifest creation, result metadata updates,
series no-publication behavior, unsupported conflict behavior, and static
no-publication behavior.

- [ ] **Step 4: Commit the regression coverage**

```powershell
git add tests/test_saxs_publication_cutover.py
git commit -m "test(saxs): lock publication cutover boundary"
```

### Task 3: Verify provider, gallery, and repository acceptance boundaries

**Files:**
- Modify: none unless a test exposes a concrete regression in the files above.
- Test: `tests/test_saxs_publication_cutover.py`, existing SAXS/provider/gallery suites.

- [ ] **Step 1: Run the complete focused SAXS and shared publication matrix**

```powershell
python -m pytest tests/test_saxs_figure_selection.py tests/test_saxs_figure_eligibility.py tests/test_saxs_temperature_status.py tests/test_saxs_publication_temperature_provider.py tests/test_saxs_strain_figure_provider.py tests/test_saxs_static_figure_provider.py tests/test_figure_pipeline.py tests/test_figure_production.py tests/test_plot_gallery_service.py tests/test_chart_viewer.py tests/test_manifest_editor_shared_plan.py tests/test_saxs_publication_cutover.py -q
```

Expected: zero failures; the run must include the manifest-backed asset and
gallery ordering assertions.

- [ ] **Step 2: Run task-card and changed-scope verification**

From the main workspace, run:

```powershell
python scripts/task_check.py --task docs/agent/tasks/2026-07-12-saxs-temperature-strain-production-cutover.md
python scripts/verify.py --task docs/agent/tasks/2026-07-12-saxs-temperature-strain-production-cutover.md --changed
python scripts/verify.py --changed --types
```

Expected: task card valid and changed-scope/type verification successful. If
the current workspace contains unrelated user edits, do not stage or alter
them; report those unrelated failures separately.

- [ ] **Step 3: Run final repository gates and inspect the diff**

```powershell
python scripts/verify.py
python scripts/verify.py --full
python scripts/verify.py --boundary
git diff HEAD~2..HEAD --check
git status --short
```

Expected: repository gates pass or any pre-existing unrelated failures are
explicitly recorded; the final diff contains only the SAXS routing/provider
contract, cutover tests, and task design/plan documentation.

- [ ] **Step 4: Record the review checkpoint**

Update the task card's verification and commit fields and update
`docs/agent/memory/active-work.md` with the final evidence link, preserving the
existing unrelated entries. Commit documentation separately:

```powershell
git add docs/agent/tasks/2026-07-12-saxs-temperature-strain-production-cutover.md docs/agent/memory/active-work.md
git commit -m "docs: record SAXS production cutover verification"
```
