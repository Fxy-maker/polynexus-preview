# PolyNexus 图表后处理工作台升级 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前“成品图设置窗口”升级为真正可用的图表后处理工作台，让用户能直接在已导出的 SVG/PNG/PDF/JPG 上完成标题、坐标标签、注释、箭头、框选、高亮、裁剪、另存等常用论文插图整理操作。

**Architecture:** 先建立统一图表规格和图表资产包契约，再保留现有 `plot_edits.json` 作为单图编辑元数据入口。编辑能力分成两条路径：静态成品图编辑负责直接烘焙到图片文件；数据可重绘编辑负责在下一次 engine `plot()` 时应用曲线级样式。第一阶段优先实现统一规格、静态图标注和直接保存，避免继续依赖用户手动重绘。

**Tech Stack:** Python, PySide6, QGraphicsView/QGraphicsScene, Matplotlib, existing `FigureFilePreview`, existing `plot_edits.json`, pytest with `QT_QPA_PLATFORM=offscreen`.

---

## 0. 当前问题判断

当前图表编辑器已经能做一部分样式保存，但用户体感仍然不实用，核心原因有三点：

- “编辑此图”的语义像是直接编辑当前图片，但历史实现主要保存 sidecar 设置，再依赖后续重绘。
- 静态成品图和 Matplotlib 数据图层没有清晰分层，导致“哪些设置会马上生效、哪些设置要重绘后生效”不够直观。
- 缺少科研图常用的后处理工具，例如文字标注、箭头、矩形框、峰区高亮、裁剪、撤销、另存副本。

已经完成的临时修复只解决了“保存当前静态图时文件必须发生变化”的底线问题。后续应把它升级成一个稳定、可解释、可扩展的工作台。

## 1. 产品边界

### 必须做

- 直接打开当前导出图并显示真实成品图。
- 支持静态图标注：文本、箭头、线段、矩形、高亮区域。
- 支持基础画布操作：选择、拖动、删除、撤销、重做、适配窗口、100% 显示。
- 支持保存当前文件和另存为新文件。
- 保存时同步写入 `plot_edits.json`，保证后续可追踪、可复用。
- UI 明确区分“直接写入当前图片”和“下次重绘时应用”。

### 暂不做

- 不做完整 Photoshop 式图像编辑。
- 不做像素级画笔、橡皮擦、滤镜、抠图。
- 不在第一阶段重写全部 Matplotlib 输出模块。
- 不恢复已经删除的 raw-data live viewer。
- 不把所有图表对象都反解析成 Matplotlib 曲线对象；SVG 反解析可作为后续增强。

## 2. 目标工作流

1. 用户在图表页选中一张图。
2. 点击“编辑”。
3. 编辑器打开真实成品图，并进入“静态标注模式”。
4. 用户可添加文本、箭头、框、高亮区，拖动调整。
5. 用户点击“保存到当前图”时，当前图片文件立即更新。
6. 用户点击“另存为”时，生成副本，不破坏原始导出图。
7. 编辑记录写入输出目录下的 `plot_edits.json`。
8. 如果该图后续被 engine 重绘，支持把可重绘样式继续应用到新图；静态标注是否重放由后续任务控制。

## 3. 统一图表规格与资产包

这一层建议作为编辑器升级的前置任务。目标不是强行只保留一种图片格式，而是把 SVG/PNG/PDF/JPG 的用途、尺寸、DPI、背景、预览、投稿输出和 sidecar key 统一起来。

### 3.1 格式职责

- **SVG:** 优先作为可编辑矢量母版，适合后续论文排版和细节微调。
- **PNG:** 优先作为 GUI 预览图和快速分享图，固定 DPI、背景和像素尺寸。
- **PDF:** 优先作为投稿、排版和矢量归档格式。
- **JPG/JPEG:** 仅作为兼容输入或轻量分享输出，不作为首选母版。
- **plot_edits.json:** 保存样式、标注、渲染模式、资产组关系，不把交互状态藏进图片文件。
- `FigureAssetSpec` 读取 SVG/PNG/PDF/JPG 基础尺寸：PNG 读取 IHDR，SVG 读取 `width/height` 或 `viewBox`，PDF 读取 `/MediaBox`，JPG 读取 SOF 段，为后续期刊尺寸和 DPI 检查打底。

