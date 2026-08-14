# Canonical Figure Assets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make newly produced evidence packages contain one SVG-based editable evidence set per logical figure, while retaining explicit publication-format export and read-only legacy compatibility.

**Architecture:** Add an evidence-oriented figure output profile whose declared assets are SVG-only, then project manifest-backed logical figures into a versioned package `figure-index.json`.  Package and GUI/ARS readers consume this index through one neutral DTO, while an index-absent adapter exposes old multi-format packages without modifying them.  The existing publication profiles continue to materialize PNG/PDF/TIFF only through an explicit publish/export action.

**Tech Stack:** Python 3.12, dataclasses, pathlib, JSON, Matplotlib, PySide6, pytest.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `polynexus/core/figures/profiles.py` | Declare the default evidence and explicit publication asset sets. |
| `polynexus/core/figures/export_service.py` | Render exactly the asset roles declared by a profile and keep atomic export behavior. |
| `polynexus/core/figures/pipeline.py` | Default normal figure runs to the evidence profile; write a per-figure metadata sidecar from public definition/document data. |
| `polynexus/core/figures/project_service.py` | Preserve working preview behavior and route only explicit publish requests through publication formats. |
| `polynexus/core/project_workflow/figure_index.py` | Define and validate the versioned, technique-neutral logical-figure index and legacy adapter. |
| `polynexus/core/project_workflow/package.py` | Copy canonical assets once, write `figure-index.json`, and expose it from the immutable manifest. |
| `polynexus/core/project_workflow/evidence_view.py` | Load the index-backed or legacy-derived logical figure DTO used by all package consumers. |
| `polynexus/gui/plot_gallery_service.py` and package-view adapter | Prefer indexed SVG/document entries and preserve object-editor capabilities. |
| Focused tests named below | Prove export, package, GUI, ARS/CLI, and old-package compatibility boundaries. |

**Confirmed boundary:** Existing ARS group renderers produce direct Matplotlib
SVGs rather than Figure Project object documents.  They are indexed as
viewable/static logical figures with no fabricated `figure.pnfig.json`; only
manifest-backed figures with a valid document enter Chart Editor object mode.

### Task 1: Add An Evidence-Only Export Profile

**Files:**
- Modify: `polynexus/core/figures/profiles.py`
- Modify: `polynexus/core/figures/export_service.py`
- Modify: `polynexus/core/figures/pipeline.py`
- Test: `tests/test_run_figure_manifest.py`
- Test: `tests/test_reactive_figure_matplotlib_renderer.py`

- [ ] **Step 1: Write failing default-profile tests**

Add one test that runs `FigurePipeline.run()` without `profile_id` and asserts
that the ready manifest's assets are exactly `{"svg"}`, the SVG exists, the
document and every declared data source exist, and no `preview`, `png`, `pdf`,
or `tiff` asset exists.  Add one direct exporter test for an explicit
publication profile that asserts its declared `png`, `pdf`, and optional `tiff`
assets still exist.

```python
manifest = FigurePipeline().run(
    output_root=tmp_path, run_id="evidence-default", technique="IR",
    definitions=[ir_definition],
)
entry = manifest.figures[0]
assert set(entry.assets) == {"svg"}
assert (tmp_path / "runs" / "evidence-default" / entry.assets["svg"]).is_file()
assert "preview" not in entry.assets
assert not list((tmp_path / "runs" / "evidence-default").rglob("*.pdf"))
```

- [ ] **Step 2: Run the new focused tests and verify failure**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_run_figure_manifest.py -k "default or publication"
```

Expected: failure because normal `paper_complete` currently creates preview,
PNG, and PDF assets.

- [ ] **Step 3: Define profile asset roles and render only declared roles**

Add an `evidence` profile whose `formal_assets` is exactly
`{"svg": "figure.svg"}` and whose preview filename is empty/optional.  Change
the exporter to construct and render `staged_assets` from `formal_assets` only;
invoke `_save_preview`, `_save_png`, `_save_pdf`, and `_save_tiff` only if the
corresponding role is declared.  Preserve atomic staging, inspector, and audit
calls.  Make `FigurePipeline.run(..., profile_id="evidence")` its default.

```python
staged_assets = {
    role: staging_dir / filename
    for role, filename in profile.formal_assets.items()
}
if profile.preview_filename:
    staged_assets["preview"] = staging_dir / profile.preview_filename
