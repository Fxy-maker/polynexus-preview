# SAXS 质量证据导出与 provenance 设计

日期：2026-07-27
状态：阶段 8 原子任务设计

## 目标

在现有 SAXS Export Bundle 中增加一个稳定的 `quality_evidence.json`，统一记录静态结果、温度/应变逐帧证据、Guinier 序列证据、序列救援候选、2D 取向证据和可选 AI rescue plan/decision。该文件与现有 `parameters.json`、Figure Manifest 和 `provenance.json` 同属一次导出，不改变任何科学数值或 publication role。

## 设计边界

- 只读取已有 result/series DTO 和可选 bridge DTO，所有输出经现有 `_jsonable` 清洗。
- 缺失证据字段保持缺失或空列表，不把 diagnostic/unusable 提升为 Main。
- 不重新分析、不应用 AI candidate、不推断 raw detector provenance，不写入用户原始数据。
- bundle manifest 增加 `quality_evidence` 文件引用，History/Editor 可通过同一个导出根目录复核。

## 数据流

`SAXSResult/TempSeriesResult/StrainSeriesResult/AI bridge → quality evidence snapshot → quality_evidence.json → bundle_manifest.files.quality_evidence`。

## 验收

1. 静态、温度、应变和空/失败导出均能安全生成或明确缺少质量证据。
2. 温度导出保留 `guinier_sequence_evidence` 和 `sequence_rescue_candidates`；逐帧质量/metric evidence 不被邻帧填充。
3. AI bridge plan/decision（若存在）只作为审计数据导出，仍保留 candidate-only/original-preserved/apply 状态。
4. Existing parameter/profile/figure/provenance files and publication roles remain unchanged。

## 后续

Workbench 质量面板、Editor 证据抽屉、重启 GUI 视觉审查和真实数据科学 sign-off 仍需独立验收。