### 3.2 推荐资产组

同一张科研图建议形成一组关联资产：

```text
figures/
  Fig-W1_profile.svg      # 可编辑母版，优先
  Fig-W1_profile.png      # GUI 预览图
  Fig-W1_profile.pdf      # 投稿/排版图
plot_edits.json
```

编辑器的选择顺序：

1. 有 SVG 时，优先以 SVG 作为编辑母版和 sidecar 主 key。
2. 没有 SVG 但有 PDF 时，渲染 PDF 首屏进入静态编辑模式。
3. 只有 PNG/JPG 时，进入静态位图编辑模式。
4. 保存副本时，默认生成 PNG；用户选择投稿输出时可生成 PDF/SVG。

### 3.3 FigureAssetSpec

新增一个轻量规格对象，统一描述单张图和它的相关格式：

```python
@dataclass
class FigureAssetSpec:
    figure_id: str
    sidecar_key: str
    master_path: str
    preview_path: str
    publication_paths: dict[str, str]
    available_formats: list[str]
    preferred_master_format: str
    width_px: int
    height_px: int
    dpi: int
    figsize_in: tuple[float, float]
    background: str
```

关键规则：

- `figure_id` 来自文件 stem，例如 `Fig-W1_profile`。
- `sidecar_key` 使用相对输出根目录的 POSIX 路径，继续兼容 `plot_edits.json`。
- 坐标保存优先使用归一化坐标 `0.0-1.0`，渲染时再映射到具体像素，避免 PNG/PDF/SVG 尺寸差异导致标注漂移。
- 如果现有图没有完整规格，运行时从实际文件读取尺寸并补全临时 spec。
- 当前实现已从 SVG/PNG/PDF/JPG 补全基础 `width_px`、`height_px`、`dpi` 和可推导的 `figsize_in`，不再只保存空尺寸占位。

### 3.4 对编辑器的收益

- 预览不再猜格式，统一从 `preview_path` 加载。
- 保存不再猜目标，统一按 `master_path` 或用户选择路径写出。
- 标注坐标不受窗口缩放影响。
- 后续做期刊导出检查时，可以直接检查 DPI、尺寸、背景、格式是否满足要求。
- 后续做批量重导图时，可以按同一个 `figure_id` 找齐 SVG/PNG/PDF。

## 4. 文件结构规划

### 新增文件

- `polynexus/core/figure_assets.py`
  - 负责 `FigureAssetSpec`、资产组发现、格式优先级、尺寸读取、sidecar key 计算。
  - 不依赖 Qt widget，方便单元测试。

- `polynexus/gui/figure_annotations.py`
  - 负责 annotation 数据模型、序列化、反序列化、版本迁移。
  - 不依赖 Qt widget，方便单元测试。

- `polynexus/gui/widgets/annotation_canvas.py`
  - 负责 QGraphicsView/QGraphicsScene 画布。
  - 加载底图 pixmap。
  - 管理文本、箭头、线段、矩形、高亮 overlay items。
  - 暴露 `load_image()`, `set_tool()`, `annotation_state()`, `load_annotation_state()`, `render_to_image()`。

- `tests/test_figure_annotations.py`
  - 覆盖 annotation schema round-trip、缺字段兼容、版本字段。

- `tests/test_figure_assets.py`
  - 覆盖 SVG/PNG/PDF 资产组发现、master/preview 选择、sidecar key 稳定性。

- `tests/test_annotation_canvas.py`
  - 覆盖离屏环境下底图加载、添加文本、渲染输出非空图。

### 修改文件

