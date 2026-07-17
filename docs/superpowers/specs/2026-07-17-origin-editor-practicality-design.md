# Origin Editor Practicality and Unified Editing Core

Status: Draft for user review

## Goal

把当前 Origin 编辑器提升为“画布优先、上下文驱动、可连续完成工作”的专业图表编辑器，同时保留向数据驱动绘图、重绘和拟合能力扩展的架构边界。

第一阶段优先保证已有 PNG/SVG/生成图表的发表级后处理可靠可用；第二阶段再接入 Origin 风格的数据、配方、坐标轴和绘图能力。

## Scope and non-goals

### In scope

- 统一生成图对象与静态图标注的选择、样式、几何、层级、撤销/重做和保存协议。
- 顶部上下文工具条、画布反馈、右侧 Inspector、对象列表之间的状态同步。
- 线条颜色/线型/线宽、文字内容/字号/颜色、矩形和高亮等基础编辑能力。
- 图表文档的版本化迁移、保存、导出和失败反馈。
- 为第二阶段的数据源、绘图配方和重新生成图表保留稳定接口。

### Out of scope for phase 1

- 完整替代 Origin 的数据表、统计分析、拟合引擎和科学计算工作流。
- 一次性支持所有图表类型、所有 Matplotlib artist 和任意第三方绘图后端。
- 在没有对象能力声明的情况下开放任意属性编辑。

## Current architecture assessment

现有代码已经具备渐进式改造所需的底座，但编辑状态仍然分裂：

- `polynexus/core/figure_document.py` 已经提供 JSON-friendly 的文档、对象、图层、数据源、配方和导出字段，并有 `normalize_figure_document()` 作为兼容入口。
- `polynexus/gui/figure_render_adapter.py` 已经负责生成图对象到 Matplotlib artist 的映射、命中测试和选择/悬停反馈。
- `polynexus/gui/figure_selection_model.py` 已经提供生成图对象的选择信号，但当前选择模型只有一个 `object_id/source`，静态标注没有接入同一协议。
- `polynexus/gui/widgets/annotation_canvas.py` 同时持有 QGraphicsScene、`_annotations`、自己的 undo/redo 栈和标注属性更新逻辑；它是一个可工作的子系统，但没有成为全编辑器唯一状态源。
- `polynexus/gui/widgets/chart_editor.py` 及多个 mixin 根据静态图、生成图和标注画布分别分支，导致控件同步、绘制、保存和脏状态容易出现不同步。
- `polynexus/gui/widgets/chart_editor_save_mixin.py` 仍需同时写 legacy edit、annotation sidecar、figure document 和最终渲染资产；这些文件没有由一个编辑事务统一产生。

因此当前架构适合支持第一阶段的 Origin-style 后处理，但不适合直接堆叠完整 Origin 功能。第一阶段必须先补上统一编辑核心；第二阶段的数据功能应建立在该核心之上，而不是继续往 UI mixin 中添加分支。

## Design principles

1. 文档状态是唯一真相；Qt 控件和画布渲染都是投影。
2. 每个用户动作都通过可描述的编辑命令进入状态，撤销/重做不再由多个组件各自维护。
3. 选择对象后只暴露该对象声明支持的属性；禁用控件必须说明原因。
4. 任何成功编辑都立即更新画布、Inspector、对象列表、脏状态和可保存文档。
5. 旧文档可读、旧导出可恢复；新字段通过版本化迁移加入。
6. 数据重绘属于“源对象/配方”能力，标注属于“画布对象”能力，两者共享编辑核心但不互相污染。

## Target architecture

### 1. Canonical scene document

继续以 `figure_document.py` 为持久化入口，把生成对象和静态标注都规范化为 `document["objects"]` 中的对象。静态背景仍是锁定的 `image_background` 对象；文字、线、箭头、矩形、高亮使用统一的对象字段：

```text
object = {
  id, type, name, visible, locked, layer_id,
  bounds or endpoint geometry,
  style,
  capabilities,
  source_ref (optional),
  data_ref (optional)
}
```

`normalize_figure_document()` 负责把现有 annotation sidecar、旧对象字段和缺失的 layer/capability 字段迁移成该形态。迁移必须幂等，不能因为打开并保存旧文件而丢失未知字段。

### 2. Edit session

新增一个不依赖 Qt widget 的编辑会话核心，至少包含：

- 当前规范化 document
- 当前选择（先支持单选，同时为多选保留集合接口）
- `dirty` 状态
- undo/redo 命令栈
- 文档变更事件和选择变更事件
- 校验错误与最后一次失败动作

`ChartEditor` 只负责把 Qt 事件转成 session 操作，并把 session 状态投影到控件。`AnnotationCanvas` 和 Matplotlib render adapter 不再各自决定持久化状态。

### 3. Command protocol

所有改变文档的动作使用统一命令协议：

```text
execute(session) -> EditResult
undo(session) -> EditResult
redo(session) -> EditResult
description -> user-visible action label
```

第一阶段命令包括：

- `AddObjectCommand`
- `DeleteObjectCommand`
- `UpdateStyleCommand`
- `UpdateTextCommand`
- `UpdateGeometryCommand`
- `MoveLayerCommand`
- `SetVisibilityCommand`
- `PasteObjectCommand`
- `CropCanvasCommand`

命令必须先校验对象能力和字段范围；失败时不改变 document、不清空选择、不吞掉异常，并返回可显示的原因。

### 4. Capability registry

每种对象类型声明自己的能力，例如：