if "svg" in staged_assets:
    self._save_svg(plan, staged_assets["svg"], profile)
```

Do not remove existing `paper_complete`, `dsc_publication`, `saxs_publication`,
or `waxs_publication` profiles.  They remain explicit compatibility or
publication choices.

- [ ] **Step 4: Make inspector/capability behavior profile-aware**

Update only the inspection assumptions that require every legacy asset.  A
complete evidence export requires its declared SVG and valid render plan; a
complete publication export continues to require every declared publication
asset.  Keep object-editing capability dependent on the Figure Project
document, not on PNG presence.

- [ ] **Step 5: Run focused export tests**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_run_figure_manifest.py tests/test_reactive_figure_matplotlib_renderer.py
```

Expected: all selected tests pass, including explicit publication asset tests.

- [ ] **Step 6: Commit the atomic profile change**

```powershell
python scripts/auto_commit.py --message "feat(figures): add evidence-only output profile" --files polynexus/core/figures/profiles.py polynexus/core/figures/export_service.py polynexus/core/figures/pipeline.py tests/test_run_figure_manifest.py tests/test_reactive_figure_matplotlib_renderer.py
```

### Task 2: Materialize Canonical Metadata And Logical Figure Index

**Files:**
- Create: `polynexus/core/project_workflow/figure_index.py`
- Modify: `polynexus/core/figures/pipeline.py`
- Modify: `polynexus/core/project_workflow/package.py`
- Modify: `polynexus/core/project_workflow/__init__.py`
- Test: `tests/test_project_workflow_package.py`
- Test: `tests/test_ars_group_figure_candidates.py`

- [ ] **Step 1: Write failing index/package tests**

Create a package test with one manifest-backed figure plus legacy-format
siblings.  Assert that package root `figure-index.json` has `version: 1`, one
row, package-relative `svg`, `document`, `data`, and `metadata` paths, and the
package contains one logical figure directory rather than copied PNG/PDF
siblings.  Add candidate test coverage that maps a selected group figure to the
one index row rather than both its SVG and PNG source paths.

```python
index = json.loads((package_path / "figure-index.json").read_text(encoding="utf-8"))
assert index["version"] == 1
assert len(index["figures"]) == 1
entry = index["figures"][0]
assert entry["svg"].endswith("/figure.svg")
assert (package_path / entry["document"]).is_file()
assert not list((package_path / "figures").rglob("*.pdf"))
```

- [ ] **Step 2: Run index/package tests and verify failure**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_workflow_package.py tests/test_ars_group_figure_candidates.py
```

Expected: failure because package creation has no `figure-index.json` and
copies extension-based assets independently.

- [ ] **Step 3: Write per-figure metadata alongside the Figure Project**

In `FigurePipeline._process_definition`, write `metadata.json` in the figure
directory after a validated definition/document is available.  Keep it
technique-neutral and derive only public facts: `figure_id`, title, category,
publication role, source run ID, data source paths, document path, profile,
and declared SVG path.  Do not duplicate measured values or infer group
identity.

- [ ] **Step 4: Implement `FigureIndexEntry` and `FigureIndex`**

Use frozen dataclasses with `to_dict()`/`from_dict()` and strict
package-relative POSIX-path validation.  Required entry fields are `id`,
`role`, `technique`, `group`, `writing_eligibility`, `svg`, `document`, `data`,
and `metadata`; `document` is `None` only for an explicitly static
direct-render figure.  Provide `FigureIndex.from_package(...)` only for a
valid new index, and a separate `derive_legacy_figure_index(...)` adapter that
reads existing package manifest/candidates/assets without writing anything.

```python
@dataclass(frozen=True)
class FigureIndexEntry:
    id: str
    role: str
    technique: str
    group: str | None
    writing_eligibility: str
    svg: str
    document: str | None
    data: str
    metadata: str
```

- [ ] **Step 5: Package canonical assets by logical figure identity**

Replace the package's extension-driven copying for figures with index-backed
descriptors.  Resolve figure identity from the run manifest/document, copy the
canonical asset quartet into `figures/<figure-id>/`, and deduplicate by the
stable figure ID plus source document path.  Preserve table copying and all
existing evidence, relation, citation metric, and ARS-writing artifacts.
Write `figure-index.json`, add its relative name to `manifest.json`, and include
its contents in the package hash before writing the manifest.

Candidate selection remains a role/intent source: map its `main` and
`supporting` choices onto index IDs and update `figure-candidates.json` to
package-relative SVG/document references.  A missing canonical asset raises a
specific `ValueError` before package completion.

- [ ] **Step 6: Run package and ARS candidate tests**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_workflow_package.py tests/test_ars_group_figure_candidates.py
```

