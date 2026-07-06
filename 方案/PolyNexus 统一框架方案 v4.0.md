# PolyNexus 统一框架方案

**版本**：v4.0
**日期**：2026-05-21
**状态**：设计稿
**定位**：PolyNexus 自包含统一框架总纲，替代此前分散的子方案体系。

---

## 目录

- [第一部分：公共基础设施](#第一部分公共基础设施)
  - §1 成熟数据栈绑定策略
  - §2 全局 SCI 输出规范
  - §3 统一导出管道
- [第二部分：各技术完整框架](#第二部分各技术完整框架)
  - §4 DSC — 差示扫描量热
  - §5 SAXS — 小角 X 射线散射
  - §6 WAXS — 广角 X 射线散射
  - §7 IR — 红外光谱
  - §8 ssNMR — 固体核磁共振
- [第三部分：交叉验证与精准度保障](#第三部分交叉验证与精准度保障)
  - §9 关键参数多技术校验矩阵
  - §10 自动校验与质量标记
- [附录](#附录)
  - A. L3 自研模块清单
  - B. 聚合物参考数据库

---

# 第一部分：公共基础设施

---

## §1 成熟数据栈绑定策略

### 1.1 核心原则

PolyNexus 的数据处理内核必须绑定成熟库。自研代码只做胶水层——参数编排、技术组合、交叉验证、统一导出。不准在核心算法层面"手搓"。

**为什么**：聚合物的数据处理链路长、数学复杂。自己实现基线校正、峰拟合、散射模型，既重复造轮子，又难以保证精度受审稿人认可。

### 1.2 三级合规性体系

每个数据处理步骤，按其对成熟库的依赖程度，标记为 L1 / L2 / L3：

| 级别 | 定义 | 示例 | 要求 |
|------|------|------|------|
| **L1 — 成熟库直接覆盖** | 成熟库原生 API 即可完成，无需适配 | pyFAI 积分、sasmodels 单模型拟合、lmfit 参数精修 | 直接调用，不封装逻辑 |
| **L2 — 成熟库 + 胶水层** | 库负责核心数学，胶水层做编排与组合 | sasmodels 模型组合（lamellar+ellipsoid 混合）、scipy.signal 信号预处理 | 不碰模型数学实现，只做编排 |
| **L3 — 自研模块** | 无合适成熟库，必须自研 | 非晶散射包络线分离（WAXS）、微纤化阶段识别（SAXS）、DSC 多步转变基线 | **必须标注 + 必须交叉验证** |

### 1.3 全局库清单与职责边界

#### 数据处理核心

| 库 | 版本建议 | 负责范围 | 红线（禁止手搓） |
|---|---|---|---|
| **pyFAI** | >=2024.x | 2D->1D 方位角积分、几何校正（.poni）、掩膜处理 | 积分算法、poni 校正逻辑 |
| **sasmodels** | >=1.0.7 | SAXS/WAXS 散射模型拟合 | 所有模型数学实现 |
| **lmfit** | >=1.2 | 全技术峰拟合、参数精修、约束优化 | 拟合引擎、参数不确定度估计 |
| **calospy** | >=0.3 | DSC 多格式文件读取、基线校正 | 文件解析、基线算法 |
| **scipy.signal** | >=1.11 | 信号滤波（Savitzky-Golay）、峰搜索、小波 | 辅助工具，不替代核心算法 |
| **numpy** | >=1.24 | 所有数值计算基础设施 | — |
| **xarray** | >=2023.x | 多维序列数据管理 | — |
| **fabio** | >=2023.x | 多格式探测器图像读取 | — |

#### DFT 计算（IR / NMR）

| 软件 | 许可 | 负责范围 | 红线 |
|---|---|---|---|
| **CASTEP** | 学术免费 | GIPAW-NMR、DFPT-IR、声子谱 | 所有 DFT 计算 |
| **Quantum ESPRESSO** | 开源 | GIPAW 开源实现、DFPT | 同上 |
| **ORCA 5** | 学术免费 | 高精度簇模型 DFT | 同上 |
| **Gaussian 16** | 商业 | 簇模型 GIAO-NMR、频率计算 | 同上 |
| **VASP** | 商业 | AIMD、周期性优化 | 同上 |
| **CP2K** | 开源 | AIMD + 偶极矩计算 | 同上 |
| **xTB** | 开源 | GFN2-xTB 快速筛选 | — |

#### 分子动力学

| 软件 | 许可 | 负责范围 |
|---|---|---|
| **GROMACS** | 开源 | 经典 MD、无定形构建 |
| **LAMMPS** | 开源 | ReaxFF-MD、交联体系 |
| **Packmol** | 开源 | 无定形胞构建 |

#### 可视化与导出

| 库 | 负责范围 |
|---|---|
| **matplotlib** | 所有图表（通过 sci_style 封装） |
| **seaborn** | 高级统计图辅助 |
| **pandas** | 参数表整理、CSV 导出 |

### 1.4 胶水层代码规范

```python
# 每个技术引擎的接口：load() -> preprocess() -> analyze() -> plot()
class MyEngine(BaseEngine):
    def load(self, filepath) -> Dataset:
        """L1/L2: 调用 fabio/calospy + xarray 封装"""
    def preprocess(self) -> ProcessedData:
        """L1/L2: 调用 pyFAI/scipy，L3 自研算法"""
    def analyze(self) -> ParameterSet:
        """L1/L2/L3: 调用 sasmodels/lmfit + 自研模块"""
    def plot(self, output_dir) -> list[Path]:
        """L1: 调用 matplotlib via sci_style"""
```

胶水层原则：
- 不在 `load()` 里手写文件解析器（用 fabio / calospy）
- 不在 `analyze()` 里手写拟合引擎（用 lmfit）
- 不在 `plot()` 里直接调 matplotlib（通过 sci_style 封装）
- L3 模块的输出必须带验证标记

### 1.5 L3 自研模块管控

任何标记为 L3 的模块，必须在代码中满足：
1. 文件头注释 `# L3_SELFBUILT: <原因>`
2. `analyze()` 返回的 ParameterSet 中包含 `_validation_status` 字段
3. 其输出参数必须在 §9 交叉验证矩阵中有对应校验路径

详单见附录 A。

---

## §2 全局 SCI 输出规范

> 实现文件：`polynexus/plotting/sci_style.py`
> 所有技术图表的唯一出口，不准绕过此模块直接调 matplotlib。
> 
> **v3.0 更新 (2026-06)**: 新增灰度色板、期刊预设尺寸、面板标签助手、拼图组合工具、
> SVG 文本可编辑导出。所有技术引擎的 `*_output.py` 中的 `set_sci_style`、`SCI_COLORS`、
> `_save_figure` 均改为从中心模块导入，消除碎片化。

### 2.1 配色方案

**序列数据（多条曲线）— Wong 色盲友好色板（8色）：**

```python
WONG_COLORS = [
    '#000000',  # 黑
    '#E69F00',  # 橙
    '#56B4E9',  # 天蓝
    '#009E73',  # 绿
    '#F0E442',  # 黄
    '#0072B2',  # 蓝
    '#D55E00',  # 红橙
    '#CC79A7',  # 紫红
]
```

**灰度色板 — 用于不允许彩色的期刊（如某些印刷版）：**

```python
GRAYSCALE_PALETTE = ['#000000', '#333333', '#666666', '#999999', '#BBBBBB', '#DDDDDD']
```

**热图配色**：强度热图 `'viridis'`、参数变化 `'RdBu_r'`、结晶度 `'plasma'`

**标注颜色**：峰位 `'#E63946'`（红）、基线 `'#457B9D'`（蓝）、分界线 `'#2D6A4F'`（深绿虚线）

### 2.2 画布尺寸与期刊预设

| 布局 | 宽度 (cm) | 高度 (cm) | 英寸 | 场景 |
|------|-----------|-----------|------|------|
| 单栏单图 | 8.5 | 6.5 | 3.35x2.56 | 单条曲线 |
| 单栏双图 | 8.5 | 13 | 3.35x5.12 | 上下对比 |
| 双栏单图 | 17.5 | 6.5 | 6.89x2.56 | 宽幅热图 |
| 双栏 2x2 | 17.5 | 13 | 6.89x5.12 | 最常用 |
| 双栏 2x3 | 17.5 | 19.5 | 6.89x7.68 | 多参数组合 |

**期刊预设尺寸**（使用 `JOURNAL_PRESETS` 字典一键切换）：

| 期刊 | 单栏(in) | 双栏(in) | 推荐导出格式 |
|------|----------|----------|-------------|
| ACS (Macromolecules) | 3.33 x 2.50 | 6.85 x 2.50 | PDF + TIFF |
| RSC (Polymer Chem) | 3.35 x 2.56 | 6.89 x 2.56 | PDF + PNG |
| Wiley (Macromol Rapid Comm) | 3.54 x 2.56 | 7.09 x 2.56 | PDF + TIFF |
| Nature (Nat Commun) | 3.35 x 2.50 | 6.89 x 2.50 | PDF + PNG |

```python
from polynexus.plotting.sci_style import JOURNAL_PRESETS
figsize = JOURNAL_PRESETS['acs']['double_2x2']  # (6.85, 5.00)
```

### 2.3 字体规范

| 元素 | 字号 | 字体 | 样式 |
|------|------|------|------|
| 坐标轴标签 | 9 pt | Arial | 加粗 |
| 刻度标签 | 8 pt | Arial | 正常 |
| 图例文字 | 8 pt | Arial | 正常 |
| 图内标注 | 8 pt | Arial | 正常 |
| 面板标签 (a)(b) | 10 pt | Arial | 加粗 |
| SVG 输出 | — | Arial | 文本保留为可编辑 `<text>` 元素 |

### 2.4 SCI Figure 核心规范

**绝对禁止：**
- ❌ 图中出现描述性大标题（如 "DSC Thermogram — Sample X"、"Scattering Profile"）
  → 标题只能出现在论文的图注（caption）中，不在图内
- ❌ 图中出现中文字符
  → 所有文本必须为英文或 LaTeX 数学符号
- ❌ 各引擎使用自己的 `SCI_COLORS`/`set_sci_style` 副本
  → 只能通过 `polynexus/plotting/sci_style.py` 统一管理

**必须做到：**
- ✅ 所有图调用 `set_sci_style()` 统一风格
- ✅ SVG 输出保持文本为可编辑 `<text>` 元素（`svg.fonttype='none'`）
- ✅ 多面板图使用 `apply_panel_label()` 添加 `(a)`/`(b)` 标签
- ✅ 保存时同时输出 PDF（矢量，投稿）和 PNG（预览）

### 2.5 面板标签与拼图

**单面板标签：** 使用 `apply_panel_label(ax, '(a)')` 在左上角添加标签，
不占用 `set_title`/`suptitle`。

```python
from polynexus.plotting.sci_style import apply_panel_label

fig, ax = plt.subplots()
ax.plot(x, y)
apply_panel_label(ax, '(a)')  # 左上角显示 (a)
```

**多面板组合图：** 使用 `make_composite_figure()` 将多个独立 Figure
拼接到统一画布上：

```python
from polynexus.plotting.sci_style import make_composite_figure

panels = [
    (fig_crystallinity, 'Crystallinity', None),
    (fig_avrami, 'Avrami Plot', None),
]
composite = make_composite_figure(panels, layout='double_col_2x2',
                                  panel_labels=True)
composite.savefig('composite.pdf', dpi=300, bbox_inches='tight')
```

### 2.6 坐标轴通用规范

```python
ax.tick_params(direction='in', top=True, right=True, length=3, width=0.8)
ax.spines[:].set_linewidth(0.8)
# 注意：已有 set_sci_style() 全局配置，一般不需要单独调
```

### 2.7 轴标签字典（LaTeX 格式）

```python
AXIS_LABELS = {
    "q":           r"$q$ (nm$^{-1}$)",
    "I":           r"$I$ (a.u.)",
    "T":           r"Temperature ($^\circ$C)",
    "strain":      r"Strain $\varepsilon$ (\%)",
    "HF_Wg":       r"Heat Flow (W/g)",
    "L":           r"$L$ (nm)",
    "lc":          r"$l_c$ (nm)",
    "phi_c":       r"$\phi_c$",
    "2theta":      r"$2\theta$ ($^\circ$)",
    "D_hkl":       r"$D_{hkl}$ (nm)",
    "wavenumber":  r"Wavenumber (cm$^{-1}$)",
    "chem_shift":  r"$\delta$ (ppm)",
}
```

### 2.8 质量标记

```python
QUALITY_FLAGS = {
    "OK":          {"symbol": "🟢", "label": "Passed"},
    "WARN":        {"symbol": "🟡", "label": "Review"},
    "ERROR":       {"symbol": "🔴", "label": "Failed"},
    "ESTIMATED":   {"symbol": "🔵", "label": "Estimated"},
    "LOW_SNR":     {"symbol": "⚠️",  "label": "Low SNR"},
    "INTERPOLATED":{"symbol": "🔶", "label": "Interpolated"},
    "CALIBRATED":  {"symbol": "✅", "label": "Calibrated"},
}
```

### 2.9 SCI 投稿清单

投稿前对照检查每张图：

- [x] 图中无描述性大标题（`audit_figure_sci()` 检查 figure / axes title）
- [x] 图中无中文（`audit_figure_sci()` 检查 CJK 文本）
- [x] 配色通过色盲测试（`audit_figure_sci()` 限定 Wong / grayscale palette）
- [x] 字号 ≥ 8 pt（`audit_figure_sci()` 检查可见文本字号）
- [x] 输出为 PDF（矢量） + TIFF/PNG（位图）（`audit_figure_sci()` 检查导出格式组合）
- [x] 面板标签 (a)(b) 统一左上角，加粗（`apply_panel_label()` + `audit_figure_sci()` 覆盖）
- [x] 线宽 ≥ 0.8 pt（`audit_figure_sci()` 检查 line width）
- [x] 所有轴有标签，使用 AXIS_LABELS 标准化名称（`audit_figure_sci()` 检查空标签和标准标签）
- [x] 图注位置不遮挡数据（`audit_figure_sci()` 标记中央数据区自由注释风险；最终投稿前仍需人工视觉复核）

自动审计入口：`polynexus.plotting.audit_figure_sci()`；覆盖测试：`tests/test_figure_audit.py`。

### 2.10 参考期刊绘图规范

PolyNexus 的绘图规范参考了以下高水平期刊的惯例（均为高分子及相关领域顶级期刊）：

| 期刊 | 影响因子 | 参考要点 |
|------|---------|----------|
| **Macromolecules** (ACS) | ~6 | 双栏图 17.8 cm 宽；面板标签 (a)(b) 左上角；8pt 刻度/10pt 轴标；线宽 1-1.5pt；无图内标题 |
| **ACS Macro Letters** | ~7 | 同 Macromolecules，颜色使用更克制（黑/红/蓝/绿顺序） |
| **Macromolecular Rapid Communications** (Wiley) | ~5 | 单栏 9 cm；支持更紧凑布局；热图使用 thermal colormap |
| **Polymer Chemistry** (RSC) | ~5 | RSC 模板 8.5 cm/17.5 cm；偏好 PDF+PNG 导出 |
| **Nature Communications** | ~16 | 更高 DPI 要求（300-600）；面板间距更宽 |

**核心共识（所有期刊一致）：**
1. 图中**没有**描述性标题（仅 panel label）
2. 所有文本必须可编辑（SVG 保留 `<text>`，PDF 保留字体）
3. 多曲线图使用色盲友好色板（Wong palette 满足此要求）
4. 面板标签加粗、左上角、8-10pt
5. 数据曲线无标记（marker-less），仅用颜色/线型区分
6. 坐标轴刻度向内（tick direction='in'），顶部和右侧保留轴线

---

## §3 统一导出管道

> 实现文件：`polynexus/export/__init__.py`

### 3.1 数据模型

```python
@dataclass
class ExportRow:
    sample_id: str
    technique: str          # dsc / saxs / waxs / ir / nmr
    submodule: str          # static / in_situ_strain / in_situ_temp
    condition: str          # T=120C / epsilon=50%
    quality: str            # OK / WARN / ERROR
    parameters: dict        # {param: {value, unit, uncertainty}}
```

### 3.2 导出函数

```python
# 每个技术输出同一格式的 CSV
def export_parameters_csv(rows: list[ExportRow], output_path: Path) -> Path

# 自动生成 Markdown 分析报告
def generate_tech_report(rows: list[ExportRow], output_path: Path) -> Path

# 多技术联合导出
def sci_export_joint(all_rows: dict[str, list[ExportRow]], base_dir: Path) -> dict
```

### 3.3 输出目录结构（所有技术共用）

```
output/
├── raw_{technique}/          # 原始数据副本
├── parameters/
│   └── {technique}_Results_All.csv
├── figures/
│   ├── main/                 # 正文用（P1 优先级）
│   └── SI/                   # 补充材料（P2/P3）
├── plot_edits.json           # GUI 图表编辑状态（按 figures 相对路径索引）
└── report/
    └── analysis_report.md
```

### 3.4 图表预览与编辑工作台（2026-06-01 已接入）

> 实现文件：`polynexus/gui/widgets/chart_viewer.py`、`polynexus/gui/widgets/chart_editor.py`、`polynexus/core/plot_edits.py`

图表页不再只是缩略图列表，而采用“缩略图选择 -> 大图预览 -> 当前图编辑”的工作台模型。

**交互规范：**
- 单击缩略图：在图表页内显示当前图大预览。
- 双击缩略图：打开独立图表查看器。
- 图库递归发现 `figures/`、`summary/`、`per_frame/` 下的 SVG/PNG/JPG/PDF，覆盖 SAXS 多级输出结构。
- 大预览支持 SVG、PNG/JPG、PDF 首页渲染，并提供适应窗口、100%、缩放、刷新、打开文件、打开目录。
- “编辑此图”必须绑定当前选中的导出图，编辑器保存后立即刷新大预览和缩略图。

**2026-06-02 交互修订：成品图与实时曲线分离**
- 选中缩略图后，大预览必须立即加载同一张导出图；预览控件在显示和载入后补一次延迟适配，避免视口尺寸未稳定导致首屏看起来为空。
- 大预览按钮改为“编辑成品图”，只打开当前选中 SVG/PNG/PDF/JPG 的成品图设置窗口；窗口标题、左侧预览、保存目标必须全部指向同一个文件。
- 成品图设置窗口不再复用实时曲线画布重画未知曲线，而是直接显示所选文件，右侧仅保存该文件的标题、轴标签、配色、字体、网格等 `plot_edits.json` 重绘设置。
- 下方工具栏不再提供实时曲线编辑入口；该方向已在 2026-06-03 删除，避免和成品图查看/编辑主流程混淆。
- 保存成品图设置后，若当前分析 engine 有缓存，则自动触发“仅重新绘图”应用设置；没有缓存时保留 sidecar，并明确提示用户手动重新绘图后生效。
- 重新绘图或刷新图库后，优先保持用户当前选中的图（如 Fig-D3），不得无故跳回第一张图。

**2026-06-02 后续修订：图库优先工作流**
- 图表页默认状态必须是“成品图图库”，不显示灰色大预览框，也不嵌入实时曲线编辑区；所有导出图以较大的真实缩略图卡片展示。
- 单击图卡或“查看”按钮后，才在图库上方打开聚焦预览框；聚焦预览必须提供“关闭预览”，关闭后回到纯图库视图。
- 图卡的“编辑”按钮直接打开当前成品图设置窗口，不强行展开聚焦预览；只有聚焦预览已打开时，保存后才刷新该预览。
- 2026-06-03 决策：删除“原始实时曲线”GUI 功能。PolyNexus 当前定位是处理已采集完成的数据，不承担在线实验监控职责；图表页只保留成品图图库、聚焦预览、独立成品图查看和成品图设置。

**2026-06-02 稳定性与命名修订**
- 图表图库、聚焦预览和 SVG 渲染不得使用 `QGraphicsDropShadowEffect` / `QGraphicsOpacityEffect` 动画；这些效果会触发 Qt 在绘制中抓取控件 pixmap，容易产生 `QPainter::begin`、`Painter not active` 等警告。
- SVG 缩略图和大图渲染必须使用显式 `QPainter.begin()` / `end()`，并用 `try/finally` 保证 painter 正常释放。
- 聚焦预览内必须提供“独立查看”，打开的窗口与灰框使用同一个导出文件路径，确保显示内容一致。
- 已删除 `LivePlotCanvas` / `QuickEditPanel` 入口和组件；不得再新增 raw-data live viewer 按钮，以免与成品图预览/编辑主流程混淆。
- 聚焦预览区域需要设置明确最小高度，默认不低于 460 px，内部图像视图不低于 360 px，保证用户能看清全图。

**2026-06-03 结果展示与文字稳定性修订**
- 图表卡片、聚焦预览和工具按钮中的中文文案必须使用稳定 Unicode 字符串，避免文件编码被重写后出现乱码。
- 结果表不得对宽结果集使用 `QHeaderView.Stretch` 强行挤压所有列；当列数较多时必须切换为 `Interactive` 列宽、启用横向滚动，并给单元格设置完整值 tooltip。
- 少量列结果仍可铺满可用区域；两列 key-value 结果保持参数列按内容自适应、值列拉伸。

**编辑与持久化：**
- `ChartEditor` 支持标题、X/Y 标签、配色、字号、线宽、画布尺寸、网格透明度、背景色。
- 保存到当前图会写回目标 SVG/PNG/PDF/JPG；另存为会生成新的导出图。
- 每次保存同步写入 `plot_edits.json`，结构如下：

```json
{
  "version": 1,
  "files": {
    "figures/Fig-W1_profile.svg": {
      "relative_path": "figures/Fig-W1_profile.svg",
      "source_path": "D:/.../figures/Fig-W1_profile.svg",
      "updated_at": "2026-06-01T12:00:00",
      "style": {
        "title": "WAXS Profile",
        "xlabel": "2θ (deg)",
        "ylabel": "Intensity (a.u.)",
        "colour_scheme": "Default Blue",
        "font": "Medium",
        "line_width": "Normal",
        "figure_size": "Medium (6in)",
        "grid_on": true,
        "grid_alpha": 0.2,
        "bg_color": "#FFFFFF",
        "dpi": 150
      }
    }
  }
}
```

**数据流约束：**
- `BaseEngine.run_pipeline()` 必须把 `plot()` 返回的 figure 路径写入 `AnalysisResult.figures`，供 GUI 建立当前图上下文。
- GUI 分析完成后缓存当前技术 engine；“仅重新绘图”优先复用缓存 engine，只运行 `plot()`，无缓存时回退为完整分析。
- 图表编辑状态是非破坏式元数据；输出模块以 `plot_edits.json` 为唯一持久化来源，重绘时自动应用同名图的样式覆盖。
- 对无法从当前分析结果重建的复杂成品图，编辑器仍允许另存当前编辑图，但必须保留原始导出文件和 sidecar 状态，避免丢失分析可追溯性。

**重绘接入范围：**
- `core/plot_edits.py` 在 `savefig` 前应用标题、坐标轴、配色、字号、线宽、画布尺寸、网格和背景色。
- 已接入 DSC、WAXS、WAXS temperature、WAXS multiscale、IR、NMR、SAXS、Joint 输出模块。
- 输出模块不得绕过 `savefig_with_edits()` 保存投稿图；新增图表类型必须走该入口或等价包装。

### 3.5 raw_data 内部诊断数据契约（2026-06-03 GUI 实时预览已删除）

> 实现文件：`polynexus/gui/main_window.py`、`polynexus/core/dsc.py`、`polynexus/core/ir.py`、`polynexus/core/nmr.py`

GUI 不再提供实时曲线查看器。`AnalysisResult.raw_data` 仅作为内部诊断、后续报告扩展和兼容旧结果对象的可选字段，不参与图表页主交互。

**核心契约：**
- 技术引擎可在 `analyze()` 完成后将诊断曲线写入 `AnalysisResult.raw_data`，但 GUI 主流程不得依赖该字段。
- GUI 图表页只消费导出的成品图文件；不得再从 `raw_data` 生成 live canvas 预览。
- 如果当前分析没有可导出的成品图，GUI 应显示图表空状态，并引导用户重新绘图或检查输出模块。

**当前 raw_data 字段：**

| 技术 / 子模块 | 必填字段 | 预览曲线 | 备注 |
|---|---|---|---|
| DSC standard | `mode="thermogram"`, `temperature`, `heat_flow` | Temperature - Heat Flow | 可选 `time_min`, `label` |
| DSC isothermal | `mode="isothermal_kinetics"`, `time_min`, `relative_crystallinity` | Time - X(t) | 可选 `relative_crystallinity_fit` 显示 Avrami 拟合线 |
| IR | `wavenumber`, `absorbance` | Wavenumber - Absorbance | GUI 可按需要反向坐标轴 |
| NMR | `ppm`, `intensity` | Chemical Shift - Intensity | GUI 可按需要反向坐标轴 |
| SAXS | `q`, `I` | q - I(q) | 由 SAXS engine 写入 |
| WAXS | `two_theta`, `I` | 2θ - Intensity | 由 WAXS engine 写入 |

**批处理与序列分析边界：**
- 普通 batch：多个独立样品，结果表逐文件汇总；图表页展示输出目录中的成品图。
- 序列分析：同一实验序列必须作为一个 engine run 处理，不能拆成普通 batch，否则动力学、变温、拉伸等跨文件参数会丢失。
- 当前必须走序列分析的输入：`saxs` 目录、`waxs` 目录、`dsc.isothermal` 目录、`dsc.nonisothermal` 目录。

---

# 第二部分：各技术完整框架

---

## §4 DSC — 差示扫描量热 🟢 EXPERIMENTAL

### 4.0 技术定位

**回答**：从热流曲线提取热力学参数——Tg、Tm、Tc、ΔHf、φc_DSC。

**方向**：仪器数据 -> 热力学参数。纯实验驱动。

**交叉验证**：φc 三重验证（DSC/WAXS/SAXS）；Tm 与 SAXS Gibbs-Thomson 反推对比。

### 4.1 数据处理链路总览

```
DSC 仪器文件 (.001/.ngb/.csv)
        │
        ▼  [L1] calospy 读取 -> 标准化 DataFrame
        │
        ▼  [L2] scipy 预处理 -> 基线校正 + 平滑
        │        [L3] 多步转变基线（scipy 辅助）
        ▼
   [L2] scipy find_peaks -> 峰识别
        │
        ▼  [L1] lmfit -> 峰面积积分 / 转变温度提取
        │
        ▼  参数集：Tg, Tm, Tc, ΔHf, φc_DSC
        │
        ▼  [L1] matplotlib (via sci_style) -> SCI 图
```

### 4.2 数据输入

| 格式 | 仪器 | L级 | 使用库 |
|------|------|-----|--------|
| .001/.txt | TA Instruments | L1 | calospy |
| .ngb/.ngt | Netzsch | L1 | calospy |
| .csv | 通用导出 | L2 | pandas |
| .mdt | Mettler Toledo | L1 | calospy |
| 序列文件夹 | 等温/非等温 | L2 | calospy + xarray |

**列名标准化**：系统内部统一使用 `T_C, HF_mW, HF_Wg, t_min`，"放热为正"（IUPAC）。

**GUI 调度约束**：`dsc.isothermal` 与 `dsc.nonisothermal` 的目录输入必须作为一个序列 engine run 传入 `DSCEngine.load_project()`，不得拆成普通 `BatchWorker` 逐文件运行。普通 batch 表示多个独立样品；动力学目录表示一个跨文件/跨程序段实验序列，两者语义不同。

### 4.3 预处理

| 步骤 | L级 | 使用库 | 调用示例 |
|------|-----|--------|----------|
| 温度/热焓校正 | L3 | 自研 | 标准品（In/Sn/Zn）线性校正 |
| 基线选择 | L2 | scipy | 线性/S形/切线/积分基线 |
| S形基线拟合 | L3 | scipy辅助 | BL(T) = HF_start + (HF_end-HF_start) x 累积积分比 |
| 平滑 | L1 | scipy.signal.savgol_filter | `savgol_filter(HF, window, 3)` |
| 基线端点检测 | L2 | scipy | 二阶导数稳定区 |

### 4.4 核心计算

#### 转变温度

| 参数 | 方法 | L级 | 调用 |
|------|------|-----|------|
| Tg | 切线交点/半高法 | L2 | scipy 线性拟合 |
| Tm/Tc | 峰顶温度 | L2 | `scipy.signal.find_peaks -> argmax` |

#### 热焓与结晶度

```python
# L2: 数值积分
ΔHf = np.trapz(HF_Wg[peak_start:peak_end], T[peak_start:peak_end])

# φc_DSC = ΔHf / ΔHf_100% x 100%
# ΔHf_100% 见附录 B
```

#### 结晶动力学（等温实验）

```python
# Avrami: Xc(t) = 1 - exp(-kt^n)
# L1: scipy.optimize.curve_fit / lmfit
```

Avrami n：~1 一维棒状 / ~2 二维盘状 / ~3 三维球晶（均相）/ ~4 异相成核。

#### Ozawa 方法（非等温）

```python
# L1: lmfit 线性回归
# ln[-ln(1-Xc)] vs ln(β), slope = -n
```

### 4.4.1 标准 DSC 物理引擎补充

本节补充标准 DSC 子模块的实现约束，作为后续等温/非等温 DSC 的公共前置层。

| 模块 | L级 | 实现要求 | 质量控制 |
|------|-----|----------|----------|
| 仪器程序段切分 | L3 | 对连续 heat-cool-heat 表格按温度方向自动切分为 monotonic scan；每段单独预处理和分析 | 禁止在混合升温/降温曲线上直接识别 Tg/Tm/Tc |
| 热流方向归一 | L3 | 读取阶段统一为 exotherm-up；优先读取仪器元数据，缺失时用高温熔融峰符号判定 | 若高温主熔融峰为正且显著强于负峰，标记并翻转 |
| 局部物理基线 | L2/L3 | 峰识别后用局部端点线性基线积分；端点来自峰宽/显著性并避开程序段边界 | 输出 onset/peak/end/ΔH，同时记录 peak width 与 prominence |
| 焓积分方向 | L2 | 对升温和降温均按 \|dT\| 积分，避免降温曲线因 x 轴递减产生假负号 | 在 exotherm-up 约定下，冷却结晶 ΔHc 输出为正值 |
| 事件分类 | L3 | 升温段：负峰=melting，Tm 前正峰=cold crystallisation，Tm 附近/之后正峰=recrystallisation；降温段：正峰=crystallisation | 起止温度 5°C 内的边界瞬态不参与 Tcc/Tc |
| Excel .xls 支持 | L1 | 标准 DSC 格式二依赖 `xlrd>=2.0.1`；`.xlsx` 继续使用 `openpyxl`；TA TRIOS 多 sheet 导出（首 sheet=元数据，后续=程序段）自动识别 [时间, 温度, 热流] 列序 | 缺失依赖时给出明确安装提示 |
| 熔融峰宽约束 | L2 | 聚合物在 10 K/min 下熔融峰宽通常 ≤ 50°C；超过此宽度的峰自动排除（可能为基线漂移或伪峰） | 输出 quality=WARN，排除出峰列表 |
| 多峰反卷积验证 | L2/L3 | 高斯反卷积后各分量中心 μ 必须在 [T_min-10, T_max+10] 范围内；分量占比 < 1% 自动丢弃 | 越界分量不写入 peak_components 也不参与 Fig-D6 |

新增配置项：`auto_segment_program`、`min_segment_points`、`min_segment_delta_T`、`peak_prominence_ratio`、`min_event_enthalpy_Jg`、`cold_cryst_max_margin_C`、`edge_event_margin_C`、`max_melting_peak_width_C`、`Tg_search_low_C`、`Tg_search_high_C`。

### 4.4.2 等温结晶动力学物理引擎补充

等温结晶动力学不直接使用整条 DSC 程序曲线，而是先从仪器程序中抽取“冷却到目标结晶温度后的温度稳定保持段”。

| 模块 | L级 | 实现要求 | 质量控制 |
|------|-----|----------|----------|
| 等温保持段检测 | L3 | 根据 `dT/dt`、温度波动范围和持续时间识别 quasi-isothermal hold；支持一个文件内多个结晶温度循环 | 默认最短 1 min，温度波动 ≤0.35°C，漂移 ≤0.12°C/min |
| 冷却后保持段筛选 | L3 | 对 heat-cool-hold-heat 程序，只把冷却段中的保持平台送入 Avrami；熔融高温保持段不参与 | 若没有冷却段，则回退到全部等温段并标记质量 |
| 热流基线与方向 | L2/L3 | 用保持段尾部估计基线；自动判断放热峰正负并归一为正放热信号 | 输出 `event_starts_at_segment_boundary` / `event_ends_at_segment_boundary` 标记 |
| 相对结晶度 | L2 | `X(t)=∫q_exo(t)dt / ∫q_exo(t)dt_total`；热流单位 W/g 时，焓值按 `60*∫HF dt_min` 转为 J/g | 要求积分面积大于最小焓阈值 |
| Avrami 拟合 | L2 | `ln[-ln(1-X)] = ln k + n ln t`，默认拟合 1%~99% 结晶区间并排除 `t=0` | 输出 n、k、log10(k)、t1/2、R²、T_iso、ΔHc_iso |

新增配置项：`isothermal_min_duration_min`、`isothermal_temp_tolerance_C`、`isothermal_max_drift_C_per_min`、`isothermal_min_enthalpy_Jg`。

**可选 raw_data 输出**：等温动力学完成后，可将诊断曲线写入 `AnalysisResult.raw_data`：

```python
{
    "mode": "isothermal_kinetics",
    "time_min": avrami.t_data,
    "relative_crystallinity": avrami.Xt_data,
    "relative_crystallinity_fit": avrami.Xt_fit,  # 可选
    "temperature_C": avrami.temperature_C,
    "label": avrami.label,
}
```

GUI 不再直接显示该 raw_data；等温动力学的用户可见图表以导出的成品图为准。

### 4.4.3 非等温结晶动力学物理引擎补充

非等温结晶动力学按“多冷却速率序列”处理，不直接在整条 heat-cool-hold-heat 程序上回归。输入文件夹允许包含 `.xls/.xlsx/.csv/.txt/.001` 等多文件；若文件名末尾包含速率（例如 `FDW-SLM-80%-30-2.5.xls`），优先把末尾数字作为冷却速率，避免仪器导出的瞬时斜率受程序切换影响。

| 模块 | L级 | 实现要求 | 质量控制 |
|------|-----|----------|----------|
| 多速率序列读取 | L2/L3 | 文件夹读取器必须支持 Excel 序列；每个文件先切分为 monotonic scan，再只筛选主降温段 | 默认温跨 ≥20°C、点数 ≥80；低温保持小段不进入非等温拟合 |
| 冷却速率识别 | L3 | 优先解析文件名末尾速率；缺失时回退到 scan.rate_K_per_min 的绝对值 | 速率必须为正且至少 3 个速率点才能做回归 |
| 放热峰窗口 | L2/L3 | 热流自动判断 exo-up/exo-down；先用局部峰显著性和 `scipy.signal.peak_widths` 定位结晶峰，再用峰两侧局部端点建立积分基线 | 程序切换瞬态不得纳入积分；窗口触及边界时输出质量标记 |
| 相对结晶度 X(T,t) | L2 | `X=∫HF_exo dt / ∫HF_exo dt_total`；若无时间列，用 `|dT|/β` 转换为时间 | 输出 `Tp`、onset/end、ΔHc、X(T)、t(X) |
| Kissinger | L2 | `ln(β/Tp^2)` 对 `1/Tp` 线性回归，输出带符号 `Ea` 和 R² | 速率点少于 3 时只返回质量标记 |
| Friedman | L2 | 在固定转化率 X=0.1~0.9 下插值 `T(X)` 与 `dX/dt`，回归 `ln(dX/dt)` 对 `1/T` | 输出 `Ea(X)` 字典与平均 R² |
| Mo 方法 | L2 | 在固定转化率下回归 `log(β)=log(F)-a log(t)` | 输出 `a`、`F(T)` 和平均 R² |
| Ozawa | L2 | 在共同温度窗口内回归 `ln[-ln(1-X(T))]` 对 `lnβ` | 若多速率曲线没有足够共同温度区间，标记 `no_common_temperature_window`，不强行给数值 |

本批 `非等温结晶动力学数据` 可用：5 个速率点（2.5/5/10/20/40 K/min）均可抽取结晶峰。当前数据适合 Kissinger、Mo、Friedman；Ozawa 需要各速率曲线在有效结晶积分窗口中有更宽的共同温度覆盖，否则只能作为不可用质量标记。

新增配置项：`nonisothermal_min_delta_T_C`、`nonisothermal_min_points`、`nonisothermal_min_enthalpy_Jg`。

**可选 raw_data 输出**：非等温动力学目录同样必须走序列 engine run。若输出诊断 raw_data，仅用于内部调试/报告扩展；GUI 图表页不得回退生成 live 曲线。

### 4.5 可视化

| 图名 | 优先级 | 布局 | 说明 |
|------|--------|------|------|
| Fig-D1 热流曲线（含标注） | P1 | 单栏 | 每条 monotonic scan 独立出图；标注 Tg/Tm/Tcc/ΔHf；文件名含 scan 前缀防覆盖 |
| Fig-D2 Tg 放大区 | P2 | 单栏 | Tg ± 30°C 局部放大，标注半高法/拐点法 |
| Fig-D3 结晶度对比 | P2 | 单栏 | Bar chart，仅含有效 Xc 的 scan；标签精简为段类型+温度范围 |
| Fig-D4 Avrami 双对数图 | P1 | 单栏 | ln(-ln(1-Xc)) vs ln(t)（等温动力学专用） |
| Fig-D5 Kissinger 图 | P2 | 单栏 | ln(β/Tp²) vs 1000/Tp（非等温动力学专用） |
| Fig-D6 多峰反卷积 | P2 | 单栏 | 熔融峰 ≥ 2 时自动生成；过滤 μ 越界和占比 < 1% 的伪分量 |
| 降温曲线 | P2 | 单栏 | 标注 Tc/ΔHc |
| Cp 曲线 | P2 | 单栏 | 蓝宝石校正后 |

所有图均通过 `sci_style.set_sci_style()` + `sci_style.save_figure_sci()` 输出。

### 4.6 输出

- **CSV 参数表**：`data/dsc_parameters.csv`
  - 列：`scan_label, Tg_C, Tg_method, DTg_C, DCp_JgK, Tm_onset_C, Tm_peak_C, Tm_end_C, DHm_Jg, Tm2_peak_C, DHm2_Jg, Tm3_peak_C, DHm3_Jg, Tc_onset_C, Tc_peak_C, DHc_Jg, Tc2_peak_C, DHc2_Jg, Tcc_onset_C, Tcc_peak_C, DHcc_Jg, Xc_pct, Xc_method, DHm0_Jg, quality_score, n_peaks`
  - 一行一条 monotonic scan；所有关键参数（Tm/Tg/Tc/Tcc/DHm）均为 NaN 的行不输出
- **CSV 逐峰表**：`data/dsc_detailed_peaks.csv`
  - 列：`scan_index, scan_label, technique, peak_type, peak_C, onset_C, end_C, enthalpy_Jg`
  - 每个检测到的热事件一行；deconv_melting 仅保留有效分量（μ 在数据范围内且占比≥1%）
- **报告**：Markdown 含质量摘要 + 参数表 + 代表性热流曲线
- **图表**：每条 scan 独立命名 `{prefix}_Fig-D1_full_curve.svg`，全局 `Fig-D3_crystallinity.svg` 等；P1->`main/`，P2/P3->`SI/`

---

## §5 SAXS — 小角 X 射线散射 🟢 EXPERIMENTAL

### 5.0 技术定位

**回答**：从散射曲线提取纳米结构——L、lc、la、φc_SAXS、Kp、Sv、Q*。

**方向**：仪器数据 -> 结构参数。纯实验驱动。

**交叉验证**：φc 三重验证；L 双法自校验（Bragg + 相关函数）；Tm 的 Gibbs-Thomson 反推。

### 5.1 数据处理链路总览

```
SAXS 图像 (.edf/.cbf/.tif) 或 1D 曲线 (.dat)
        │
        ▼  [L1] fabio 读取 -> 2D numpy 数组
        │
        ▼  [L1] pyFAI 积分 -> I(q) 1D 曲线
        │
        ▼  [L2] scipy -> 背景扣除 + 归一化 + 平滑
        │
        ▼  [L1] sasmodels + lmfit -> 散射模型拟合
        │
        ▼  [L2] numpy -> 相关函数 γ(r) -> L/lc/la
        │
        ▼  [L3] 自研: 微纤化混合模型 / 变温双层状模型
        │
        ▼  参数集: L/lc/la/φc/Kp/Sv/Q* (+ 原位专有参数)
        │
        ▼  [L1] matplotlib (via sci_style) -> SCI 图
```

### 5.2 数据输入

| 格式 | L级 | 使用库 |
|------|-----|--------|
| .edf/.cbf/.tif | L1 | fabio |
| .dat/.txt | L2 | numpy |
| .h5/.hdf5 | L1 | fabio/h5py |
| 序列文件夹 | L2 | fabio + xarray |

**xarray 序列管理**：

```python
ds = xr.Dataset({
    "I": (["condition", "q"], I_array),
    "condition": (["condition"], T_or_strain_values),
})
```

### 5.3 预处理

| 步骤 | L级 | 使用库 | 调用示例 |
|------|-----|--------|----------|
| 2D->1D（全周） | L1 | pyFAI | `ai.integrate1d(data, npt=1000)` |
| 定向积分（子午/赤道） | L1 | pyFAI | `ai.integrate1d(data, azimuth_range=(-15,15))` |
| 掩膜 | L1 | pyFAI | `ai.mask = mask_array` |
| 背景扣除 | L2 | numpy | `I_corr = I_sample - I_bg` |
| 归一化校正 | L2 | numpy | 透射率/厚度 |
| 平滑 | L1 | scipy.signal.savgol_filter | |
| 热膨胀校正 | L3 | 自研 | `L_corr = L_meas / (1 + alpha*(T-T0))` |

### 5.4 核心计算

#### 基础参数

| 参数 | 方法 | L级 | 调用 |
|------|------|-----|------|
| L (Bragg) | L = 2π/q* | L2 | lmfit 峰拟合 |
| L (相关) | γ(r) 一阶极大 | L2 | numpy FFT |
| lc | γ(r) 切线 / IDF | L2 | numpy |
| la | la = L - lc | L2 | — |
| φc_SAXS | lc/L 或 Q*法 | L2 | — |
| Q* | ∫q²I(q)dq | L2 | numpy.trapz |
| Kp | lmfit 线性回归 | L1 | `lmfit.Model(linear).fit(Iq4, q4)` |

#### 默认可信度策略（v4.1 实装）

SAXS 核心输出分为 **final 参数** 与 **diagnostic 参数**：

- `L_nm` 默认来自 Bragg 候选峰评分：在 `I(q)q²` 中找候选峰，排除低 q upturn/空穴峰，序列数据使用上一帧 `q*` 做锚定；Lorentz 与相关函数只在与 Bragg 一致时参与 ensemble。
- `lc_nm/la_nm/Xc` 默认不直接相信 raw tangent/IDF。优先级为：`sasmodels` 拟合（若启用且 R² 合格）→ 参考结晶度/Q* 校准 → tangent/IDF raw 诊断值。
- 原位拉伸必须由 GUI 子模块或文件名识别进入 `experiment_type="strain"`，不得走 static 的 `Qstar_calibrated` 批处理；`saxs / strain` 中 `L_nm` 只由赤道/指定方位 Bragg 峰锚定追踪，`Q_star_rel` 只用于层状有序度/有效 `Xc/lc` 的相对校准。
- `lc_tangent_nm`、`lc_gamma_min_nm`、`phi_c_invariant` 保留为诊断列；当与 final 参数冲突时，不覆盖 final 参数。
- 无绝对强度标定、Δρ 或可靠参考结晶度时，`φc_SAXS` 只能作为形态学/相对结晶度，不等价于 DSC/WAXS 的总体结晶度。

#### 散射模型拟合

```python
# L1: sasmodels + lmfit
import sasmodels.core as sm
import sasmodels.data as sd

data = sd.Data1D(q=q, I=I)
model = sm.load_model('lamellar')
result = model.fit(data, thickness=10, sld_sheet=1e-6)
```

常用模型：lamellar（片晶）、cylinder（微纤）、ellipsoid（空穴）、core_shell_sphere（核壳）、parallelepiped（三轴微纤）、fractal（聚集体）。

#### 原位拉伸：微纤化混合模型（L3）

```python
# L2: sasmodels 单模型 + 胶水层组合
I_total = phi_lam * I_lamellar(q) + phi_fib * I_cylinder(q) + I_ellipsoid(q)
```

四阶段识别（L3）：弹性/空穴/微纤转变/完全微纤化，判定逻辑见代码中的 `detect_strain_phase()`。实际输出分通道处理：赤道/指定方位追踪 lamellar `L`，全周/低 q 用于空穴和 `Q*` 相对变化，取向因子来自 2D/χ 分布；避免把低 q 空穴峰误判为长周期。对于 PAD8 这类原位拉伸序列，最终表中的 `lc_nm/Xc` 是参考结晶度 + `Q_star_rel` 得到的有效层状参数，`lc_raw_nm/Xc_raw` 仅作诊断，不覆盖 final 参数。

#### 原位变温特有分析

- 双层状模型（预熔融）：sasmodels lamellar 双模型叠加
- 熔融三判据：I(q*)下降 + Q*->0 + q*消失
- Avrami 动力学：用 Q* 计算 Xc(t)，lmfit 拟合
- Ornstein-Zernike（熔体）：`I(q) = I0/(1+xi²q²)`，lmfit 拟合

### 5.5 可视化

| 图名 | 优先级 | 布局 |
|------|--------|------|
| 1D 散射曲线（双对数 + q*标注） | P1 | 单栏/双栏 |
| 相关函数 γ(r) + L/lc 切线 | P1 | 单栏 |
| IDF g1(r) | P1 | 单栏 |
| 2D 散射图序列（拉伸） | P1 | 双栏宽 1xN |
| 结构参数演变（L/lc/la/f/φv/AR） | P1 | 双栏 2x3 |
| I(q,T) 热图 | P1/P2 | 双栏宽 |
| Avrami 双对数图 | P1 | 单栏 |
| Porod/Kratky 图 | P2 | 单栏 |

### 5.6 输出

- **CSV**：`saxs_parameters.csv`，一行一个 frame/sample，必须使用 final 参数；同时附带 `lc_method`、`lc_confidence`、`L_bragg`、`L_lorentz`、`L_method`、`Q_star_rel` 等诊断列。
- **报告**：Markdown 含阶段判定 + 质量摘要
- **图表**：P1->`main/`，P2/P3->`SI/`
- **一致性要求**：CLI、GUI、CSV、summary 图必须读取同一套 final parameters；raw tangent/IDF 只能作为诊断列或低置信度图注。

---

## §6 WAXS — 广角 X 射线散射 🟢 EXPERIMENTAL

### 6.0 技术定位

**回答**：从衍射曲线提取晶体学参数——φc_WAXS、D_hkl、d_spacing、f_Herman、晶型归属。

**方向**：仪器数据 -> 晶体学参数。纯实验驱动。

**交叉验证**：φc 三重验证；晶胞参数可对比 DFT 计算；f 与 SAXS 对比。

### 6.1 数据处理链路总览

```
WAXS 图像 (.edf/.cbf/.tif) 或 1D 曲线 (.dat)
        │
        ▼  [L1] fabio 读取 -> 2D numpy 数组
        │
        ▼  [L1] pyFAI 积分 -> I(q) / I(2θ)
        │
        ▼  [L2] scipy -> 背景扣除 + 归一化 + 偏振校正
        │
        ▼  [L3] 自研 -> 非晶散射包络线分离
        │
        ▼  [L1] lmfit -> 多峰 Pseudo-Voigt 拟合
        │
        ▼  [L2] numpy -> Scherrer -> D_hkl / Bragg -> d_spacing
        │
        ▼  参数集：φc_WAXS, D_hkl, d_spacing, f, 晶型
        │
        ▼  [L1] matplotlib (via sci_style) -> SCI 图
```

### 6.2 数据输入

| 格式 | L级 | 使用库 |
|------|-----|--------|
| .edf/.cbf/.tif | L1 | fabio |
| .dat/.xy/.txt | L2 | numpy |
| .h5 | L1 | fabio |
| .xrdml | L2 | 适配器 |
| .raw (Bruker) | L2 | 适配器 |

### 6.3 预处理

| 步骤 | L级 | 使用库 |
|------|-----|--------|
| 2D->1D | L1 | pyFAI `integrate1d(data, npt=2000)` |
| 背景扣除 | L2 | numpy |
| 偏振校正 | L1 | pyFAI `polarization_factor=0.99` |
| 平滑 | L1 | scipy.signal.savgol_filter（窗口<=峰宽1/3） |
| 仪器展宽校正 | L2 | Caglioti公式：LaB6/CeO2 标定提取 U/V/W |

### 6.4 核心计算

#### 非晶散射分离（L3 自研）

| 方法 | 使用场景 | 推荐度 |
|------|----------|--------|
| 非晶参考样品法 | 有对照 | ★★★ |
| 宽 Gaussian 拟合 | 无参考 | ★★ |
| Ruland 方法 | 高精度 | ★★★ |

输出显式标记 `_amorphous_subtraction_method`。

#### 多峰拟合

```python
# L1: lmfit PseudoVoigt 模型
from lmfit.models import PseudoVoigtModel

model = PseudoVoigtModel(prefix='p1_') + PseudoVoigtModel(prefix='p2_')
params = model.make_params()
params['p1_center'].set(value=21.5, min=21.0, max=22.0)  # 约束峰位
result = model.fit(I, params, x=q)
```

三级峰搜索：`scipy.find_peaks` -> 二阶导数验证 -> 参考数据库交叉验证。

#### 结晶度与晶粒尺寸

```
φc_WAXS = ΣA_crystalline / (ΣA_crystalline + A_amorphous)
D_hkl = K·λ / (β·cosθ)    # Scherrer, K=0.89
```

#### Herman 取向因子

```python
f = (3*<cos²φ> - 1) / 2
# <cos²φ> 由方位角 I(φ) 积分
```

### 6.5 可视化

| 图名 | 优先级 | 布局 |
|------|--------|------|
| 1D 衍射 + 多峰拟合 | P1 | 单栏/双栏 |
| 非晶分离图 | P1 | 单栏 |
| 2D 衍射图序列（原位） | P1 | 双栏宽 1xN |
| 结晶度/晶粒尺寸演变 | P1 | 双栏 2x2 |
| Herman f | P1 | 单栏 |
| 极图 | P2 | 单栏 |

### 6.6 输出

- **CSV**：`WAXS_Results_All.csv`（φc | D_hkl | d_spacing | f | 晶型 | 非晶分离方法）
- **验证**：峰拟合 R² > 0.95

---

## §7 IR — 红外光谱 🟡 HYBRID

### 7.0 技术定位

**回答**：
- 实验侧：从红外谱图识别官能团、定量结晶度
- 计算侧：从分子结构通过 DFT/MD 模拟振动频率，与实验谱图对比

**方向**：双轨并行——实验谱图 -> 官能团/结晶度 & 结构模型 -> DFT/MD -> 模拟谱图。

**交叉验证**：结晶度与 DSC/WAXS；频率 RMSD < 10 cm⁻¹；与 ssNMR 互补验证。

### 7.1 数据处理链路总览

```
     ┌── 实验轨道 ──┐              ┌── 理论轨道 ──┐
     │  实验谱图      │              │  CIF/PDB/SMILES│
     └──────┬─────────┘              └──────┬─────────┘
            ▼                               ▼
       [L2] SPA/CSV/DPT读取           [L1] CASTEP/QE/ORCA
       -> A(ν)标准化                 -> 几何优化
       [L2] ATR/基线/平滑
       [L2] 峰检测+局部线型拟合
       -> 峰位/FWHM/面积/归属/带比指数
            │                               │
            │                          [L3] 状态分类器
            │                     ┌────────┼────────┐
            │                     ▼        ▼        ▼
            │               结晶/半结晶  无定形   橡胶态
            │               [L1] DFPT [L1] 簇DFT [L1] AIMD
            │               (CASTEP)  (ORCA)   (CP2K)
            │               LO-TO劈裂  MD系综   DACF
            │                     └────────┬────────┘
            │                              ▼
            │                        [L2] 频率缩放+谱图模拟
            │                              │
            └──────────────┬───────────────┘
                           ▼
                    计算 vs 实验对比 -> RMSD
```

### 7.2 数据输入

**实验谱图**：.spa (Thermo OMNIC) | .csv/.txt/.dat | .dpt (Thermo table) — `.spa` 采用 L2 二进制描述符读取器（真实 X 轴 + float32 数据块），通用表格由 pandas/numpy 读取后做单位判别。

**普通红外标准化字段**：`wavenumber_cm1` 单调递减；`absorbance` 为统一分析量；`transmittance` 输入必须先按 `A=-log10(T)` 转为吸光度。

**结构模型**：.cif -> CASTEP/VESTA | .pdb -> GROMACS/ORCA | SMILES -> Packmol+GROMACS

### 7.3 状态分类器（L3 自研，与 ssNMR 共享）

```
有明确晶胞？
  YES -> 结晶度>80%? -> YES -> DFPT (CASTEP)
                        -> NO  -> DFPT + 簇DFT（两相）
  NO  -> T<Tg? -> YES -> 玻璃态: 淬火+簇DFT
                -> NO  -> 交联? -> YES -> ReaxFF+簇DFT
                                  -> NO  -> 橡胶态: AIMD+DACF
```

| 状态 | 核心方法 | L级 | 工具 | 线型 |
|------|----------|-----|------|------|
| 结晶态 | DFPT(PBE-D3)+LO-TO | L1 | CASTEP/QE | Lorentzian |
| 无定形 | MD系综+簇DFT | L1 | GROMACS+ORCA | Gaussian |
| 半结晶 | DFPT+簇DFT两相 | L1 | CASTEP+ORCA | Voigt |
| 玻璃态 | 淬火构型+簇DFT | L1 | ORCA | Gaussian |
| 橡胶态 | AIMD+DACF | L1 | CP2K/VASP | Lorentzian |
| 交联 | ReaxFF-MD+簇DFT | L1 | LAMMPS+ORCA | Gaussian |

### 7.4 实验轨道：核心计算

**官能团归属**（L2）：

```python
from scipy.signal import find_peaks
peaks, props = find_peaks(
    absorbance,
    height=Amin + 0.02 * (Amax - Amin),
    prominence=0.015 * (Amax - Amin),
    distance=12 / dnu,
)
# 每个峰在 ±35 cm^-1 窗口内做 Lorentzian/Gaussian 局部拟合
# 输出 peak_cm1, height, prominence, FWHM, area, assignment
```

特征频率数据库（高频->低频）：OH(3200~3650) | NH(3280~3350) | CH2(2846~2926) | C=O酯(1715~1740) | C=O酰胺(1630~1680) | CF(1100~1250) | SiOSi(1000~1100)

**普通红外预处理**：

| 步骤 | L级 | 实现要求 |
|------|-----|----------|
| Thermo SPA 读取 | L2 | 从 SPA 头部描述符读取点数、起止波数和有效 float32 数据块，禁止用裸 float 全文件切半 |
| 透过率转吸光度 | L2 | 表头含 Trans/%T 或数值为 0~100% 时转换；0~1 的无表头数据默认按吸光度处理 |
| ATR 修正 | L2 | 可选；按穿透深度一阶校正，低波数过强项按 `A_corr ∝ ν` 补偿 |
| 基线校正 | L2 | 优先 pybaselines rubberband / asLS；保留线性/多项式回退 |
| 平滑 | L1 | scipy Savitzky-Golay，窗口必须为奇数且小于数据长度 |
| 聚合物初判 | L2 | 以主峰显著性加权匹配数据库，并惩罚不属于该聚合物的强峰 |

**结晶度定量**：

| 聚合物 | 公式 |
|--------|------|
| PE | IR index = A730/(A730+A720) |
| PET | IR index = A1340/(A1340+A1370) |
| iPP | IR index = A998/(A998+A973) |
| PVDF β | Fβ = A840/(A840+1.26·A763) |
| PA6 | IR index = A1200/A1637；辅以 A1120/A1637、A929/A1637 |

未接入外部标定曲线时，上述结果输出为 **IR band index**，不得直接声称为绝对结晶度；若由 DSC/WAXS/XRD 标定，可再映射为 `Xc_IR`。

#### 7.4.1 原位变温二维 IR / 2D-COS

原位变温红外归入 **二维 IR 子模块**，这里的二维含义为“扰动维度（温度/保温时间/冷却序列） × 波数”以及 Noda 二维相关红外谱（同步/异步相关）。真实数据目录 `测试数据/IR/原位变温红外` 按整目录作为一个序列输入，不拆成普通 IR 的逐文件批处理。

**序列识别与排序**：

| 文件名模式 | 物理阶段 | 排序规则 |
|------------|----------|----------|
| `*-SW-30.csv` ... `*-SW-250.csv` | 升温段 heating | 温度升序 |
| `250-for 1min.csv` ... | 恒温保温 hold | 时间升序 |
| `*-JW-240.csv` ... `*-JW-30.csv` | 降温段 cooling | 温度降序 |

**核心计算**：

1. 每一帧先走普通 IR 标准化链路：读取 CSV/SPA/DPT -> 吸光度统一 -> 基线/平滑 -> 峰检测/归属 -> PA6 特征带比。
2. 将各帧插值到统一 `wavenumber_cm1` 网格，构造矩阵 `A(frame, wavenumber)`。
3. 追踪 PA6 特征带：3298、2931、2860、1637、1541、1463、1263、1200、1120、929 cm⁻¹。
4. 输出 PA6 带比随温度程序变化：`A1200/A1637`、`A1120/A1637`、`A929/A1637` 等。未标定时仍标注为 **IR band index**。
5. 计算二维相关红外：

```python
Y = A - mean(A, axis=0)          # 动态谱，按扰动序列均值中心化
Phi = Y.T @ Y / (m - 1)          # synchronous 2D-COS
Psi = Y.T @ N @ Y / (m - 1)      # asynchronous 2D-COS, N 为 Hilbert-Noda 矩阵
```

同步谱 `Phi` 用于判断谱带协同增强/减弱；异步谱 `Psi` 用于判断变温扰动下谱带响应先后，符号解释必须注明采用当前排序方向（升温->保温->降温）。

### 7.5 理论轨道：DFT/MD 计算

**精度分级**：

| 级别 | 方法 | 频率误差 | 工具 | L级 |
|------|------|----------|------|-----|
| C1 快速 | GFN2-xTB | ±30~50 cm⁻¹ | xTB | L1 |
| C2 标准 | B3LYP/def2-SVP | ±15~25 cm⁻¹ | Gaussian | L1 |
| C3 高精 | ωB97X-D/def2-TZVP | ±5~10 cm⁻¹ | ORCA | L1 |
| C4 基准 | CCSD(T)/cc-pVTZ | ±2~5 cm⁻¹ | ORCA | L1 |

**频率缩放因子**：

| 泛函/基组 | 高频(>2000) | 中频 | 低频(<1000) |
|-----------|------------|------|------------|
| B3LYP/6-31G* | 0.9614 | 0.9734 | 0.9826 |
| ωB97X-D/def2-TZVP | 0.9572 | 0.9712 | 0.9801 |
| PBE-D3（周期性）| 0.9850 | 0.9920 | 0.9950 |

**谱图模拟**：

```python
def simulate_ir_spectrum(freqs, intensities, lineshape='gaussian', fwhm=10):
    x = np.linspace(400, 4000, 5000)
    spectrum = np.zeros_like(x)
    for freq, intensity in zip(freqs, intensities):
        if lineshape == 'gaussian':
            sigma = fwhm / 2.355
            spectrum += intensity * np.exp(-0.5*((x-freq)/sigma)**2)
        elif lineshape == 'lorentzian':
            spectrum += intensity * (fwhm/2)**2 / ((x-freq)**2 + (fwhm/2)**2)
    return x, spectrum
```

### 7.6 可视化

| 图名 | 优先级 | 布局 | 说明 |
|------|--------|------|------|
| 实验谱图+峰归属 | P1 | 双栏宽 | 标注主要官能团峰 |
| 局部峰拟合 | P1 | 单栏/双栏 | 峰位、FWHM、面积、局部 R² |
| IR band index 对比 | P1 | 单栏 | 普通红外带比指数 |
| 原位变温 IR 热图 | P1 | 双栏 | frame/temperature × wavenumber 吸光度矩阵 |
| 原位变温 IR 瀑布图 | P1 | 双栏 | 升温/保温/降温序列叠加 |
| 2D-COS 同步相关谱 | P1 | 方图 | 谱带协同变化 |
| 2D-COS 异步相关谱 | P1 | 方图 | 谱带响应先后 |
| PA6 特征带追踪 | P1 | 单栏 | A1637、A1541、A1200、A1120、A929 随温度程序变化 |
| 计算 vs 实验叠加 | P1 | 单栏/双栏 | 上下对比 |
| 频率回归图 | P2 | 单栏 | calc vs exp + R² |

### 7.7 输出与验证

- 普通红外输出：`ir_parameters.csv`（样品级摘要）、`ir_peaks.csv`（逐峰 peak_cm1/FWHM/area/assignment）、`ir_band_indices.csv`（带比指数）。
- 原位变温二维 IR 输出：`ir_temperature_parameters.csv`（逐帧温度/阶段/峰数/带比/特征带高）、`ir_temperature_matrix.csv`（统一波数网格上的吸光度矩阵）、`ir_temperature_2dcos_cross_peaks.csv`（同步/异步相关谱交叉峰）。
- 原位变温二维 IR 图件：`Fig-IRT1_2D_heatmap`、`Fig-IRT2_waterfall`、`Fig-IRT3_band_indices`、`Fig-IRT4_band_tracking`、`Fig-IRT5_2DCOS_synchronous`、`Fig-IRT6_2DCOS_asynchronous`。
- 普通红外验证：SPA 真实轴必须落在 400~4000 cm⁻¹；主峰拟合局部 R² 建议 > 0.95；数据库归属 tolerance 默认 18 cm⁻¹；IR band index 必须标注未标定/已标定状态。
- 原位变温二维 IR 验证：序列帧数 ≥ 3；所有谱图必须插值到同一波数轴；`SW/for min/JW` 阶段排序需可追溯；2D-COS 异步谱符号必须注明扰动排序方向。
- 计算-实验验证：峰位误差（校正后）< 10 cm⁻¹ | 结晶度误差 < 5%（vs XRD）| R² > 0.99
- LO-TO 劈裂：含极性键（PET/尼龙/PVDF）必须执行

---

## §8 ssNMR — 固体核磁共振 🟡 HYBRID

### 8.0 技术定位

**回答**：
- 实验侧：从固体 NMR 谱图获取化学位移、各向异性参数、弛豫时间
- 计算侧：GIPAW-DFT/簇 DFT 计算化学位移张量，与实验对比

**方向**：双轨并行。

**交叉验证**：归属与 IR 互补；晶体结构与 WAXS 对比。

### 8.0.1 软件实现更新（2026-06-02）

NMR GUI 分区已从单一“固态 NMR”调整为四个子模块：

| 子模块 | GUI 名称 | 当前处理对象 | 当前引擎状态 |
|------|---------|------------|-------------|
| `nmr.liquid_h` | 液体 H 谱 | 原始 `fid`、液体 JEOL `.jdf`、两列表格 | 已接入 FID/液体 JEOL payload -> FFT/相位/基线/峰检测；新增正积分、积分归一化、SNR、FWHM、区域积分和可能残余溶剂标记 |
| `nmr.liquid_c` | 液体 C 谱 | 原始 `fid`、液体 JEOL `.jdf`、两列表格 | 已接入 13C 默认 ppm 轴/峰检测；液体 JEOL `.jdf` 不再按 processed spectrum 直画，而按 FID 转换；未指定聚合物时只做通用化学位移区域归属 |
| `nmr.solid_h` | 固体 H 谱 | JEOL.NMR `.jdf/.bin`、两列表格 | 已接入 JEOL 容器 float64 谱段识别/基线/峰检测；多谱导出按样品名区分，新增固体 H 区域积分 |
| `nmr.solid_c` | 固体 C 谱 | JEOL.NMR `.jdf/.bin`、两列表格 | 已接入 JEOL 容器 float64 谱段识别；只有明确晶相/非晶相归属后输出 Xc，否则给 `Xc_NMR_assignment=WARN` |

实施顺序采用“先液体、后固体”：

1. 液体核磁优先保证 raw `fid` 能转为可分析一维谱：读取 little-endian int32 实/虚交错 FID，去除前导零点，做指数窗函数、零填充 FFT、零阶相位搜索、基线校正和归一化。
2. 固体核磁先保证真实 JEOL 数据不再 `No NMR data`：识别 `JEOL.NMR` 容器，自动定位中部高熵 little-endian float64 谱段，并记录 `data_offset/data_points/X_*` 元数据。
3. 暂无完整采集参数时，ppm 轴按相态和核种使用默认范围：液体 1H 12.5~-0.5 ppm，液体 13C 220~-10 ppm，固体 1H 60~-20 ppm，固体 13C 240~-20 ppm。后续拿到完整 Bruker `acqus/procs` 或 JEOL 参数映射后，用真实频率/扫宽覆盖默认轴。

2026-06-02 本轮 NMR 物理引擎优化已完成：

1. GUI 分区按注册优先级稳定显示为 `nmr.liquid_h -> nmr.liquid_c -> nmr.solid_h -> nmr.solid_c`，液体谱默认 Lorentzian 窄峰拟合，固体谱默认 mixed 峰形。
2. 液体 H/C 谱新增物理指标：正峰面积、`integral_norm`、`median_snr`、`mean_fwhm_ppm`、`dominant_peak_ppm`、化学位移区域积分百分比；13C 未指定 `polymer_name` 时不参与聚合物晶/非晶相数据库匹配。
3. 固体 H/C 谱新增同样的正面积、SNR、FWHM、主峰和区域积分；固体 13C 结晶度仅在存在明确晶相与非晶/中间相峰面积时输出，其他情况保留为未定量并记录质量 WARN。
4. NMR 导出新增逐峰表 `data/nmr_peaks.csv`，参数表 `data/nmr_parameters.csv` 包含主峰、SNR、FWHM、区域积分和峰积分；多条固体谱的图件按样品标签命名，避免同名覆盖。
5. 已用 `D:\PolyNexus\测试数据\NMR数据` 中液体 H、液体 C、固体 H、固体 C 四类真实数据验证。后续仍未实现：GIPAW/簇 DFT 自动任务、CSA 椭球图、T1/T2 自动序列识别与弛豫曲线图、Simpson/DMFit 联动。

2026-06-09 液体 NMR 稳定性修订：

1. 修复液体 H/C 分区误读固体 JEOL 目录的问题：GUI 运行前和 `NMREngine.load()` 内部都会按当前子模块检查 `liquid/solid` 与 `1H/13C`，明显不匹配时停止；混合目录只保留与当前分区匹配的谱图。
2. 修复液体 JEOL `.jdf` 处理路径：对 `20260527-xye_Carbon-1-1.jdf`、`20260527-xye_proton-1-1.jdf` 这类液体 JEOL payload，按时域 FID 执行复数重组、异常 float 清理、指数窗、FFT、零阶相位和默认 ppm 轴，而不是把 payload 直接当谱图绘制。
3. 修复中文路径识别稳定性：`液体/固体/H谱/碳谱` 判断改为稳定的 Unicode 转义字面量，`JEOL.NMR` 容器本身不再被默认判为固体。
4. 降低图形误导性：谱图只标峰位 ppm，归属/区域/积分保存在 `nmr_peaks.csv`；低拟合质量的 deconvolution 图标为 diagnostic fit，并通过质量旗标提示。
5. 新增回归测试：液体 C 不能运行固体 H 目录；液体 C 对含 H/C 的 JEOL 混合目录只保留 Carbon 谱；液体 JEOL `.jdf` 必须走 `jeol_fid_fft`。

### 8.1 数据处理链路总览

```
     ┌── 实验轨道 ──┐              ┌── 理论轨道 ──┐
     │  实验谱图      │              │  CIF/PDB/SMILES│
     └──────┬─────────┘              └──────┬─────────┘
            ▼                               ▼
       [L1] nmrglue/DMFit              [L1] CASTEP/Gaussian
       -> 读取+峰拟合                  -> 几何优化
            │                               │
            │                          [L3] 状态分类器
            │                     ┌────────┼────────┐
            │                     ▼        ▼        ▼
            │               结晶态    无定形    橡胶态
            │               [L1] GIPAW [L1]簇DFT [L2]MD
            │               (CASTEP) (ORCA)  (GROMACS)
            │               静态      MD系综   动力学平均
            │                     └────────┬────────┘
            │                              ▼
            │                        [L2] 谱图模拟 (Simpson/DMFit)
            │                              │
            └──────────────┬───────────────┘
                           ▼
                    计算 vs 实验对比 -> RMSD
```

### 8.2 数据输入

**实验谱图**：Bruker raw `fid` -> L3 自研 FID/FFT reader | Bruker `pdata/1/1r` -> L2 TopSpin processed reader | JEOL `JEOL.NMR` `.jdf/.bin` -> L3 自研容器谱段 reader | ASCII/CSV -> L2 pandas

**结构模型**：.cif/.pdb -> L1 CASTEP/GROMACS

### 8.3 状态分类器 + 核素策略

状态路由与 §7.3 的 IR 分类器共享。

| 核素 | 推荐方法 | 特殊注意 |
|------|----------|----------|
| ¹H | GIPAW-PBE / Cluster PBE0 | 氢键敏感 |
| ¹³C | GIPAW-PBE / B3LYP-GIAO | 参考TMS，构象平均 |
| ¹⁵N | PBE0-GIAO / GIPAW | 需高基组 |
| ¹⁹F | PBE0 / GIPAW | 强各向异性，需张量全分量 |
| ²⁹Si | GIPAW-PBE | 硅橡胶标配 |
| ³¹P | B3LYP / GIPAW | 参考H₃PO₄ |

### 8.4 理论轨道：QM/MD 计算

**精度分级**：

| 级别 | 方法 | ¹³C误差 | 工具 | L级 |
|------|------|---------|------|-----|
| C1 快速 | PM7/GFN2-xTB | ±5~10 ppm | MOPAC/xTB | L1 |
| C2 标准 | B3LYP/PBE0+def2-TZVP | ±2~4 ppm | Gaussian/ORCA | L1 |
| C3 GIPAW | PBE/PBE0+D3(BJ) | ±1~2 ppm | CASTEP/QE | L1 |

**GIPAW 参数**：截断能>=700 eV | k点间距<=0.04 Å⁻¹ | SCF 收敛 1e-8 eV

**化学位移转换**：

```python
δ_calc = σ_ref - σ_calc
δ_exp = δ_calc * slope + intercept  # 线性校正
# 参考：TMS(¹H/¹³C), NH₄Cl(¹⁵N), H₃PO₄(³¹P)
```

**MD 动力学平均**：从 MD 轨迹等间隔取 N>=50 帧，簇 DFT 后 Boltzmann 加权。

### 8.5 谱图模拟

| 状态 | 线型 | 工具 | L级 |
|------|------|------|-----|
| 结晶态 | Lorentzian | Simpson/DMFit | L1 |
| 无定形/玻璃 | Gaussian | DMFit | L1 |
| 半结晶 | Voigt | DMFit | L1 |
| 橡胶态 | Lorentzian | Simpson | L1 |

```python
def simulate_1d_nmr(shifts, intensities, fwhm=1.0, lineshape='lorentzian'):
    x = np.linspace(min(shifts)-20, max(shifts)+20, 5000)
    spectrum = np.zeros_like(x)
    for shift, intensity in zip(shifts, intensities):
        if lineshape == 'lorentzian':
            spectrum += intensity*(fwhm/2)**2/((x-shift)**2+(fwhm/2)**2)
        elif lineshape == 'gaussian':
            sigma = fwhm/2.355
            spectrum += intensity*np.exp(-0.5*((x-shift)/sigma)**2)
    return x, spectrum
```

### 8.6 可视化

| 图名 | 优先级 | 布局 | 说明 |
|------|--------|------|------|
| 计算 vs 实验叠加 | P1 | 双栏 | 对比 |
| 化学位移回归图 | P1 | 单栏 | δ_calc vs δ_exp + R² |
| 各向异性参数 | P2 | 单栏 | CSA 椭球 |
| 弛豫曲线 | P2 | 单栏 | T1/T2 vs τ |

### 8.7 输出与验证

- **验证指标**：¹³C RMSD < 2 ppm | ¹H RMSD < 0.5 ppm | 线性斜率~1.0 | FWHM 偏差 < 20%
- **CSI 各向异性**：计算 δ11/δ22/δ33、CQ、η
- **弛豫**：T1/T2，允许误差 ±30%

---

# 第三部分：交叉验证与精准度保障

---

## §9 关键参数多技术校验矩阵

### 9.1 核心校验矩阵

| 参数 | DSC | SAXS | WAXS | IR | ssNMR | 校验规则 |
|------|:---:|:----:|:----:|:--:|:-----:|----------|
| **结晶度 φc** | ΔHf法 | lc/L法 | 峰面积法 | 特定峰比 | — | 三者偏差>±5% -> 🔴 |
| **长周期 L** | — | Bragg+γ(r) | — | — | — | 两法偏差>±3% -> 🟡 |
| **熔点 Tm** | 峰顶 | G-T反推 | — | — | — | 偏差>±3°C -> 🔴 |
| **取向 f** | — | Herman | Herman | — | — | 偏差>±0.05 -> 🟡 |
| **晶胞参数** | — | — | Bragg峰位 | — | — | 偏差>±1% -> 🟡 |
| **化学位移** | — | — | — | — | calc vs exp | ¹³C RMSD>2ppm -> 🔴 |
| **频率/官能团** | — | — | — | calc vs exp | — | 偏差>10cm⁻¹ -> 🟡 |

### 9.2 φc 三重验证详解

```
检查点：φc_DSC vs φc_WAXS vs φc_SAXS
  |- |φc_DSC - φc_WAXS|  <= 5%  -> 🟢
  |- |φc_DSC - φc_SAXS|  <= 5%  -> 🟢
  |- |φc_WAXS - φc_SAXS| <= 5%  -> 🟢
  └─ 任一项超出 5%     -> 🔴 告警
```

三重来源差异原因：DSC=热力学总体 | WAXS=晶体学有序度 | SAXS=形态学片晶比。三者一致 -> 可靠。不一致 -> 有信息价值（界面相/缺陷），不可忽略。

### 9.3 Tm 双向校验

```
DSC 实测 Tm  ↕  SAXS Gibbs-Thomson: Tm = Tm∞[1 - 2σe/(ΔHf·ρc·lc)]
偏差 <= 3°C -> 🟢 / > 3°C -> 🔴
```

---

## §10 自动校验与质量标记

### 10.1 触发时机

`analyze()` 完成后 -> 自动运行 `_validate_results()` -> 注入质量标记。

### 10.2 告警分级

| 级别 | 标记 | 含义 | 阻断导出？ |
|------|------|------|-----------|
| 🔴 ERROR | `"ERROR"` | 超出合理范围或交叉验证失败 | 阻断 |
| 🟡 WARN | `"WARN"` | 灰色地带，建议复核 | 不阻断，标记 |
| 🟢 OK | `"OK"` | 全部校验通过 | 正常 |

### 10.3 各技术合理性校验

**DSC**：Tg/Tm 在已知范围？ φc 在 0~100%？ ΔHf 在合理范围？ 熔融峰宽 ≤ 50°C（10 K/min）？ 反卷积 μ 在数据温度范围内？ 反卷积分量占比 ≥ 1%？ Tg 检测 DCp ≥ 0.01 J/g·K 且 DTg ≥ 2°C？

**SAXS**：L 在 5~100 nm？ lc < L？ q* 信噪比>3？ 变温序列 Q* 单调性？

**WAXS**：φc 在 0~100%？ 非晶分离残差无结构？ D_hkl 1~1000 nm？ 拟合 R²>0.95？

**IR/NMR**：计算 vs 实验 RMSD 达标？ 参考物质统一性？

### 10.4 嵌入机制

```python
class ParameterSet:
    quality_flags: dict[str, str] = {}
    validation_passed: bool = True
    validation_warnings: list[str] = []

    def add_flag(self, param, flag):
        self.quality_flags[param] = flag
        if flag == "ERROR":
            self.validation_passed = False

# 导出到 ExportRow
row = ExportRow(quality=",".join(f"{k}:{v}" for k,v in ps.quality_flags.items()), ...)
```

---

# 附录

---

## 附录 A：L3 自研模块清单

| 编号 | 模块 | 技术 | 功能 | 验证路径 |
|------|------|------|------|----------|
| L3-01 | 多步转变基线 | DSC | 多峰重叠步进基线 | 与线性/S形结果对比，偏差>10%告警 |
| L3-02 | 微纤化混合模型 | SAXS | lamellar+ellipsoid+cylinder 组合 | Q* 不变量守恒校验 |
| L3-03 | 阶段自动识别 | SAXS | 原位拉伸四阶段判定 | 2D图案人工复核 |
| L3-04 | 变温双层状模型 | SAXS | 预熔融双lamellar | Q* 连续性校验 |
| L3-05 | 热膨胀校正 | SAXS | L/lc 热膨胀补偿 | 与文献 α 对比 |
| L3-06 | 非晶散射分离 | WAXS | 非晶包络+结晶度 | 三重验证 |
| L3-07 | 状态分类器 | IR,NMR | 状态->计算路由 | 人工复核 |
| L3-08 | 无定形构象平均 | IR | MD系综+Boltzmann | 与实验 RMSD |

所有 L3 模块要求：`# L3_SELFBUILT` 注释 + `_validation_status` 字段 + CI 回归测试。

---

## 附录 B：聚合物参考数据库

### B.1 100% 结晶理论熔融焓 ΔHf_100% (J/g)

| 聚合物 | ΔHf | 聚合物 | ΔHf |
|--------|-----|--------|-----|
| PE (HDPE) | 293 | PET | 140 |
| iPP (α) | 207 | PBT | 145 |
| sPP | 196 | PTFE | 82 |
| PA6 (α) | 230 | PEEK | 130 |
| PA66 | 255 | POM | 326 |
| PLA | 93 | PVDF (β) | 105 |

### B.2 热转变温度

| 聚合物 | Tg (°C) | Tm (°C) | 密度 (g/cm³) |
|--------|---------|----------|-------------|
| PE (HDPE) | -120~-90 | 130~137 | 0.94~0.97 |
| iPP | -20~-5 | 160~170 | 0.90~0.91 |
| PS | 90~105 | — | 1.04~1.06 |
| PET | 65~80 | 245~265 | 1.33~1.40 |
| PA6 | 40~60 | 215~225 | 1.12~1.15 |
| PA66 | 50~70 | 255~265 | 1.13~1.15 |
| PTFE | 120~130 | 327~342 | 2.15~2.20 |
| PMMA | 100~120 | — | 1.17~1.20 |
| PC | 140~150 | — | 1.20~1.22 |
| PEEK | 143~150 | 334~343 | 1.26~1.32 |
| PVDF | -40~-30 | 170~180 | 1.76~1.78 |
| PLA | 55~65 | 150~180 | 1.24~1.26 |

### B.3 常见聚合物晶体参数

| 聚合物 | 晶系 | 空间群 | a(Å) | b(Å) | c(Å) | 典型 2θ(Cu Kα) |
|--------|------|--------|------|------|------|----------------|
| PE | 正交 | Pnam | 7.40 | 4.93 | 2.53 | 21.5°, 24.0° |
| iPP(α) | 单斜 | P2₁/c | 6.65 | 20.96 | 6.50 | 14.1°, 16.9°, 18.6°, 21.8° |
| PET | 三斜 | P-1 | 4.56 | 5.94 | 10.75 | 17.8°, 22.8°, 25.8° |
| PA6(α) | 单斜 | P2₁ | 9.56 | 17.2 | 8.01 | 20.0°, 24.0° |
| PTFE | 六方 | P3₁ | 5.66 | 5.66 | 19.5 | 18.1° |
| PVDF(α) | 正交 | P2₁₂₁₂₁ | 9.64 | 4.96 | 4.62 | 18.4°, 20.1° |
| PVDF(β) | 正交 | Cm2m | 8.58 | 4.91 | 2.56 | 20.8° |

---

*文档结束*
*本方案为 PolyNexus v4.0 自包含统一框架总纲，所有具体实现以此为准。*
