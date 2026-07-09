# SAXS 温度序列 `lc` 路径选择方案

## 1. 背景问题

当前温度 SAXS 链路已经能识别一部分不可靠 `lc`，例如 PA6 在 185 C 附近出现 `lc_nm_raw = 0.99 nm` 时，会被标记为 `diagnostic_only`，并从最终 `lc_nm` 主列移除。

这解决的是“不要把错误数值当结果”的问题，但还没有解决“如何更稳定地提取出可信 `lc`”的问题。

根因是当前流程仍然接近：

```text
每帧独立提取 lc -> 得到一个主值 -> 后处理判断是否可信
```

更稳的方向应该是：

```text
每帧生成多个 lc 候选 -> 对整条温度序列选择一条最少矛盾的 lc(T) 路径 -> 再输出有效值和置信度
```

## 2. 目标

1. 把 `lc` 从“单帧单值提取”升级为“候选池 + 序列级路径选择”。
2. 在 PA6 这类高温弱结构数据中，避免把 0.8-1.0 nm 这类假候选误当成层片厚度。
3. 在证据足够时恢复更合理的 `lc_nm_effective`，证据不足时明确输出 `None`。
4. 保留 raw/candidate/effective 三层，不静默覆盖原始提取值。
5. 让 AI 只参与参数建议和诊断解释，不直接决定最终 `lc`。

## 3. 推进原则

- 证据优先：候选必须能追溯到曲线证据、方法来源和评分原因。
- 物理约束是软硬结合：`0 < lc < L` 是硬约束，材料合理范围和连续性是软约束。
- 序列优先于单帧：温度序列中孤立突变候选需要更强证据才能被接受。
- 不把“未熔融”直接等价为“lc 必须可提取”：185 C 未必熔融，但仍可能不适合可靠提 `lc`。
- 不把“符合预期”当验收标准：验收看证据一致性、透明度和错误拦截能力。

## 4. 总体设计

### 4.1 候选池

每个温度帧生成多个 `lc` 候选，而不是只保留一个主值。

候选来源：

- `tangent`: correlation tangent method
- `idf`: IDF 特征厚度
- `gamma_min`: correlation function first minimum
- `porod_invariant`: invariant / Porod 约束反推
- `reference_Xc`: 如果用户或 WAXS/DSC 提供参考结晶度，则 `lc = L * Xc_ref`
- `sequence_prediction`: 由前后温度点平滑预测得到的候选
- `raw_selected`: 当前 core 选出的原始主候选

候选结构建议：

```python
@dataclass
class LcCandidate:
    value_nm: float
    source: str
    score_local: float
    hard_valid: bool
    reject_reason: list[str]
    evidence: dict[str, Any]
```

每帧保留：

```python
@dataclass
class LcCandidateFrame:
    temperature_C: float
    L_nm: float
    Q_star: float
    melting_window_status: str
    candidates: list[LcCandidate]
```

### 4.2 单帧评分

每个候选先得到单帧分 `score_local`。

硬约束：

- `lc` 必须有限且 `lc > 0`
- `L` 必须有限且 `L > 0`
- `lc < L`
- `Xc = lc / L` 必须在 `(0, 1)` 内

软约束：

- `lc / L` 过低时降权，例如 `< 0.12`
- `lc < 1.5 nm` 对 PA6 这类材料强降权，但不作为绝对删除
- 多方法候选彼此接近时加分
- 与 `Q_star`、峰强、Porod slope、invariant 趋势一致时加分
- 当前帧处于 `near_onset / within_window` 时提高证据门槛

示例评分项：

```text
score_local =
  method_confidence
+ method_agreement_bonus
+ peak_support_bonus
+ invariant_consistency_bonus
- minority_fraction_penalty
- implausible_lc_penalty
- method_conflict_penalty
- melting_window_penalty
```

### 4.3 序列路径选择

对整个温度序列选择一条 `lc(T)` 路径，而不是逐帧独立选最大分。

路径允许两种节点：

- 选择某个候选 `lc`
- 选择 `None`，表示该帧不可可靠提取

