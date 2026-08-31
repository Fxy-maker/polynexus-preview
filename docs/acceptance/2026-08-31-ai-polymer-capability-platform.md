# AI-first 高分子通用实验数据与能力平台：阶段验收

日期：2026-08-31
任务卡：`docs/agent/tasks/2026-08-30-ai-polymer-capability-platform.md`

## 目标与范围

本阶段把 PolyNexus 的共享计算边界推进为 AI 可发现、可规划、可组合、可拒答且可复算的实验能力基础层。重点是公共契约和跨入口投影，不是一次实现所有厂商格式或每个高分子测试的科学 provider。

## 共享对象与入口

- `DataBlock`、`AxisProvenance`、`CalibrationRef`、`UncertaintyRef`、`MissingnessPolicy` 和四轴 `ComputationState` 负责统一数据、轴来源、校准、不确定度、缺失和发布状态。
- 版本化 `CapabilityDescriptor`/registry、`CapabilityPlanner` 和确定性 `ExecutionGraph` 为 AI/CLI 提供能力发现、缺失输入规划、依赖顺序、缓存键和节点 provenance。
- `ComputeRun`、`metric_manifest`、Agent/Codex workflow、CLI、GUI、Evidence、Joint 使用同一份 descriptor/state/provenance 投影；legacy provider 字段只作为兼容投影。

## 已实现能力

- 标量、序列、矩阵/立方体、复数和表格引用的严格 JSON/hash/形状/坐标校验。
- 观测、校准、用户确认、推断和合成轴来源语义；合成/推断轴不能满足定量门禁。
- IR/FTIR alias 归一化；温度序列可组成温度×波数矩阵和二维相关输入。
- SAXS/WAXS 探测器图像保留二维 reference-only canonical envelope，并要求显式几何校准后才能进入定量 profile 能力。
- NMR FID 保留 real/imaginary 复数数据；FFT、T1/T2、二维 FFT 仅在采样/参考等输入显式声明后规划，缺失时返回 `needs_input`。
- DMA/DMTA、流变、TGA/DTG、SEC/GPC、力学能力族已进入目录；未绑定真实 provider 时明确返回 `unsupported` 或 `needs_input`，不生成科学占位值。
- Evidence promotion、结果表、写作指标和 workflow projection 对状态、descriptor、provenance、uncertainty 冲突 fail closed；诊断结果不会静默升级为结果候选。

## 验证证据

```text
Focused matrix: 207 passed in 10.78s
Task verifier: Ruff/py_compile/whitespace passed; quality 313 passed; preprocessing 157 passed; exit 0
Compile smoke: python -m compileall -q polynexus -> exit 0
Diff check: git diff --check -> exit 0
Full boundary: 4492 passed, 38 failed, 25 skipped, 27 warnings
```

Full boundary 的 38 个失败集中在既有 GUI/figure/SAXS/TPAE baseline（例如 chart gallery reflow、figure asset expectations、IR bridge ambiguity、main-window persistence、SAXS dirty-frame/scientific baseline、TPAE `255°C`/`180°C` golden mismatch），不属于本阶段改动，因此未擅自修改。

## 限制与后续

当前高优先级能力族的 descriptor 是诚实的 contract-first 壳：DMA/DMTA、流变、TGA/DTG、SEC/GPC、力学的真实读取、预处理、QC、指标、不确定度和 evidence provider 仍需后续 atomic tasks。N-D descriptor 的 executor binding、校准内容数值验证、跨厂家 replay fixtures 和完整暂停/恢复资源管理也仍待增强。

本阶段不写入或推断科学占位值。架构、schema、promotion policy 及科学语义必须经过人工 review 后，才能进入主线合并或论文发布边界。

用户已有的 elastomer 论文任务/计划/spec、脚本/测试、运行目录、`active_run.json`、memory 改动等均保留，未纳入本阶段 checkpoint。