- `polynexus/gui/widgets/chart_editor.py`
  - 从“样式设置面板”升级为“图表后处理工作台”的窗口壳。
  - 静态文件模式使用 `AnnotationCanvas`。
  - 保留已有样式模板控件，但移动到“样式”区域。

- `polynexus/core/plot_edits.py`
  - 扩展 `plot_edits.json` schema，增加 `annotations`、`render_mode` 和可选 `asset_spec`。
  - 保持旧格式读取兼容。

- `polynexus/gui/widgets/chart_viewer.py`
  - 只需确认编辑入口继续传入当前文件路径。
  - 保存后刷新缩略图和大预览。

- `polynexus/gui/i18n.py`
  - 增加工具栏、模式、保存提示、删除确认、撤销重做等中英文文案。

- `tests/test_chart_editor.py`
  - 增加静态标注保存、另存为、副本不覆盖原图等回归。

## 5. 数据结构规划

`plot_edits.json` 保持当前 `version/files/style` 结构，新增字段如下：

```json
{
  "version": 2,
  "files": {
    "figures/Fig-W1_profile.png": {
      "relative_path": "figures/Fig-W1_profile.png",
      "source_path": "D:/PolyNexus/results/figures/Fig-W1_profile.png",
      "updated_at": "2026-07-06T12:00:00",
      "render_mode": "static_baked",
      "asset_spec": {
        "figure_id": "Fig-W1_profile",
        "sidecar_key": "figures/Fig-W1_profile.png",
        "master_path": "D:/PolyNexus/results/figures/Fig-W1_profile.svg",
        "preview_path": "D:/PolyNexus/results/figures/Fig-W1_profile.png",
        "publication_paths": {
          "pdf": "D:/PolyNexus/results/figures/Fig-W1_profile.pdf"
        },
        "available_formats": ["svg", "png", "pdf"],
        "preferred_master_format": "svg",
        "width_px": 1800,
        "height_px": 1200,
        "dpi": 300,
        "figsize_in": [6.0, 4.0],
        "background": "#FFFFFF"
      },
      "style": {
        "title": "",
        "xlabel": "",
        "ylabel": "",
        "colour_scheme": "Wong (SCI)",
        "font": "Small",
        "line_width": "Normal",
        "figure_size": "Medium (6in)",
        "grid_on": false,
        "grid_alpha": 0.0,
        "bg_color": "#FFFFFF",
        "dpi": 150
      },
      "annotations": [
        {
          "id": "ann-001",
          "type": "text",
          "x": 0.25,
          "y": 0.18,
          "text": "alpha peak",
          "font_size": 12,
          "color": "#111111"
        },
        {
          "id": "ann-002",
          "type": "arrow",
          "x1": 0.35,
          "y1": 0.28,
          "x2": 0.48,
          "y2": 0.40,
          "color": "#D55E00",
          "line_width": 2.0
        }
      ]
    }
  }
}
```

兼容要求：

- 旧 `version=1` 文件没有 `annotations` 时，读取为空列表。
- 旧 `style` 字段继续按现有逻辑应用。
- 旧文件没有 `asset_spec` 时，运行时从图片路径推导临时 spec。
- 写入时使用 `version=2`，但不删除旧字段。
- annotation 坐标使用归一化底图坐标，避免窗口缩放和多格式尺寸差异影响保存结果。

## 6. 任务拆分

### Task 1: 统一图表资产规格

**Files:**
- Create: `polynexus/core/figure_assets.py`
- Create: `tests/test_figure_assets.py`

- [x] **Step 1: 写失败测试**

测试内容：
- 同一目录下有 `Fig-W1_profile.svg/png/pdf` 时，资产组识别为同一个 `figure_id`。
- 有 SVG 时 `preferred_master_format == "svg"` 且 `master_path` 指向 SVG。
- `preview_path` 优先指向 PNG；没有 PNG 时可回退到 SVG/PDF。
- `sidecar_key` 使用相对输出根目录的 POSIX 路径。

