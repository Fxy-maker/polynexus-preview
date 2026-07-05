# PolyNexus 番外阶段 G 二维 IR 可信度矫正清单

## 0. 当前问题定位

二维 IR 这里指 `ir.temperature_2d`：原位变温红外序列、frame/temperature × wavenumber 矩阵，以及 Noda 2D-COS 同步 / 异步相关谱。

它和普通 IR 的可信度问题不一样：

- 普通 IR 主要判断“单张谱的峰是否抓对、归属是否可信”。
- 二维 IR 还要判断“序列轴是否正确、每一帧是否可比、动态谱是否真实、同步/异步相关峰是否是伪相关”。

目前代码已经具备最小链路：

- `detect_temperature_2d()` 能识别真实目录为 `ir.temperature_2d`
- `parse_temperature_condition()` 能从 `SW / for min / JW` 文件名恢复阶段、温度、时间
- `analyze_temperature_2d_series()` 能构造吸光度矩阵、追踪 PA6 特征带、计算同步/异步 2D-COS
- `generate_temperature_2d_figures()` 能输出热图、瀑布图、带指数、带追踪、同步/异步 2D-COS
- `tests/test_ir_temperature.py` 已经覆盖真实序列能跑通和导出

但当前可信度层仍然偏薄：

- 还没有冻结真实二维 IR 基线台账
- 没有专门的 `analysis_evidence` 结构描述 2D IR 序列质量
- `neg_fraction` 只是参数字段，还没有变成明确风险
- 2D-COS 相关峰目前更多是“找出来”，还没有判断是否可靠
- 异步谱符号依赖扰动排序方向，GUI / agent 还没把这个讲清楚
- AI 调参还没有二维 IR 专属症状到动作白名单


## 1. 专项目标

把二维 IR 从“能算出 2D-COS 图”升级成“能说明这组 2D-COS 图和相关峰是否可信”。

最终用户应该能看明白：

- 序列温度 / 阶段 / 时间轴是否可靠
- 每一帧是否可比较
- 吸光度矩阵是否有过扣基线、归一化扭曲或插值风险
- 同步谱和异步谱是否有足够动态信号支撑
- 交叉峰是可解释的谱带耦合，还是噪声 / 排序 / 基线造成的伪相关
- 哪些图可以作为论文图，哪些只能作为诊断图


## 2. 阶段边界

### 2.1 本专项要做什么？

- 做二维 IR 专属基线台账
- 补二维 IR evidence 分层
- 补序列轴、矩阵、2D-COS、交叉峰、带指数的可信度约束
- 补二维 IR 症状到参数动作桥接
- 补 GUI 的结果语义解释
- 补真实样本回归测试

### 2.2 本专项暂时不做什么？

- 不重写普通 IR core
- 不把 2D-COS 解释成最终机理结论
- 不自动生成论文讨论段落
- 不强行判定所有异步峰的因果先后
- 不在没有温度 / 时间轴可信度时强行优化 2D-COS 图


## 3. 最小闭环

二维 IR 的最小可信闭环应该是：

1. 读取真实原位变温红外目录
2. 恢复阶段轴：heating / hold / cooling
3. 恢复扰动轴：temperature_C / time_min / sequence_order
4. 每帧先走普通 IR 单谱 evidence
5. 构造统一 wavenumber 网格和 absorbance matrix
6. 评估矩阵质量：缺失、负值比例、动态信号强度、帧间连续性
7. 计算同步 / 异步相关谱
8. 提取 2D-COS cross peaks
9. 评估 cross peak 是否有带归属、动态强度、序列稳定性支撑
10. GUI 和 agent 只把证据充分的结果标成 paper-ready


## 4. 任务清单

### G-T1. 二维 IR 真实序列基线台账冻结

目标：
先把 `测试数据\IR\原位变温红外` 当前行为冻结下来，作为后续修复对照。

主要落点：
- `D:\PolyNexus\方案\PolyNexus 番外阶段G-T1 二维IR当前基线台账.md`
- `D:\PolyNexus\tests\test_ir_temperature.py`
- `D:\PolyNexus\polynexus\core\ir_engine\ir_temperature.py`

