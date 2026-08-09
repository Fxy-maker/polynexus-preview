# GUI Performance Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make History and high-volume logging non-blocking at normal GUI scale, and publish SAXS pipeline timing evidence without changing analysis results.

**Architecture:** Add a header-only read contract to `SampleDB`, consume it from the existing history service, and lazily replace a selected header with the existing full record contract. Batch GUI log updates through one Qt timer and delay only the non-critical post-persist History refresh. Time existing SAXS boundaries with monotonic clocks and logging only.

**Tech Stack:** Python 3.14, SQLite, PySide6, pytest.

---

### Task 1: Add indexed history headers

**Files:**
- Modify: `polynexus/data/sample_db.py`
- Modify: `polynexus/gui/analysis_history_service.py`
- Test: `tests/test_sample_db.py`
- Test: `tests/test_analysis_history_service.py`

- [x] **Step 1: Write failing header-query tests**

```python
def test_list_analysis_run_headers_omits_large_json_payloads(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    batch_id = _create_batch(db)
    run_id = db.create_analysis_run(batch_id, "saxs", parameters={"large": "x" * 10000})

    header = db.list_analysis_run_headers()[0]

    assert header["id"] == run_id
    assert "parameters" not in header
    assert "results_summary" not in header


def test_collect_history_rows_prefers_header_query_when_available():
    db = _HeaderOnlyHistoryDB()
    assert collect_history_rows(db) == [{"id": "run-1", "technique": "saxs"}]
    assert db.header_calls == 1
```

- [x] **Step 2: Verify RED**

Run: `python -m pytest tests/test_sample_db.py tests/test_analysis_history_service.py -q`

Expected: FAIL because `list_analysis_run_headers` is absent and the service only traverses batches.

- [x] **Step 3: Implement header query and indexes**

```python
def list_analysis_run_headers(self, *, limit: int = 500) -> list[dict]:
    rows = self._conn.execute(
        "SELECT id,batch_id,technique,submodule,output_dir,status,ai_tuned,confirmed,created_at "
        "FROM analysis_runs ORDER BY created_at DESC LIMIT ?",
        (max(1, int(limit)),),
    ).fetchall()
    return [dict(row) for row in rows]
```

Create `idx_batches_sample_id` and `idx_analysis_runs_batch_created_at` with
`CREATE INDEX IF NOT EXISTS` in `_create_tables()`. In `collect_history_rows`,
call `list_analysis_run_headers()` when it exists; otherwise preserve the
existing fake-DB traversal.

- [x] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_sample_db.py tests/test_analysis_history_service.py -q`

Expected: PASS.

### Task 2: Hydrate selected History records on demand

**Files:**
- Modify: `polynexus/gui/main_window_history_mixin.py`
- Test: `tests/test_main_window_persistence.py`

- [x] **Step 1: Write a failing lazy-hydration regression**

```python
def test_selected_history_header_hydrates_only_selected_record(window, tmp_path):
    window._sample_db = SampleDB(tmp_path / "samples.db")
    first_id, second_id = _create_two_history_runs(window._sample_db)
    window._refresh_history()

    window._history_table.selectRow(0)
    selected = window._selected_history_record()

    assert selected["id"] == first_id
    assert selected["parameters"]
    assert "parameters" not in window._history_cache[1]
```

- [x] **Step 2: Verify RED**

Run: `python -m pytest tests/test_main_window_persistence.py -k selected_history_header_hydrates -q`

Expected: FAIL because header records are returned unchanged.

- [x] **Step 3: Implement minimal cache replacement**

```python
def _selected_history_record(self):
    row = self._selected_history_row()
    if row < 0 or row >= len(self._history_cache):
        return None
    record = self._history_cache[row]
    if "parameters" not in record:
        loaded = self._ensure_sample_db().get_analysis_run(record.get("id"))
        if loaded is not None:
            self._history_cache[row] = loaded
            record = loaded
    return record
```

Keep table rendering header-safe by accepting absent `parameters`,
`results_summary`, and `analysis_evidence` as empty mappings.

- [x] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_main_window_persistence.py -k 'history and not real' -q`

Expected: PASS.

### Task 3: Batch and bound GUI logs

**Files:**
- Modify: `polynexus/gui/main_window.py`
- Test: `tests/test_gui_startup.py`
- Test: `tests/test_main_window_persistence.py`

- [x] **Step 1: Write failing log-buffer tests**

```python
def test_gui_log_buffer_flushes_many_lines_as_one_bounded_document(qt_app):
    window = MainWindow(defer_optional_ui=True)
    for index in range(700):
        window.log(f"line {index}")

    assert "line 699" not in window._log_panel.toPlainText()
    window.flush_pending_log_messages()

    assert "line 699" in window._log_panel.toPlainText()
    assert window._log_panel.document().blockCount() <= 500
```

- [x] **Step 2: Verify RED**

Run: `python -m pytest tests/test_gui_startup.py tests/test_main_window_persistence.py -k log_buffer -q`