Run:

```powershell
pytest tests/test_figure_assets.py -q
```

Expected:

```text
FAILED tests/test_figure_assets.py::test_figure_asset_spec_prefers_svg_master_and_png_preview
```

- [ ] **Step 2: 实现最小规格模块**

实现建议：
- 定义 `FigureAssetSpec` dataclass。
- 定义 `discover_figure_asset(path: str, output_root: str | None = None) -> FigureAssetSpec`。
- 定义 `figure_id_from_path(path: str) -> str`。
- 定义 `sidecar_key_for_path(path: str, output_root: str | None = None) -> str`。
- 定义格式优先级：master 为 `svg > pdf > png > jpg`，preview 为 `png > jpg > svg > pdf`，publication 为 `pdf > svg > png`。

- [ ] **Step 3: 运行测试确认通过**

Run:

```powershell
pytest tests/test_figure_assets.py -q
```

Expected:

```text
all tests passed
```

### Task 2: Annotation 数据模型

**Files:**
- Create: `polynexus/gui/figure_annotations.py`
- Create: `tests/test_figure_annotations.py`

- [ ] **Step 1: 写失败测试**

测试内容：
- `FigureAnnotationState` 能 round-trip。
- 缺少 `annotations` 时返回空列表。
- 未知 annotation type 保留但标记为 `unknown`，不导致读取失败。

Run:

```powershell
pytest tests/test_figure_annotations.py -q
```

Expected:

```text
FAILED tests/test_figure_annotations.py::test_annotation_state_round_trip
```

- [ ] **Step 2: 实现最小数据模型**

实现建议：
- 用 dataclass 表达 `AnnotationState`。
- 用普通 dict/list 保持 JSON 兼容。
- 提供 `normalize_annotation_payload(payload: dict) -> dict`。
- 提供 `load_annotations_from_entry(entry: dict) -> list[dict]`。
- 提供 `save_annotations_to_entry(entry: dict, annotations: list[dict]) -> dict`。

- [ ] **Step 3: 运行测试确认通过**

Run:

```powershell
pytest tests/test_figure_annotations.py -q
```

Expected:

```text
3 passed
```

### Task 3: 扩展 plot_edits sidecar

**Files:**
- Modify: `polynexus/core/plot_edits.py`
- Test: `tests/test_plot_edits.py`

- [ ] **Step 1: 写失败测试**

测试内容：
- `save_figure_edit()` 可以保存 style + annotations。
- `load_figure_edit()` 旧行为不变，只返回 style。
- 新增 `load_figure_annotations()` 返回 annotations。
- 新增 `load_figure_asset_spec()` 返回 asset spec，旧 sidecar 没有该字段时返回 `{}`。

Run:

```powershell
pytest tests/test_plot_edits.py -q
```

Expected:

```text
FAILED tests/test_plot_edits.py::test_plot_edits_persist_annotations
```

- [ ] **Step 2: 增加 API**

新增函数：

```python
def load_figure_annotations(figure_path: str) -> list[dict]:
    ...

def save_figure_annotations(figure_path: str, annotations: list[dict]) -> tuple[Path, str]:
    ...

def load_figure_asset_spec(figure_path: str) -> dict:
    ...

def save_figure_asset_spec(figure_path: str, asset_spec: dict) -> tuple[Path, str]:
    ...
```

修改 `save_figure_edit()`：
- 保留已有 annotations，不因保存 style 被清空。
- 保留已有 asset spec，不因保存 style 被清空。
- 写入 `version=2`。

- [ ] **Step 3: 回归旧测试**

Run:

```powershell
pytest tests/test_plot_edits.py -q
```

Expected:

```text
all tests passed
```

### Task 4: 静态标注画布

**Files:**
- Create: `polynexus/gui/widgets/annotation_canvas.py`
- Create: `tests/test_annotation_canvas.py`

- [ ] **Step 1: 写失败测试**

