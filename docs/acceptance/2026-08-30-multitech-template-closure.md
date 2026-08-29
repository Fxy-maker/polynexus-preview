# 多技术 canonical 模板阶段验收（2026-08-30）

这是 Goal 的中间检查点，不是最终完成报告。

## 已验证

- IR 温度序列目录：多个一维帧合并为一个 `ir.temperature_series.v1`，项目入口只产生一个 `ir.temperature_2d` ComputeRun 步骤。
- SAXS EDF 与 WAXS EDF：在只读临时项目中分别生成
  `saxs.detector_image.v1` / `waxs.detector_image.v1`，并成功进入项目 evidence package。
- NMR 液体 ¹H vendor `fid`：真实文件回放成功，使用 `nmr.spectrum.v1`，通过 ComputeRun 和 evidence package；结果保留 `review_required`。
- 混合项目：IR/WAXS、NMR/WAXS 均通过 composite recipe，跨技术关系写入 package。

## 仍未宣称完成

- SAXS/WAXS detector image 的 provider-specific 几何、mask、orientation 和论文 promotion 仍由现有科学审查门控制；canonical 转换不填默认校准。
- NMR 四模式需要调用方显式传入 `nmr.liquid_h`、`nmr.liquid_c`、`nmr.solid_h` 或 `nmr.solid_c`；不会从文件名猜测核种或相态。
- 尚未基于完整真实回放做公共字段精简，也尚未完成最终 GUI/CLI/ARS 全矩阵验收。

## 验证命令

```text
python -m pytest tests/test_detector_image_canonical.py tests/test_project_workflow_adapters.py tests/test_mixed_technique_project_run.py tests/test_nmr_shared_compute_run.py -q
python scripts/verify.py --changed --types
```