Expected: FAIL because `log()` appends synchronously and no flush method exists.

- [x] **Step 3: Implement one-timer buffering**

Create `_pending_log_lines`, a single-shot `QTimer`, and
`flush_pending_log_messages()`. Queue both ordinary and warning-summary lines,
set `self._log_panel.document().setMaximumBlockCount(500)`, and append the
joined queued HTML once per timer tick. Enable copying from the queued state;
do not call `toPlainText()` during each append.

- [x] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_gui_startup.py tests/test_main_window_persistence.py -k 'log_buffer or log_' -q`

Expected: PASS.

### Task 4: Defer only non-critical completion refresh

**Files:**
- Modify: `polynexus/gui/main_window_history_mixin.py`
- Modify: `polynexus/gui/main_window_run_mixin.py`
- Test: `tests/test_main_window_persistence.py`

- [x] **Step 1: Write a failing completion-scheduling regression**

```python
def test_finished_run_schedules_history_refresh_after_persist(window, result, monkeypatch):
    scheduled = []
    monkeypatch.setattr(window, "_schedule_history_refresh", lambda: scheduled.append(True))
    monkeypatch.setattr(window, "_persist_analysis_run", lambda *_args, **_kwargs: "run-1")

    window._on_finished(result)

    assert scheduled == [True]
```

- [x] **Step 2: Verify RED**

Run: `python -m pytest tests/test_main_window_persistence.py -k schedules_history_refresh -q`

Expected: FAIL because persistence immediately calls `_refresh_history()`.

- [x] **Step 3: Add the scheduling boundary**

Add `refresh_history: bool = True` to `_persist_analysis_run`; preserve direct
callers with the default. Add `_schedule_history_refresh()` using an idempotent
`QTimer.singleShot(0, ...)`. In `_on_finished`, persist with
`refresh_history=False` and call the scheduler after Results and Plots are
published.

- [x] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_main_window_persistence.py -k 'schedules_history_refresh or persist' -q`

Expected: PASS.

### Task 5: Emit SAXS stage timing evidence

**Files:**
- Modify: `polynexus/core/saxs.py`
- Test: `tests/test_saxs_engine.py`

- [x] **Step 1: Write a failing timing-log regression**

```python
def test_saxs_pipeline_logs_elapsed_stage_durations(monkeypatch, tmp_path):
    messages = []
    engine = SAXSEngine(log_fn=messages.append)
    monkeypatch.setattr(engine, "_run_pipeline_stage", lambda *args: _result())

    engine.run_pipeline("fixture.edf", str(tmp_path))

    assert any("saxs_stage_duration" in message for message in messages)
```

- [x] **Step 2: Verify RED**

Run: `python -m pytest tests/test_saxs_engine.py -k stage_duration -q`

Expected: FAIL because no timing log is emitted.

- [x] **Step 3: Measure existing boundaries without changing calls**

Wrap the existing SAXS pipeline call and its existing export/publication
boundary with `time.perf_counter()`. Emit `saxs_stage_duration stage=<name>
seconds=<rounded>` through the existing logger/log callback only after each
stage succeeds. Re-raise existing exceptions unchanged.

- [x] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_saxs_engine.py -k stage_duration -q`

Expected: PASS.

### Task 6: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-08-09-gui-performance-recovery.md`
- Modify: `docs/superpowers/specs/2026-08-09-gui-performance-recovery-design.md`
- Modify: `docs/superpowers/plans/2026-08-09-gui-performance-recovery.md`
- Modify: `docs/agent/memory/current-state.md`

- [x] **Step 1: Run focused regression suites**

Run: `python -m pytest tests/test_sample_db.py tests/test_analysis_history_service.py tests/test_gui_startup.py tests/test_main_window_persistence.py tests/test_saxs_engine.py -q`

Expected: PASS, with any existing warnings recorded separately.

- [x] **Step 2: Run structured verification**

Run: `python scripts/verify.py --task docs/agent/tasks/2026-08-09-gui-performance-recovery.md --changed --types`

Expected: exit code 0.

- [x] **Step 3: Create the explicit-allowlist checkpoint**

```powershell
python scripts/auto_commit.py `
  --message "perf(gui): remove history and log stalls" `
  --files polynexus/data/sample_db.py polynexus/gui/analysis_history_service.py polynexus/gui/main_window_history_mixin.py polynexus/gui/main_window_run_mixin.py polynexus/gui/main_window.py polynexus/core/saxs.py tests/test_sample_db.py tests/test_analysis_history_service.py tests/test_gui_startup.py tests/test_main_window_persistence.py tests/test_saxs_engine.py docs/agent/tasks/2026-08-09-gui-performance-recovery.md docs/superpowers/specs/2026-08-09-gui-performance-recovery-design.md docs/superpowers/plans/2026-08-09-gui-performance-recovery.md docs/agent/memory/current-state.md
```

Expected: one local commit; no push, merge, or database cleanup.
