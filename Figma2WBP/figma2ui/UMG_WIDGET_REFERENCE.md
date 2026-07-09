# UMG Widget Type Reference (Figma2UI)

Figma2UI 转换时可使用的 UMG 控件类型一览。
AI 参考本文档为每个 Figma 节点选择合适的 UMG 类型。
每个类型标注了：适用场景、对应的 Figma 源类型、以及使用指南。

---

## 布局容器类 (Layout Containers)

### CanvasPanel
- **UMG 类名**: `UCanvasPanel`
- **用途**: 绝对定位容器，子控件通过 (x, y) 坐标自由放置
- **适用场景**:
  - 页面根节点 / 顶层 Frame
  - 子控件位置不遵循水平或垂直排列规律
  - 需要重叠放置多个控件时（如背景 + 前景）
  - 一个或多个子节点需要自由定位组合的 FRAME（如矢量图标由多条路径组合）
  - GROUP 类型节点（自由布局）
- **Figma 对应**: 根 FRAME、GROUP、或子节点坐标无明显行列规律的 FRAME
- **使用指南**: 根节点自动判定；GROUP 类型自动判定；未知类型的 fallback

### VerticalBox
- **UMG 类名**: `UVerticalBox`
- **用途**: 垂直方向依次排列子控件
- **适用场景**:
  - Figma autoLayout.layoutMode == "VERTICAL" 的 FRAME（上下文中显示 `autoLayout=VERTICAL`）
- **Figma 对应**: 上下文中明确标注 `autoLayout=VERTICAL` 的 FRAME
- **使用指南**: **仅当**上下文显示 `autoLayout=VERTICAL` 时才使用，否则不得选用此类型

### HorizontalBox
- **UMG 类名**: `UHorizontalBox`
- **用途**: 水平方向依次排列子控件
- **适用场景**:
  - Figma autoLayout.layoutMode == "HORIZONTAL" 的 FRAME（上下文中显示 `autoLayout=HORIZONTAL`）
- **Figma 对应**: 上下文中明确标注 `autoLayout=HORIZONTAL` 的 FRAME
- **使用指南**: **仅当**上下文显示 `autoLayout=HORIZONTAL` 时才使用，否则不得选用此类型

### WrapBox
- **UMG 类名**: `UWrapBox`
- **用途**: 子控件水平排列，超出宽度时自动换行
- **适用场景**:
  - 技能 / 道具网格（非固定列数）
  - 子控件数量不定，需要自适应宽度换行
- **Figma 对应**: 名称中 `[...]` 内含 WrapBox 的 FRAME
- **使用指南**: 名称 `[...]` 内模式匹配

### UniformGridPanel
- **UMG 类名**: `UUniformGridPanel`
- **用途**: 等宽等高的网格布局
- **适用场景**:
  - 背包格子 / 道具栏
  - 九宫格按钮组
  - 固定行列数的均匀布局
- **Figma 对应**: 名称中 `[...]` 内含 Grid / 格子 / 背包 的 FRAME，且子控件尺寸一致
- **使用指南**: 名称 `[...]` 内模式匹配

### UIScrollBox (自定义)
- **UMG 类名**: `UUIScrollBox` (继承 `UPanelWidget`)
- **用途**: 可滚动区域，替代标准 `UScrollBox`，支持 ListView 模式、网格布局、惯性过滚参数
- **适用场景**:
  - 长列表 / 聊天记录 / 日志
  - 内容高度可能超出容器高度的区域
  - 需要虚拟化 ListView 模式的滚动列表
  - **子控件溢出的 auto-layout FRAME**：上下文中标注 `overflow` 的节点（子控件总尺寸 > 容器在主轴方向的尺寸）
- **Figma 对应**: 名称中 `[...]` 内含 Scroll / 滚动 的 FRAME；或上下文中有 `overflow` 标记的 auto-layout FRAME
- **使用指南**: 名称 `[...]` 内模式匹配 → overflow 标记匹配
- **头文件**: `UI/Element/UIScrollBox.h`

---

## 尺寸与约束类 (Size & Constraint)

### SizeBox
- **UMG 类名**: `USizeBox`
- **用途**: 强制约束子控件尺寸（固定宽/高/最小/最大值）
- **适用场景**:
  - 图标容器（固定 18×18, 24×24 等）
  - 需要固定某个控件尺寸的外层包裹
  - 头像 / 缩略图的固定尺寸框
- **Figma 对应**: 名称中 `[...]` 内含 SizeBox 的 FRAME（固定尺寸的容器），且最多只含有一个子控件
- **使用指南**: 名称 `[...]` 内模式匹配

### ScaleBox
- **UMG 类名**: `UScaleBox`
- **用途**: 按比例缩放子控件以适应容器大小
- **适用场景**:
  - 自适应不同分辨率的整体 UI 缩放
  - 视频 / 画面预览区域
- **Figma 对应**: 通常手动指定，不自动映射
- **使用指南**: 不自动推断，需手动指定