测试内容：
- 加载 80x40 PNG 后画布有底图。
- 调用 `add_text_annotation("Edited", 10, 10)` 后 annotation 数量为 1。
- annotation 状态保存为归一化坐标。
- `render_to_image()` 返回非空 `QImage`。

Run:

```powershell
pytest tests/test_annotation_canvas.py -q
```

Expected:

```text
FAILED tests/test_annotation_canvas.py::test_annotation_canvas_renders_text_overlay
```

- [ ] **Step 2: 实现最小画布**

实现范围：
- `AnnotationCanvas(QWidget)` 内部使用 `QGraphicsView` + `QGraphicsScene`。
- `load_image(path: str) -> bool`。
- `add_text_annotation(text: str, x: float, y: float) -> str`。
- `annotation_state() -> list[dict]`。
- `render_to_image(bg_color: str = "#FFFFFF") -> QImage`。

暂不实现完整工具栏，只保证 API 可用。

- [ ] **Step 3: 运行测试确认通过**

Run:

```powershell
pytest tests/test_annotation_canvas.py -q
```

Expected:

```text
1 passed
```

### Task 5: ChartEditor 接入静态画布

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/core/figure_assets.py`
- Test: `tests/test_chart_editor.py`

- [ ] **Step 1: 写失败测试**

测试内容：
- `set_source_figure()` 后静态模式使用 annotation canvas。
- `set_source_figure()` 会调用 `discover_figure_asset()` 得到 master/preview/spec。
- 添加文本标注后 `save_to_target()` 会改变当前图片文件。
- `plot_edits.json` 写入 annotations。

Run:

```powershell
pytest tests/test_chart_editor.py::test_chart_editor_static_annotation_save_updates_file_and_sidecar -q
```

Expected:

```text
FAILED tests/test_chart_editor.py::test_chart_editor_static_annotation_save_updates_file_and_sidecar
```

- [ ] **Step 2: 接入画布**

实现要求：
- 静态模式隐藏 Matplotlib toolbar。
- 左侧显示真实底图 + overlay canvas。
- 优先加载 `FigureAssetSpec.preview_path`，保存时按当前目标路径写出。
- 现有标题/X/Y 输入先保留，保存时仍可烘焙。
- 新增内部方法 `_save_static_canvas_to_path(path: Path) -> bool`。
- 保存成功后 emit `figure_saved`。

- [ ] **Step 3: 保留旧行为兼容**

兼容要求：
- 有 `_fig_generator` 时仍走现有 Matplotlib 保存。
- 静态文件加载失败时仍回退到当前 `_show_placeholder_style_preview()`。
- SVG/PDF 首屏预览继续通过现有 `FigureFilePreview._load_pixmap()` 渲染。

- [ ] **Step 4: 运行相关测试**

Run:

```powershell
pytest tests/test_chart_editor.py tests/test_chart_viewer.py tests/test_plot_edits.py -q
```

Expected:

```text
all tests passed
```

### Task 6: 工具栏和对象操作

**Files:**
- Modify: `polynexus/gui/widgets/annotation_canvas.py`
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/i18n.py`
- Test: `tests/test_annotation_canvas.py`

- [ ] **Step 1: 写失败测试**

测试内容：
- 添加矩形 annotation 后可序列化。
- 删除选中 annotation 后状态减少。
- undo/redo 恢复 annotation 数量。

Run:

```powershell
pytest tests/test_annotation_canvas.py -q
```

Expected:

```text
FAILED tests/test_annotation_canvas.py::test_annotation_canvas_undo_redo_annotation_changes
```

- [ ] **Step 2: 增加工具状态**

工具集合：
- Select
- Text
- Arrow
- Line
- Rectangle
- Highlight

UI 要求：
- 顶部工具栏使用短按钮或图标。
- 当前工具有明显选中态。
- 删除可用 `Delete` 快捷键。
- 撤销 `Ctrl+Z`，重做 `Ctrl+Y`。

