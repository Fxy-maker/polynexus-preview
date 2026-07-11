# PolyNexus 维护边界清单

这份清单用于约束后续维护和重构的边界。目标不是一次性改完，而是在每次改动时避免职责继续扩散，让 GUI、分析引擎、数据持久化、评测和文档各自保持清晰边界。

## 使用方式

- 修改某个模块前，先确认它属于下面哪一类边界。
- 如果一次改动跨越多个边界，先拆成更小的步骤，或在提交说明中写清楚跨界原因。
- 新功能优先复用已有边界；只有现有边界不能表达新需求时，才新增接口或服务。
- 清理和重构应配套最小验证命令，避免“看起来更整洁但行为变了”。

## 最高优先级

- [ ] GUI 主窗口只负责窗口组装、信号连接、页面切换和用户反馈。
- [ ] 分析引擎只通过统一 pipeline 和 `AnalysisResult` 向外暴露结果。
- [ ] 样本库只负责持久化和兼容迁移，不承载 GUI 或算法业务规则。
- [ ] 临时产物、调试脚本、生成报告不得成为主流程依赖。
- [ ] 文档按 `docs/README.md` 的目录规则放置，不再新增根目录方案文档。

## GUI 边界

当前压力点：

- `polynexus/gui/main_window.py` 体量过大，包含窗口、任务调度、样本库、历史记录、图表、导入建议和 AI 调参等多类职责。
- GUI 测试也容易随着主窗口增长而变成大而全的持久化回归。

维护规则：

- [ ] `main_window.py` 保留应用窗口、菜单、主导航、信号连接和跨页面协调。
- [ ] 批处理、AI tune、样本库、图表历史、导入建议、设置持久化逐步下沉到 controller 或 service。
- [ ] GUI 不直接读取技术线内部中间变量，只消费 `AnalysisResult`、样本库 DTO 或明确的 view model。
- [ ] 长耗时任务通过 worker/task 封装，主窗口只关心开始、进度、完成、失败。
- [ ] 用户可见错误在 GUI 层转成可操作提示，详细 traceback 写入日志。

优先拆分候选：

- [ ] `BatchController`：批处理任务、预设、最近运行。
- [ ] `AnalysisRunController`：保存 analysis run、刷新历史、选择当前 run。
- [ ] `ChartHistoryController`：图表预览、编辑状态、导出入口。
- [ ] `ImportSuggestionController`：导入识别、建议展示、确认落库。
- [ ] `AiTuneController`：调参启动、进度事件、结果持久化。

## 核心引擎边界

当前基础：

- `BaseEngine` 已定义 `load -> preprocess -> analyze -> plot -> get_parameters`。
- `AnalysisResult` 已承载参数、图表、日志、证据和校验状态。

维护规则：

- [ ] 各技术线只通过 `BaseEngine.run_pipeline()` 或同级明确入口被 GUI/CLI 调用。
- [ ] 技术线内部中间数组、拟合状态、诊断字段不直接泄露给 GUI。
- [ ] 新增参数应进入 `AnalysisResult.parameters` 或技术线专用的 typed result，再由 adapter 汇总。
- [ ] 新增图表应进入 `AnalysisResult.figures`，文件命名和 figure key 保持稳定。
- [ ] 新增质量判断应进入 `AnalysisResult.analysis_evidence` 或 validation 字段。

不得做：

- [ ] 不在 GUI 中判断某个技术线内部算法分支。
- [ ] 不让 CLI、GUI、评测各自拼一套结果 dict。
- [ ] 不把用户界面文案写入核心算法返回值，除非是明确的摘要字段。

## 结果对象边界

维护规则：

- [ ] `AnalysisResult` 是跨层通信的默认结果载体。
- [ ] `to_dict()` 输出应向后兼容，尤其是 `parameters`、`figures`、`analysis_evidence`、`validation_*`。
- [ ] 新增跨层字段前，先确认是否能放入已有结构。
- [ ] 需要结构化演进时，优先新增 dataclass/schema，再提供 `to_dict()` 兼容旧调用。
- [ ] 评测、样本库和报告导出应尽量复用同一份结果映射逻辑。

检查项：

- [ ] GUI 是否依赖了结果对象之外的引擎内部状态？
- [ ] CLI 输出和样本库保存是否从同一份结果读取？
- [ ] 旧分析记录缺字段时是否有兼容路径？

