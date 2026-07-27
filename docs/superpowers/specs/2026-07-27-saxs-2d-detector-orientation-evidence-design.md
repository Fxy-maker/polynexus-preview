# SAXS 2D 探测器与取向证据设计

日期：2026-07-27
状态：阶段 5 设计
关联 Goal：建立可解释、可验证、可降级的 PolyNexus SAXS 数据质量与分析体系

## 1. 目标与边界

在已有 1D/模式证据契约上，建立 2D detector quality 和 orientation evidence
的最小闭环。当前 `analyze_anisotropy` 接收的是 sector-integrated 2D map，
因此结果必须明确数据来源；sector map 不能被误称为完整 raw detector quality。

本阶段不重写 pyFAI、几何标定、方位积分或 Herman 算法，不自动识别未经调用
方提供的饱和值，不猜 beam center，不把未知图像格式补成有效元数据。

## 2. DetectorQualityReport

新增不可变、严格 JSON-safe 的 `DetectorQualityReport`，记录：图像 shape、总
像素、有限/非有限/非正/正像素、显式 mask 像素、显式 saturation 像素、
有效覆盖率、来源类型、beam center 是否存在、q/chi 轴覆盖和 reason codes。

`build_detector_quality_report(image, mask=None, saturation_value=None, source_kind="unknown", beam_center=None)`
只读输入。饱和统计仅在 `saturation_value` 显式提供时启用；不从最大值推断
探测器上限。没有有效像素为 `Unusable`，存在缺陷或来源/几何信息不足时为
`Diagnostic`，完整且来源/几何明确时最高 `Trend`，本阶段不产出 2D
`Quantitative`。

## 3. OrientationEvidence

`build_orientation_evidence(anisotropy_payload, detector_quality, applicability="unknown", source_ref="")`
把现有 `f_herman/P2/P4/pattern_type/anisotropy_ratio/anisotropy_index/confidence`
包装为 `MetricEvidence(metric_name="Orientation")`。有限取向指标、峰/形状
摘要和 detector quality 引用进入 `fit_evidence`/`physical_checks`；不自动
把 pattern type 解释成材料机理，不新增取向阈值。未知适用性或 detector
quality 不足最高 `Diagnostic`，缺失指标 `Unusable`。

`AnisotropyResult` 增加 `detector_quality_report` 和 `orientation_evidence`
字典，但保留所有现有数值字段和数组。2D evidence 的来源必须区分
`raw_detector`、`sector_map`、`unknown`。

## 4. 测试与后续边界

focused tests 覆盖 raw/sector/unknown source、mask、显式 saturation、无效
像素、空图、取向缺失、未知适用性和严格 JSON。后续阶段再把 raw detector
reader/geometry/pyFAI mask 的报告传进来，并把证据传播到 Figure/Workbench；
本阶段不改变发布角色。