路径总分：

```text
path_score =
  sum(score_local_i)
- sum(jump_penalty_i)
- sum(L_lc_inconsistency_penalty_i)
- sum(Q_invariant_inconsistency_penalty_i)
- sum(melting_window_misinterpretation_penalty_i)
- none_penalty
```

连续性惩罚示例：

```text
jump_penalty = abs(log(lc_i / lc_{i-1})) * weight
```

但如果同时出现以下证据，可以降低突变惩罚：

- Bragg 峰强明显丢失
- Q invariant 明显下降
- 进入 sequence-derived melting window
- WAXS/DSC 同步显示结晶消失或相变

推荐算法：

- 第一版使用动态规划/Viterbi。
- 每帧候选数量通常很小，复杂度 `O(n * k^2)` 可接受。
- 后续再考虑 HMM 或贝叶斯平滑，不作为第一版范围。

### 4.4 输出字段

每帧输出：

```text
lc_nm_raw
lc_nm_effective
lc_nm
lc_candidate_selected_nm
lc_candidate_selected_source
lc_candidate_score
lc_candidate_count
lc_candidate_rejected_reason
lc_path_status
lc_path_reason
lc_reliability_status
lc_reliability_reason
```

字段语义：

- `lc_nm_raw`: 单帧原始算法直接提取值。
- `lc_nm_effective`: 序列路径选择后的有效值；如果不可可靠提取，则为 `None`。
- `lc_nm`: 面向表格主显示，默认等于 `lc_nm_effective`。
- `lc_candidate_selected_nm`: 路径算法选中的候选值。
- `lc_path_status`: `usable / low_confidence / diagnostic_only / no_path`
- `lc_candidate_rejected_reason`: 被拒绝候选的主要原因摘要。

### 4.5 AI 联动边界

AI 可以参与：

- 建议 `q` 范围、背景扣除、平滑强度、IDF 窗口。
- 解释为什么某些候选被拒绝。
- 建议是否启用材料软先验，例如 PA6 的低 `lc` 警戒线。
- 发现数据问题，例如低 q 覆盖不足、beamstop 影响、峰追踪丢失。

AI 不可以参与：

- 直接指定最终 `lc` 数值。
- 绕过 deterministic path scorer。
- 把材料手册熔点直接当成熔融判据。
- 覆盖用户确认前的 raw 数据和诊断证据。

## 5. 分阶段范围

### 阶段 A：候选池落地

修改范围：

- `polynexus/core/saxs_engine/core.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs.py`

任务：

- 把 `lc_tangent_nm / lc_idf_nm / lc_gamma_min_nm / lc_porod_nm` 统一收集为候选。
- 增加候选评分函数 `score_lc_candidate()`。
- 在温度结果对象中保留每帧候选列表。

验收：

- PA6 185 C 的 `0.99 nm` 候选不丢失，但能看到它因 `minority_fraction_too_low / sequence_conflict` 被降权。
- 稳定低温帧至少有一个候选进入 `usable` 或 `low_confidence`。

### 阶段 B：序列路径选择

新增建议文件：

- `polynexus/core/saxs_engine/lc_path_selection.py`

任务：

- 实现 `select_lc_sequence_path(frames, cfg)`。
- 支持候选节点和 `None` 节点。
- 输出 `lc_nm_effective` 和 `lc_path_status`。

验收：

- 孤立的 `0.99 nm` 候选不会因为单帧局部特征被直接选为有效 `lc`。
- 如果候选池没有可靠替代值，则输出 `None`，而不是编造平滑值。
- 对稳定合成序列，路径结果不应比原始提取更差。

### 阶段 C：材料软先验

任务：

- 增加可选配置，例如：

```python
lc_soft_min_nm: Optional[float] = None
lc_soft_max_nm: Optional[float] = None
Xc_soft_min: Optional[float] = None
Xc_soft_max: Optional[float] = None
polymer_family: str = ""
```

- PA6 不写死在 core 里，只通过配置或识别结果传入软约束。

验收：

