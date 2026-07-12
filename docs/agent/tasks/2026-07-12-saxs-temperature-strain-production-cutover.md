# Agent Task

## Goal

将 SAXS 温度/时间序列和应变序列的绘图生产路径，逐步切换到当前统一的 `FigureDefinition → FigurePipeline → RunFigureManifest → Gallery/Editor` 生命周期。用户可观察到的结果是：按当前实验模式生成稳定的 Main / SI / Diagnostics publication pack，写入 active manifest，并能被现有图库和编辑器打开。

任务日期：2026-07-12

## Non-goals

- 不重新设计 SAXS 科学分析算法、质量评分、物理模型或参数拟合。
- 不改变已经接入的 SAXS 静态 publication provider，除非共享契约修复直接影响其回归。
- 不合并整块 GUI streamlining、旧版图库 fallback 或旧 editor 架构迁移。
- 不把 DSC、WAXS、NMR 的生产切换混入本任务。
- 不通过猜测缺失的科学证据来提升 publication role；缺失证据必须进入 SI/Diagnostics 或保留明确原因。

## Context

- Related modules:
  - `polynexus/core/saxs.py`
  - `polynexus/core/saxs_engine/figure_common.py`
  - `polynexus/core/saxs_engine/figure_selection.py`
  - `polynexus/core/saxs_engine/figure_eligibility.py`
  - `polynexus/core/saxs_engine/figure_temperature.py`
  - `polynexus/core/saxs_engine/figure_strain.py`
  - `polynexus/core/saxs_engine/figure_provider.py`
  - `polynexus/core/figures/`
  - `polynexus/gui/plot_gallery_service.py`
  - `polynexus/gui/widgets/chart_viewer.py`
- Existing contracts:
  - `FigureDefinition.publication_role` / `display_order`
  - `FigurePipeline`、`FigureProductionPublisher`、`RunFigureManifest`
  - shared publication audit and 600-DPI TIFF asset group
  - current SAXS `SAXSFrameView`、representative-frame selection and eligibility contracts
- Relevant docs:
  - `docs/superpowers/plans/2026-07-10-saxs-publication-figure-packs.md`
  - `docs/baselines/PolyNexus 番外阶段C-T1 温变SAXS当前基线台账.md`
  - `docs/baselines/PolyNexus 番外阶段I-T1 拉伸SAXS当前基线台账.md`
  - `docs/agent/testing-matrix.md`
- Existing tests:
  - `tests/test_saxs_figure_selection.py`
  - `tests/test_saxs_figure_eligibility.py`
  - `tests/test_saxs_temperature_figure_provider.py`
  - `tests/test_saxs_temperature_status.py`
  - `tests/test_saxs_static_figure_provider.py`
  - `tests/test_saxs_figure_document.py`
  - `tests/test_figure_pipeline.py`
  - 新增/补齐：`tests/test_saxs_publication_temperature_provider.py`、`tests/test_saxs_strain_figure_provider.py`、`tests/test_saxs_publication_pipeline.py`、`tests/test_saxs_publication_acceptance.py`

## Acceptance criteria

- [ ] 明确且可测试地选择 `static`、`temperature/time`、`strain` 模式；一次运行只能进入一个 mode-specific provider，不得混入其他模式的 figure definitions。
- [ ] 温度/时间 publication pack 只在已有时间轴、有限值、质量和实验状态证据满足时生成 Main；完整 waterfall、未达 Main 的 evidence 和失败原因分别落入 SI/Diagnostics。
- [ ] 应变 publication pack 支持已有证据覆盖的 1D/2D 路径；不凭空生成 detector/orientation panel，二维 detector evidence 使用受控的 selected snapshot，不保留完整 detector stack。
- [ ] `SAXSEngine.plot()` 通过共享 production publisher 写出 manifest-backed `preview/svg/png/pdf/tiff` 资产，并更新 `result.metadata` / `result.figures`；旧的 legacy helper 保持必要的导入兼容。
- [ ] active manifest gallery 默认显示 ready Main，并能切换 SI/Diagnostics；历史无 manifest 的旧输出不重新扫描进入当前 gallery。
- [ ] 真实或合成的温度、应变 acceptance case 覆盖 ready、SI downgrade、diagnostic veto、缺失 evidence、1D fallback 和失败路径。
- [ ] 在 production cutover 前完成科学语义人工复核，确认 role 判定、fallback 语义、基线数值和图形面板没有被误改。

## Affected boundaries

- [ ] GUI
- [ ] CLI
- [x] Analysis engine
- [x] Result/schema contract
- [x] Persistence
- [x] Export/reporting
- [x] Evaluation/baseline
- [x] Documentation/tooling