最小输出：
- `n_frames`
- `n_bands_tracked`
- 阶段计数：heating / hold / cooling
- 温度范围与是否单调
- 是否存在缺失温度 / 缺失时间 / 估算时间
- `absorbance_matrix.shape`
- `neg_fraction`
- `dynamic_matrix` 强度摘要
- `sync_cross_peaks / async_cross_peaks` 数量与 top peaks
- 当前导出图和 CSV 是否完整

验收标准：
- 不看图也能知道当前二维 IR 结果是“序列轴问题”、还是“矩阵质量问题”、还是“2D-COS 解释问题”
- 后续每次修复都能和这份基线对比

推荐模型：`mini`


### G-T2. 二维 IR evidence 分层设计

目标：
把二维 IR 的 evidence 从普通 IR 单谱证据扩展成序列证据。

主要落点：
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\polynexus\core\ir_engine\ir_temperature.py`
- 如有必要新增：`D:\PolyNexus\polynexus\core\ir_temperature_evidence.py`

建议分层：
- `sequence_evidence`
  - `n_frames`
  - `stage_counts`
  - `temperature_min_C / temperature_max_C`
  - `temperature_missing_count`
  - `time_missing_count`
  - `time_estimated_count`
  - `sequence_order_source`
- `matrix_evidence`
  - `wavenumber_count`
  - `matrix_shape`
  - `neg_fraction`
  - `nan_fraction`
  - `dynamic_signal_rms`
  - `dynamic_signal_to_noise`
- `single_frame_evidence`
  - 每帧普通 IR 的 `polymer_score / n_peaks / key_band_support_score`
  - 低可信帧比例
- `band_tracking_evidence`
  - 带高曲线是否连续
  - 带指数是否异常跳变
  - transition 是否由多帧支持
- `cos_evidence`
  - sync / async 是否已计算
  - sync autocorr 强度
  - async 强度与 sync 的比例
  - top cross peaks 是否远离对角线
- `interpretation_evidence`
  - cross peak 是否落在参考带附近
  - 是否支持 Noda 规则解释
  - 是否可以 paper-ready

验收标准：
- GUI 和 AI 不再只看到 `n_frames + 2D-COS 图`
- 能明确区分“矩阵能算”和“2D-COS 结论可信”

推荐模型：`5.4`


### G-T3. 序列轴可信度约束

目标：
防止温度 / 时间 / 阶段顺序错了但 2D-COS 仍被解释为真实响应先后。

主要落点：
- `D:\PolyNexus\polynexus\core\ir_engine\ir_temperature.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`

建议新增约束：
- `temperature_axis_missing`
- `stage_order_ambiguous`
- `temperature_sequence_nonphysical`
- `hold_time_missing_or_estimated`
- `cooling_heating_direction_mixed`
- `insufficient_perturbation_frames`

判据建议：
- 帧数 < 5：不允许 paper-ready 2D-COS
- 温度全缺失：只能做 sequence-order 诊断，不解释热响应
- heating / hold / cooling 混排：异步谱先后解释降级
- 时间估算比例过高：hold 段动态结论降级

验收标准：
- 扰动轴不稳时，系统明确提示“2D-COS 可生成，但异步谱先后解释不可靠”

推荐模型：`mini`


### G-T4. 矩阵质量与预处理约束

目标：
判断 absorbance matrix 是否适合做动态谱和 2D-COS。

主要落点：
- `D:\PolyNexus\polynexus\core\ir_engine\ir_temperature.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`

建议新增约束：
- `matrix_negative_fraction_high`
- `matrix_nan_fraction_high`
- `dynamic_signal_too_weak`
- `frame_intensity_scale_unstable`
- `baseline_over_subtraction_sequence`
- `normalization_erased_temperature_trend`
- `wavenumber_grid_inconsistent`

判据建议：
- `neg_fraction > 0.15`：soft warn
- `neg_fraction > 0.35`：paper-ready 阻断
- dynamic RMS 太低：说明 2D-COS 可能只是在放大噪声
- 单帧最大强度漂移异常：提示归一化或基线问题

验收标准：
- 不再只因为 2D-COS 图有颜色就认为有真实相关
- 基线过扣和归一化扭曲能进入可信度判断

推荐模型：`5.4`


### G-T5. 2D-COS 交叉峰可信度判据

目标：
让同步 / 异步 cross peaks 从“数值最大点”变成“有谱带归属和动态证据支撑的候选峰”。

主要落点：
- `D:\PolyNexus\polynexus\core\ir_engine\ir_temperature.py`
- `D:\PolyNexus\rag\polymer_knowledge.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`

建议新增字段：
- `cross_peak_count`
- `assigned_cross_peak_count`
- `unassigned_cross_peak_count`
- `diagonal_distance_cm1`
- `near_reference_band_1 / near_reference_band_2`
- `sync_support`
- `async_support`
- `noda_rule_interpretation_ready`

建议新增约束：
- `cross_peak_near_diagonal`
- `cross_peak_without_band_assignment`
- `async_peak_without_sync_support`
- `cross_peak_noise_dominant`
- `noda_rule_not_applicable`

判据建议：
- 交叉峰距离对角线太近：更像自相关或峰宽泄漏
- 两端都不靠近参考带：只作为 unassigned peak
- 异步峰没有同步谱支撑：不解释先后关系
- top peaks 全是未归属：2D-COS 结论降级

验收标准：
- AI 不能再只说“出现交叉峰，所以说明谱带相关”
- 必须说明是哪两个谱带、支撑强弱、能否用 Noda 规则解释

推荐模型：`5.4`


### G-T6. 带指数与 transition 可信度约束

目标：
让 `A1200/A1637`、`A1120/A1637`、`A929/A1637` 等带指数变化有连续性和多帧支撑。

主要落点：
- `D:\PolyNexus\polynexus\core\ir_engine\ir_temperature.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`

建议新增约束：
- `band_index_jump_single_frame`
- `band_index_denominator_unstable`
- `transition_single_frame_only`
- `band_tracking_missing_key_band`
- `temperature_trend_not_reproducible`

判据建议：
- transition 至少由 2-3 帧连续斜率支持
- 分母带强过低或过噪时，带指数不 paper-ready
- 单点突跳只标记为 anomaly，不标记为 transition

验收标准：
- 带指数图可以直接告诉用户“趋势可信 / 仅供诊断 / 不建议解释”

推荐模型：`5.4`


### G-T7. 二维 IR 症状到参数动作桥接

目标：
让 agent 针对二维 IR 的真实问题给出受控调参，而不是把普通 IR 的峰阈值策略硬套到 2D-COS。

主要落点：
- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\config_bridge.py`
- 如有必要新增：`D:\PolyNexus\polynexus\core\ir_temperature_action_registry.py`
- `D:\PolyNexus\rag\prompt_builder.py`