### Spacer
- **UMG 类名**: `USpacer`
- **用途**: 空白占位，填充 Box 布局中的剩余空间
- **适用场景**:
  - 在 HorizontalBox/VerticalBox 中推开左右/上下元素
  - 实现 space-between 效果
- **Figma 对应**: 无可见内容的极小 FRAME 或空白区域
- **使用指南**: 不自动推断，需手动指定

---

## 基础显示类 (Display Widgets)

### TextBlock
- **UMG 类名**: `UTextBlock`
- **用途**: 显示静态文本
- **适用场景**:
  - 标题、正文、标签、数值显示
  - 所有不需要编辑的文本内容
- **Figma 对应**: TEXT 类型节点
- **使用指南**: figmaType == "TEXT" → 自动判定

### RichTextBlock
- **UMG 类名**: `URichTextBlock`
- **用途**: 显示富文本（混合粗体/颜色/大小）
- **适用场景**:
  - 同一段文本中有不同样式（如粗体关键词 + 正常正文）
  - 带内联图标的文本
  - 聊天消息、公告内容
- **Figma 对应**: 多个相邻 TEXT 节点且样式不同时的父容器
- **使用指南**: 不自动推断（需分析子节点 TEXT 样式差异后手动指定）

### Image
- **UMG 类名**: `UImage`
- **用途**: 显示图片 / 纹理 / 材质
- **适用场景**:
  - 图标图片、背景图、装饰图
  - 纯色矩形块 / 分隔线
  - 矢量图形的光栅化显示
  - 叶子 FRAME（无子节点的装饰/占位）
- **Figma 对应**: RECTANGLE, ELLIPSE, VECTOR, STAR, POLYGON, BOOLEAN_OPERATION, 无子节点的叶子 FRAME
- **使用指南**: figmaType 为 RECTANGLE/ELLIPSE/VECTOR/STAR/POLYGON/BOOLEAN_OPERATION → 自动判定；FRAME 无子节点 → 自动判定

---

## 交互控件类 (Interactive Widgets)

### CheckBox
- **UMG 类名**: `UCheckBox`
- **用途**: 勾选框（开/关状态）
- **适用场景**:
  - 设置选项的开关
  - 多选列表
- **Figma 对应**: 名称中 `[...]` 内含 CheckBox / Toggle / 勾选 的 FRAME/INSTANCE
- **使用指南**: 名称 `[...]` 内模式匹配（含 CheckBox/Toggle/勾选）

### Slider
- **UMG 类名**: `USlider`
- **用途**: 滑动条（连续数值选择）
- **适用场景**:
  - 音量调节、亮度设置
  - 数值范围选择
- **Figma 对应**: 名称中 `[...]` 内含 Slider / 滑块 的 FRAME/INSTANCE
- **使用指南**: 名称 `[...]` 内模式匹配（含 Slider/滑块）

### ProgressBar
- **UMG 类名**: `UProgressBar`
- **用途**: 进度条（只读数值展示）
- **适用场景**:
  - 加载进度、经验条、血量条
  - 任务完成度
- **Figma 对应**: 名称中 `[...]` 内含 Progress / 进度 的 FRAME/INSTANCE
- **使用指南**: 名称 `[...]` 内模式匹配（含 Progress/进度）

### ComboBox (ComboBoxString)
- **UMG 类名**: `UComboBoxString`
- **用途**: 下拉选择框
- **适用场景**:
  - 分辨率选择、语言选择
  - 枚举值选择
- **Figma 对应**: 名称中 `[...]` 内含 Dropdown / Select / ComboBox / 下拉 的 FRAME/INSTANCE
- **使用指南**: 名称 `[...]` 内模式匹配（含 Dropdown/Select/ComboBox/下拉）

### EditableTextBox
- **UMG 类名**: `UEditableTextBox`
- **用途**: 可编辑的文本输入框
- **适用场景**:
  - 搜索框、聊天输入框
  - 登录表单中的用户名/密码
- **Figma 对应**: 名称中 `[...]` 内含 Input / TextInput / 输入 的 FRAME/INSTANCE
- **使用指南**: 名称 `[...]` 内模式匹配（含 Input/TextInput/输入）

---

## 高级容器类 (Advanced Containers)

### UIWidgetSwitcher (自定义)
- **UMG 类名**: `UUIWidgetSwitcher` (继承 `UOverlay`)
- **用途**: 多个子控件中只显示一个，替代标准 `UWidgetSwitcher`，支持动态异步加载子面板
- **适用场景**:
  - Tab 页面切换
  - 状态切换（如不同游戏阶段的 HUD）
  - 需要按需异步加载子页面的场景
- **Figma 对应**: 名称中 `[...]` 内含 Tab / Switcher / 切换 的 FRAME
- **使用指南**: 名称 `[...]` 内模式匹配（含 Tab/Switcher/切换）
- **头文件**: `UI/Element/UIWidgetSwitcher.h`

---

## 复合控件类 (Composite)

