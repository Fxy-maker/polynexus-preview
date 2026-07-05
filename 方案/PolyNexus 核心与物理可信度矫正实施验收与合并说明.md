# PolyNexus 核心与物理可信度矫正实施验收与合并说明

## 当前状态

- 集成分支：`integrate-phys-confidence`
- 集成提交：`36e5444 fix: finish physical confidence integration`
- 工作区路径：`C:\Users\Fan Xuyi\.config\superpowers\worktrees\PolyNexus\integrate-phys-confidence`
- 基线提交：`99dbd2c chore: keep core warning logs reachable`
- 主工作区：`D:\PolyNexus` 仍有未提交改动，暂不直接合并，避免覆盖用户正在做的图表后处理工作台相关变更。

## 已覆盖规划项

本轮集成确认主线已经包含核心规划的大部分实现，并补齐最后的收尾差异：

- `analysis_evidence` 已作为一等数据进入 SampleDB、GUI、CLI/batch/AI tune 保存链路。
- Joint Hub 已读取 evidence context，并按 evidence 权重降级弱来源冲突。
- Joint model 已从初始向量评估升级为真实 least-squares 优化。
- NMR/IR/SAXS/WAXS/DSC 已补齐关键可靠性状态、校准状态、仪器展宽、基线敏感性与 uncertainty 相关证据字段。
- GUI 历史记录、结果风险摘要、上下文建议、复制表格等回归已同步到当前 UI 契约。
- 删除 `return` 后不可达 logger，并新增 core/gui 日志与公开文本 mojibake 防回归测试。
- 修复调参参数约束为 `None` 时的 `_tunable_params()` 崩溃风险。

## 本轮新增提交内容

`36e5444` 主要包含：

- `polynexus/gui/main_window.py`
  - 非 SAXS 参数风险摘要初始化 condition 变量，避免引用未定义变量。
  - 历史指标摘要补充 results_summary 顶层标量，保留 validation/joint 等元数据过滤。
- `polynexus/orchestrator.py`
  - `rule.constraint is None` 时输出空约束列表。
- `polynexus/gui/widgets/chart_editor.py`
  - 修复图表 DPI 样式异常日志中的 mojibake 文本。
- `polynexus/core/**` 与 `polynexus/gui/convergence_viewer.py`
  - 删除不可达 `return` 后 logger。
- `tests/test_core.py`
  - 扩展不可达 logger 扫描与公开文本/日志 mojibake 扫描。
- `tests/test_main_window_persistence.py`
  - 增加 Qt top-level widget 自动清理夹具，稳定 GUI 持久化回归。
  - 更新当前 UI 表格列、按钮文本和历史指标顺序断言。
- `tests/test_phase3.py`
  - 更新 Advisor action-aware 输出 schema 断言。

## 验证记录

已在隔离 worktree 中完成：

```powershell
pytest tests/test_core.py tests/test_phase3.py -q --basetemp .pytest_tmp_integration_core3
# 20 passed

pytest tests/test_main_window_persistence.py -q --basetemp .pytest_tmp_integration_gui2
# 182 passed

git diff --check
# passed

pytest -q --basetemp .pytest_tmp_full_integration_final
# 600 passed, 2 warnings
```

剩余 warning 为 `tests/test_nmr_engine.py` 导出图片时 Arial 缺少中文 glyph，属于既有字体渲染 warning，不影响本轮核心/物理可信度逻辑。

全量 `python -m compileall polynexus tests -q` 暂不能作为项目级验收命令，因为既有文件 `polynexus/readers/edf_reader.py` 当前包含非 UTF-8 字节，Python 默认 UTF-8 解码会报错。本轮改动涉及文件已用 `py_compile` 验证通过。

## 为什么暂不直接并回 D:\PolyNexus

`D:\PolyNexus` 当前 `main` 工作区存在多处未提交改动，并且与本轮集成提交有重叠文件，例如：

- `polynexus/gui/main_window.py`
- `polynexus/gui/widgets/chart_editor.py`
- `tests/test_core.py`
- `tests/test_main_window_persistence.py`
- `polynexus/core/plot_edits.py`

直接 merge 可能把用户未提交的图表后处理/标注相关改动卷入冲突，甚至产生难以区分的混合差异。因此当前最安全状态是保留隔离分支，等待主工作区改动提交、暂存或另行整理后再合并。

## 后续安全合并路径

推荐顺序：

1. 在 `D:\PolyNexus` 先处理当前未提交改动：提交到单独分支，或确认可以暂存。
2. 回到主工作区后合并：

```powershell
cd D:\PolyNexus
git merge integrate-phys-confidence
```

3. 如有冲突，优先保留图表后处理工作台新增文件与 UI 改动，再把本分支的物理可信度收尾修复手工合入。
4. 合并后重新运行：

```powershell
pytest tests/test_core.py tests/test_main_window_persistence.py tests/test_phase3.py -q
pytest -q
```

## 建议下一步

如果要继续推进同一条主线，建议先处理主工作区的图表后处理工作台改动，把它们独立提交或迁到单独分支；然后再把 `integrate-phys-confidence` 合并回主线。这样核心/物理可信度和图表工作台两条线不会互相污染。