- [ ] **Step 3: 增加对象属性**

每个对象至少支持：
- 位置
- 颜色
- 线宽或字号
- 文本内容

第一版不做复杂右侧属性面板，选中对象后可以通过默认属性创建，后续再补属性编辑。

- [ ] **Step 4: 运行 UI 相关回归**

Run:

```powershell
pytest tests/test_annotation_canvas.py tests/test_chart_editor.py -q
```

Expected:

```text
all tests passed
```

### Task 7: 另存为和覆盖保护

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Test: `tests/test_chart_editor.py`

- [ ] **Step 1: 写失败测试**

测试内容：
- 另存为新路径时原文件字节不变。
- 新文件存在且包含标注结果。
- 新路径有自己的 sidecar entry。
- 新路径写入自己的 `asset_spec`，不复用原图 sidecar key。

Run:

```powershell
pytest tests/test_chart_editor.py::test_chart_editor_static_save_as_keeps_original_file -q
```

Expected:

```text
FAILED tests/test_chart_editor.py::test_chart_editor_static_save_as_keeps_original_file
```

- [x] **Step 2: 实现保存策略**

保存策略：
- “保存到当前图”：覆盖当前文件。
- “另存为”：写新文件，不改原文件。
- 覆盖当前静态源图前自动生成同目录 `.bak` 备份，已存在时保留原备份不反复覆盖。
- 如果目标文件已存在，沿用 Qt 保存对话框确认行为。
- sidecar entry 按目标文件路径写入。

- [x] **Step 3: 运行回归**

Run:

```powershell
pytest tests/test_chart_editor.py -q
```

Expected:

```text
all tests passed
```

### Task 8: i18n 和用户反馈收口

**Files:**
- Modify: `polynexus/gui/i18n.py`
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Test: `tests/test_chart_editor.py`

- [ ] **Step 1: 写失败测试**

测试内容：
- `retranslate()` 会更新新增工具按钮文本。
- 静态模式提示不再说“重绘后生效”。

Run:

```powershell
pytest tests/test_chart_editor.py::test_chart_editor_retranslate_updates_annotation_tools -q
```

Expected:

```text
FAILED tests/test_chart_editor.py::test_chart_editor_retranslate_updates_annotation_tools
```

- [ ] **Step 2: 调整文案**

中文建议：
- “选择”
- “文字”
- “箭头”
- “线段”
- “矩形”
- “高亮”
- “撤销”
- “重做”
- “保存到当前图”
- “另存为”
- “已保存到当前图，并写入编辑记录。”

英文建议：
- “Select”
- “Text”
- “Arrow”
- “Line”
- “Rectangle”
- “Highlight”
- “Undo”
- “Redo”
- “Save to Current Figure”
- “Save As”
- “Saved to current figure and wrote edit state.”

- [ ] **Step 3: 回归 i18n 测试**

Run:

```powershell
pytest tests/test_chart_editor.py -q
```

Expected:

```text
all tests passed
```

### Task 9: 阶段收口回归

**Files:**
- No new production files.
- Tests: existing chart-related tests.

- [x] **Step 1: 运行局部回归**

Run:

```powershell
pytest tests/test_annotation_canvas.py tests/test_chart_editor.py tests/test_chart_viewer.py tests/test_plot_edits.py -q
pytest tests/test_figure_assets.py tests/test_figure_annotations.py -q
```

Expected:

```text
all tests passed
```

- [x] **Step 2: 检查空白和 diff**

Run:

```powershell
git diff --check -- polynexus/core/figure_assets.py polynexus/gui/widgets/chart_editor.py polynexus/gui/widgets/annotation_canvas.py polynexus/gui/figure_annotations.py polynexus/core/plot_edits.py polynexus/gui/i18n.py tests/test_figure_assets.py tests/test_annotation_canvas.py tests/test_chart_editor.py tests/test_plot_edits.py
```

Expected:

