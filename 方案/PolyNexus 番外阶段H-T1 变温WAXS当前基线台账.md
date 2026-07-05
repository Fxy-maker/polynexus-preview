# PolyNexus 番外阶段 H-T1 变温 WAXS 当前基线台账

## 1. 基线对象

- 技术：`waxs.temperature`
- 样品目录：`D:\PolyNexus\测试数据\waxs\原位变温广角`
- 数据帧数：`6`
- 帧文件：
  - `PA6-250-170-W_0_00002.edf`
  - `PA6-250-185-W_0_00001.edf`
  - `PA6-250-195-W_0_00000.edf`
  - `PA6-250-205-W_0_00000.edf`
  - `PA6-250-220-W_0_00000.edf`
  - `PA6-250-W_0_00000.edf`

## 2. 当前序列摘要

| Temperature (C) | r_squared | Xc_pct (%) | D_Scherrer (nm) | n_peaks | residual_type | max_residual_region | physical_support_pass | paper_ready_candidate |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| 170 | 0.1076 | 0.1015 | 2.8180 | 6 | peak_count_underfit | 2theta=31.78 deg | False | False |
| 185 | 0.0940 | 0.0463 | 3.2567 | 8 | peak_count_underfit | 2theta=18.33 deg | False | False |
| 195 | -157.2838 | 0.1570 | 6.0301 | 3 | peak_count_underfit | 2theta=16.61 deg | False | False |
| 205 | 0.0213 | 0.1723 | 2.9075 | 6 | peak_count_underfit | 2theta=18.96 deg | False | False |
| 220 | -3.8717 | 0.1134 | 4.4417 | 5 | peak_count_underfit | 2theta=15.28 deg | False | False |
| 250 | 0.0441 | 0.0000 | 2.7126 | 6 | peak_count_underfit | 2theta=32.69 deg | False | False |

## 3. 当前趋势结论

- 温度轴本身是连续且单调的：`170 -> 185 -> 195 -> 205 -> 220 -> 250 C`
- `Xc_pct` 范围很小，基本落在 `0.0% ~ 0.17%`
- `D_Scherrer_nm` 波动明显，范围约 `2.71 ~ 6.03 nm`
- 峰数不稳定，`n_peaks` 在 `3 ~ 8` 之间跳动
- 所有帧当前残差都被判成 `peak_count_underfit`
- 当前没有检测到稳定转变点：`transitions = []`

## 4. 峰族与峰形状态

- 当前峰位追踪还不能算成稳定峰族追踪
- 峰位列表在各帧间变化明显，不能直接把第 1 个峰、第 2 个峰当作同一物理峰族
- 峰宽多数落在 `1.07 ~ 3.00 deg`
- 当前峰宽也不稳定，且多帧接近拟合上限
- 这说明目前更像“每帧各自找峰”，还不是“同一峰族的温度演化”

## 5. 残差与症状基线

当前每一帧的残差类型都一致：

- `peak_count_underfit`

当前常见症状包括：

- `peak_count_insufficient`
- `amorphous_partition_unstable`
- `crystallinity_without_peak_support`
- `size_without_multi_peak_support`
- `peak_count_underfit`

这意味着现阶段的主要问题不是单纯的 GUI 展示，而是：

1. 峰族支撑不够
2. 背景 / 非晶分离还不稳
3. `Xc` 和 `D` 还不能被当作稳定趋势直接解读

## 6. 当前 evidence 读法

按现有 `analysis_evidence` 链路看，这组数据会被解释为：

- `structure_support_score = 0.712`
- `physical_support_pass = False`
- `paper_ready_candidate = False`
- 当前结果应视为“诊断级结果”，不是“论文结论级结果”

## 7. GUI 应该怎么读

当前 GUI 对这组结果最合理的解释是：

- 温度轴可用
- waterfall 图可导出
- 单帧拟合存在
- 但峰支撑、背景分离和晶粒尺寸链条都还不够稳
- `Xc-T` 和 `D-T` 暂时只能作为诊断趋势
- 不应把当前结果直接理解为“已经可以写结论”

更直白一点：

> 图可以看，结论先别急着下。

## 8. 当前语义缺口

当前我在跑 `analysis_evidence` 时发现一个小但真实的语义缺口：

- 温变 WAXS 引擎输出的是 `n_peaks`
- `analysis_evidence` 的部分 WAXS 汇总逻辑还在偏向 `peak_count`

所以在现阶段：

- 引擎层已经知道“有多少峰”
- 证据层却还没有完全把这个字段吃进去

这不影响 H-T1 作为基线冻结，但会影响后续 H-T3 的 evidence 分层补强。

## 9. 当前冻结结论

这份基线可以直接作为后续对照尺：

- 如果后面修完后 `peak_count_underfit` 变少，说明峰家族真的稳了一些
- 如果 `Xc-T` 和 `D-T` 变平滑，但 `physical_support_pass` 仍然是 `False`，那只是图更顺眼，不代表更可信
- 如果后面出现新的转变点，必须同时给出峰族和趋势证据

