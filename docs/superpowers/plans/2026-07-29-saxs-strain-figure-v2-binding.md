# SAXS strain Figure V2 Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind every emitted SAXS strain Figure to the existing `saxs_strain` V2 route without changing scientific, evidence, or publication semantics.

**Architecture:** The strain provider's final recipe normalizer is the one shared boundary traversed by every optional Figure builder. Add the existing adapter key there with `setdefault`; V2 capability and fallback remain owned by the shared Figure capability layer.

**Tech Stack:** Python 3.14, NumPy, pytest, FigurePipeline, FigureDefinition, V2 capability artifact.

---

### Task 1: Establish provider-wide RED evidence

**Files:**

- Modify: `tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 1: Write the failing capability test**

```python
def test_strain_v2_figures_are_v2_ready() -> None:
    definitions = build_strain_figure_definitions(_strain_engine())
    assert definitions
    assert all(item.recipe["v2_adapter"] == "saxs_strain" for item in definitions)
    assert all(
        build_v2_definition_artifact(item).capability["v2_runtime"] == "ready"
        for item in definitions
    )
```

- [x] **Step 2: Write the failing Manifest-sidecar test**

```python
def test_strain_v2_pipeline_writes_manifest_sidecar(tmp_path) -> None:
    definition = build_strain_figure_definitions(_strain_engine())[0]
    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="saxs-strain-v2",
        technique="saxs",
        definitions=(definition,),
    )
    entry = manifest.figures[0]
    assert entry.capability_report["v2_runtime"] == "ready"
    assert (tmp_path / "runs" / "saxs-strain-v2" / entry.capability_report["v2_sidecar"]).is_file()
```

- [x] **Step 3: Run RED and confirm the missing adapter is the failure**

Run: `python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k "strain_v2"`

Expected: both tests fail because strain recipe definitions have no
`v2_adapter`, yielding `not_configured` and no sidecar key.

### Task 2: Bind the existing route at the shared strain recipe boundary

**Files:**

- Modify: `polynexus/core/saxs_engine/figure_strain.py:1820-1828`

- [x] **Step 1: Add the minimal default**

```python
def _ensure_display_order(definition: FigureDefinition) -> FigureDefinition:
    recipe = dict(definition.recipe)
    recipe.setdefault("v2_adapter", "saxs_strain")
    parameters = dict(recipe.get("parameters", {}))
    parameters.setdefault("display_order", int(definition.display_order))
    recipe["parameters"] = parameters
    return definition.__class__(**{**definition.__dict__, "recipe": recipe})
```

- [x] **Step 2: Run GREEN**

Run: `python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k "strain_v2"`

Expected: `2 passed` and the Manifest test finds the generated V2 sidecar.

### Task 3: Verify adjacent consumers and checkpoint

**Files:**

- Modify: task card, design, and this plan with actual evidence/check marks.

- [x] **Step 1: Run Figure/provider consumer tests**

Run: `python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_saxs_detector_figure_modes.py tests/test_saxs_figure_document.py`

Expected: exit code 0 with a complete pytest summary.

- [x] **Step 2: Run structured verification and complete SAXS matrix**

Run the exact commands in the task card. Require exit code 0 and final
summaries before recording success.

- [x] **Step 3: Run non-destructive storage audit and diff check**

Run the two task-card storage commands without `--apply`, then `git diff --check`.

- [x] **Step 4: Create the explicit allowlist checkpoint**

Run:

```powershell
python scripts/auto_commit.py --message "feat(saxs): bind strain figures to v2" --files docs/agent/tasks/2026-07-29-saxs-strain-figure-v2-binding.md docs/superpowers/specs/2026-07-29-saxs-strain-figure-v2-binding-design.md docs/superpowers/plans/2026-07-29-saxs-strain-figure-v2-binding.md polynexus/core/saxs_engine/figure_strain.py tests/test_saxs_figure_evidence_binding.py
```

Expected: one local commit containing exactly the five listed files and no
push, merge, storage apply, GUI change, or parallel-workspace artifact.
