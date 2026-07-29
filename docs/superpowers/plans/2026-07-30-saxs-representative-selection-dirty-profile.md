# SAXS Representative Selection Dirty Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve valid representative-selection q/I features when SAXS profiles contain malformed tokens.

**Architecture:** Reuse `figure_common._coerce_numeric_array()` at the private selection feature boundary. The existing pair alignment, finite filters, integration, maximum, and transition ranking remain unchanged.

**Tech Stack:** Python, NumPy, pytest, existing SAXS Figure selection contracts, and repository verifier scripts.

---

### Task 1: Add the failing regression

**Files:**
- Create: `tests/test_saxs_figure_selection_dirty_input.py`.

- [x] **Step 1: Write the failing test**

```python
from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.figure_common import SAXSFrameView
from polynexus.core.saxs_engine.figure_selection import _intensity_features


def test_intensity_features_keep_finite_pairs_from_malformed_profile() -> None:
    frame = SAXSFrameView(
        index=0,
        label="dirty",
        condition=100.0,
        q=np.asarray([0.1, "bad-q", 0.3, 0.4], dtype=object),
        intensity=np.asarray([2.0, 3.0, 4.0, "bad-intensity"], dtype=object),
        analysis=SimpleNamespace(),
        parameters={},
    )

    area, maximum = _intensity_features(frame)

    assert area == 0.6
    assert maximum == 4.0
```

- [x] **Step 2: Run RED**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_rep_selection_dirty_red'
python -m pytest -q tests/test_saxs_figure_selection_dirty_input.py
```

Expected: one failure with `(nan, nan)` from the existing whole-array float
conversion.

### Task 2: Implement the minimal projection fix

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_selection.py:134-158`.

- [x] **Step 1: Reuse the existing helper**

Change the import to include `_coerce_numeric_array`:

```python
from .figure_common import SAXSFrameView, _coerce_numeric_array
```

Replace only the conversion inside `_intensity_features()`:

```python
try:
    q = _coerce_numeric_array(frame.q)
    intensity = _coerce_numeric_array(frame.intensity)
except (TypeError, ValueError):
    return np.nan, np.nan
```

Leave the aligned-prefix, finite masks, maximum, sorting, trapezoid area, and
return logic unchanged.

- [x] **Step 2: Run GREEN**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_rep_selection_dirty_green'
python -m pytest -q tests/test_saxs_figure_selection_dirty_input.py tests/test_saxs_mode_evidence_contract.py
```

Expected: a fresh zero-failure pytest summary.

### Task 3: Verify and checkpoint

**Files:**
- Use only the seven paths in the task card allowlist.

- [x] **Step 1: Run the structured verifier**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-representative-selection-dirty-profile.md --changed --types
```

- [x] **Step 2: Run the fresh SAXS matrix**

```powershell
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts= --basetemp=D:\PolyNexus_saxs_rep_selection_dirty_saxs_matrix
```

Count it only with a final pytest summary and exit code `0`.

- [x] **Step 3: Audit storage and diff**

```powershell
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
```

Do not run `test_storage.py --apply` or modify unrelated directories.

- [ ] **Step 4: Create the atomic checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(saxs): preserve dirty selection features" --files polynexus/core/saxs_engine/figure_selection.py tests/test_saxs_figure_selection_dirty_input.py docs/agent/tasks/2026-07-30-saxs-representative-selection-dirty-profile.md docs/superpowers/specs/2026-07-30-saxs-representative-selection-dirty-profile-design.md docs/superpowers/plans/2026-07-30-saxs-representative-selection-dirty-profile.md docs/acceptance/2026-07-30-saxs-representative-selection-dirty-profile.md docs/agent/memory/active-work.md
```

## Plan self-review

- The spec's projection, preservation, fail-closed, and verification
  requirements map to Tasks 1-3.
- No new scientific threshold or selection policy is introduced.
- The helper and test names match the code references used throughout.
