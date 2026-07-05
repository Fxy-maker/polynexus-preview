# PolyNexus 番外阶段 C-T1 温变 SAXS 当前基线台账

## 1. 目标

先把这批 `无定形单个样品变温` 的真实状态冻结下来，作为后续修复的对照基线。

这一步不改算法，只回答三个问题：

1. 这批数据当前到底坏在哪。
2. 哪些结果还能当作稳定证据。
3. 哪些结果只是 fallback 或保守估计。


## 2. 样本范围

- 路径：`D:\PolyNexus\测试数据\saxs\无定形单个样品变温`
- 输出目录：`D:\PolyNexus\测试数据\saxs\无定形单个样品变温\polynexus_output`
- 帧数：`17`
- 帧文件：`Check-20260618_0_00002.edf` 到 `Check-20260618_0_00018.edf`


## 3. 当前基线摘要

### 3.1 轴与样本状态

- `condition_source = header`
- `condition_confidence = 0.9`
- 温度轴单调递增
- 说明条件轴恢复基本可信，不是当前主要问题

### 3.2 主要问题

- `quality_flag` 全批次一致为：
  - `ERROR:qstar_contaminated;WARN:mask_truncated`
- `validation_summary` 存在多个版本，但总体都指向：
  - 低 q 被污染
  - Guinier 区损失
  - invariant / correlation / IDF 不稳定
- `lc_method = calibrated`
- `lc_nm` 整批锁定在 `3.07`
- `lc_confidence` 出现保守化，但 batch 摘要会把它看起来写得很平

### 3.3 统计数字

- 帧数：`17`
- 温度范围：`-20.0` 到 `150.2`
- `L_nm` 范围：`6.62` 到 `9.02`
- `L_nm` 均值：`7.375`
- `lc_nm` 范围：`3.07` 到 `3.07`
- `lc_nm` 均值：`3.07`
- `Xc` 范围：`0.34` 到 `0.464`
- `Xc` 均值：`0.421`
- `lc_confidence` 范围：`0.2` 到 `0.5`
- `lc_confidence` 均值：`0.452`
- `L_confidence` 范围：`0.2` 到 `0.5`
- `L_confidence` 均值：`0.452`
- `q_peak_snr` 范围：`6.88` 到 `22.54`
- `q_peak_snr` 均值：`9.887`


## 4. 真实症状判断

这批样本当前最像下面这几类问题叠加：

1. `beamstop_or_low_q_contamination`
2. `gamma_tangent_unstable`
3. `multi_method_disagreement`
4. `idf_artifact_regular_spacing`

其中最核心的是第一条：

- 低 q 被污染
- 低 q 直接拖坏了 invariant / IDF / correlation 的可信度
- 后面的 `lc` 推导被迫退到校准型 fallback


## 5. 目录层面的证据

输出目录里现在能看到的状态是：

- `per_frame` 有 `17` 个帧目录
- `_LOW.pdf` 文件共 `51` 个
- 普通版 `02_correlation_function.pdf / 03_IDF.pdf / 04_porod_analysis.pdf` 几乎没有
- `summary` 目录里有 `5` 个总览图

这说明当前这批结果确实不是“没出图”，而是：

**出图了，但多数图仍然被判定为低置信。**


## 6. 代表帧快照

几个代表帧当前状态：

- `Check-20260618_0_00002.edf`
  - `T=-20.0`
  - `L=8.78`
  - `lc=3.07`
  - `lc_confidence=0.5`
  - `quality_flag=ERROR:qstar_contaminated;WARN:mask_truncated`
- `Check-20260618_0_00003.edf`
  - `T=0.9`
  - `L=8.34`
  - `lc=3.07`
  - `lc_confidence=0.5`
  - `quality_flag=ERROR:qstar_contaminated;WARN:mask_truncated`
- `Check-20260618_0_00004.edf`
  - `T=10.1`
  - `L=6.8`
  - `lc=3.07`
  - `lc_confidence=0.5`
  - `quality_flag=ERROR:qstar_contaminated;WARN:mask_truncated`
- `Check-20260618_0_00010.edf`
  - `T=70.1`
  - `L=6.86`
  - `lc=3.07`
  - `lc_confidence=0.5`
  - `quality_flag=ERROR:qstar_contaminated;WARN:mask_truncated`
- `Check-20260618_0_00017.edf`
  - `T=140.1`
  - `L=8.6`
  - `lc=3.07`
  - `lc_confidence=0.5`
  - `quality_flag=ERROR:qstar_contaminated;WARN:mask_truncated`
- `Check-20260618_0_00018.edf`
  - `T=150.2`
  - `L=9.02`
  - `lc=3.07`
  - `lc_confidence=0.5`
  - `quality_flag=ERROR:qstar_contaminated;WARN:mask_truncated`


## 7. 这份基线说明了什么

1. 这批样本不是“全坏”，因为 `L_nm` 还有变化。
2. 但这批样本也不是“已经稳定可信”，因为低 q 证据链明显不稳。
3. 当前 `lc_nm` 的整批恒定值更像是温变摘要 fallback，而不应直接被当成真实趋势。
4. 后续修复不应先追求“图变漂亮”，而应先让系统区分：
   - 真实测得值
   - fallback 校准值
   - 低置信证据


## 8. 后续接力方向

下一步应接着做：

1. 拆 `raw evidence` / `calibrated fallback`
2. 给低 q 污染和 fallback 冲突新增稳定症状
3. 让 orchestrator 先修低 q，再碰厚度链
4. 让 GUI 明确告诉用户当前可信和不可信的部分

这份台账是后面所有修复的参照点。


## 9. 回归验证记录

为了确认这份基线不是只在文档里冻结，我已经补跑了真实样本回归：

- `python -m tests.eval.runner --cases-dir tests/eval/cases/real`
- 结果：`15/15 PASS`
- 真实 SAXS 样本 `saxs_real_temperature_check_20260618`
  - `composite=1.000`
  - `phys=1.000`
  - `peak=1.000`
- `pytest tests/eval/test_runner_real_saxs.py tests/test_saxs_condition_recovery.py tests/eval/test_audit_reporter.py -q`
  - 通过

这次回归没有改变这份基线里记录的真实问题本身：

- 低 q 污染仍然存在
- `calibrated_fallback_active` 仍然是当前批次的关键语义
- `lc_nm` 的整批恒定值仍然说明 fallback 还在参与摘要

所以这份台账现在同时具备了两层意义：

1. 它冻结了当前真实问题
2. 它也证明现有代码链已经能把这批真实问题解释清楚