## 物理证据边界

当前压力点：

- `polynexus/core/analysis_evidence.py` 体量较大，容易混合数据结构、评分规则、技术线适配和摘要文案。

维护规则：

- [ ] 数据结构和序列化逻辑独立于具体技术线。
- [ ] 通用评分规则与技术线特定规则分开。
- [ ] 文案摘要与数值评分分开，避免改措辞影响算法测试。
- [ ] 新技术线接入证据系统时，通过 adapter 或 builder 接入，不直接扩展一个巨大函数。

候选拆分：

- [ ] `analysis_evidence/models.py`
- [ ] `analysis_evidence/scoring.py`
- [ ] `analysis_evidence/builders/<technique>.py`
- [ ] `analysis_evidence/summary.py`
- [ ] `analysis_evidence/compat.py`

## Orchestrator 边界

当前压力点：

- `polynexus/orchestrator.py` 同时承担调参流程、参数建议、评分比较、回滚、报告和部分持久化协作。

维护规则：

- [ ] Orchestrator 只编排调参流程和轮次状态。
- [ ] LLM 调用封装在 `llm/` 或专用 advisor 中。
- [ ] 参数建议、参数应用、回滚策略、收敛判断分别独立。
- [ ] 持久化由样本库服务或 CLI/GUI 调用层负责。
- [ ] 调参报告结构应稳定，供 CLI、GUI 和测试共享。

候选拆分：

- [ ] `orchestrator/session.py`
- [ ] `orchestrator/parameter_actions.py`
- [ ] `orchestrator/convergence.py`
- [ ] `orchestrator/reporting.py`
- [ ] `orchestrator/compat.py`

## 数据库边界

维护规则：

- [ ] `SampleDB` 负责 SQLite 表结构、迁移兼容、CRUD 和事务边界。
- [ ] “一次分析 run 应该包含什么业务含义”放在上层 service。
- [ ] plot edits、analysis evidence、results summary 的 JSON 结构应向后兼容。
- [ ] 数据库异常在持久化层记录详细日志，上层决定是否向用户显示。
- [ ] 测试数据库必须使用临时路径，不能依赖仓库内真实 `*.db`。

检查项：

- [ ] 新增字段是否提供旧库迁移或缺省兼容？
- [ ] GUI 是否直接拼复杂 SQL 或业务 JSON？
- [ ] CLI 和 GUI 是否复用了保存 analysis run 的逻辑？

## CLI 边界

维护规则：

- [ ] `polynexus/__main__.py` 只负责参数解析、退出码和控制台输出。
- [ ] 批处理、预设、AI tune 持久化逐步迁到 `polynexus/cli/` 或 service。
- [ ] CLI 错误使用明确退出码：参数错误、分析失败、部分失败应可区分。
- [ ] CLI 输出可读即可；机器可读输出应使用显式 `--json`，不要混在普通输出中。

候选拆分：

- [ ] `cli/parser.py`
- [ ] `cli/run_single.py`
- [ ] `cli/run_batch.py`
- [ ] `cli/run_ai_tune.py`
- [ ] `cli/output.py`

## 测试边界

维护规则：

- [ ] 单元测试覆盖纯函数、数据结构和 adapter。
- [ ] 引擎测试覆盖真实 pipeline 的关键行为和物理可信度边界。
- [ ] GUI 测试覆盖用户流程、状态持久化和异常反馈，不验证算法细节。
- [ ] Eval 测试覆盖基线样本和综合评分，不替代普通单元测试。
- [ ] 超长测试文件应拆出 fixture、helper 和场景文件。

提交前最小验证：

```bash
python -m compileall polynexus tests -q
pytest tests/test_core.py -q
git diff --check
```

按影响范围补充：

- [ ] 改 GUI：运行相关 `tests/test_*window*.py`、`tests/test_chart_*.py` 或小组件测试。
- [ ] 改某技术线：运行对应 engine、residual、temperature/strain/scoring 测试。
- [ ] 改证据系统：运行 `tests/test_analysis_evidence.py` 和受影响技术线测试。
- [ ] 改样本库：运行 `tests/test_sample_db.py`、`tests/test_sample_browser.py`。
- [ ] 改评测：运行 `tests/eval/test_*.py` 的相关子集。

## 文档边界

维护规则：

