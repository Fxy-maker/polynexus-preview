# AI-first 高分子通用实验数据与能力平台设计

## 目标

将 PolyNexus 从当前的五类技术专用分析框架，演进为一个面向 AI 的高分子实验能力平台。AI 能够发现可用能力、检查输入、规划和组合确定性计算、理解结果边界，并在需要时提出可执行的补数据或补实验请求；GUI、CLI、Agent/Codex 和论文 Suite 始终消费同一套公共对象。

## 已确认的产品边界

目标对话已经确认以下分工：

- PolyNexus Core 负责原始数据标准化、确定性计算、图表、质量控制、不确定度和 provenance；
- AI/ARS 负责研究问题、能力规划、论点组织、文献和文字表达；
- FigurePlan、ClaimRecord、EvidencePackage、ComputeRun 等是跨入口共享对象；
- 人机协同采用自适应询问：普通流程自动推进，只有会改变科学结果的歧义才请求用户确认；
- AI 不得改写原始数据、绕过 canonical validation、猜测材料身份或把诊断结果升级为科学事实。

论文生成是上层应用，不是计算 Core 的唯一目标。DMA、流变、TGA、SEC/GPC、力学等新增测试应作为可组合能力插件接入，而不是各自建立独立的 GUI 和结果格式。

## 非目标

- 本阶段不一次性实现所有厂商文件格式；格式适配器与科学算子分离，长尾格式以后通过插件加入。
- 不重写已经稳定的 DSC、FTIR、SAXS、WAXS、NMR provider 算法；先提供兼容投影，再逐步迁移到统一数据对象。
- 不把 AI 生成的解释、论文文字或图形审美判断写入确定性科学结果。
- 不放宽现有校准、质量门和 `diagnostic_only`/`review_required` 边界。
- 不新增第二套技术专用二维数据模型。

## 架构

```text
仪器原始文件 / 用户导入数据
            |
            v
  RawArtifact + DataBlock + AxisProvenance
            |
            v
  CanonicalExperiment / ResearchGraph
            |
            v
  CapabilityDescriptor + CapabilityPlanner
            |
            v
  ExecutionGraph / ComputeRun / Cache
            |
            v
  Metric + Uncertainty + Evidence + Figure
            |
            v
  AI/ARS、CLI、GUI、Joint、Export
```

### 公共对象

#### `DataBlock`

不可变、可序列化的数据引用。小数组可以内联，大数组使用内容寻址的外部 chunked artifact。字段包括：

- `block_id`、`schema_version`、`kind`（scalar/series/matrix/cube/complex/table/event）；
- `shape`、`dims`、`coords`、`coord_units`；
- `array_ref`、`mask_ref`、`uncertainty_ref`、`source_artifact_id`；
- `axis_provenance` 和坐标变换记录；
- 数据哈希、缺失值策略和质量标记。

`Measurement` 可以继续作为一维兼容视图，但新的能力不得要求把二维、复数或多帧数据强行压成 `x + intensity`。

#### `AxisProvenance` 与 `CalibrationRef`

每个物理轴都必须记录来源类别：`observed`、`calibrated`、`inferred`、`user_confirmed` 或 `synthetic`，以及方法、误差、校准文件哈希和有效性。

合成轴只允许进入形状诊断和可视化，不允许进入绝对定量、动力学、相鉴定或论文结果能力。能力 descriptor 必须显式声明接受的轴来源。

#### `CapabilityDescriptor`

统一收敛现有 `CapabilitySpec`、`ProviderCapabilitySpec`、`CapabilityCoverage`、`SubModuleSpec` 和相关 alias。必须声明：

- 能力 ID、版本、技术族和成本；
- 输入字段、维度、单位和数量约束；
- 前置质量门和轴来源要求；
- 输出 schema、单位、公式和不确定度策略；
- 依赖能力、替代能力和执行器；
- 缺失输入动作、失败原因和 evidence promotion policy。

#### `ComputationState`