建议动作：
1. `repair_sequence_axis`
   - 目标症状：`temperature_axis_missing`, `stage_order_ambiguous`
   - 参数：condition pattern / filename parser / manual axis metadata
2. `stabilize_matrix_baseline`
   - 目标症状：`matrix_negative_fraction_high`, `baseline_over_subtraction_sequence`
   - 参数：baseline_method, mute-zone anchors, normalization_method
3. `recover_dynamic_signal`
   - 目标症状：`dynamic_signal_too_weak`, `normalization_erased_temperature_trend`
   - 参数：matrix preprocessing mode, normalization_method
4. `denoise_2dcos`
   - 目标症状：`cross_peak_noise_dominant`
   - 参数：smooth_window, cross_peak_threshold
5. `tighten_cross_peak_assignment`
   - 目标症状：`cross_peak_without_band_assignment`, `async_peak_without_sync_support`
   - 参数：assignment_tolerance_cm1, cross_peak_exclusion_cm1

验收标准：
- agent 优先修序列轴和矩阵质量，再谈 cross peak 解释
- 每轮仍只改 1-2 个参数
- 调参建议必须说明预期改善哪一层 evidence

推荐模型：`5.4`


### G-T8. GUI 二维 IR 结果语义拆分

目标：
让用户一眼看懂二维 IR 的用途，不把漂亮的 2D-COS 色图误读成可靠机理结论。

