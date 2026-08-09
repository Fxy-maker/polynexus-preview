# GUI Import and AI Panel Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove full-history JSON hydration from the synchronous import and Results-page candidate paths.

**Architecture:** Extend `SampleDB` with compact count/latest-header reads, use them in work-memory construction, and rank comparison candidates from headers. Detailed comparison keeps the existing full-run contract and loads one selected baseline only when the user opens it.

**Tech Stack:** Python, SQLite, PySide6, pytest.

---

### Task 1: Provide compact work-memory reads

**Files:**
- Modify: `polynexus/data/sample_db.py`
- Modify: `polynexus/gui/work_memory_service.py`
- Test: `tests/test_sample_db.py`
- Test: `tests/test_work_memory_service.py`

- [x] **Step 1: Write failing tests**

```python
def test_work_memory_snapshot_uses_latest_run_header_without_full_batch_runs(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    # Seed a sample, batch, and a large run JSON payload.
    snapshot = collect_work_memory_db_snapshot(db)
    assert snapshot.recent_run["id"]
    assert "parameters" not in snapshot.recent_run
```

- [x] **Step 2: Verify RED**

Run: `python -m pytest tests/test_work_memory_service.py -k latest_run_header -q`

Expected: FAIL because the existing snapshot calls `get_analysis_runs()` and
returns a decoded `parameters` mapping.

- [x] **Step 3: Implement compact reads**

```python
def get_work_memory_snapshot(self) -> dict:
    return {
        "sample_count": int(self._conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]),
        "batch_count": int(self._conn.execute("SELECT COUNT(*) FROM batches").fetchone()[0]),
        "recent_run": (self.list_analysis_run_headers(limit=1) or [None])[0],
        "recent_sample": (self.list_samples(limit=1) or [None])[0],
    }
```

Have `collect_work_memory_db_snapshot()` consume this compact mapping and
hydrate the one recent run only in `build_work_memory_payload()` when metrics
are required.

- [x] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_sample_db.py tests/test_work_memory_service.py -q`

Expected: PASS.

### Task 2: Rank comparison candidates from headers

**Files:**
- Modify: `polynexus/gui/analysis_history_service.py`
- Modify: `polynexus/gui/main_window_results_mixin.py`
- Test: `tests/test_analysis_history_service.py`
- Test: `tests/test_main_window_persistence.py`

- [x] **Step 1: Write failing tests**

```python
def test_result_comparison_candidates_prefer_header_query():
    db = HeaderOnlyComparisonDB()
    candidates = result_comparison_candidates({"technique": "saxs"}, db)
    assert [item["id"] for item in candidates] == ["run-1"]
    assert db.full_run_calls == 0
```

- [x] **Step 2: Verify RED**

Run: `python -m pytest tests/test_analysis_history_service.py -k comparison_candidates_prefer_header -q`

Expected: FAIL because candidate discovery iterates `get_analysis_runs()`.

- [x] **Step 3: Implement header ranking and selected hydration**

```python
headers = db.list_analysis_run_headers(limit=500)
selected = select_result_comparison_baseline(headers, selected_id=selected_id)
if selected and "parameters" not in selected:
    selected = db.get_analysis_run(selected["id"])
```

Use only header fields for selector labels/ranking. In
`_open_current_result_comparison()`, hydrate the selected record before calling
the existing detailed comparison view.

- [x] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_analysis_history_service.py tests/test_main_window_persistence.py -k 'comparison or results_compare' -q`

Expected: PASS.

### Task 3: Verify and checkpoint

**Files:**
- Modify: task/spec/plan/memory documents for this task

- [x] **Step 1: Run focused regression tests**

Run: `python -m pytest tests/test_sample_db.py tests/test_work_memory_service.py tests/test_analysis_history_service.py tests/test_main_window_persistence.py -q`

Expected: PASS.

- [x] **Step 2: Run structured verification**

Run: `python scripts/verify.py --task docs/agent/tasks/2026-08-09-gui-import-ai-panel-performance.md --changed --types`

Expected: exit code 0.

- [x] **Step 3: Create one explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "perf(gui): remove import history stalls" --files polynexus/data/sample_db.py polynexus/gui/work_memory_service.py polynexus/gui/analysis_history_service.py polynexus/gui/main_window_results_mixin.py tests/test_sample_db.py tests/test_work_memory_service.py tests/test_analysis_history_service.py tests/test_main_window_persistence.py docs/agent/tasks/2026-08-09-gui-import-ai-panel-performance.md docs/superpowers/specs/2026-08-09-gui-import-and-ai-panel-performance-design.md docs/superpowers/plans/2026-08-09-gui-import-ai-panel-performance.md docs/agent/memory/current-state.md
```

Expected: one local commit and no push, merge, or deployment.
