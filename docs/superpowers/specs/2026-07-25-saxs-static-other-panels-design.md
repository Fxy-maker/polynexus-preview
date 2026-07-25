# SAXS static other panels design

## Context

静态 SAXS 已有 comparison/sample 主图、correlation/profile SI 和 per-frame
diagnostics，但需要把板块顺序和 role 固定为可复用的出版链路，避免诊断图或
单样品支持图被误读为主结论。

## Design choice

保留 `polynexus/core/saxs_engine/figure_static.py` 的现有 provider 和统一
ResultsTable/Manifest/Gallery/Editor 边界，只补充回归合同，不新增静态专用 GUI
状态。静态链路为：

1. `saxs.static.comparison` 或 `saxs.static.sample`：Main，order 10；
2. `saxs.static.correlation.support` 或 `saxs.static.profile.si`：SI，order 20；
3. `saxs.static.frame.*.*`：per-frame diagnostic，order 100+。

当 comparison gate 不满足时沿用 sample/支持图 fallback；缺失 correlation、
IDF 或其他诊断证据不创建空 figure，也不提升 publication role。

## Responsibilities and testing

- provider 负责比较/样品选择、order、role 和 fallback；
- ResultsTable/Manifest/Gallery/Editor 只消费定义，不重新计算结构指标；
- `tests/test_saxs_publication_pack_upgrade.py` 锁定完整顺序、ID、role，并继续
  验证每个定义通过 `validate_figure_definition`；
- 运行静态聚焦测试、Ruff、compile、`git diff --check` 和仓库 verifier。