把目前分散的执行状态和科学状态拆成四个互不替代的轴：

```text
data_availability: missing | raw | partial | canonical
computability: blocked | needs_input | computed | not_applicable | failed
validity: not_assessed | diagnostic | validated
promotion: diagnostic_only | review_required | results_candidate
```

每个状态都可以附带 `preconditions`、`missing_inputs`、`reason_codes` 和下一步动作。

#### `ExecutionGraph`

节点以输入哈希、descriptor 版本、参数、校准和运行环境共同生成缓存键。节点应支持依赖失效、重试、取消、恢复和资源估计；旧的同步 `ComputeRunService` 作为兼容执行器保留。

## AI 调用协议

AI 只能通过以下公开动作请求工作：

1. `inspect_project`：返回材料、样品、批次、条件和数据清单；
2. `discover_capabilities`：按输入和目标列出可执行、待补输入和不适用能力；
3. `plan_execution`：生成可审查的能力 DAG；
4. `execute_plan`：由 Core 校验并运行确定性节点；
5. `inspect_evidence`：获取指标、图、限制、不确定度和来源；
6. `request_missing_input`：提出具体的校准、样品身份或补实验请求。

AI 不直接读取并重算任意原始文件，也不直接写入 `ComputeRun`、EvidencePackage 或原始 artifact。

## 高分子能力路线

第一优先级能力族：

- DSC/FTIR/SAXS/WAXS/NMR 的 N-D、二维和不确定度闭环；
- DMA/DMTA：E′、E″、tanδ、Tg、主曲线、蠕变和松弛；
- 流变：黏度、G′/G″、屈服、触变、TTS、蠕变恢复和应力松弛；
- TGA/DTG：失重阶段、残炭和动力学；
- SEC/GPC：Mn、Mw、Mz、Đ、分布和校准；
- 力学：拉伸、压缩、弯曲、冲击、疲劳、断裂和蠕变。

后续能力族包括显微图像、Raman/XPS/接触角、溶胀/凝胶分数、阻隔、MFI/MFR、密度/孔隙率、电学/介电、老化/降解、阻燃、生物和模拟计算。每个能力族都必须经过“读取→标准化→预处理→QC→指标/模型→不确定度→证据→导出”的闭环。

## 兼容与迁移

- 现有 `CanonicalExperiment`、`ComputeRun`、`metric_manifest`、Figure 和 evidence JSON 继续作为公共外部边界；新字段采用可选、版本化方式。
- 旧的一维 provider 结果先通过 descriptor projection 暴露，不改变已有科学值。
- `ir`/`ftir`、`nmr` 子模块和供应商 alias 在 descriptor 层统一归一化，并增加跨入口回归测试。
- Joint 从 legacy `results_summary` 逐步迁移到共享 ComputeRun、metric manifest 和不确定度；在迁移完成前明确标记兼容来源。

## 验收示例

1. EDF 二维像素、mask、几何和校准被保留为一个 DataBlock，可派生径向和方位结果；
2. 多条温度 FTIR 自动组成 `I(T,ν)`，并能发现二维相关能力；
3. 复数 NMR FID 可作为 DataBlock 输入 FFT、T1/T2 和二维能力；
4. 缺少 NMR 原始数据时返回 `data_availability=missing`，而不是“能力不存在”；
5. 缺少校准时返回 `needs_input`，不会用默认物理轴生成定量结果；
6. 修改校准只使下游依赖节点失效，重复请求未变化节点命中缓存；
7. AI、CLI、GUI、evidence 和 Joint 读取同一份状态、指标和 provenance；
8. diagnostic 结果不能被论文 Suite 自动提升为结果候选。

## 评测与人审

建立跨技术 golden fixtures 和 AI tool-call 回归集，分别测量：能力发现准确率、缺失输入识别、数值一致性、状态正确性、provenance 完整性、缓存命中和拒答边界。架构、schema、科学语义和 promotion policy 在合并前仍需要人工评审。
