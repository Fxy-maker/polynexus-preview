# PolyNexus full software development architecture design

## 1. Product boundary

PolyNexus 不是一组独立分析脚本，而是一条可追溯的科学工作流：输入数据经过
预处理和确定性分析，形成带 evidence/confidence 的结果；结果同时进入定制
Results Workbench 和统一 Figure lifecycle；用户从 Workbench、Gallery、Editor
和 Export 看到的是同一份 run/document/provenance 状态。

```text
Input/Preprocess
      -> AnalysisResult + Evidence
      -> Results Workbench Profile
      -> FigureDefinition/Document
      -> RunFigureManifest
      -> Gallery <-> ChartEditor
      -> Export/Report/Origin
      -> History/AI/Joint context
```

## 2. Shared contracts

### Analysis and evidence

科学模块只负责分析和输出既有物理量；`analysis_evidence*` 服务负责把质量、
置信度、限制、症状、建议和 cross-technique constraints 结构化。GUI 不推导
技术算法状态，只消费 DTO/view model。

### Results Workbench

Workbench 由统一壳层和技术 Profile 组成：

- shell：hero grid、主结果、支持证据、诊断、review hint、actions、figure links；
- profile：模式标题、hero 指标、primary/detail/diagnostic 字段、tab 命名、
  review actions、图包入口和空态/失败态；
- profile 不拥有科学计算，不复制 evidence gate；
- 每个 Profile 必须能把当前结果直接映射到 Figure Pack 和 Manifest 条目。

### Figure lifecycle

Technique provider 只产生 FigureDefinition；共享 pipeline 负责 validation、
FigureDocument、preview/publication assets、Manifest、capability、Gallery、
Editor 和 export。publication role 由 evidence 合同决定，显示顺序不能改变 role。

## 3. Technique profiles

| Technique | Main narrative | Support evidence | Diagnostics |
|---|---|---|---|
| SAXS static | comparison/sample structure | L/lc/phi_c, correlation/IDF | per-frame quality/low-q |
| SAXS temperature | evolution and transition | Avrami, condition trends, selected frames | missing axis/low confidence |
| SAXS strain | evolution and morphology | invariant, correlation, IDF, orientation, phase | full sequence, low-q, excluded frames |
| DSC standard | thermal events | integration/crystallinity | baseline/fit quality |
| DSC isothermal | X(t) crystallization | Avrami fit | fit range/quality |
| DSC non-isothermal | conversion and kinetics | Kissinger/Ozawa/Mo/Friedman | method disagreement |
| WAXS static | pattern/phase | size/orientation/assignment | 2D/image and peak diagnostics |
| WAXS temperature | phase/size transition | trend support and selected maps | invalid frames/axis |
| WAXS strain | orientation/phase/size | azimuthal and phase evidence | 2D detector diagnostics |
| IR standard | spectrum and bands | assignments/baseline | residual/noise |
| IR temperature-2D | spectral transition | band trend and map support | pixel/sequence validity |
| IR mapping | map and ROI | ROI spectra/assignment | invalid pixels |
| NMR liquid H/C | peaks and assignments | solvent/fit support | SNR/overlap/assignment |
| NMR solid H/C | phase and composition | crystallinity/coverage | broad line/weak assignment |
| Joint | cross-technique consistency | constraints and provenance | conflict/review |

## 4. Delivery rules

每个技术模式按照同一顺序交付：

1. 读取真实输入并确定 condition axis；
2. 锁定已有分析输出和 evidence schema；
3. 建立 Workbench Profile；
4. 建立 Main/SI/diagnostic Figure Pack；
5. 接入 Manifest/Gallery/Editor/export；
6. 添加 fallback、AI-off、AI-failure 和诊断路径；
7. 运行 focused tests、quality/type/boundary gates；
8. 用真实或 Golden fixture 做视觉和科学验收；
9. 记录 checkpoint、已知限制和下一模块入口。

## 5. Safety and review boundaries

- 不在 GUI 事件中重算科学状态；
- 不把诊断图或低置信度结果塞入 Main；
- 不让 AI 覆盖确定性结果或静默改变配置；
- 不让 Gallery、Editor、Export 各自解释 publication 状态；
- Joint 只报告一致性/冲突和 provenance，不替用户做科学裁决；
- 每个技术模块在 human scientific review 前不得宣称 release-ready。
