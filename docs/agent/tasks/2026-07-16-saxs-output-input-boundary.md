# 日常任务卡：修复 SAXS 输出目录污染输入

- 日期：2026-07-16
- 模块：SAXS 原位变温目录分析
- 状态：已完成
- 优先级：高

## 问题

分析 `测试数据/saxs/pa6变温` 时，扫描器递归进入 `polynexus_output/runs/.../assets`，将历史 `figure.tiff` 当作 SAXS 原始图像读取，导致 TIFF 解码回退、默认几何参数警告、内存占用升高和运行极慢。

## 根因

`polynexus/core/saxs_engine/io.py` 使用不可剪枝的递归扫描，未排除 `polynexus_output` 和历史 `results*` 目录。

## 修复清单

- [x] 增加输出目录污染的回归测试。
- [x] 改为可剪枝目录遍历。
- [x] 用真实 PA6 目录确认只发现 5 个 EDF。
- [x] 确认历史输出未被删除或覆盖。
- [x] 记录测试结果。

## 验收标准

1. 原始目录包含历史输出时，SAXS 扫描不返回任何 `polynexus_output` 下的文件。
2. 真实 PA6 目录发现 5 个 EDF，发现的 TIFF 数为 0。
3. SAXS 条件恢复测试通过。
4. 历史 `polynexus_output` 文件不发生删除或修改。

## 验证记录

- 回归测试：`tests/test_saxs_condition_recovery.py`，5 passed。
- SAXS 发布相关回归：`tests/test_saxs_condition_recovery.py tests/test_saxs_publication_cutover.py tests/test_saxs_temperature_figure_provider.py`，17 passed。
- 真实目录扫描：5 conditions、5 files、`.edf` 5、生成输出文件 0、`.tiff` 0。
- `git diff --check`：通过。
- 历史 `测试数据/saxs/pa6变温/polynexus_output` 未被扫描验证改写。

## 备注

当前已启动的旧进程不会自动切换到新代码；需停止该进程后重新运行，或用只包含原始 EDF 的目录重启分析。EDF 几何信息缺失的警告仍需按仪器配置单独校准，本修复只处理输出资产误入输入的问题。