```text
text:       text, color, font_size, geometry, deletable, reorderable
line:       color, line_width, line_style, geometry, deletable, reorderable
plot_series: color, line_width, line_style, marker, marker_size, point_geometry
legend:     geometry, text, deletable, reorderable
background: visibility, crop, locked
```

Inspector 根据 capability schema 生成或启用控件，而不是由 `ChartEditorAnnotationControlsMixin` 维护大量对象类型分支。未支持的属性必须显示为 disabled 或 hidden，并带简短说明。

### 5. Rendering boundary

渲染分为两类，但都读取同一份 document：

- `MatplotlibRenderAdapter`：负责生成对象、坐标轴、plot series、legend 等可重绘内容。
- `AnnotationRenderAdapter`：负责静态背景上的文字、线、箭头、矩形、高亮等覆盖对象。

两者都必须返回 object id 到可视对象的映射，供统一 selection model 使用。渲染失败只影响当前对象并产生明确错误，不得让 Inspector 显示“已应用”而画布保持旧状态。

### 6. Persistence transaction

保存时从 session 的 canonical document 生成一个版本化保存包：

- `.pnfig.json`：规范化文档和可恢复编辑状态
- 目标图像文件：由同一份文档渲染得到
- legacy sidecar：仅作为兼容输出，不能再作为编辑真相

保存应使用临时文件、校验后替换，并在失败时保留原文件和脏状态。导出成功后才更新 `last_exported` 和 saved badge。

## Phase 1: reliable publication editing

### User flow

1. 打开图表时不自动弹出额外预览；编辑器直接进入可编辑画布。
2. 用户在画布或对象列表选择对象；顶部工具条显示当前工具和对象类型。
3. Inspector 只显示当前对象可用属性。
4. 改色、改线型、改文字或拖动几何后，画布立即反馈，状态栏显示已修改对象。
5. Ctrl+Z/Ctrl+Shift+Z 撤销或重做同一套命令。
6. 保存/导出从同一 session 文档生成，失败时保留修改并报告原因。

### Phase 1 acceptance criteria

- 对 line/arrow/text/rectangle/highlight/plot_series 至少各有一条端到端测试，覆盖选择 → 修改 → 画布/文档状态 → 保存后重新加载。
- 改颜色后，渲染对象、Inspector 值、规范化文档三者在同一事件循环内一致。
- 文字新增、编辑、移动、复制、删除和撤销重做不会丢失文本或选中状态。
- 任意对象的非法颜色、非法数值、越界几何都不会破坏原状态。
- 保存失败不会清除 dirty 状态，且不会覆盖上一次成功导出。
- 640px 宽窗口下画布仍保持可操作宽度，Inspector 不产生不可见的横向控件。

## Phase 2: Origin-style data-aware editing

第二阶段在不改变 Phase 1 命令协议的前提下加入数据能力：

- `DataSource`：CSV、内存数组、项目结果表等统一数据引用。
- `PlotRecipe`：图表类型、字段映射、筛选、分组、统计/拟合参数和样式模板。
- 数据预览和字段选择面板。
- 坐标轴标题、范围、刻度、对数/线性尺度、单位和格式化。
- 多图层/多面板布局和图例配置。
- 重绘命令与“保留现有标注”的绑定策略。
- 数据缺失、配方过期和重绘失败的可恢复错误状态。

数据对象的重绘只更新由 `source_ref/data_ref` 管理的对象；用户手工添加的 annotation object 默认保留。需要删除或重定位标注时必须有明确提示和可撤销命令。

## Error and compatibility behavior

- 所有旧文档先经过版本迁移，再进入 edit session；迁移失败时以只读预览打开，并明确提示不可编辑原因。
- 能力不完整的对象仍可移动、隐藏或删除（如果这些能力存在），不能因为一个属性不支持而让整个 Inspector 失效。
- 渲染失败、保存失败、数据源缺失和导出失败使用不同错误类别，状态栏提供下一步动作。
- 不在正常打开图表路径中递归发现或隐式修改历史文件。

## Testing strategy

### Core tests

- 文档迁移、规范化、未知字段保留和幂等性。
- 每个 command 的 execute/undo/redo、非法输入和 no-op 行为。
- capability schema 与 Inspector 字段映射。
- persistence transaction 的成功、失败恢复和旧 sidecar 兼容。

### Qt integration tests

- 画布选择、对象列表选择、Inspector 修改三者互相同步。
- 改色、改线型、加文字、编辑文字和保存重载的端到端路径。
- 键盘快捷键、连续撤销/重做、窗口窄尺寸和多语言布局。

### Visual regression checks

- line/text/rectangle/legend/plot_series 的选中反馈。
- 选中对象、悬停对象、不可编辑对象的视觉差异。
- 640px、1024px 和宽屏下画布/Inspector 的最小可用布局。
- 导出 PNG/SVG/PDF 与编辑器预览的一致性。

## Rollout and migration

1. 先新增 core edit session、command 和 capability 测试，不改变用户入口。
2. 把静态标注接入 canonical document，保留 sidecar 兼容读写。
3. 把生成对象样式和几何修改迁移到同一命令协议。
4. 接入 A 方向顶部工具条和上下文 Inspector。
5. 完成 Phase 1 端到端验收后，再开始 DataSource/PlotRecipe 和重绘能力。

每一步都必须保持旧图表可打开、可导出，并能从失败保存中恢复；不把 Phase 2 的数据模型提前混入 Phase 1 的 UI 分支。