- 没有用户/上下文确认材料时，不启用 PA6 专属范围。
- 启用 PA6 软先验后，`lc < 1.5 nm` 强降权，但仍可在强证据下进入 `low_confidence`。

### 阶段 D：导出与解释

任务：

- CSV 导出候选路径字段。
- evidence/report 展示 raw/effective/candidate 的区别。
- GUI 表格主列显示 `lc_nm_effective`，诊断列显示 raw 和 rejected reason。

验收：

- 用户不会只看到一个裸 `lc_nm`。
- 对 `diagnostic_only` 帧，报告能明确写出“不是判定熔融，而是 SAXS 证据不足以可靠提取 lc”。

### 阶段 E：AI 调参闭环

任务：

- AI tuning 读取候选拒绝原因。
- 调参目标从“让 `lc` 变合理”改成“提升候选证据质量”。
- 对候选路径分数没有提升的调参自动回滚。

验收：

- AI 不直接产生 `lc` 数值。
- AI 推荐参数必须能改善 deterministic evidence，例如 `candidate_score`、`method_agreement`、`peak_support`。

## 6. 不做什么

- 不把 PA6 熔点 220 C 写死为熔融判据。
- 不用 AI 直接修正 `lc`。
- 不用平滑曲线强行填补不可提取帧。
- 不在没有候选证据时生成“看起来合理”的 `lc`。
- 不一次性重构 static/strain/temperature 所有 SAXS 模式。
- 不把 `lc_nm_raw` 覆盖成路径选择结果。

## 7. 验收标准

真实 PA6 温度序列：

- 170 C 可以保留 `low_confidence` 或 `usable`，但必须展示原因。
- 185 C 的 `lc_nm_raw = 0.99 nm` 不能直接成为有效 `lc_nm`。
- 如果没有更强候选，185 C 应输出 `lc_nm = None` 和 `lc_path_status = diagnostic_only`。
- 205/220 C 接近或进入 melting window 时，不继续按普通固态层片解释。

合成稳定序列：

- `lc(T)` 缓慢变化时，路径选择不能过度置空。
- 方法候选一致时，`lc_path_status` 应为 `usable`。

合成突变序列：

- 单帧 `lc` 突然坍塌但 `L/Q/peak` 不支持时，应拒绝该候选。
- 如果 `Q/peak/melting_window` 同时支持结构崩塌，可以接受为 `low_confidence` 或 `diagnostic_only`，但不能无说明地输出普通 `lc`。

导出/证据：

- CSV 至少包含 `lc_nm_raw / lc_nm_effective / lc_candidate_selected_source / lc_path_status / lc_path_reason`。
- `analysis_evidence` 能展示候选选择和拒绝原因。
- 用户确认结果前，系统不把 candidate/effective 值写成不可追溯的最终结论。

## 8. 风险

- 候选评分过强会把真实薄层片误判为不可提取。
- 候选评分过弱会继续接受 0.99 nm 这类假极值。
- 材料软先验如果来源不明，会引入人为偏置。
- 序列路径选择可能让单帧局部真实突变被平滑惩罚压掉。
- GUI 如果仍只突出 `lc_nm`，用户可能忽略 raw/effective 区别。

缓解方式：

- 所有软约束都输出 reason 和 score。
- 材料先验默认关闭或弱启用。
- `None` 节点是合法结果，避免强行补值。
- 路径算法先作为温度 SAXS 专项，不影响静态和拉伸 SAXS。
- 用 PA6 真实温度序列和合成边界序列双重验收。

## 9. 推荐第一步

先做阶段 A + B 的最小闭环：

1. 新增 `lc_path_selection.py`。
2. 从现有 `StructureParams` 收集候选。
3. 实现简单 Viterbi 路径选择。
4. 把 `lc_nm_effective` 从当前可靠性置空逻辑升级为路径选择结果。
5. 增加 PA6 185 C 式回归测试：`0.99 nm` raw 保留，但不作为有效 `lc`。

这一步完成后，系统才算从“会判错”进入“会尝试选更合理路径”的阶段。
