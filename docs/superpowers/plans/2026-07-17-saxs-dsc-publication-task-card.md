# SAXS + DSC 论文级图包联合任务卡

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 同时交付 SAXS（小角）和 DSC 的可直接用于 SCI 论文的 Main/SI/Diagnostics 图包，并确保每个图包都能被当前 V2/ChartEditor 编辑、保存、重发布和导出。

**Architecture:** 两种技术分别由自己的 FigureDefinition provider 负责科学图包编排；共享 publisher、manifest、gallery、audit 和编辑器生命周期负责落盘与复现。Main 只放论文主结论图，相关性/诊断类图转入 SI 或 Diagnostics；数据不足时必须显式回退为 `no_publication_ready_figure`，不得伪造 Main。

**Tech Stack:** Python、Matplotlib、FigureDefinition/V2 runtime、ChartEditor、JSON manifest、pytest、ruff。

---

## 任务范围与图包矩阵

### SAXS

- 静态/多样品：主图为 I(q)（必要时 I(q)·q² 或拟合/残差），多样品比较；SI 保留 Guinier、Kratky、Porod/IDF 和 correlation；Diagnostics 保留质量、拟合和可靠性证据。
- 变温/时间序列：主图为代表性 I(q) 或关键参数随温度/时间变化；SI 为 waterfall/heatmap/参数面板；Diagnostics 为帧级质量和证据状态。
- 原位拉伸：主图为代表性曲线或结构参数随应变变化；SI 为 waterfall/代表帧；Diagnostics 为应变标定、帧质量和不确定性。

### DSC

- 标准升降温：热流曲线、Tg/Tm/Tc 标记、结晶度/焓变化。
- 多样品比较：统一坐标和事件标记的跨样品主图，差异摘要放 SI。
- 等温结晶：转化率/Avrami 拟合主图（若证据充分），原始曲线和拟合残差放 SI/Diagnostics。
- 非等温动力学：conversion curves 与 Kissinger/动力学参数；孤立元数据不得晋升 Main。

## 实施任务

### Task 1: 建立 RED 验收基线

**Files:**
- Test: `tests/test_saxs_publication_pack_upgrade.py`
- Test: `tests/eval/test_dsc_publication_real_data.py`
- Test: `tests/test_saxs_dsc_publication_acceptance.py`

- [ ] 为 SAXS 三种模式和 DSC 四种模式写失败测试，断言 `publication_role`、`display_order`、`v2_runtime`、`audit_passed` 和失败回退原因。
- [ ] 为 manifest/gallery 顺序、编辑器对象编辑、reactive save/re-publish、失败回退和导出格式写联合测试。
- [ ] 串行运行新增测试，确认测试先因实现缺口失败。

### Task 2: 完成 SAXS 论文图包

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_provider.py`
- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/core/saxs_engine/saxs_output.py`（仅保留兼容/追溯路径）
- Test: `tests/test_saxs_publication_pack_upgrade.py`

- [ ] 为静态/多样品、变温/时间序列、原位拉伸分别生成 Main/SI/Diagnostics 定义。
- [ ] correlation 不得出现在默认 Main；在证据可用时保留为 SI/Diagnostics，并携带来源和质量状态。
- [ ] 所有定义只引用可移植数值快照，支持当前 V2/ChartEditor object editing。
- [ ] `paper_complete` 输出包含 Preview、SVG、PDF、600-dpi PNG 和 600-dpi TIFF；不完整数据返回明确的 no-publication-ready 状态。

### Task 3: 完成 DSC 论文图包

**Files:**
- Modify: `polynexus/core/dsc_engine/figure_standard.py`
- Modify: `polynexus/core/dsc_engine/figure_isothermal.py`
- Modify: `polynexus/core/dsc_engine/figure_nonisothermal.py`
- Modify: `polynexus/core/dsc_engine/figure_provider.py`
- Test: `tests/test_dsc_publication_standard_provider.py`
- Test: `tests/test_dsc_publication_isothermal_provider.py`
- Test: `tests/test_dsc_publication_nonisothermal_provider.py`

- [ ] 标准、等温、非等温模式分别执行证据门控；缺失 Main 证据时统一写入 `no_publication_ready_figure` 与 reason。
- [ ] 等温缺失 Avrami fit、非等温只有孤立 kinetics 元数据时生成 Diagnostics/回退，不错误晋升 Main。
- [ ] 保持 DSC `dsc_publication` profile 的完整资产输出和编辑器兼容。

### Task 4: 接通共享编辑器与发布生命周期

**Files:**
- Modify: 共享 figure publisher/manifest/gallery/audit 相关实现（按测试定位）
- Test: `tests/test_saxs_dsc_publication_acceptance.py`

- [ ] Main → SI → Diagnostics 排序稳定，角色和显示顺序写入 manifest。
- [ ] ChartEditor 能加载每个对象、修改样式/文本、保存 working revision 并重新 publish；旧发布保持不变。
- [ ] reactive runtime 和 legacy/ChartEditor 路径都能 republish，run-relative 数据路径可复现。
- [ ] 任一导出失败时保留上一版发布并返回可诊断错误。

### Task 5: 真实数据、质量门禁与交付

- [ ] 用仓库 SAXS/DSC 数据完成真实数据验收，检查 PNG/TIFF DPI、SVG/PDF 可读性和 manifest 完整性。
- [ ] 运行专项测试、`python scripts/quality_gate.py`、changed-file `ruff`、`git diff --check`。
- [ ] 更新验收记录，列出通过的测试数量、输出目录和任何仅限 Diagnostics 的证据。
- [ ] 仅在所有验收通过后将 goal 标记为 `complete`。

## 完成定义

- [ ] SAXS 和 DSC 的每种模式都有独立、可解释的 Main/SI/Diagnostics 图包。
- [ ] 默认 Main 不包含 correlation 或未经证据支持的动力学图；相关图仍可追溯。
- [ ] 所有图包在 V2/ChartEditor 中可编辑、可保存、可重发布，并生成 Preview/SVG/PDF/600-dpi PNG/TIFF。
- [ ] manifest、gallery、audit、失败回退和真实数据验收全部通过。

