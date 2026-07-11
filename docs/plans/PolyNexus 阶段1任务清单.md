# PolyNexus 阶段 1 任务清单

## 1. 阶段目标

阶段 1 只解决一个问题：修复影响用户第一印象和基本可用性的体验问题，不改核心分析算法，不一次性引入新功能。

这一阶段的关键词：

- 乱码修复
- 文案收敛
- 空入口处理
- 错误提示补齐

## 2. 阶段边界

### 做什么

- 修复 README 和 GUI 中明显乱码
- 统一一批高频界面文案的来源
- 处理已经暴露给用户但尚未完成的入口
- 补齐关键失败场景的提示文案

### 不做什么

- 不改 `SAXS/WAXS/DSC/IR/NMR` 分析逻辑
- 不改数据库结构
- 不做样品库新功能闭环
- 不补联合分析图表能力
- 不改 AI 调参流程

## 3. 任务拆分

### T1. README 修复

目标：
恢复 README 的可读性，让新用户能正常安装、启动并理解项目结构。

涉及文件：

- [README.md](/D:/PolyNexus/README.md)

任务内容：

- 修复标题、技术列表、架构说明中的乱码
- 校正 Quick Start 示例
- 确认 README 中的目录结构与当前仓库基本一致
- 删除会误导用户的过时描述

验收标准：

- GitHub / 编辑器内打开 README 时不再出现明显乱码
- 安装和启动说明可直接照着执行
- 项目定位、模块划分和入口命令表达清楚

风险：

- README 可能混入历史版本结构描述，需要顺手核对而不是只做字符替换

---

### T2. i18n 基础清理

目标：
把最核心的一批 UI 文案收回到统一翻译表，减少后续继续出现硬编码和乱码的机会。

涉及文件：

- [polynexus/gui/i18n.py](/D:/PolyNexus/polynexus/gui/i18n.py)
- [polynexus/gui/main_window.py](/D:/PolyNexus/polynexus/gui/main_window.py)
- [polynexus/gui/widgets/chart_viewer.py](/D:/PolyNexus/polynexus/gui/widgets/chart_viewer.py)
- [polynexus/gui/widgets/chart_editor.py](/D:/PolyNexus/polynexus/gui/widgets/chart_editor.py)
- [polynexus/gui/widgets/sample_browser.py](/D:/PolyNexus/polynexus/gui/widgets/sample_browser.py)

任务内容：

- 修复 `i18n.py` 中已经损坏的中文词条
- 优先补齐高频区域的 key：
  `样品库`、`联合分析`、`图表查看器`、`图表编辑器`、`结果导出`
- 减少这些文件里的中文硬编码
- 统一处理中英文切换时的默认文案

验收标准：

- 主窗口、样品库、图表查看器、设置页中的高频按钮和提示不再乱码
- 同一类按钮和状态文案在不同页面表达一致
- 中英文切换不会出现一部分翻译、一部分硬编码混杂的明显割裂

风险：

- 当前 `i18n.py` 本身已经存在乱码，不能机械替换，必须逐项校对

---

### T3. 空入口处理

目标：
确保界面上保留下来的入口都能给出确定反馈，不再让用户点到“没有任何反应”的按钮。

涉及文件：

- [polynexus/gui/widgets/sample_browser.py](/D:/PolyNexus/polynexus/gui/widgets/sample_browser.py)
- [polynexus/gui/main_window.py](/D:/PolyNexus/polynexus/gui/main_window.py)

当前已知空入口：

- `样品库 -> 新建样品`
- `样品库 -> 导出报告`

处理策略建议：

1. 如果阶段 1 不做功能闭环，则先禁用按钮并显示“即将支持”提示
2. 如果成本很低，则补最小可用占位对话框，明确说明当前阶段能力边界

本阶段推荐：

- 默认采用“禁用或提示”而不是直接补完整功能

验收标准：

- 用户点击这些入口时，不会出现静默无响应
- 所有未实现功能都能被明确识别出来
- 不会让用户误以为功能损坏

风险：

- 如果只隐藏入口而不梳理相关流程，后续做阶段 2 时可能需要再调 UI

---

### T4. 错误提示与失败反馈补齐

