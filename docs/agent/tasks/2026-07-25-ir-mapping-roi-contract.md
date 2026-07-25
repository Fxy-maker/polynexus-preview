# IR mapping/ROI contract and figure lifecycle

## Goal

为 IR mapping/ROI 建立一个不猜仪器格式的结构化输入边界，并完成
AnalysisResult/evidence、Main/SI/diagnostic FigureDefinition、Manifest 发布和
Workbench figure routing 的最小闭环。

## Non-goals

- 不推断仪器厂商二维文件格式、坐标原点或波数 band 的科学含义。
- 不从任意目录自动猜测 map metric、ROI 或成分分类。
- 不把 invalid-pixel 或低置信度诊断提升为 Main 结论。

## Affected boundaries

- `polynexus/core/ir_engine/ir_mapping.py`：显式 map/ROI DTO、验证和 Figure provider。
- `polynexus/core/ir.py`：可选 mapping result handoff。
- `polynexus/gui/results_workbench_profiles.py`：真实 mapping figure IDs。
- `tests/test_ir_mapping.py` 及 Workbench/生命周期回归。
- `docs/acceptance/`、`docs/agent/memory/`。

## Implementation plan

1. Lock the explicit mapping/ROI DTO and structural validation with failing tests.
2. Publish Main, SI, and diagnostic FigureDefinitions through the shared pipeline.
3. Connect `AnalysisResult`, engine handoff, and Results Workbench figure links.
4. Run focused/full IR regressions, the task verifier, and an allowlisted checkpoint commit.

## Contract decision

上游必须明确提供：二维 scalar map、row/column 坐标、invalid-pixel mask、
map metric 标签，以及已定义的 ROI 光谱。Provider 只校验形状、有限性、
provenance 和 publication role，不解释 scalar map 的物理来源，也不自动选择
band。JSON/仪器 reader 适配留给后续科学评审。

## Acceptance criteria

- [x] 有 typed mapping/ROI DTO，拒绝 shape、坐标、mask 和 ROI 光谱不一致的数据。
- [x] 有 Main map、SI ROI spectra、diagnostic invalid-pixel FigureDefinition。
- [x] 三类 definition 可通过 shared FigurePipeline 生成 Manifest。
- [x] Mapping Workbench links 指向这些真实 figure IDs；没有数据时保持明确 empty state。
- [x] focused pytest、structured verifier 和 auto-commit 均有记录（checkpoint commit 待完成）。

## Verification

```powershell
python -m pytest tests/test_ir_mapping.py tests/test_ir_nmr_joint_workbench_profiles.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-25-ir-mapping-roi-contract.md --changed --types
```

## Known limitation

这项 checkpoint 仍不等于真实仪器 mapping reader 或人工作图验收；需要用户确认
输入文件/像素矩阵和 ROI 配置的实际来源后再接入 reader。