Expected: all selected tests pass; the package tests prove no duplicate figure
formats and the ARS tests prove candidate selection still works.

- [ ] **Step 7: Commit the index/package change**

```powershell
python scripts/auto_commit.py --message "feat(evidence): index canonical figure assets" --files polynexus/core/figures/pipeline.py polynexus/core/project_workflow/figure_index.py polynexus/core/project_workflow/package.py polynexus/core/project_workflow/__init__.py tests/test_project_workflow_package.py tests/test_ars_group_figure_candidates.py
```

### Task 3: Unify Package Readers And Preserve Legacy Packages

**Files:**
- Modify: `polynexus/core/project_workflow/evidence_view.py`
- Modify: `polynexus/core/project_workflow/__init__.py`
- Test: `tests/test_evidence_package_view.py`
- Test: `tests/test_project_workflow_package.py`
- Test: `tests/test_ai_native_project_entrypoint.py`

- [ ] **Step 1: Write failing reader tests**

Add an index-backed package fixture and assert `load_evidence_package_view()`
returns one neutral figure view with `svg_path`, optional `document_path`,
role, technique, group, and writing eligibility.  Add an old-package fixture
with no index and legacy SVG/PNG/PDF siblings; assert it returns one derived
logical figure and does not create `figure-index.json`.

```python
view = load_evidence_package_view(indexed_package)
assert view.figures[0].svg_path.endswith("figure.svg")
assert not (legacy_package / "figure-index.json").exists()
```

- [ ] **Step 2: Run reader tests and verify failure**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_evidence_package_view.py tests/test_ai_native_project_entrypoint.py
```

Expected: failure because `EvidencePackageView` has no logical-figure index DTO.

- [ ] **Step 3: Add a neutral `EvidenceFigureView` to the package DTO**

Expose an immutable DTO whose paths are package-relative and whose public
properties match `FigureIndexEntry`.  `load_evidence_package_view()` loads and
validates `manifest["figure_index"]` when present; if absent, it invokes the
read-only legacy adapter.  It rejects malformed indexed paths and does not
silently downgrade an invalid new index to a legacy package.

- [ ] **Step 4: Preserve ARS/CLI package projection**

Add `figure_index` references to the existing writing input only as package
navigation metadata.  Continue to source metrics, Results/Discussion
eligibility, limitations, and prohibited conclusions from the existing
citation/writing contracts.  This prevents the index from inventing scientific
claims.

- [ ] **Step 5: Run focused reader and project-entrypoint tests**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_evidence_package_view.py tests/test_project_workflow_package.py tests/test_ai_native_project_entrypoint.py
```

Expected: all selected tests pass, including the index-absent legacy fixture.

- [ ] **Step 6: Commit the reader compatibility change**

```powershell
python scripts/auto_commit.py --message "feat(evidence): load canonical figure index" --files polynexus/core/project_workflow/evidence_view.py polynexus/core/project_workflow/__init__.py tests/test_evidence_package_view.py tests/test_project_workflow_package.py tests/test_ai_native_project_entrypoint.py
```

### Task 4: Make GUI Gallery And Editor Consume Logical Figure Entries

**Files:**
- Modify: `polynexus/gui/plot_gallery_service.py`
- Modify: `polynexus/gui/figure_window_service.py`
- Modify: GUI package/evidence adapter that constructs gallery entries
- Test: `tests/test_plot_gallery_service.py`
- Test: `tests/test_figure_window_service.py`
- Test: `tests/test_chart_editor_save_mixin.py`

- [ ] **Step 1: Write failing GUI contract tests**

Add a gallery-entry fixture populated from `EvidenceFigureView`.  Assert it
uses the indexed SVG as `primary_path`, an available PN figure document as
`document_path`, and yields one entry regardless of legacy sibling formats.
Add an editor-open test proving its valid object-editing capability opens
without `force_static`; add an ARS-group/static fixture and a corrupt document
fixture that force static mode.

```python
request = resolve_chart_editor_entry(indexed.svg_path, entry=indexed_entry)
assert request.force_static is False
assert request.entry.document_path.endswith("figure.pnfig.json")
```

