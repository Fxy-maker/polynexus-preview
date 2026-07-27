# Temperature SAXS Guinier evidence

## Goal

把现有变温 SAXS 单帧分析中的 Guinier 数值结果扩展为带拟合证据、
不确定度、`qRg` 物理门槛、适用性声明和质量等级的逐帧结果。

## Non-goals

- 不重写现有 `guinier_analysis` 的 q 窗口选择或 SAXS 层片算法。
- 不对缺失温度帧插值，不自动把层片/Bragg 主导数据声明为 Guinier 适用。
- 不在本阶段实现序列趋势融合、AI 救援、Porod/Kratky 扩展或 GUI 发布变更。

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/__init__.py`
- `polynexus/core/saxs_engine/core.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_quality_contracts.py`
- `tests/fixtures/saxs_quality_cases.py`
- `tests/test_saxs_guinier_evidence.py`
- `tests/test_saxs_temperature_guinier_evidence.py`

## Implementation plan

1. 先用合成 q/ln(I) 写出 R²、斜率不确定度、Rg 不确定度、适用性和 qRg
   门槛的失败测试。
2. 在现有质量契约中实现只读 `GuinierEvidence` 构造器，不改变窗口选择。
3. 将证据字典接入 `SAXSResult` 和 `TemperaturePointResult`，保留失败帧缺失。
4. 运行 focused/完整 SAXS 回归、结构化 verifier，更新记忆并创建 checkpoint。

## Acceptance criteria

- [x] 现有 Guinier 拟合输出可生成严格 JSON-safe 的 `GuinierEvidence`。
- [x] `Quantitative` 必须同时满足数据质量、显式适用性、拟合质量和
  `qRg < 1.3`；适用性未知/不支持时最高为 `Diagnostic`。
- [x] `Rg` 不确定度在自由度和斜率有效时可追溯；否则显式降级。
- [x] 变温每帧保留自己的数据质量、证据、等级和 reason code。
- [x] core 失败或输入缺失时不伪造温度帧或曲线。
- [x] focused tests、结构化 verifier 和原子 checkpoint 有实际证据。

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_temperature_guinier_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-temperature-guinier-evidence.md --changed --types
```

## Verification evidence (2026-07-27)

The Stage 1 implementation is verified locally. The Guinier, temperature, and
quality focused matrix passed with `18 passed`; the extended temperature and
physical-helper matrix passed with `36 passed`; and the complete
`tests/test_saxs_*.py` matrix passed with `228 passed, 4 warnings` in `18.95s`
using an external basetemp. Ruff, compileall, py_compile, and diff-check passed.

The structured verifier passed with quality gate `282 passed`, preprocessing
gate `103 passed`, and exit code 0. The default repository basetemp still
reproduces the known Windows `WinError 5` cleanup lock; the external-basetemp
rerun is the authoritative result. The added provenance regression confirms
that `processed_data_ref` remains available through
`MetricEvidence.data_quality_ref`.

实际证据：Guinier/变温 focused tests `24 passed`；完整 SAXS 矩阵
`227 passed`（4 个既有 Matplotlib 字体 warning）；quality gate `282
passed`；preprocessing gate `103 passed`；结构化 verifier 通过。代码
checkpoint 为 `17dcb0b`。`core.py` 和 `saxs_temperature.py` 的历史 Ruff
baseline findings 与本阶段科学行为分开记录，未将其误报为新回归。

## Known limitations

本阶段只做逐帧证据和硬门槛；真实层片/Bragg 场景的科学适用性仍需显式
实验上下文和人工审查，序列趋势、AI 候选、其他方法及发布链另行验收。

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/__init__.py`
- `polynexus/core/saxs_engine/core.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_quality_contracts.py`
- `tests/fixtures/saxs_quality_cases.py`
- `tests/test_saxs_guinier_evidence.py`
- `tests/test_saxs_temperature_guinier_evidence.py`
- this task card
- `docs/superpowers/plans/2026-07-27-saxs-temperature-guinier-evidence.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
