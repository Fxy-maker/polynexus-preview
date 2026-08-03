# SAXS Tensile Axis and Results Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture an explicit detector-plane tensile axis for SAXS strain runs and present stable Task 1/2 orientation evidence without GUI-side scientific decisions.

**Architecture:** Core owns coordinate normalization, convention validation, applicability, and flattened result DTOs. A focused nullable Qt editor captures direct or drag input and the existing table/workbench surfaces render detached values without selecting features or substituting diagnostics.

**Tech Stack:** Python 3.12+, NumPy, PySide6, dataclasses, pytest, existing SAXS result-table and persistence services.

---

## Dependency gate

Do not start this task until Tasks 1 and 2 are checkpointed and their DTO names
match this plan. If `QResolvedOrientationEvidence` or
`OrientationSequenceEvidence` differs, stop for scientific contract review;
do not adapt GUI code to private algorithm state.

## File map

- Modify `polynexus/core/saxs_engine/config.py`: public axis convention and nullable config fields.
- Modify `polynexus/core/saxs_config_binding.py`: pair validation, normalization, and provenance.
- Modify `polynexus/core/saxs.py`: strain config schema and detached result transport.
- Modify `polynexus/core/saxs_engine/saxs_2d_review_context.py`: allowlisted axis and tracking projection.
- Modify `polynexus/core/saxs_engine/figure_strain.py`: preserve existing no-fallback gate while consuming final DTOs.
- Create `polynexus/gui/widgets/saxs_tensile_axis_editor.py`: nullable entry and detector-coordinate drag capture.
- Modify `polynexus/gui/main_window_config_panel_mixin.py`: custom widget collection and preset restore.
- Modify `polynexus/gui/main_window_ai_tuning_mixin.py`: generic custom-widget value restore only.
- Modify `polynexus/gui/main_window_retranslate_mixin.py`: preserve config values across language rebuild.
- Modify `polynexus/gui/main_window_run_mixin.py`: invalidate cached SAXS analysis when scientific config changes.
- Modify `polynexus/gui/result_table_templates.py`: distinct final, diagnostic, delta, q, stability, and reliability columns.
- Modify `polynexus/gui/saxs_results_table_service.py`: consume flattened DTO fields only.
- Modify `polynexus/gui/result_table_models.py` and `polynexus/gui/results_table_service.py`: detach and carry the review context.
- Modify `polynexus/gui/i18n.py`: Chinese and English labels/tooltips.
- Add or extend the focused tests listed in the task card.

### Task 1: Lock coordinate and binding contracts

- [ ] **Step 1: Add RED tests for None, zero, modulo, and convention rejection**

```python
def test_tensile_axis_binding_keeps_none_distinct_from_zero() -> None:
    empty = SAXSConfig()
    apply_saxs_config_panel_values(empty, {
        "tensile_axis_deg": None,
        "tensile_axis_convention": "detector_image_clockwise_deg_v1",
    })
    assert empty.tensile_axis_deg is None

    zero = SAXSConfig()
    report = apply_saxs_config_panel_values(zero, {
        "tensile_axis_deg": 180.0,
        "tensile_axis_convention": "detector_image_clockwise_deg_v1",
    })
    assert zero.tensile_axis_deg == 0.0
    assert report["normalized_values"]["tensile_axis_deg"] == 0.0


def test_tensile_axis_binding_rejects_unknown_convention() -> None:
    cfg = SAXSConfig()
    report = apply_saxs_config_panel_values(cfg, {
        "tensile_axis_deg": 45.0,
        "tensile_axis_convention": "screen_angle_v0",
    })
    assert cfg.tensile_axis_deg is None
    assert report["unavailable"]["tensile_axis_deg"] == "unsupported_tensile_axis_convention"
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_config_binding.py -q`

Expected: the convention field and pair binding do not exist.

- [ ] **Step 3: Add the core convention and pair normalizer**

```python
TENSILE_AXIS_CONVENTION = "detector_image_clockwise_deg_v1"

@dataclass
class SAXSConfig:
    tensile_axis_deg: Optional[float] = None
    tensile_axis_convention: str | None = None


def normalize_tensile_axis(value: Any, convention: Any) -> tuple[float | None, str | None]:
    if value is None or str(value).strip() == "":
        return None, None
    if str(convention or "").strip() != TENSILE_AXIS_CONVENTION:
        raise ValueError("unsupported_tensile_axis_convention")
    angle = float(value)
    if not math.isfinite(angle):
        raise ValueError("tensile_axis_nonfinite")
    return angle % 180.0, TENSILE_AXIS_CONVENTION
```

In `apply_saxs_config_panel_values()`, consume the two axis keys as one pair
before the ordinary field loop. Apply neither field if pair validation fails.
Record `source="explicit_run_config"` in `config_binding_report`; do not use
`orientation_axis_deg` as a fallback.

- [ ] **Step 4: Recheck the Task 1 backend azimuth parity gate**

