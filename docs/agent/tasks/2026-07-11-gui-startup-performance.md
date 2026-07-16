# Agent Task

## Goal

把 GUI 启动优化到主窗口可见且首屏可交互，冷启动目标为 3 秒内。

## Non-goals

- 不改变任何分析算法、结果 schema、持久化、导出或科学语义。
- 不重写全部 `MainWindow`/mixin 架构。
- 不删除功能或跳过必要初始化来制造虚假速度提升。

## Context

- Related modules: `polynexus/app.py`, `polynexus/gui/main_window.py`, 首屏和非首屏 GUI widgets。
- Existing contracts: `MainWindow()` 默认同步构造；GUI 使用既有 Qt signals、tab 顺序和 `AnalysisResult` 相关服务。
- Relevant docs: `docs/superpowers/specs/2026-07-11-gui-startup-performance-design.md`, `docs/maintenance-boundaries.md`, `docs/agent/testing-matrix.md`。
- Existing tests: `tests/test_main_window_*.py`、`tests/test_chart_viewer.py`、`tests/test_sample_browser.py`、`tests/test_main_window_persistence.py`。
- Baseline note: 当前环境对 `pandas` 与 PySide6/Shiboken 的导入组合存在兼容性异常，启动基线需在依赖正常环境中复测。

## Acceptance criteria

- [x] GUI 入口显示主窗口后，数据输入首屏控件已创建且可交互。
- [x] 非首屏组件在事件循环中完成延迟初始化，重复调度不会重复创建或连接信号。
- [x] 默认同步 `MainWindow()` 调用和既有 GUI 行为保持兼容。
- [x] 启动阶段有可复现计时输出；当前环境首屏约 1.90 秒，fresh-process probe 约 2.67 秒。
- [ ] `python scripts/verify.py --changed --types` 通过（被存量 `main_window.py` Ruff 问题阻断，详见验收记录）。

## Affected boundaries

- [x] GUI
- [ ] CLI
- [ ] Analysis engine
- [ ] Result/schema contract
- [ ] Persistence
- [ ] Export/reporting
- [ ] Evaluation/baseline
- [x] Documentation/tooling

## Implementation plan

1. 增加首屏/延迟阶段的失败回归测试和计时探针。
2. 在 `app.py` 延迟导入主窗口，并为 GUI 入口启用延迟初始化。
3. 在 `MainWindow` 中保留同步路径，新增幂等的延迟组件构造和占位状态。
4. 运行 focused GUI tests、统一验证和类型检查，复核完整 diff。

## Verification

```powershell
pytest tests/test_gui_startup.py tests/test_main_window_persistence.py -q
python scripts/verify.py --changed --types
git diff --check
```

## Risks and compatibility

- User-visible risk: 延迟 tab 在初始化期间短暂显示加载状态。
- Data/schema risk: 无预期影响；不改分析结果或持久化结构。
- Scientific/baseline risk: 无预期影响；不改科学计算路径。
- Rollback or compatibility path: `MainWindow()` 默认保持同步模式；GUI 入口可关闭 defer 参数恢复原有构造顺序。

## Memory impact

- [ ] No durable project memory change.
- [x] Update `docs/agent/memory/active-work.md`。
- [x] Add or update a decision entry。
- [ ] Add a lesson or known-issue entry。

## Handoff

- Changed files: 见 `docs/acceptance/2026-07-11-gui-startup-performance.md`。
- Verification results: focused startup 3 passed，持久化 222 passed；统一命令被存量 Ruff 阻断。
- Known limitations: 启动时间受 Python、Qt、科学栈版本和机器冷缓存影响。
- Follow-up tasks: 如仍未达到 3 秒，再单独评估科学栈拆包或更细粒度的 widget 分片。

## Commit and review checkpoint

- Task ID or slug: `gui-startup-performance`
- Intended commit/PR scope: 仅 GUI 启动性能、focused tests、任务/设计/验收记录。
- Human review required? [ ] No [x] Yes
- Reviewer focus: architecture / data contract / security / performance / science
- Commit or PR reference: 未提交；遵循用户/仓库规则不自动 commit。
