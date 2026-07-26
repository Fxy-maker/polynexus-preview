# PolyNexus full software vertical delivery

## Goal

按完整垂直闭环完成 PolyNexus 全软件：统一底座、定制 Results Workbench、
SAXS、DSC、WAXS、IR、NMR、Joint、AI 质量门、图包生命周期、Gallery/Editor、
导出和发布验收。

## Delivery principle

一个技术模式只有完成以下链路才算完成：

`输入/预处理 -> 科学分析消费 -> evidence/confidence -> 定制结果工作台 ->
Main/SI/diagnostic Figure Pack -> Manifest/Gallery/Editor -> export/provenance ->
AI-off/failure/fallback -> regression/real-data/visual acceptance`

Provider-only、字段模板-only、单元测试-only 都只能标记为 foundation，不得标记
为模块完成。

## Scope

### Shared platform

- AnalysisResult、evidence、confidence、review action、Run/History/Persistence。
- FigureDefinition、FigureDocument、RunFigureManifest、publication role、
  capability report、Gallery、ChartEditor、export bundle 和 provenance。
- 统一 Results Workbench shell，加模式 Profile：标题、hero、primary、support、
  diagnostics、review hint、actions 和 figure navigation。

### Scientific techniques

- SAXS：static、temperature/time、strain。
- DSC：standard、isothermal、non-isothermal。
- WAXS：static、temperature/time、strain、2D detector/image-grid。
- IR：standard、temperature-2D、mapping/ROI。
- NMR：liquid H、liquid C、solid H、solid C。
- Joint：跨技术一致性、冲突、校准和 provenance。

### Cross-cutting quality

- Deterministic path、AI-off path、AI failure path、fallback 和诊断路径。
- Golden/real-data fixtures、TDD regression、type/lint/compile、quality gate、
  visual GUI review、publication audit、CI/release checks。

## Acceptance criteria

- [ ] Each technique mode has a typed result/evidence presentation and a customized Results Workbench profile.
- [ ] Main/SI/diagnostic figures publish through FigureDefinition and RunFigureManifest, appear in the active Gallery, and route to Editor/export with provenance.
- [ ] History, persistence, export, AI-off/failure/fallback, Golden/real-data, and restarted-GUI checks are recorded for every released mode.
- [ ] Scientific, schema, and unresolved mapping/ROI decisions remain explicitly marked for human review instead of being guessed.

## Affected boundaries

- Core analysis/evidence and technique-specific figure providers.
- Shared FigureDocument/Manifest/Gallery/Editor/export/history contracts.
- Results Workbench profiles, MainWindow adapters, and focused regression tests.
- `docs/acceptance/`, `docs/agent/memory/`, and this task card.

## Implementation plan

1. Inventory and lock shared result, evidence, Workbench, figure, Manifest, history, and export contracts.
2. Complete each technique as an independent vertical slice in dependency order.
3. Add typed Workbench/profile and MainWindow integration regressions before production changes.
4. Verify normal, fallback, low-confidence, invalid, AI-off, and AI-failure paths with Golden/real-data fixtures.
5. Run structured and release verifiers, update acceptance/memory, and create one atomic checkpoint per slice.

## Non-goals

- 不在绘图层重算科学参数、修复输入数据或改变证据阈值。
- 不把低置信度、缺失、诊断或冲突证据提升为 Main。
- 不为每个技术复制一套 Manifest/Gallery/Editor/export 生命周期。
- 不删除既有用户数据、生成输出、真实回归数据集、secret 或 scratch。
- 不 push、merge、deploy 或发送外部消息，除非用户另行明确授权。

## Module acceptance

每个模式必须交付：

1. 输入/条件轴/预处理合同；
2. 已有科学结果的 AnalysisResult/evidence 消费；
3. Main/SI/diagnostic publication role 和 fallback；
4. 定制 Results Workbench profile；
5. 可编辑 Figure Pack、Manifest、Gallery、Editor 入口；
6. 导出数据、图片、参数、证据和 provenance；
7. 正常、缺失、低置信度、错误、AI-off、AI-failure 测试；
8. 至少一组真实或 Golden 数据验收；
9. 重启 GUI 后的视觉检查记录和已知限制。

## Dependency order

1. 统一底座和 Workbench shell/profile contract；
2. SAXS 三模式完整闭环；
3. DSC 三模式完整闭环；
4. WAXS static/temperature/strain/2D；
5. IR standard/temperature-2D/mapping；
6. NMR liquid/solid H/C；
7. Joint cross-technique；
8. AI tuning、发布验收和全量回归。

每一阶段独立设计、计划、测试和 checkpoint；跨阶段共享的接口必须先更新
总体设计和任务卡。

## Verification

Default command:

```powershell
python scripts/verify.py --changed --types
```

Full boundary/release command:

```powershell
python scripts/verify.py --changed --types --full --boundary
```

Windows pytest 的仓库 `.pytest_tmp` 若被既有 scratch 锁定，使用仓库外的、无空格
临时目录覆盖 `PYTEST_ADDOPTS=--basetemp=...`，不得删除既有 scratch。

## Completion evidence

## Current audit (2026-07-26)

Automated shared/platform and mode lifecycle boundaries are covered by the
recorded focused matrices, and the full/boundary verifier now passes with
2587 tests in 1042.86 seconds. A fresh real-fixture audit completed DSC
standard, WAXS static/temperature, IR standard, and SAXS temperature engine
publication runs; WAXS strain and IR temperature-2D exceeded the bounded
diagnostic runtime, and the SAXS temperature fixture remains scientific
validation-error/diagnostic-only. Evidence is in
`docs/acceptance/2026-07-26-real-published-run-audit.md`.

This overall task remains active. Real published-run Gallery/Editor/export/
History inspection for every mode, restarted-GUI visual review, human
scientific sign-off, and the final release decision remain open;
IR mapping/ROI is no longer blocked at the typed DTO and provider-contract
layer, but vendor semantics still require confirmation.

- Overall design: `docs/superpowers/specs/2026-07-25-full-software-development-architecture-design.md`。
- Overall plan: `docs/superpowers/plans/2026-07-25-full-software-development.md`。
- 每阶段在本任务卡、`docs/agent/memory/active-work.md` 和 acceptance notes 中
  记录状态、commit、命令、结果、已知限制和下一阶段。
