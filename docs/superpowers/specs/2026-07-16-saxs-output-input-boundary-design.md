# SAXS 输出目录输入边界设计

## 目标

阻止 SAXS 目录分析把 `polynexus_output` 中历史生成的 figure TIFF 当作原始探测器图像读取，避免重复 TIFF 解码、错误几何参数回退和分析结果污染。

## 方案

将 `scan_experiment_dir()` 的递归遍历改为可剪枝的目录遍历。在进入目录前排除 `polynexus_output` 和已有 `results*` 目录；原始数据目录中的 EDF、CBF、TIFF 等受支持格式仍按现有规则处理。这样既避免发现输出资产，也避免为了过滤输出文件而遍历整个历史结果树。

## 验证

增加回归测试：临时输入目录包含一个 EDF 和一个 `polynexus_output/runs/.../figure.tiff`，扫描结果只能包含 EDF。随后运行 SAXS 条件恢复测试，并对 PA6 真实目录检查发现文件只剩 5 个 EDF。
