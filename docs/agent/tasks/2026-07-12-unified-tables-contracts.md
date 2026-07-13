# Agent Task

## Goal

从最新 `main` 提取 Unified Tables 第一条可审查切片，建立稳定的 immutable table presentation contract、状态字段和 raw/display value 边界，使后续 result service 能消费结构化结果而不修改分析算法。

## Non-goals

- 不直接合并 PR #9 的历史提交。
- 不实现结果表 service、批处理汇总、导出或 GUI 面板。
- 不修改 SAXS/DSC/WAXS 科学算法、publication role 或 evidence gate。
- 不把技术特定分支判断放入 `MainWindow`。

## Context

- Related modules: `polynexus/gui/result_table_models.py`；后续切片使用 `polynexus/gui/results_table_service.py`。
- Existing contracts: `AnalysisResult` 稳定结果字段、raw/display/provenance 分离、已合并 figure lifecycle。
- Relevant docs: `docs/superpowers/specs/2026-07-10-unified-table-system-design.md`; `docs/superpowers/plans/2026-07-11-unified-tables-wave1-foundation-saxs.md`; `docs/acceptance/2026-07-12-mainline-integration-reconciliation-inventory.md`。
- Existing tests: `tests/test_engine_result.py`; `tests/test_result_table_models.py`。

## Acceptance criteria

- [x] TableColumn、TableCell、ResultTableSection、HeroMetric 和 ResultsTablePresentation 是 immutable contracts。
- [x] numpy scalar 可归一化为 Python scalar；嵌套 mutable raw value 被拒绝。
- [x] missing、boolean、integer、finite float 和 non-finite float 有稳定可测试的显示语义，且 raw value 不丢失。
- [x] 变更仅限 contract、对应测试和任务卡，并通过 data-contract review。

## Affected boundaries

- [ ] GUI
- [ ] CLI
- [ ] Analysis engine
- [x] Result/schema contract
- [ ] Persistence
- [ ] Export/reporting
- [x] Evaluation/baseline
- [x] Documentation/tooling

## Implementation plan

1. 从 `origin/main` 创建 `codex/unified-tables-contracts-v2`，保留用户工作区不变。
2. 先写并验证失败测试，再实现最小 immutable contract 和 scalar/format helpers。
3. 运行 focused、changed-scope、type、compile 和 whitespace checks，形成独立 PR；不携带 service、export 或 GUI navigation 文件。

## Verification

```bash
python scripts/task_check.py --task docs/agent/tasks/2026-07-12-unified-tables-contracts.md
python -m pytest tests/test_engine_result.py tests/test_result_table_models.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-12-unified-tables-contracts.md --changed
python scripts/verify.py --changed --types
git diff --check
```

## Risks and compatibility

- User-visible risk: 显示状态或 missing/unavailable 文案分类错误。
- Data/schema risk: raw value 必须保持可追溯，不能把展示字符串写回分析结果。
- Scientific/baseline risk: 本卡不判定 Main/SI/Diagnostics。
- Rollback or compatibility path: 单独 revert contract commit，不影响后续 service/export 切片。

## Memory impact

- [ ] No durable project memory change。
- [x] Update `docs/agent/memory/active-work.md`。
- [x] Add or update a decision entry for the canonical table contract。
- [ ] Add a lesson or known-issue entry。

## Handoff

- Changed files: `polynexus/gui/result_table_models.py`、`tests/test_result_table_models.py` 和本卡。
- Verification results: task_check passed; 16 focused tests passed; changed Python Ruff passed; compileall passed; staged diff check passed; GitHub CI quality gate passed on PR #11。
- Known limitations: result service/export/panel 尚未接入。
- Follow-up tasks: `2026-07-12-unified-tables-results-export.md`。

## Commit and review checkpoint

- Task ID or slug: `unified-tables-contracts-2026-07-12`
- Intended commit/PR scope: Unified Tables immutable contract 第一切片，一个 PR。
- Human review required? [ ] No [x] Yes
- Reviewer focus: data contract / architecture / scientific evidence semantics
- Commit or PR reference: PR #11, reviewed and approved by the user in chat on 2026-07-13。
