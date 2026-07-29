# Advanced SAXS Figure V2 Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all advanced static and temperature SAXS Figure definitions V2-capable without changing scientific or publication semantics.

**Architecture:** Reuse existing adapter and layout gates.  Static uses its recipe helper default; temperature adds the same adapter key to each existing recipe.  Tests use the existing provider fixtures and Pipeline boundary.

**Tech Stack:** Python 3.14, NumPy, pytest, FigurePipeline, V2 capability artifact.

---

### Task 1: Add RED provider-wide capability assertions

**Files:**
- Modify: `tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 1: Write the failing tests**

```python
from polynexus.core.figures.v2_capabilities import build_v2_definition_artifact


def test_static_advanced_figures_are_v2_ready():
    definitions = build_static_saxs_figure_definitions(_static_engine())
    assert definitions
    assert all(item.recipe["v2_adapter"] == "saxs_static" for item in definitions)
    assert all(
        build_v2_definition_artifact(item).capability["v2_runtime"] == "ready"
        for item in definitions
    )


def test_temperature_advanced_figures_are_v2_ready():
    definitions = build_temperature_figure_definitions(_temperature_engine())
    assert definitions
    assert all(
        item.recipe["v2_adapter"] == "temperature_saxs" for item in definitions
    )
    assert all(
        build_v2_definition_artifact(item).capability["v2_runtime"] == "ready"
        for item in definitions
    )
```

- [x] **Step 2: Run RED**

Run: `python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k advanced_v2`

Expected: both tests fail because advanced definitions have no adapter key.

### Task 2: Bind existing adapters at provider recipe boundaries

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_static.py`
- Modify: `polynexus/core/saxs_engine/figure_temperature.py`

- [x] **Step 1: Add the static default**

```python
v2_adapter: str = "saxs_static",
```

Keep the existing recipe conditional and pass the default through the existing
`_definition` calls; do not alter any data source or object.

- [x] **Step 2: Add the temperature keys**

```python
"v2_adapter": "temperature_saxs",
```

Add this member to the existing evolution, Avrami, waterfall, evidence, and
detector recipe dictionaries.

- [x] **Step 3: Run GREEN**

Run: `python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k advanced_v2`

Expected: both tests pass.

### Task 3: Verify Manifest and export consumers

**Files:**
- Modify: `tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 1: Add representative Pipeline assertions**

```python
manifest = FigurePipeline().run(
    output_root=tmp_path,
    run_id="saxs-advanced-v2",
    technique="saxs",
    definitions=(definitions[0],),
)
entry = manifest.figures[0]
assert entry.status == "ready"
assert entry.capability_report["v2_runtime"] == "ready"
assert entry.capability_report["v2_sidecar"]
```

- [x] **Step 2: Run the focused consumer matrix**

Run: `python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_saxs_temperature_figure_panels.py tests/test_saxs_static_publication_gate.py`

Expected: exit code 0.

- [x] **Step 3: Run structured verification and SAXS matrix**

Run the task verifier and the PowerShell-expanded SAXS matrix from the task
card.  Both require exit code 0 and a final pytest summary.

- [x] **Step 4: Run storage dry-run and create the allowlist checkpoint**

Run the task card's report/clean dry-run and `git diff --check`, then use
`scripts/auto_commit.py` with exactly the six-file allowlist in the task card.
