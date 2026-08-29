# 多技术 canonical 模板阶段验收（2026-08-30）

这是 Goal 的中间检查点，不是最终完成报告。

## 已验证

- IR 温度序列目录：多个一维帧合并为一个 `ir.temperature_series.v1`，项目入口只产生一个 `ir.temperature_2d` ComputeRun 步骤。
- SAXS EDF 与 WAXS EDF：在只读临时项目中分别生成
  `saxs.detector_image.v1` / `waxs.detector_image.v1`，并成功进入项目 evidence package。
- NMR 四类 vendor registry（液体/固体 × ¹H/¹³C）：现有真实案例回放测试通过；项目入口要求显式子模块，使用 `nmr.spectrum.v1`，结果保留 `review_required`。
- 混合项目：IR/WAXS、NMR/WAXS 均通过 composite recipe，跨技术关系写入 package。
- NMR vendor 回放额外验证了 evidence-only export：导出包含 run/recipe/evidence/results/figures 清单，不复制 raw 目录。

## 仍未宣称完成

- SAXS/WAXS detector image 的 provider-specific 几何、mask、orientation 和论文 promotion 仍由现有科学审查门控制；canonical 转换不填默认校准。
- NMR 四模式需要调用方显式传入 `nmr.liquid_h`、`nmr.liquid_c`、`nmr.solid_h` 或 `nmr.solid_c`；不会从文件名猜测核种或相态。
- 经验性精简结论：`CanonicalExperiment` 外壳、`ConversionRecord`、`ComputeRun`、`metric_manifest` 和现有单输入/序列 adapter 已是至少两种技术共享的最小层；IR 的 frame/condition 关系与 SAXS/WAXS 的 detector geometry 不具备可安全合并的科学语义，因此没有新增第二个二维公共模型，也没有删除专用字段。
- GUI/CLI/ARS 的最终全矩阵仍需在后续产品验收中执行；当前项目/AI/evidence/export 入口已覆盖。

## 验证命令

```text
python -m pytest tests/test_detector_image_canonical.py tests/test_project_workflow_adapters.py tests/test_mixed_technique_project_run.py tests/test_nmr_shared_compute_run.py -q
python scripts/verify.py --changed --types
```
