# 物理可信度集成补丁包

这个目录由 `integrate-phys-confidence` 分支相对 `main` 生成，方便在 `D:\PolyNexus` 主工作区整理完未提交改动后审阅或应用。

## 补丁顺序

1. `0001-fix-finish-physical-confidence-integration.patch`
   - 物理可信度集成收尾修复。
   - 包含 GUI 持久化清理、历史指标补全、不可达 logger 清理、调参 `constraint=None` 修复等。
2. `0002-docs-record-physical-confidence-integration-status.patch`
   - 新增实施验收与合并说明。
3. `0003-chore-restore-utf8-source-compilation.patch`
   - 修复 `edf_reader.py` 非 UTF-8 源码问题。
   - 扩展 core 扫描测试到整个 `polynexus` 包。
   - 恢复项目级 `compileall` 验收。

## 应用方式

在主工作区先处理当前未提交改动，然后执行：

```powershell
cd D:\PolyNexus
git am "docs\patch-bundles\物理可信度集成补丁包\0001-fix-finish-physical-confidence-integration.patch"
git am "docs\patch-bundles\物理可信度集成补丁包\0002-docs-record-physical-confidence-integration-status.patch"
git am "docs\patch-bundles\物理可信度集成补丁包\0003-chore-restore-utf8-source-compilation.patch"
```

如果主工作区已经有重叠改动，也可以改用三方应用：

```powershell
git am --3way "docs\patch-bundles\物理可信度集成补丁包\*.patch"
```

## 验证命令

```powershell
python -m compileall polynexus tests -q
pytest tests/test_core.py tests/test_main_window_persistence.py tests/test_phase3.py -q
pytest -q
```

## 当前隔离分支验证结果

- `python -m compileall polynexus tests -q` passed
- `git diff --check` passed
- `pytest -q --basetemp .pytest_tmp_full_integration_encoding_final`
  - `600 passed, 2 warnings`

剩余 warning 来自 NMR 导出图片时 Arial 缺少中文 glyph，属于字体渲染 warning。
