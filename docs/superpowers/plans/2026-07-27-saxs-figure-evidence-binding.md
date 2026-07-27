# SAXS Figure/Manifest Evidence Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attach compact, strict JSON-safe references to existing SAXS quality evidence to every static, temperature, and strain FigureDefinition.

**Architecture:** A new provider-side projection module reads only `SAXSFrameView`, existing frame quality fields, and optional completed series DTOs. The projection is merged under `recipe["evidence"]["quality_provenance"]` by the existing SAXS providers; publication-role logic and the authoritative Export Bundle remain unchanged.

**Tech Stack:** Python dataclasses, immutable SAXS frame views, existing FigureDefinition/FigurePipeline contracts, NumPy finite checks, pytest.

---

### Task 1: Write the failing projection and provider tests

**Files:**
- Create: `tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 1: Add fixtures and the strict projection test.**

```python
def test_projection_is_detached_and_strict_json_safe():
    metric = {"metric_name": "Porod", "level": "Trend", "value": float("nan"), "reason_codes": ["observed"]}
    frame = _frame(index=0, condition=25.0, metric_evidence={"porod": metric})
    payload = build_saxs_figure_evidence((frame,), mode="static")

    json.dumps(payload, allow_nan=False)
    assert payload["frame_records"][0]["metric_evidence"]["porod"]["value"] is None
    metric["level"] = "Unusable"
    assert payload["frame_records"][0]["metric_evidence"]["porod"]["level"] == "Trend"
```

- [x] **Step 2: Add static provider and missing/malformed evidence tests.**

```python
def test_static_provider_binds_frame_evidence_without_changing_roles():
    engine = _static_engine_with_metric_evidence()
    definitions = build_static_saxs_figure_definitions(engine)
    provenance = definitions[0].recipe["evidence"]["quality_provenance"]
    assert provenance["mode"] == "static"
    assert provenance["frame_records"][0]["metric_evidence"]["porod"]["level"] == "Trend"
    assert definitions[0].publication_role == "main"


def test_missing_or_malformed_evidence_is_not_promoted_or_fatal():
    definitions = build_static_saxs_figure_definitions(_static_engine_without_evidence())
    assert definitions
    for definition in definitions:
        provenance = definition.recipe.get("evidence", {}).get("quality_provenance", {})
        assert provenance.get("frame_records", [{}])[0].get("metric_evidence", {}) == {}
```

- [x] **Step 3: Add temperature source-index and series tests.**

```python
def test_temperature_binding_keeps_frame_and_original_source_indices():
    engine = _temperature_engine_with_sorted_source_indices()
    definitions = build_temperature_figure_definitions(engine)
    provenance = definitions[0].recipe["evidence"]["quality_provenance"]
    assert [row["source_index"] for row in provenance["frame_records"]] == [0, 1]
    assert provenance["series_record"]["guinier_sequence_evidence"]["frame_source_indices"] == [1, 0]
```

- [x] **Step 4: Add strain orientation separation and FigurePipeline serialization tests.**

```python
def test_strain_binding_keeps_orientation_separate_and_survives_manifest_document(tmp_path):
    definition = build_strain_figure_definitions(_strain_engine_with_evidence())[0]
    provenance = definition.recipe["evidence"]["quality_provenance"]
    assert "orientation_evidence" in provenance["series_record"]
    assert "orientation" not in provenance["series_record"].get("metric_evidence", {})
    FigurePipeline().run(output_root=tmp_path, run_id="saxs-evidence", technique="saxs", definitions=(definition,))
    document = next((tmp_path / "runs" / "saxs-evidence" / "figures").glob("*/figure.pnfig.json"))
    payload = json.loads(document.read_text(encoding="utf-8"))
    json.dumps(payload, allow_nan=False)
    assert payload["recipe"]["evidence"]["quality_provenance"]["quality_evidence_file"] == "quality_evidence.json"
```

- [x] **Step 5: Run RED.**

Run:

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_figure_evidence_red'
python -m pytest tests/test_saxs_figure_evidence_binding.py -q
```

Expected: collection or assertion failures because `figure_evidence` and
`quality_provenance` do not exist yet; no production provider should be edited
before this RED result is observed.

### Task 2: Implement the detached evidence projection

**Files:**
- Create: `polynexus/core/saxs_engine/figure_evidence.py`

- [x] **Step 1: Implement strict JSON conversion and compact field selection.**

Implement these exact public functions:

```python
def build_saxs_figure_evidence(
    frames: Sequence[SAXSFrameView],
    *,
    mode: str,
    series: Any = None,
) -> dict[str, Any]: ...


def attach_saxs_figure_evidence(
    definitions: Sequence[FigureDefinition],
    frames: Sequence[SAXSFrameView],
    *,
    mode: str,
    series: Any = None,
) -> tuple[FigureDefinition, ...]: ...
```

