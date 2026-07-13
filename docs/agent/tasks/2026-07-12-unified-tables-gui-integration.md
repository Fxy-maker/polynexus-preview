# Agent Task

## Goal

将已合并的 Unified Tables contracts 与 results/export model 接入现有 GUI 结果面板和 workspace/history 流程，同时保持 MainWindow 只消费 service/view-model。

## Non-goals

- 不重新设计 GUI streamlining；PR #8 仍是 navigation authority。
- 不恢复旧 gallery discovery、重复 chart/compare controls 或 legacy editor fallback。
- 不修改 SAXS/DSC/WAXS provider、分析算法、publication role 或 evidence gate。
- 不把 Unified Tables、Editor、Startup performance 混成一个 PR。

## Context

- Related modules: `polynexus/gui/widgets/results_table_panel.py`, `main_window_results_mixin.py`, `main_window_output_mixin.py`, `main_window_history_mixin.py`, `main_window_retranslate_mixin.py`, `workspace_mode.py`。
- Existing contracts: PR #10/11/12 合并后的 figure/evidence/table contracts、`ResultsTableModel`、`ResultsTablePresentation` 与 workspace/navigation contracts。
- Existing tests: `tests/test_results_table_panel.py`, `tests/test_unified_tables_gui_integration.py`, `tests/test_main_window_results_mixin.py`, `tests/test_main_window_result_semantics_mixin.py`, `tests/test_main_window_persistence.py`, `tests/test_chart_viewer.py`。

## Acceptance criteria

- [x] 结果面板显示 Unified Tables model 的字段、状态、单位和 evidence/provenance reason，且不读取 technique-specific 内部状态。
- [x] workspace 切换、复核、history restore 和持久化 round-trip 不丢失当前 result table context。
- [x] 缺失、降级和失败结果有稳定的用户可见状态和 action hint。
- [x] 不重新引入 PR #8 已删除的重复控件或旧 gallery 行为。
- [x] diff 只包含结果面板/GUI consumption、history/workspace 接线、focused tests、task/memory evidence；不包含旧 PR #9 的其他切片。

## Affected boundaries

- [x] GUI
- [ ] CLI
- [ ] Analysis engine
- [x] Result/schema contract
- [x] Persistence
- [ ] Export/reporting
- [ ] Evaluation/baseline
- [x] Documentation/tooling

## Implementation plan

1. 从最新 `main` 创建 `codex/unified-tables-gui-integration-v2`，只移植已审计的 results panel commits，不合并旧 PR #9。
2. 先添加 panel 接线、workspace context、history restore 和 bilingual retranslate 回归测试，再通过 `ResultsTableModel`/`ResultsTablePresentation` 接入现有 panel。
3. 运行 focused GUI matrix、task_check、changed Ruff/compile/type/boundary gate、CI 和 GUI boundary review，再创建独立 PR。

## Verification

```bash
python scripts/task_check.py --task docs/agent/tasks/2026-07-12-unified-tables-gui-integration.md
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest tests/test_results_table_panel.py tests/test_unified_tables_gui_integration.py tests/test_main_window_results_mixin.py tests/test_main_window_result_semantics_mixin.py tests/test_main_window_persistence.py tests/test_chart_viewer.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-12-unified-tables-gui-integration.md --changed
python scripts/verify.py --boundary
python scripts/verify.py --changed --types
git diff --check
```

Tooling note: `scripts/task_check.py`, `scripts/verify.py`, and the agent-memory
checker are user-local process assets under `D:\PolyNexus` and are not tracked
in the production `main` baseline. Their direct paths are therefore not
reproducible from this branch; the task-check, changed Ruff/compile, quality
gate, boundary audit, diff-check, and type-target checks were run against this
worktree using those local tools, with the limitation recorded here.

## Risks and compatibility

- User-visible risk: structured status/evidence display could mislead users or lose context during restore.
- Data/schema risk: persistence stores only stable result/workspace DTOs and never provider objects.
- Scientific/baseline risk: GUI does not recompute science or alter evidence gates.
- Rollback path: revert this GUI consumption PR independently; generic table fallback remains available when submodule context is absent or an adapter fails.

## Memory impact

- [ ] No durable project memory change.
- [x] Update `docs/agent/memory/active-work.md`.
- [x] Add or update a decision entry for GUI consumption boundaries.
- [ ] Add a lesson or known-issue entry.

## Handoff

- Changed files: results table panel, MainWindow result/output/history/retranslate/navigation mixins, focused GUI integration tests, task/memory evidence.
- Verification results: 225 GUI-focused tests passed after stale-submodule regression coverage; task-check, changed Ruff, compileall, diff-check, and local quality gate (280 tests) passed; boundary/type-target/CI evidence is recorded before merge.
- Known limitations: no editor/export foundation changes; unqualified legacy GUI result payloads intentionally use generic fallback.
- Follow-up tasks: Editor/Export reconciliation card.

## Commit and review checkpoint

- Task ID or slug: `unified-tables-gui-integration-2026-07-12`
- Intended commit/PR scope: Unified Tables GUI consumption third slice, one PR.
- Human review required? [ ] No [x] Yes
- Reviewer focus: GUI boundary / persistence / user-visible state
- Commit or PR reference: pending
