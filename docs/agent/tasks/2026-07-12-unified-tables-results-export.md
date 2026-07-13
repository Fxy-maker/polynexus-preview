# Agent Task

## Goal

在已合并的 Unified Tables immutable contract 之上，接入 generic/structured result presentation、CSV/TSV/XLSX export 和 clipboard extraction，使结果表保留 raw value、status、evidence reason 与可追溯的导出边界。

## Non-goals

- 不直接合并 PR #9；仅移植已审计的 table-specific commits。
- 不接入结果表 GUI panel、MainWindow、workspace navigation 或 history service。
- 不修改 SAXS/DSC/WAXS 科学算法、publication role 或 evidence gate。
- 不混入 preprocessing、editor、sample browser 或 management table 变更。

## Context

- Related modules: `polynexus/gui/result_table_models.py`, `result_table_templates.py`, `analysis_result_table_templates.py`, `analysis_results_table_service.py`, `saxs_results_table_service.py`, `results_table_service.py`, `table_export_service.py`, `table_clipboard_service.py`。
- Existing contracts: immutable presentation contracts from PR #11、`AnalysisResult.parameters`/`analysis_evidence`/validation fields、generic fallback compatibility。
- Relevant docs: `docs/superpowers/specs/2026-07-10-unified-table-system-design.md`; `docs/superpowers/plans/2026-07-11-unified-tables-wave2-analysis-results.md`。
- Existing tests: table model/template/service tests、SAXS/analysis presentation tests、export and clipboard tests。

## Acceptance criteria

- [x] generic single/multi-sample/batch result paths preserve existing stored rows and fallback semantics。
- [x] SAXS and DSC/IR/WAXS/NMR structured presentation paths expose primary/detail/diagnostic sections without moving science logic into GUI handlers。
- [x] CSV/TSV/XLSX bundle export keeps typed values and literal formula-like strings; invalid bundles do not overwrite files。
- [x] clipboard extraction respects selected rows, column offsets, and empty-table behavior。
- [x] diff contains only result-table/presentation/export/clipboard modules, tests, task/memory evidence; no MainWindow/panel/history/preprocess files。

## Affected boundaries

- [x] GUI
- [ ] CLI
- [ ] Analysis engine
- [x] Result/schema contract
- [ ] Persistence
- [x] Export/reporting
- [x] Evaluation/baseline
- [x] Documentation/tooling

## Implementation plan

1. 从最新 `main` 创建 `codex/unified-tables-results-export-v2`，保留用户工作区不变；先写 RED tests，再移植 PR #9 table-specific commits。
2. 接入 structured templates/adapters、generic dispatch、bundle export 和 clipboard helpers，修复 generic fallback 与旧 payload 兼容差异。
3. 运行 task_check、focused matrix、changed Python Ruff、compileall、type/verify gate、CI 和 data-contract/export review，再创建单独 PR。

## Verification

```bash
python scripts/task_check.py --task docs/agent/tasks/2026-07-12-unified-tables-results-export.md
python -m pytest tests/test_result_table_models.py tests/test_result_table_templates.py tests/test_results_export_contracts.py tests/test_export_contracts.py tests/test_clipboard_contracts.py tests/test_table_export_service.py tests/test_results_table_service.py tests/test_saxs_results_table_service.py tests/test_analysis_result_table_templates.py tests/test_analysis_results_table_service.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-12-unified-tables-results-export.md --changed
python scripts/verify.py --changed --types
git diff --check
```

## Risks and compatibility

- User-visible risk: structured table status/evidence display or export columns may mislead review users。
- Data/schema risk: raw values and typed export cells must remain distinct from formatted display text; old generic payloads remain readable。
- Scientific/baseline risk: table adapters only expose provider evidence and never promote values to Main。
- Rollback or compatibility path: revert this result-table/export PR independently; keep existing generic fallback and export entry point。

## Memory impact

- [ ] No durable project memory change。
- [x] Update `docs/agent/memory/active-work.md`。
- [x] Add or update a decision entry for result presentation/export boundaries。
- [ ] Add a lesson or known-issue entry。

## Handoff

- Changed files: table templates/services/export/clipboard, focused tests, task card and memory evidence only。
- Verification results: task card valid; focused matrix 133 passed; quality gate 280 passed; changed-file Ruff, compileall, and `git diff --check` passed. The standard verifier was also audited; its script-root assumption is recorded below。
- Known limitations: GUI panel and workspace consumption remain in the next task card。
- Follow-up tasks: `2026-07-12-unified-tables-gui-integration.md`。

## Commit and review checkpoint

- Task ID or slug: `unified-tables-results-export-2026-07-12`
- Intended commit/PR scope: Unified Tables result presentation/export 第二切片，一个 PR。
- Human review required? [ ] No [x] Yes
- Reviewer focus: data contract / export compatibility / GUI service boundary
- Commit or PR reference: pending