## Implementation plan

1. 在独立 worktree/分支中盘点当前 SAXS 温度/应变入口、结果字段、旧绘图路径和真实/合成 acceptance case；建立旧路径到新 manifest/provider 的契约矩阵，并先写失败的 provider-boundary 测试。
2. 实现 temperature/time provider 与 mode dispatcher：只读取已发出的 result/evidence，定义 Main/SI/Diagnostics gate、role/order、缺失证据原因和兼容入口；运行 focused temperature/status/provider tests。
3. 实现 strain provider：先完成 1D，再处理已有 detector evidence 支持的 2D；限制 snapshot 数量和单图数据规模，明确 orientation/anisotropy 的证据门槛；运行 strain/scoring/symptom tests。
4. 将 `SAXSEngine.plot()` 接到共享 production publisher，补齐 manifest/gallery/editor cutover、失败状态和 legacy helper compatibility；运行 pipeline、gallery、editor 和 asset/audit tests。
5. 使用真实/合成 acceptance cases 做分层回归，更新必要 baseline/acceptance 文档；完成人工科学语义复核后，再执行统一验证和 boundary 检查。

## Verification

```bash
# Task-card validation
python scripts/task_check.py --task docs/agent/tasks/2026-07-12-saxs-temperature-strain-production-cutover.md

# Focused tests
python -m pytest tests/test_saxs_figure_selection.py tests/test_saxs_figure_eligibility.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_temperature_status.py -q
python -m pytest tests/test_saxs_publication_temperature_provider.py tests/test_saxs_strain_figure_provider.py tests/test_saxs_publication_pipeline.py tests/test_saxs_publication_acceptance.py -q
python -m pytest tests/test_figure_pipeline.py tests/test_figure_production.py tests/test_plot_gallery_service.py tests/test_chart_viewer.py tests/test_manifest_editor_shared_plan.py -q

# Changed-scope and unified gates
python scripts/verify.py --task docs/agent/tasks/2026-07-12-saxs-temperature-strain-production-cutover.md --changed
python scripts/verify.py --changed --types
python scripts/verify.py
python scripts/verify.py --full
python scripts/verify.py --boundary
```

## Risks and compatibility

- User-visible risk: gallery default selection or role filters may hide an existing result if readiness/status mapping is wrong; keep manifest-only behavior and add explicit status tests.
- Data/schema risk: temperature/strain result payloads contain legacy aliases and optional nested evidence; read through adapters and preserve old document/manifest defaults.
- Scientific/baseline risk: `lc`, `q_star`, strain axis, detector/orientation and crystallinity fallbacks may be calibrated or diagnostic-only; never promote them to Main without emitted evidence.
- Rollback or compatibility path: keep legacy plot helpers import-compatible, gate production cutover behind the mode dispatcher, and retain the previous plotting path until focused and acceptance tests pass.

## Memory impact

- [ ] No durable project memory change.
- [x] Update `docs/agent/memory/active-work.md`.
- [ ] Add or update a decision entry.
- [ ] Add a lesson or known-issue entry.

## Handoff

- Changed files: task card only at creation time; implementation files are intentionally untouched.
- Verification results: task-card validation must pass before implementation; implementation verification is pending.
- Known limitations: current mainline has SAXS static publication support, but temperature/strain production cutover and real acceptance closure are not yet complete.
- Follow-up tasks: implement temperature provider, implement strain provider, then perform production/gallery cutover and acceptance review.

## Commit and review checkpoint

- Task ID or slug: `saxs-temperature-strain-production-cutover-2026-07-12`
- Intended commit/PR scope: one contract/provider slice per commit, followed by one production cutover commit; do not mix GUI streamlining.
- Human review required? [ ] No [x] Yes
- Reviewer focus: architecture / data contract / science
- Commit or PR reference: pending

## Execution evidence

- Implementation branch: `codex/saxs-temperature-strain-production-cutover`
- Design commit: `9a3f5d1c`
- RED test commit: `3fd6769f`
- Production cutover commit: `3316c9a6`
- Focused SAXS/shared publication matrix: 143 passed
- Main workspace task-card validation: passed
- Main workspace quality/boundary gate: 516 focused tests passed, 108 preprocess tests passed, boundary audit passed
- Direct changed-file checks: `figure_provider.py` and cutover tests pass Ruff; changed files compile
- Full `pytest -q`: exceeded the 5-minute execution limit without a reported failing test; treat as pending repository-runtime follow-up
- Human review: required before integration