目标：
当用户失败时，至少能知道自己是选错文件、技术不匹配、导出失败，还是数据库落库失败。

涉及文件：

- [polynexus/__main__.py](/D:/PolyNexus/polynexus/__main__.py)
- [polynexus/core/engine.py](/D:/PolyNexus/polynexus/core/engine.py)
- [polynexus/gui/main_window.py](/D:/PolyNexus/polynexus/gui/main_window.py)
- [polynexus/gui/widgets/chart_viewer.py](/D:/PolyNexus/polynexus/gui/widgets/chart_viewer.py)

任务内容：

- 清理 CLI 中用户可见的乱码输出
- 统一“未知技术”“文件格式不支持”“导出失败”“预览失败”等错误表达
- 把关键错误区分成用户可修复和内部异常两类
- 避免把纯日志文本直接暴露成用户提示

验收标准：

- CLI 常见失败信息可以直接读懂
- GUI 中失败提示能够帮助定位问题
- 日志保留详细异常，界面提示保持简洁

风险：

- 如果日志和用户提示没有分层，容易修着修着把调试信息也冲掉

---

### T5. 高频页面文本巡检

目标：
把最常被高频用户打开的页面逐页扫一遍，避免阶段 1 做完后还残留一堆刺眼的小问题。

建议巡检页面：

- 主窗口顶部和侧边栏
- 数据页
- 结果页
- 图表页
- 样品库
- 联合分析工作台
- 设置页

涉及文件：

- [polynexus/gui/main_window.py](/D:/PolyNexus/polynexus/gui/main_window.py)
- [polynexus/gui/widgets/sample_browser.py](/D:/PolyNexus/polynexus/gui/widgets/sample_browser.py)
- [polynexus/gui/widgets/joint_analysis_hub.py](/D:/PolyNexus/polynexus/gui/widgets/joint_analysis_hub.py)
- [polynexus/gui/widgets/chart_viewer.py](/D:/PolyNexus/polynexus/gui/widgets/chart_viewer.py)
- [polynexus/gui/widgets/chart_editor.py](/D:/PolyNexus/polynexus/gui/widgets/chart_editor.py)
- [polynexus/gui/widgets/settings_dialog.py](/D:/PolyNexus/polynexus/gui/widgets/settings_dialog.py)

任务内容：

- 检查是否还有残留乱码
- 检查中英文混用是否突兀
- 检查按钮名称、状态文案、空状态文案是否一致
- 检查空页面是否给出有用提示

验收标准：

- 主路径页面不再出现明显乱码
- 高级功能没做完也不会显得“坏掉”
- UI 语言表现达到“可信、能懂、不会出戏”的水平

## 4. 推荐实施顺序

建议按下面顺序做：

1. `T1 README 修复`
2. `T2 i18n 基础清理`
3. `T3 空入口处理`
4. `T4 错误提示补齐`
5. `T5 高频页面巡检`

原因：

- 先修文档和翻译表，后面改界面文案时成本最低
- 空入口和错误提示要晚于文案收敛，不然会重复返工
- 最后做巡检，适合作为阶段收口动作

## 5. 回归检查

阶段 1 完成后，至少检查以下场景：

1. 打开 README，确认安装和启动说明可读
2. 启动 GUI，确认主界面和侧边栏无明显乱码
3. 切换中英文，确认高频文案正常
4. 进入样品库，确认按钮和表头可读
5. 点击未完成入口，确认有明确反馈
6. 导入不匹配文件，确认错误提示可读
7. 打开图表查看器，确认空状态和失败状态可读

## 6. 阶段完成定义

满足下面条件即可视为阶段 1 完成：

- 用户首次打开项目时，不再因为乱码和空入口怀疑软件已损坏
- 用户在主流程中遇到失败时，能够知道问题大概出在哪
- 高亮暴露给用户的界面入口都已具备最小可解释性
- 没有改动核心分析流程和数据库结构

## 7. 后续衔接

阶段 1 完成后，下一步进入阶段 2：样品库最小闭环。

阶段 2 开始前建议先复用本清单的输出，尤其是：

- 已整理的文案 key
- 已清理的空入口策略
- 已统一的错误提示风格