### UserWidget
- **UMG 类名**: `UUserWidget`
- **用途**: 自定义组合控件（可复用的 UI 蓝图）
- **适用场景**:
  - Figma 组件实例 (INSTANCE) — 表示引用了一个可复用组件
  - Figma 组件主体 (COMPONENT) — 表示组件定义
  - 需要封装独立逻辑的子 UI 模块
  - 列表项模板 (Entry Widget)
- **Figma 对应**: INSTANCE 类型节点、COMPONENT 类型节点
- **使用指南**: figmaType == "INSTANCE" 或 "COMPONENT" → 自动判定

---

## Figma 类型 → UMG 类型 默认映射表

| Figma Type          | 默认 UMG Type  | 备注                          |
|---------------------|---------------|-------------------------------|
| TEXT                | TextBlock     | 所有文本节点                    |
| VECTOR              | Image         | 矢量图形（图标路径等）           |
| RECTANGLE           | Image         | 矩形色块 / 图片占位             |
| ELLIPSE             | Image         | 椭圆图形                       |
| STAR                | Image         | 星形                           |
| POLYGON             | Image         | 多边形                         |
| BOOLEAN_OPERATION   | Image         | 布尔运算图形                    |
| INSTANCE            | UserWidget    | 组件实例（可复用组件）            |
| COMPONENT           | UserWidget    | 组件主体                        |
| GROUP               | CanvasPanel   | 分组容器（绝对定位）             |
| FRAME               | *按规则推断*   | 见下方推断规则                   |

### FRAME 类型使用指南（按以下思路选择）

1. **名称匹配**（最高优先级，**只匹配节点名称中 `[xxx]` 方括号内的部分**，名称中方括号外的内容不参与匹配）:
   - `[CheckBox]` / `[Toggle]` / `[勾选]` → `CheckBox`
   - `[Slider]` / `[滑块]` → `Slider`
   - `[Progress]` / `[进度]` → `ProgressBar`
   - `[Dropdown]` / `[Select]` / `[ComboBox]` / `[下拉]` → `ComboBox`
   - `[Input]` / `[TextInput]` / `[输入]` → `EditableTextBox`
   - `[Scroll]` / `[滚动]` → `UIScrollBox`
   - `[Tab]` / `[Switcher]` / `[切换]` → `UIWidgetSwitcher`
   - `[ListView]` → `UIScrollBox`
   - `[TileView]` / `[GridView]` → `UIScrollBox`
   - `[WrapBox]` → `WrapBox`
   - `[Grid]` → `UniformGridPanel`
   - `[SizeBox]` → `SizeBox`
   - 如果节点名称中没有 `[...]` 方括号，则跳过此步骤
2. **根节点** → `CanvasPanel`
3. **溢出检测** (来自上下文中的 `overflow` 标记):
   - 有 `overflow` 标记 → `UIScrollBox`（子控件总尺寸超出容器，需要滚动）
4. **autoLayout 信息** (来自 slim JSON):
   - `layoutMode == "HORIZONTAL"` → `HorizontalBox`
   - `layoutMode == "VERTICAL"` → `VerticalBox`
5. **无子节点** → `Image`（叶子 Frame 视为装饰/占位图）
6. **多子节点** → 分析子控件坐标:
   - 子节点需要自由定位组合（无明确的行/列排列规律） → `CanvasPanel`
   - 找不到合适的类型 → `CanvasPanel`
   - **注意**: 不得依据坐标跨度推断为 HorizontalBox 或 VerticalBox，这两种类型只能通过 autoLayout 信息（步骤 4）或名称匹配（步骤 1）判定

---

## 所有 UMG Type 速查表

| UMG Type           | 类别     | 自动推断 | 典型场景               |
|--------------------|---------|---------|----------------------|
| CanvasPanel        | 布局     | ✅      | 根节点、自由定位容器     |
| VerticalBox        | 布局     | ✅      | 垂直列表、导航栏        |
| HorizontalBox      | 布局     | ✅      | 水平行、标题栏、工具栏   |
| WrapBox            | 布局     | ✅      | 自动换行网格     |
| UniformGridPanel   | 布局     | ✅      | 等尺寸网格、背包格子     |
| UIScrollBox        | 布局     | ✅      | 可滚动区域 (自定义)     |
| SizeBox            | 约束     | ✅      | 固定尺寸容器、图标框     |
| ScaleBox           | 约束     | ❌      | 分辨率自适应缩放        |
| Spacer             | 约束     | ❌      | 空白占位               |
| TextBlock          | 显示     | ✅      | 静态文本               |
| RichTextBlock      | 显示     | ❌      | 富文本（混合样式）       |
| Image              | 显示     | ✅      | 图片、矩形、矢量图      |
| CheckBox           | 交互     | ✅      | 勾选框                 |
| Slider             | 交互     | ✅      | 滑动条                 |
| ProgressBar        | 交互     | ✅      | 进度条                 |
| ComboBox           | 交互     | ✅      | 下拉选择               |
| EditableTextBox    | 交互     | ✅      | 输入框                 |
| UIWidgetSwitcher   | 高级     | ✅      | 标签页切换 (自定义)     |
| UserWidget         | 复合     | ✅      | 自定义组合控件          |