The implementation must:

- read frame quality from `frame.parameters`, `frame.analysis.final_parameters`,
  then the analysis attributes, without invoking analysis;
- compact only the contract fields in the design and retain unknown/malformed
  entries as missing rather than inventing a level;
- derive temperature `source_index` only by matching existing series point
  `source_index` values to the provider frame index;
- convert NumPy scalars, arrays, mappings, sequences, non-finite floats, and
  enums to JSON-safe values;
- merge into `recipe["evidence"]["quality_provenance"]` while preserving all
  pre-existing `recipe["evidence"]` keys and `publication_role`.

- [x] **Step 2: Run the projection tests GREEN.**

Run the Task 1 focused command again. Expected: all projection tests pass and
`json.dumps(..., allow_nan=False)` succeeds.

### Task 3: Attach the helper to all SAXS figure routes

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_provider.py`
- Modify: `polynexus/core/saxs_engine/figure_static.py`
- Modify: `polynexus/core/saxs_engine/figure_temperature.py`
- Modify: `polynexus/core/saxs_engine/figure_strain.py`

- [x] **Step 1: Attach static evidence after existing role/ordering logic.**

Call `attach_saxs_figure_evidence` on the final static definitions with
`mode="static"` and the existing frame views. Do not move or alter
`classify_frame_eligibility`, `_aggregate_publication_role`, or the static
figure selection.

- [x] **Step 2: Attach production temperature and strain evidence.**

Call the helper after existing definitions are ordered, passing the existing
frame views and `_temperature_result` or `_strain_result`. Preserve the
temperature point/source mapping and keep orientation as its own field.

- [x] **Step 3: Attach compatibility-provider evidence.**

Update `build_saxs_temperature_definitions` and the legacy static/strain route
in `figure_provider.py` to attach the same contract. The helper must tolerate
empty `evidence_frames` and retain definitions unchanged when no evidence is
available.

- [x] **Step 4: Run provider compatibility GREEN tests.**

Run:

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_figure_evidence_green'
python -m pytest tests/test_saxs_figure_evidence_binding.py tests/test_saxs_mode_evidence_contract.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_publication_pack_upgrade.py -q
```

Expected: all new tests and existing figure provider tests pass.

### Task 4: Verify the Figure Manifest and SAXS export boundary

**Files:**
- Modify: `tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 1: Verify document serialization.**

Assert the generated `figure.pnfig.json` carries the compact provenance under
`recipe.evidence.quality_provenance` and contains no non-finite JSON values.

- [x] **Step 2: Verify no publication-role drift.**

Compare the role set and figure IDs from the new fixture with the existing
publication-pack expectations. Evidence attachment must be the only new recipe
content.

- [x] **Step 3: Run the focused final matrix.**

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_figure_evidence_final'
python -m pytest tests/test_saxs_figure_evidence_binding.py tests/test_saxs_mode_evidence_contract.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_publication_pack_upgrade.py tests/test_saxs_export_bundle.py -q
```

Expected: all tests pass with only previously known SAXS font warnings.

### Task 5: Task-scoped verification and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-27-saxs-figure-evidence-binding.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [x] **Step 1: Run exact structured verification.**

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_figure_evidence_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-figure-evidence-binding.md --changed --types
```

Expected: task/memory checks, changed Ruff, compile/type, quality,
preprocessing, and whitespace checks pass; any pre-existing out-of-scope
workspace findings are recorded rather than mixed into this task.

- [x] **Step 2: Run the complete SAXS matrix and diff check.**

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_figure_evidence_saxs'
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
git diff --check
```

- [x] **Step 3: Update durable records with exact counts and limitations.**

Record the focused matrix, complete SAXS count, task-scoped gates, strict JSON
result, and any full/boundary timeout without claiming it passed. Preserve all
pre-existing untracked and unrelated tracked changes.

- [x] **Step 4: Create the atomic checkpoint.**

```powershell
python scripts/auto_commit.py --message "feat(saxs): bind figure evidence provenance" --files polynexus/core/saxs_engine/figure_evidence.py polynexus/core/saxs_engine/figure_provider.py polynexus/core/saxs_engine/figure_static.py polynexus/core/saxs_engine/figure_temperature.py polynexus/core/saxs_engine/figure_strain.py tests/test_saxs_figure_evidence_binding.py docs/agent/tasks/2026-07-27-saxs-figure-evidence-binding.md docs/superpowers/plans/2026-07-27-saxs-figure-evidence-binding.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

Expected: one local commit containing exactly the listed files and no push.