主要落点：
- `D:\PolyNexus\polynexus\gui\main_window.py`
- `D:\PolyNexus\polynexus\gui\i18n.py`

建议界面区块：
- 序列轴
  - 帧数、阶段、温度范围、缺失温度、估算时间
- 矩阵质量
  - 负值比例、动态信号、缺失比例
- 2D-COS 可信度
  - 同步 / 异步是否可解释
  - top cross peaks 是否归属
- 带指数趋势
  - 趋势可信 / 单点异常 / 不建议解释
- 论文可用状态
  - Figure usable
  - Cross peaks tentative
  - Sequence axis unresolved
  - Paper conclusion ready

验收标准：
- 用户能明确知道：
  - 图能不能用
  - 峰能不能解释
  - 异步先后关系能不能写
  - 还缺什么证据

推荐模型：`mini`


### G-T9. 真实二维 IR 回归验证

目标：
让真实原位变温红外目录成为二维 IR 可信度链的回归样本。

主要落点：
- `D:\PolyNexus\tests\test_ir_temperature.py`
- `D:\PolyNexus\tests\eval\cases\real\ir_temperature_2d_*.json`
- `D:\PolyNexus\tests\test_analysis_evidence.py`
- `D:\PolyNexus\tests\test_prompt_builder.py`
- `D:\PolyNexus\tests\test_main_window_persistence.py`

最小验证内容：
- 真实目录识别为 `ir.temperature_2d`
- 阶段排序稳定：heating -> hold -> cooling
- 矩阵形状稳定
- `neg_fraction` 被纳入 evidence
- sync / async cross peaks 有数量和归属统计
- 异步谱解释会说明扰动排序方向
- GUI 能区分“图可用”和“机理结论待确认”

验收标准：
- 即使二维 IR 结果暂时还不能完全 paper-ready，系统也能把原因讲对
- 后续如果真的修好，系统能说明比基线强在哪里

推荐模型：`5.4`


## 5. 推荐推进顺序

1. **G-T1 基线台账**
   - 先冻结真实序列当前行为
   - 防止后面改动后不知道变好了还是变坏了

2. **G-T2 + G-T3**
   - 先补 evidence 结构和序列轴约束
   - 这是二维 IR 最基础的可信度底座

3. **G-T4**
   - 再补矩阵质量约束
   - 先保证动态谱不是基线 / 归一化伪影

4. **G-T5 + G-T6**
   - 再补 cross peak 和带指数可信度
   - 这部分最接近用户真正会写进论文的解释

5. **G-T7**
   - 接 agent 调参
   - 让 agent 按 evidence 层逐级修，而不是自由发挥

6. **G-T8 + G-T9**
   - 最后补 GUI 和真实回归
   - 确保用户看得懂、测试守得住


## 6. 完成后的产品变化

完成番外阶段 G 后，二维 IR 页面应该从：

> 这组数据生成了热图、瀑布图、同步 / 异步 2D-COS 图。

升级为：

> 这组数据的序列轴可信 / 矩阵质量可接受 / 同步谱可解释 / 异步谱先后关系仍需谨慎 / top cross peaks 中有 6 个可归属、2 个仅供诊断。

也就是说，软件不只是“画出 2D-COS”，而是能告诉用户：

- 为什么这张 2D-COS 图可信
- 为什么某些交叉峰不能解释
- 哪些参数应该先修
- 哪些结论可以写进论文，哪些不能急着写


## 7. 我对二维 IR 这条线的判断

二维 IR 会成为 PolyNexus 里很有辨识度的功能，但它比普通 IR 更容易“图很好看、解释很危险”。

所以这一阶段最重要的不是追求更多图，而是建立一句话原则：

**先证明序列轴和动态矩阵可信，再解释同步 / 异步相关峰。**

agent 的角色也应该非常克制：

- 它可以建议修序列轴
- 可以建议修矩阵预处理
- 可以建议重新筛 cross peaks
- 可以组织 Noda 规则解释的证据

但它不应该在证据链不稳时替用户下最终机理结论。