- [ ] **Step 2: Run GUI contract tests and verify failure**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_plot_gallery_service.py tests/test_figure_window_service.py -k "index or editor"
```

Expected: failure because gallery discovery is not yet driven by
`EvidenceFigureView`.

- [ ] **Step 3: Adapt gallery discovery without duplicating contracts**

Add a narrow adapter from `EvidenceFigureView` to the existing gallery entry
shape.  Prefer `svg_path` as display/primary path and `document_path` for
object editing.  Keep existing run-manifest and legacy discovery fallbacks.
Do not add technique-specific calculations or separate GUI persistence.

- [ ] **Step 4: Preserve explicit publication and save behavior**

Verify `FigureProjectService.save_working()` may generate a private preview for
the editor, while `publish()` remains the only action that invokes an explicit
publication profile.  Update the save-mixin test expectations to distinguish a
transient working preview from a persisted evidence package asset.

- [ ] **Step 5: Run focused GUI/editor tests**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_plot_gallery_service.py tests/test_figure_window_service.py tests/test_chart_editor_save_mixin.py
```

Expected: all selected tests pass; object editing remains available for indexed
documents and bare SVG remains static.

- [ ] **Step 6: Commit the GUI consumer change**

```powershell
python scripts/auto_commit.py --message "feat(gui): show logical evidence figures" --files polynexus/gui/plot_gallery_service.py polynexus/gui/figure_window_service.py tests/test_plot_gallery_service.py tests/test_figure_window_service.py tests/test_chart_editor_save_mixin.py
```

### Task 5: Cross-Entry Verification And Durable Records

**Files:**
- Create: `docs/agent/tasks/2026-08-14-canonical-figure-assets.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/acceptance/2026-08-14-canonical-figure-assets.md`
- Test: focused tests from Tasks 1-4

- [ ] **Step 1: Create the structured task card before implementation**

Record the shared Chart/Export/Evidence Package objects, producer and GUI/CLI/
ARS consumers, non-goals, exact task verification command, and explicit
allowlist.  Mark architecture review required because the evidence/export
contract changes.

- [ ] **Step 2: Run the cross-entry focused matrix**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_run_figure_manifest.py tests/test_reactive_figure_matplotlib_renderer.py tests/test_project_workflow_package.py tests/test_ars_group_figure_candidates.py tests/test_evidence_package_view.py tests/test_ai_native_project_entrypoint.py tests/test_plot_gallery_service.py tests/test_figure_window_service.py tests/test_chart_editor_save_mixin.py
python scripts/verify.py --task docs/agent/tasks/2026-08-14-canonical-figure-assets.md --changed --types
git diff --check
```

Expected: all selected tests and structured checks pass.

- [ ] **Step 3: Inspect a fresh package and record acceptance evidence**

Create a fixture-backed or read-only project smoke package, inspect its
`figure-index.json`, verify every index path is package-relative and exists,
confirm no default PNG/PDF/TIFF is present, and open one valid indexed document
through the GUI service in object mode.  Record commands/results and the fact
that legacy packages were not modified.

- [ ] **Step 4: Update durable memory and task status**

Record the new default asset policy, explicit publication-export boundary,
legacy read-only adapter, verification totals, any remaining publication route
limitations, and human architecture review requirement.  Do not store raw test
logs or real data.

- [ ] **Step 5: Commit documentation and acceptance records**

```powershell
python scripts/auto_commit.py --message "docs(evidence): record canonical figure assets" --files docs/agent/tasks/2026-08-14-canonical-figure-assets.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md docs/acceptance/2026-08-14-canonical-figure-assets.md
```

## Plan Self-Review

- Spec coverage: Tasks 1-2 cover the two profiles, canonical asset set, index,
  metadata, deduplication, and immutable packaging.  Task 3 covers AI/CLI/ARS
  and legacy compatibility.  Task 4 covers SVG display and retained object
  editing.  Task 5 covers structured verification, acceptance evidence, and
  review recording.
- Placeholder scan: no deferred implementation markers or generic test steps;
  each task names files, expected failures, concrete assertions, commands, and
  checkpoint command.
- Type consistency: `FigureIndexEntry` is the index payload source,
  `EvidenceFigureView` is its package-reader DTO, and gallery entries adapt
  from that DTO.  `figure.pnfig.json` remains the canonical editor document.
