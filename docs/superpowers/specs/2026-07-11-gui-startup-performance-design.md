# GUI Startup Performance Design

**Date:** 2026-07-11

## Goal

让 `polynexus --gui` 和 `polynexus-gui` 尽快显示一个可交互的主窗口，验收点是主窗口可见且首屏数据输入控件可操作，目标冷启动时间不超过 3 秒。

## Scope

### In scope

- 延迟 GUI 入口对重量级模块的导入。
- 将主窗口初始化拆成首屏初始化和非首屏初始化两个阶段。
- 首屏创建顶部栏、侧栏、数据输入区、基础状态栏和日志区。
- 主窗口显示并进入事件循环后，再创建配置、结果、图表、历史、样品库和联合分析等非首屏控件。
- 保留 `MainWindow()` 的默认同步初始化行为，兼容现有 GUI 单元测试和内部调用方。
- 增加首屏阶段、延迟阶段和启动计时点的回归测试。

### Out of scope

- 不修改 DSC、IR、WAXS、SAXS、NMR 或联合分析算法。
- 不修改 `AnalysisResult`、持久化 schema、导出格式和用户数据迁移策略。
- 不重写 `MainWindow` 或拆分现有 mixin 体系。
- 不通过删除功能、关闭错误处理或跳过必要校验来换取启动速度。

## Design

`polynexus.app` 只负责创建 Qt 应用、延迟导入 `MainWindow`、构造窗口并启动事件循环。GUI 入口使用 `MainWindow(defer_optional_ui=True)`；直接构造 `MainWindow()` 时仍采用现有同步路径。

延迟模式下，`MainWindow.__init__` 只创建轻量的 shell 和数据输入首屏，并把非首屏 tab 替换为明确的加载占位页。窗口显示后，入口调用 `schedule_deferred_startup()`，该方法使用 Qt 事件循环调度 `finish_deferred_startup()`。后者按既有 builder 顺序创建真实 tab 和可选 widget，完成信号连接、主题翻译和状态刷新，并且是幂等的。延迟初始化发生异常时写入日志并将占位页替换为可操作的错误提示，不能阻塞首屏。

重量级组件（核心引擎、图表预览、联合分析 hub、样品浏览器）只在对应 builder 或延迟阶段导入；不改变这些组件的公开类和既有信号契约。

## State and compatibility

- 延迟模式必须在首屏阶段初始化所有首屏事件处理所需的属性。
- 延迟 tab 完成前，导航和 tab 切换不会触发未创建组件的业务逻辑。
- `finish_deferred_startup()` 重复调用不重复创建 widget 或重复连接信号。
- 默认同步模式继续让现有测试直接访问完整组件。

## Testing and acceptance

- 首屏回归测试验证延迟模式构造后已有数据文件输入控件、窗口标题和基础导航。
- 延迟阶段回归测试验证完成后所有原有 tab 和可选组件存在，且重复调用保持幂等。
- 入口测试验证 `app.main` 在启动 probe 模式下可构造并显示窗口而不进入永久事件循环。
- 启动计时测试输出应用创建、窗口可见、首屏可交互和延迟初始化完成四个阶段；性能结果作为环境相关证据记录，不把不稳定的硬件时间写成科学基线。
- 运行受影响的 GUI 测试，以及 `python scripts/verify.py --changed --types`。

## Risks and rollback

主要风险是延迟阶段与现有 tab 索引、retranslate、主题切换和测试 fixture 的耦合。通过保留同步模式、占位页、幂等 guard 和 focused tests 控制风险。若启动阶段出现兼容性回归，可由入口关闭延迟模式恢复原有同步构造，而不需要回滚业务模块。
