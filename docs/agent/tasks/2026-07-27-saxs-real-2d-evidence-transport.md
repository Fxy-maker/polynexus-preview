# SAXS Real 2D Evidence Transport

## Goal

修复真实 SAXS strain 流程中已有 sector-map detector evidence 从
`analyze_anisotropy` 到 `StrainPointResult`/`StrainSeriesResult` 丢失的问题，
让现有证据继续进入已有 parameters/Figure/Export 传输边界。

## Non-goals

- 不把 sector map 误报为 raw detector。
- 不猜 mask、saturation、beam center 或几何有效性。
- 不修改 pyFAI、EDF reader、方位积分、Herman/axis 算法、物理阈值、质量等级、
  Figure role、Workbench risk text、AI 或 publication eligibility。
- 不以自动化 transport 证据替代真实科学 sign-off。

## Current evidence and defect

真实 PAD8 原位拉伸 EDF replay（外部输出目录）显示：单帧图像为
`(1028, 512)` `float64`，EDF geometry header 含 `SampleDistance`、`Center_1`
和 `Center_2`；5 帧的 `geometry_source` 均为 `header`、confidence 均为
`0.95`；pipeline `validation_passed=True`，并产生 5 个 sector maps。

但真实 run 中 orientation evidence 已包含 `source_kind=sector_map`、约
`0.787--0.789` coverage、`nonpositive_pixels`、unknown saturation 和缺失
beam center 的 detector report，而 `StrainPointResult.detector_quality_report`
与 `StrainSeriesResult.detector_quality_report` 均为 `None`。这不是科学降级
本身，而是 provenance transport 丢失。

设计文档：
`docs/superpowers/specs/2026-07-27-saxs-real-2d-evidence-transport-design.md`

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_strain.py`：sector-map 到 strain DTO 的传递。
- `tests/test_saxs_2d_evidence_propagation.py`：真实代码回归。
- `docs/acceptance/`、`docs/agent/memory/`：验证证据与 durable state。

## Acceptance criteria

- [x] sector-map detector report 从 `herman_from_sector_data` 进入对应
  `StrainPointResult`。
- [x] 有 sector evidence 时，`StrainSeriesResult.detector_quality_report`
  由现有 rollup 生成；无 sector evidence 时仍不生成伪报告。
- [x] frame/series payload 保持 strict JSON-safe，source kind 仍明确为
  `sector_map`，不提升到 raw detector 或 Quantitative。
- [x] 现有 strain orientation 数值、缺失/失败行为、parameters/Figure/Export
  consumers 不回归。
- [x] focused RED/GREEN、完整 SAXS 矩阵、结构化 verifier、真实 PAD8 replay
  和显式 allowlist checkpoint 均有实际证据。

## Implementation plan

1. 写 finite sector-map transport regression，先观察预期 RED。
2. 在 `herman_from_sector_data` 返回已有 detector report，并在 strain point
   DTO 写入它；不添加新的计算。
3. 运行 focused、SAXS 矩阵、task-scoped verifier 和真实 PAD8 replay。
4. 更新本卡、spec/plan、durable memory，并用显式 allowlist 创建 checkpoint。

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_real_2d_transport_verify'
python -m pytest tests/test_saxs_2d_evidence_propagation.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-real-2d-evidence-transport.md --changed --types
git diff --check
```

完整 SAXS 矩阵使用 PowerShell 展开的 `tests/test_saxs_*.py` 文件列表，并
必须记录最终 pytest 摘要；无摘要或 timeout 不计为通过。

## Verification evidence (2026-07-27)

- TDD RED（修正 sector fixture 形状后）：`1 failed, 11 passed`，失败为
  `StrainPointResult.detector_quality_report` 仍为 `None`。
- TDD GREEN：`python -m pytest tests/test_saxs_2d_evidence_propagation.py -q`
  返回 **12 passed**。
- 完整 SAXS 文件矩阵（PowerShell 展开 `tests/test_saxs_*.py`）：**365
  passed, 4 warnings in 29.96s**。warning 为既有 SAXS figure Arial CJK
  glyph warnings。
- `python scripts/verify.py --task
  docs/agent/tasks/2026-07-27-saxs-real-2d-evidence-transport.md --changed
  --types`：exit 0；task/memory、Ruff、compile/type、quality gate **283
  passed**、preprocessing gate **106 passed**、whitespace 均通过。
- 外部真实 replay 输出于
  `C:\Temp\PolyNexus_saxs_real_2d_transport_green_20260727`：
  `validation_passed=True`；5 个 frame detector report 的
  `source_kind` 均为 `sector_map`；series detector summary 不再为 `null`，
  仍为保守 `Unusable`，reason 保留
  `detector_saturation_unknown`、`beam_center_missing`、
  `nonpositive_pixels`；5 帧 geometry source 均为 `header`、confidence
  均为 `0.95`。
- `git diff --check` 通过；checkpoint 使用本卡下方的显式 allowlist 创建，
  未包含并行未跟踪文件。

## Known limitations

该 slice 只补齐 provenance transport。真实 raw detector mask propagation、
几何校准科学有效性、取向机理解释、重启 GUI 视觉检查和最终 release approval
仍是独立门槛。

## Pre-existing workspace changes

不修改或清理现有 pytest 临时目录、`.superpowers/`、GUI/editor 草稿、
`tests/_tmp_phase3/` 和其他并行未跟踪文件。

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_2d_evidence_propagation.py`
- 本任务卡
- `docs/superpowers/specs/2026-07-27-saxs-real-2d-evidence-transport-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-real-2d-evidence-transport.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
