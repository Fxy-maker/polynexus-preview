# SAXS 2D 探测器与取向证据

## Goal

为 2D detector quality 和 anisotropy orientation 建立严格 JSON-safe、可降级
且明确数据来源的证据契约。

## Non-goals

- 不重写 pyFAI/几何/方位积分/Herman 数值算法。
- 不从最大像素值猜测饱和上限，不猜 beam center，不伪造 raw detector provenance。
- 不新增取向/形状/材料机理硬阈值，不修改 Figure/Workbench 发布角色。

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/saxs_anisotropy.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_2d_detector_orientation_evidence.py`
- `docs/superpowers/specs/2026-07-27-saxs-2d-detector-orientation-evidence-design.md`

## Implementation plan

1. 先写 detector/orientation focused failing tests，锁定显式 mask/saturation、
   来源标记、空图/缺失指标和严格 JSON 语义。
2. 实现 `DetectorQualityReport`、`build_detector_quality_report` 和
   `build_orientation_evidence`，复用 `QualityLevel/MetricEvidence`。
3. 在 `AnisotropyResult` 和 `analyze_anisotropy` 中挂载两个字典，保留现有
   数值/数组和失败返回行为。
4. 跑 2D/anisotropy/完整 SAXS/结构化 verifier，记录证据并 checkpoint。

## Acceptance criteria

- [x] detector report 记录 shape、覆盖率、无效/掩膜/显式饱和计数和来源。
- [x] 未提供 saturation value 时不生成饱和判断。
- [x] orientation evidence 引用 detector report，未知适用性最高 Diagnostic，
  缺失取向指标 Unusable，完整证据最高 Trend。
- [x] `AnisotropyResult` 兼容现有调用方，空图仍返回可用对象且不伪造证据。
- [x] focused、完整 SAXS、结构化 verifier、两道质量 gate 和 checkpoint 有
  实际证据。

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_2d_detector_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-2d-detector-orientation-evidence.md --changed --types
```

## Verification evidence (2026-07-27)

- `python -m pytest tests/test_saxs_2d_detector_orientation_evidence.py -q`:
  **6 passed**.
- The complete SAXS file matrix (`test_saxs_*.py`, PowerShell-expanded) passed
  **250 tests, 4 warnings**. The warnings are the existing Arial CJK glyph
  warnings from SAXS figure layout.
- `python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-2d-detector-orientation-evidence.md --changed --types` passed; quality gate **282 passed**, preprocessing gate **103 passed**, task-card/memory/Ruff/compile/type/whitespace checks passed.
- The atomic checkpoint is created with the changed-file allowlist below; no
  generated outputs or pre-existing temporary diagnostics are included.

## Known limitations

当前 evidence 只描述传入的 2D/sector map，不替代真实 raw detector/geometry
审查。pyFAI mask 传播、2D 误差估计、取向序列和发布闭环另行验收。

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/saxs_anisotropy.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_2d_detector_orientation_evidence.py`
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-2d-detector-orientation-evidence-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-2d-detector-orientation-evidence.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
