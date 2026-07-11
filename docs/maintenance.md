# PolyNexus 维护说明

这份说明记录日常开发、验证和文档维护的约定。更面向维护者；用户入口仍是根目录 `README.md`。

## 环境

安装开发依赖：

```bash
pip install -e .[dev]
```

启动 GUI：

```bash
polynexus --gui
```

或：

```bash
polynexus-gui
```

## 常用验证

快速语法与导入检查：

```bash
python -m compileall polynexus tests -q
```

可选的静态检查：

```bash
ruff check polynexus scripts tests
```

完整测试：

```bash
pytest
```

聚焦测试时优先运行受影响模块，例如：

```bash
pytest tests/test_saxs_scoring.py -q
pytest tests/test_waxs_residual_analyzer.py -q
pytest tests/test_nmr_engine.py -q
```

本地维护门禁：

```bash
python scripts/quality_gate.py --root .
```

需要额外包含全量 pytest 时：

```bash
python scripts/quality_gate.py --root . --all-tests
```

边界审计：

```bash
python scripts/boundary_audit.py --root .
```

需要保存给 CI 或阶段台账时，可输出 JSON：

```bash
python scripts/boundary_audit.py --root . --json
```

提交前检查空白错误：

```bash
git diff --check
```

## 文档维护

- 文档索引在 `docs/README.md`。
- 维护职责边界和重构约束在 `docs/maintenance-boundaries.md`。
- 规划、路线图、阶段任务和专题清单放入 `docs/plans/`。
- 当前基线台账放入 `docs/baselines/`。
- 验收说明和收口总结放入 `docs/acceptance/`。
- 补丁包放入 `docs/patch-bundles/`，并在包内 README 写明应用顺序和验证命令。
- 不再新增根目录 `方案` 或单数 `doc` 目录。

移动文档后，检查旧路径引用：

```powershell
$oldDocDir = '方' + '案'
$oldPathPattern = "D:\\PolyNexus\\$oldDocDir|D:/PolyNexus/$oldDocDir|/D:/PolyNexus/$oldDocDir|$oldDocDir/|$oldDocDir\\|git add $oldDocDir"
rg -n $oldPathPattern README.md docs polynexus tests
```

## 临时产物

根目录可能出现本地测试产物，例如 `.pytest_tmp*`、`.tmp_pytest*`、`test_output/`、`results/`、`polynexus.log`。优先运行只读审计命令查看当前状态：

```bash
python scripts/maintenance_audit.py --root .
```

审计命令不会删除文件。清理前仍需确认这些文件没有被 Git 跟踪：

```bash
git status --short
git ls-files .pytest_tmp* .tmp_pytest* test_output results polynexus.log
```

生成清理计划：

```bash
python scripts/maintenance_cleanup.py --root .
```

清理计划默认是 dry-run，不会删除文件。确认计划只包含本地测试输出后，才使用显式 apply：

```bash
python scripts/maintenance_cleanup.py --root . --apply
```

只清理确认属于本地测试输出的内容。不要删除 `tests/eval/cases/`、`tests/eval/synth_data/` 或 `测试数据/` 中用于回归的样本。

## 补丁包

应用补丁包前先确认工作区干净或已明确保存当前改动：

```bash
git status --short
```

优先阅读补丁包内 README，再按顺序应用。应用后至少运行：

```bash
python -m compileall polynexus tests -q
pytest -q
```
