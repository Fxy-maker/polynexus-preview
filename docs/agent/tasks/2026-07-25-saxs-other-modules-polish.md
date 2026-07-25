# SAXS other modules polish

## Goal

按温变 -> 拉伸 -> 静态 SAXS 的顺序，把已在 temperature waterfall 上验证过的
板块组织经验扩展到其他板块。第一阶段先完成温变 SAXS 的
`evolution / Avrami / selected evidence`，让主结论、补充证据和诊断证据在
结果页与 figure manifest 中保持清晰的层级关系。

## Sub-projects

1. 温变 SAXS：evolution、Avrami、selected evidence；waterfall 保持现状。
2. 拉伸 SAXS：evolution、full sequence、invariant/correlation/IDF/azimuthal/
   phase/low-q 的主图、SI、diagnostic 链路。
3. 静态 SAXS：comparison/sample、structure metrics、correlation/IDF、diagnostic
   链路。

每个子项目独立设计、测试和 checkpoint；本任务当前只进入第 1 项。

## Boundaries

- 复用现有 `FigureDefinition`、ResultsTable presentation、Manifest、Gallery
  和 Editor 边界。
- 保持现有 figure ID、数据列、`publication_role`、evidence eligibility 和
  fallback 语义不变。
- GUI 只消费已有的 `AnalysisResult`、DTO 或 view model；不在事件处理器中
  重算科学状态。
- 继续由 core/services 负责板块排序、证据层级和 review hint。

## Non-goals

- 不修改 SAXS 科学算法、阈值、温度/应变识别、LC 或峰追踪。
- 不把低置信度、缺失或诊断证据提升为 Main。
- 不修改 waterfall 的细调结果。
- 不扩展到 WAXS、DSC、IR 或 NMR。
- 不改动生成输出、真实回归数据集、secret 或本地 runtime 目录。
- 不 push、merge、deploy 或发送外部消息。

## Acceptance criteria

- 温变 figure provider 对 evolution、Avrami、selected evidence 的顺序和角色
  有聚焦回归覆盖；waterfall 仍为 SI 且保持既有 ID。
- 现有温变 review hint wiring 继续只表达已有 evidence 状态，不新增科学判断。
- 结果页能按现有主/详情/诊断边界消费这些板块，且不绕过 manifest/gallery/editor
  合同。
- 每个行为变更先有失败测试，再有最小实现；测试覆盖正常、fallback、缺失或
  不合格证据路径。
- 第一阶段运行聚焦 pytest、Ruff、compile、`git diff --check`，以及：
  `python scripts/verify.py --changed --types`。
- 验证后用 `scripts/auto_commit.py` 按明确 allowlist 建立一个原子 checkpoint。
- 阶段结论、验证证据、已知限制和下一阶段入口写入 agent memory。

## Verification commands

```powershell
python -m pytest tests/test_saxs_temperature_figure_panels.py tests/test_main_window_output_mixin.py tests/test_analysis_result_table_templates.py -q
python -m ruff check tests/test_saxs_temperature_figure_panels.py
python -m compileall -q tests/test_saxs_temperature_figure_panels.py
git diff --check
python scripts/verify.py --changed --types
python scripts/auto_commit.py --message "test(saxs): lock temperature figure panel contracts" --files docs/agent/tasks/2026-07-25-saxs-other-modules-polish.md docs/superpowers/specs/2026-07-25-saxs-temperature-other-panels-design.md docs/superpowers/plans/2026-07-25-saxs-temperature-other-panels.md tests/test_saxs_temperature_figure_panels.py docs/agent/memory/active-work.md
```

## Pre-existing changes

工作区已有大量 Origin/editor 相关未跟踪目录、临时 pytest 目录和文档草稿。
它们不属于本任务，必须保持原样，不得加入本任务 checkpoint。

## Temperature slice status

- Focused SAXS/provider and GUI consumer regressions: `15 passed`.
- Repository verifier with an external pytest basetemp: quality gate `282 passed`,
  preprocessing gate `103 passed`; memory, Ruff, compile, type baseline and
  whitespace checks passed.
- Production SAXS algorithms and providers were left unchanged because the
  existing implementation already satisfied the locked contracts.

## Strain and static slice status

- Strain provider order/role regression and shared review-hint wiring are
  checkpointed in `51709fd`; focused strain matrix: `8 passed`.
- Static comparison/support/diagnostic order regression is isolated in
  `tests/test_saxs_static_figure_panels.py`; focused test: `1 passed`.
- Static checkpoint: `2346df0`; the three SAXS slices are complete. Optional
  follow-up is a restarted-GUI visual walkthrough and human scientific review.