```text
no whitespace errors
```

- [ ] **Step 3: 手动验收**

手动流程：
- 打开 GUI。
- 运行一次任意能产图的分析。
- 进入图表页。
- 选中一张 PNG 或 SVG。
- 点击编辑。
- 添加文本、箭头、矩形。
- 保存到当前图。
- 回到图表页确认缩略图和大预览刷新，且不会触发自动重绘覆盖刚保存的标注。
- 重新打开编辑器，确认 annotation state 可读取。
- 另存为副本，确认原图未被覆盖，且新副本出现在图库并成为当前选中图。

## 6. 验收标准

第一阶段完成后，必须满足：

- 用户能直接对当前成品图添加文字、箭头、矩形、高亮。
- 点击保存后，当前图文件立即变化，无需再点“重新绘图”。
- 静态成品图保存后只刷新图库和预览，不自动触发 `_replot()`。
- 点击另存为时，原图不被破坏。
- 另存为新文件后，图库追加新文件缩略图并切换当前选中路径。
- `plot_edits.json` 同时保存 style 和 annotations。
- 同一图的 SVG/PNG/PDF 能被识别为同一资产组。
- `asset_spec` 能记录 SVG/PNG/PDF/JPG 的基础尺寸，保存 sidecar 时带上真实宽高。
- 旧图表样式模板功能不回归。
- 图表预览、缩略图刷新、复制路径、打开文件等现有功能不回归。

## 7. 风险与控制

- **风险：ChartEditor 继续膨胀。**
  - 控制：把 annotation 画布拆到 `annotation_canvas.py`，把 schema 拆到 `figure_annotations.py`。

- **风险：SVG/PDF 渲染和保存格式不一致。**
  - 控制：第一阶段按当前可见渲染结果烘焙保存；需要保持矢量对象可编辑时，后续单独做 SVG overlay 导出。

- **风险：静态标注和重绘样式互相覆盖。**
  - 控制：`style` 和 `annotations` 分字段保存；保存 style 不清空 annotations。

- **风险：用户误覆盖原始导出图。**
  - 控制：保留“另存为”主路径；保存到当前静态源图前自动创建同目录 `.bak`，避免第一次覆盖后无法回退原始图。

## 8. 推荐里程碑

### M1: 统一规格和可保存的静态标注最小闭环

包含 Task 1-5。

交付效果：
- 能识别同一张图的 SVG/PNG/PDF 资产组。
- 能打开图。
- 能通过 API 或最小 UI 加文字。
- 能保存当前图。
- 能写 sidecar。

### M2: 可用工具栏

包含 Task 6。

交付效果：
- 选择、文字、箭头、线段、矩形、高亮可用。
- 支持删除、撤销、重做。

### M3: 交付级体验

包含 Task 7-9。

交付效果：
- 另存为不破坏原图。
- 文案清楚。
- 局部回归通过。
- 手动流程可完成。

## 9. 后续增强方向

后续可以继续做，但不进入第一阶段：

- SVG overlay 矢量保存，保留文字和箭头为可编辑 SVG 元素。
- 对 Matplotlib 原始 figure 做对象级编辑，例如曲线颜色、legend、峰标签。
- 标注模板，例如“一键添加期刊 panel label (a)(b)(c)”。
- 自动峰标注：从分析结果读取 peak table，自动生成箭头和标签。
- 导出前检查：DPI、字体、中文字符、图中标题、线宽、期刊尺寸。

## 10. 开工建议

建议先做 M1，不要一开始做完整工具栏。

第一刀只要完成：
- `figure_assets.py`
- `figure_annotations.py`
- `annotation_canvas.py` 的最小文本 overlay
- `ChartEditor` 静态模式保存 overlay 到当前图
- 对应测试

这会最快把功能从“格式不稳定、只能设置”推进到“有统一图表规格，并且真的能编辑图片”。之后再补箭头、矩形、高亮和撤销重做，用户体验会自然变得完整。