Run the Task 1 synthetic spot regression for +column, +row, -column, and -row.
It must prove NumPy and pyFAI both map them to 0, 90, 0, and 90 degrees modulo
180 under `detector_image_clockwise_deg_v1`. If this prerequisite is absent or
fails, stop and repair/review Task 1; do not enable drag in Task 3.

- [ ] **Step 5: Run focused GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_config_binding.py tests/test_saxs_feature_orientation_foundation.py tests/test_saxs_preprocess.py -q`

### Task 2: Build a nullable detector-axis editor

- [ ] **Step 1: Add RED transform and interaction tests**

```python
@pytest.mark.parametrize("transform", preview_transforms())
def test_screen_drag_round_trips_to_detector_axis(transform: QTransform) -> None:
    start, end = detector_axis_points(beam_center=(128.0, 96.0), angle_deg=35.0)
    screen_start = transform.map(QPointF(*start))
    screen_end = transform.map(QPointF(*end))
    assert screen_vector_to_detector_axis(screen_start, screen_end, transform.inverted()[0]) == pytest.approx(35.0)


def test_editor_clear_is_none_but_explicit_zero_is_zero(qtbot) -> None:
    editor = SAXSTensileAxisEditor()
    editor.set_axis(0.0, TENSILE_AXIS_CONVENTION)
    assert editor.config_values()["tensile_axis_deg"] == 0.0
    editor.clear_axis()
    assert editor.config_values()["tensile_axis_deg"] is None
```

- [ ] **Step 2: Implement pure screen-to-detector conversion**

```python
def screen_vector_to_detector_axis(
    screen_start: QPointF,
    screen_end: QPointF,
    screen_to_detector: QTransform,
) -> float:
    p0 = screen_to_detector.map(screen_start)
    p1 = screen_to_detector.map(screen_end)
    d_col = p1.x() - p0.x()
    d_row = p1.y() - p0.y()
    if not all(math.isfinite(v) for v in (d_col, d_row)) or math.hypot(d_col, d_row) < 2.0:
        raise ValueError("tensile_axis_drag_too_short")
    return math.degrees(math.atan2(d_row, d_col)) % 180.0
```

The widget exposes `config_values()`, `set_config_values(mapping)`,
`clear_axis()`, and `axisChanged`. It uses a nullable text/spin editor plus an
unframed detector preview. The preview may be empty, but it always shows the
beam center, +column direction, and +row direction. Never infer an axis from
image intensity.

- [ ] **Step 3: Reject unproved preview transforms**

Only accept a drag when the widget has an invertible `QTransform` whose
detector-to-screen-to-detector round trip is within 0.25 pixel at the beam
center and both endpoints. Otherwise keep the prior value and emit
`preview_transform_unverified` as a visible validation state.

- [ ] **Step 4: Run editor GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_tensile_axis_editor.py -q`

### Task 3: Wire config, presets, retranslation, and reruns

- [ ] **Step 1: Add the strain-only schema**

```python
config_schema={
    "tensile_axis_deg": {
        "type": "saxs_tensile_axis",
        "default": None,
        "convention": "detector_image_clockwise_deg_v1",
        "label_key": "CONFIG_SAXS_TENSILE_AXIS",
    }
}
```

Resolve `label_key` in GUI code. Do not import `polynexus.gui.i18n` from core.
This schema also removes the current early return that hides shared SAXS
calibration/mask controls in strain mode; add a regression asserting the full
intended panel appears.

- [ ] **Step 2: Add a generic custom-widget protocol to panel collection**

```python
values_fn = getattr(widget, "config_values", None)
if callable(values_fn):
    values.update(values_fn())
    continue
```

Likewise, `_apply_best_config()` calls `set_config_values(best_config)` before
the standard widget type branches. Update `_current_config_widget_keys()` to
include `widget.config_keys()` so both angle and convention survive preset
compatibility filtering.

- [ ] **Step 3: Preserve values across language rebuild**

Before rebuilding the config panel, capture `_collect_config_panel_values()`;
rebuild through `_update_config_panel()` for the active submodule; then restore
only compatible keys. Assert named presets preserve explicit `None`, zero,
angle, and convention. Assert recent calibration excludes both tensile-axis
keys because they describe sample mounting.

- [ ] **Step 4: Invalidate stale cached SAXS engines**

In `_replot()`, compare `saxs_config_snapshot(new_config)` with the cached
engine's configuration snapshot. If they differ, do not pass the cached engine
and do not use `skip_to="plot"`. Add a regression proving an axis change reaches
the new engine rather than replotting stale analysis.

- [ ] **Step 5: Run GUI config/persistence GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_main_window_persistence.py tests/test_gui_startup.py -q`

### Task 4: Transport and present stable orientation evidence

- [ ] **Step 1: Add RED table and DTO tests**

```python
def test_strain_table_never_substitutes_raw_for_missing_final() -> None:
    presentation = build_saxs_results_presentation(strain_payload(final=None, raw=0.41))
    row = presentation.primary_section.rows[0]
    assert row.cells["f_Herman"].value is None
    assert row.cells["f_Herman_raw"].value == pytest.approx(0.41)