- [ ] 根目录 `README.md` 面向安装、启动和常用入口。
- [ ] `docs/README.md` 是文档索引。
- [ ] `docs/maintenance.md` 是日常维护说明。
- [ ] `docs/maintenance-boundaries.md` 是职责边界和重构约束。
- [ ] `docs/plans/` 放规划、路线图、任务清单。
- [ ] `docs/baselines/` 放当前行为基线。
- [ ] `docs/acceptance/` 放验收、收口、合并说明。
- [ ] `docs/patch-bundles/` 放补丁包和应用说明。

不得做：

- [ ] 不再新增根目录 `方案` 或单数 `doc` 目录。
- [ ] 不把临时讨论稿混入 `README.md`。
- [ ] 不把执行状态散落在多个同名文档中。

## 临时产物边界

维护规则：

- [ ] `.pytest_tmp*`、`.tmp_pytest*`、`test_output/`、`results/`、`polynexus.log` 视为本地输出。
- [ ] 根目录 `_*.py` 视为临时诊断脚本，不作为产品入口。
- [ ] 清理前先确认文件未被 Git 跟踪。
- [ ] 真实回归样本不得和临时输出混放。

清理前检查：

```bash
python scripts/maintenance_audit.py --root .
```

生成 dry-run 清理计划：

```bash
python scripts/maintenance_cleanup.py --root .
```

清理前再确认 Git 状态：

```bash
git status --short
git ls-files .pytest_tmp* .tmp_pytest* test_output results polynexus.log
```

保护项：

- [ ] `tests/eval/cases/`
- [ ] `tests/eval/synth_data/`
- [ ] `测试数据/`
- [ ] `docs/baselines/`

## 异常处理边界

维护规则：

- [ ] 用户输入或文件格式错误：返回可操作提示。
- [ ] 算法失败：保留上下文、参数和 traceback，结果标记为失败或 warning。
- [ ] 可恢复错误：允许降级，但必须记录降级原因。
- [ ] 内部 bug：日志保留 traceback，GUI 不直接展示长堆栈。
- [ ] 不吞掉异常后继续生成看似成功的结果。

检查项：

- [ ] `except Exception` 是否记录了足够上下文？
- [ ] 是否区分用户错误和内部错误？
- [ ] 降级路径是否有测试覆盖？
- [ ] GUI 和 CLI 是否对同一错误给出一致状态？

## 质量门禁边界

当前最小门禁：

```bash
python scripts/quality_gate.py --root .
```

全量测试可通过显式参数加入：

```bash
python scripts/quality_gate.py --root . --all-tests
```

后续建议补齐：

- [ ] 在 `pyproject.toml` 增加 `ruff` 配置。
- [ ] 增加格式化和 lint 命令说明。
- [ ] 增加覆盖率报告入口。
- [ ] 增加 CI，至少运行 compileall、ruff、核心 pytest。
- [ ] 将慢速 eval 测试与普通测试分组。

## 分阶段落地建议

第一阶段：低风险清边界。

- [ ] 新增或完善维护文档。
- [ ] 清理未跟踪临时产物。
- [ ] 给质量门禁增加明确命令。
- [ ] 标注超大文件的候选拆分点，不搬代码。

第二阶段：抽服务，不改行为。

- [ ] 从 GUI 中抽出批处理、样本库、图表历史 controller。
- [ ] 从 CLI 中抽出 batch 和 ai-tune runner。
- [ ] 给保存 analysis run 建立共享 service。
- [ ] 用现有测试保证行为不变。

第三阶段：统一接口。

- [ ] 收敛 `AnalysisResult` 的字段和兼容层。
- [ ] 拆分 `analysis_evidence.py`。
- [ ] 拆分 orchestrator 策略模块。
- [ ] 将 eval、GUI、CLI 都迁到同一套结果映射。

## 每次改动前的快速自检

- [ ] 这次改动属于哪个边界？
- [ ] 是否让一个模块承担了新的跨层职责？
- [ ] 是否需要先运行 `python scripts/boundary_audit.py --root .` 查看大文件和宽泛异常热点？
- [ ] 是否需要用 `python scripts/boundary_audit.py --root . --json` 保存结构化审计结果？
- [ ] 是否引入了新的隐式数据格式？
- [ ] 是否需要兼容旧分析记录或旧文档路径？
- [ ] 是否有最小测试能证明行为没有变？
- [ ] 是否需要更新 `docs/maintenance.md`、baseline 或验收说明？
