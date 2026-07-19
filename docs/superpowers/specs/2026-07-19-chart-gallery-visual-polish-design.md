# Chart Gallery Visual Polish Design

## Decision

采用“三列卡片精修”方向：保留当前图表浏览密度和公开信号，只整理视觉层级与状态表达。

## Interaction model

- Hover 是短暂的指针反馈：当前卡片显示蓝色 focus 描边和轻微表面提升。
- Selection 是点击后的业务状态：用于当前预览/资产面板，但不再使用高饱和蓝色描边抢占 hover 的视觉语义。
- `select_figure()`、`figure_selected`、`edit_requested` 等既有路径不变。

## Visual structure

- `ChartThumbnail` 自身作为统一卡片容器，包含缩略图、状态/角色徽章、标题和操作区。
- 卡片采用统一内边距、圆角和边界；缩略图只保留轻量内框。
- hover 与 selection 的颜色使用当前主题 token，兼容 dark/light theme。
- 三列布局和滚动容器保持不变，避免改变图库可见密度。

## Testing

- 使用 Qt offscreen 测试创建真实 `ChartThumbnail`，分别验证 hover、leave 和 selected 的样式状态组合。
- 保留现有图库筛选、选中、资源面板和信号回归测试。