def test_all_tracks_are_presented_without_primary_selection() -> None:
    presentation = build_saxs_results_presentation(two_track_payload())
    assert {row.cells["orientation_track_id"].value for row in presentation.detail_sections[0].rows} == {"track-a", "track-b"}
```

- [ ] **Step 2: Flatten core-owned per-observation fields**

`SAXSEngine.get_parameters()` copies the complete sequence DTO and creates one
table row per frame/track observation with these names only:

```python
{
    "f_Herman": observation.f_reference,
    "f_Herman_raw": observation.f_principal_raw,
    "delta_f_from_zero": observation.delta_f_from_zero,
    "delta_f_stability_lower": lower_or_none,
    "delta_f_stability_upper": upper_or_none,
    "orientation_q_min_nm1": observation.q_range_nm1[0],
    "orientation_q_max_nm1": observation.q_range_nm1[1],
    "orientation_track_id": track.track_id,
    "orientation_reliability_status": observation.reliability_status,
    "orientation_reason_summary": "; ".join(observation.reason_codes),
}
```

No GUI service recomputes lower/upper bounds, chooses a track, checks support,
or changes status.

- [ ] **Step 3: Extend the strict review context**

Allowlist `tensile_axis_deg`, `reference_axis_deg`, `reference_axis_kind`,
`orientation_vector_kind`, `herman_convention`, `isotropic_baseline`, and the
bounded tracking summaries. Deep-copy the context when converting
`ResultsTablePresentation` to `ResultsTableModel` so GUI mutation cannot alter
the source DTO.

- [ ] **Step 4: Add explicit table labels**

Add separate translated labels for tensile-axis Herman, principal-axis
diagnostic Herman, same-feature delta, stability bound, q range, track ID,
reliability, and reasons. Missing final values render the existing unavailable
cell; diagnostic values never fill them. Keep `_effective_orientation_fherman()`
as the figure gate.

- [ ] **Step 5: Run presentation GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_results_table_service.py tests/test_result_table_templates.py tests/test_results_table_service.py tests/test_saxs_strain_method_evidence.py tests/test_saxs_figure_evidence_binding.py -q`

### Task 5: Verify, visually inspect, and checkpoint

- [ ] **Step 1: Run the full required matrix**

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_config_binding.py tests/test_saxs_tensile_axis_editor.py tests/test_saxs_results_table_service.py tests/test_result_table_templates.py tests/test_results_table_service.py tests/test_saxs_strain_method_evidence.py tests/test_main_window_persistence.py tests/test_saxs_figure_evidence_binding.py -q
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
$env:PYTHONUTF8='1'
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-tensile-axis-results-presentation.md --changed --types
git diff --check
```

- [ ] **Step 2: Perform restarted-GUI acceptance**

Launch a fresh GUI process. In SAXS strain mode, verify direct 0 degrees,
direct 35 degrees, clear, and drag input; switch language; save/load a named
preset; confirm recent calibration does not restore the axis; rerun; inspect
final/raw/delta/q/reliability columns at desktop and narrow window widths.
Record screenshots or concise observations in the task card, not generated
files in the repository.

- [ ] **Step 3: Review and checkpoint the exact allowlist**

Use the task card's final affected-boundary list plus tests actually changed.
Do not include Task 1/2 files unless this task genuinely changed them after a
scientific stop-gate review. Then run:

```powershell
python scripts/auto_commit.py --message "feat(saxs): add tensile axis results workflow" --files polynexus/core/saxs.py polynexus/core/saxs_config_binding.py polynexus/core/saxs_engine/config.py polynexus/core/saxs_engine/saxs_2d_review_context.py polynexus/core/saxs_engine/figure_strain.py polynexus/gui/main_window_config_panel_mixin.py polynexus/gui/main_window_ai_tuning_mixin.py polynexus/gui/main_window_retranslate_mixin.py polynexus/gui/main_window_run_mixin.py polynexus/gui/widgets/saxs_tensile_axis_editor.py polynexus/gui/result_table_templates.py polynexus/gui/result_table_models.py polynexus/gui/results_table_service.py polynexus/gui/saxs_results_table_service.py polynexus/gui/i18n.py tests/test_saxs_config_binding.py tests/test_saxs_tensile_axis_editor.py tests/test_saxs_results_table_service.py tests/test_result_table_templates.py tests/test_results_table_service.py tests/test_saxs_strain_method_evidence.py tests/test_main_window_persistence.py tests/test_saxs_figure_evidence_binding.py docs/agent/tasks/2026-08-03-saxs-tensile-axis-results-presentation.md
```

Do not push. Record the restarted-GUI and coordinate evidence, then continue to
Task 4 only when no documented stop gate is triggered. Human scientific/GUI
review remains required before merge.
