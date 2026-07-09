# UMG → Figma 逆映射参考

`figma2ui/UMG_WIDGET_REFERENCE.md` 的反向表。供 `wbp2figma.py` 与人工对账用。

## 类型映射

| UMG 类 | Figma 节点 | 父布局模式 | 说明 |
|---|---|---|---|
| CanvasPanel | FRAME | absolute | 子节点带 x/y/width/height |
| VerticalBox | FRAME | auto (VERTICAL) | itemSpacing/padding |
| HorizontalBox | FRAME | auto (HORIZONTAL) | itemSpacing/padding |
| WrapBox | FRAME | auto (VERTICAL + WRAP) | layoutWrap="WRAP" |
| UniformGridPanel | FRAME | absolute | 子节点按格绝对定位 |
| Overlay | FRAME | absolute | 子节点全 0,0 重叠 |
| SizeBox | FRAME | absolute | 固定 width/height, 单子节点填充 |
| ScrollBox / UIScrollBox | FRAME | absolute | clipsContent=true |
| Border | FRAME | auto (VERTICAL) | fill=tint, padding |
| Button | FRAME | auto (HORIZONTAL) | 内容居中 |
| TextBlock / RichTextBlock | TEXT | leaf | fontSize/font/justify/color |
| Image | RECTANGLE | leaf | image fill 或 tint |
| Spacer | FRAME | leaf | 空白占位 |
| CheckBox | FRAME | auto (HORIZONTAL) | — |
| Slider / ProgressBar / EditableTextBox | FRAME | leaf | — |
| ComboBoxString | FRAME | auto (HORIZONTAL) | — |
| UserWidget (根) | FRAME | absolute | designSize |
| UIWidgetSwitcher | FRAME | absolute | 多子重叠, 显示其一 |

## 布局模式判定

- **absolute**（子节点保留 `x/y`）：父为 CanvasPanel / Overlay / SizeBox / UniformGridPanel / ScrollBox / UIWidgetSwitcher。
- **auto**（父设 auto-layout，子不带 `x/y`，带 `layoutSizing`）：父为 VerticalBox / HorizontalBox / WrapBox / Border / Button。

## 锚点数学（CanvasPanelSlot）

详见 `geometry.py:slot_to_rect`。
- 点锚 (`min==max`，逐轴)：`pos = anchor*parent + offset(left/top)`；`size = offset(right/bottom)`；`topleft = pos - alignment*size`。
- 拉伸锚 (`min!=max`)：`left = min*parent + offset.left`；`right = max*parent - offset.right`；`size = right - left`。
- X/Y 轴独立。

## 属性映射

| UMG | Figma |
|---|---|
| ColorAndOpacity / Brush.tint (FLinearColor) | fills[0] SOLID `{r,g,b}` + opacity=a |
| TextBlock 文本颜色 | TEXT `fills` |
| TextBlock content (FText) | `characters` |
| Font.Size / Typeface | `fontSize` / `fontName{family,style}`（经 font_map.json 映射） |
| Justification (Left/Center/Right) | `textAlignHorizontal` |
| RenderOpacity | `opacity` |
| Visibility (Collapsed/Hidden) | `visible=false` |
| ScrollBox 裁剪 | `clipsContent=true` |
| Brush.resource_object (UTexture2D) | image fill（exportImageName → upload_assets） |
| Border padding | auto-layout `paddingTop/Right/Bottom/Left` |
| Box slot Size (0=fill) | `layoutSizingHorizontal/Vertical` FILL/FIXED |

## 中等保真未覆盖（Phase 2）

- RenderTransform（平移/缩放/旋转/剪切）→ Figma `relativeTransform`
- 九宫格切片（Brush margin+borders）→ Figma 9-slice
- ScrollBox 视口裁剪与滚动条
- FLinearColor 线性 → sRGB gamma 校正
