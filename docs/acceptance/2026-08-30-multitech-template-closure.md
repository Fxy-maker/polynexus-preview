# 多技术 canonical 模板阶段验收（2026-08-30）

这是 Goal 的最终代码与回放验收记录。

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
- GUI/CLI/ARS DTO 消费矩阵已通过 78 项跨入口回归；GUI/ARS 仍只消费共享 run/package/result-table/figure DTO，不拥有技术算法分支。

## 灵活性精简补充

- `TechniqueSeriesAdapter` 不再根据路径名片段（如 `saxs`、`waxs`、`ir`）
  阻断调用方声明的技术；实际 artifact inspection 和 canonical conversion
  负责最终判定。
- 混合入口不再提前统计 IR 目录中支持文件数量，目录直接进入 IR 路由；
  不足帧数仍由 canonical 模板返回原有阻断原因，不会生成伪二维结果。
- 保留哈希绑定、二维 shape、IR 多帧、NMR 显式子模块和 review/diagnostic
  边界等科学约束。

## 验证命令

```text
python -m pytest tests/test_detector_image_canonical.py tests/test_project_workflow_adapters.py tests/test_mixed_technique_project_run.py tests/test_nmr_shared_compute_run.py -q
python scripts/verify.py --changed --types
```

## 最终相关矩阵

```text
python -m pytest tests/eval/test_nmr_vendor_real_case_registry.py tests/test_saxs_real_2d_scientific_acceptance.py tests/test_waxs_lifecycle_closure.py -q  # 14 passed
python -m pytest tests/test_mixed_technique_project_run.py tests/test_ai_native_project_entrypoint.py tests/test_project_workflow_cli.py tests/test_project_workflow_package.py tests/test_capability_evidence_projection.py tests/test_ir_complete_figure_provider.py tests/test_saxs_workbench_figure_contracts.py tests/test_waxs_workbench_figure_contracts.py tests/test_nmr_figure_provider.py -q  # 78 passed
```
