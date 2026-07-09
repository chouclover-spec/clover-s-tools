# PSD → Figma 映射参考

`psd2figma/` 第 ② 段翻译器（`psd2figma.py`）的映射依据。与 `UMG_TO_FIGMA_REFERENCE.md` 并列。
输出 `scene.json` 格式与 `wbp2figma` 完全一致，`figma_writer.js.template` 零改动复用。

## 图层类型映射

| PSD 图层 (`psdKind`) | Figma 节点 | 说明 |
|---|---|---|
| group | FRAME | 子节点绝对定位，坐标转相对父组 |
| type | TEXT | font/size/color/tracking |
| pixel | RECTANGLE | 栅格化 PNG → image fill |
| smartobject | RECTANGLE | 栅格化 PNG → image fill（丢内部可编辑性） |
| shape | RECTANGLE | 优先栅格化 PNG；矢量填充/路径留 Phase 2 |
| adjustment / fill 等 | FRAME | 占位（Phase 2 细化） |

## 坐标转换

PSD 图层 `left/top/right/bottom` 是画布绝对坐标。翻译时转相对父组：
```
child.x = layer.left - parent.left
child.y = layer.top  - parent.top
width   = right - left
height  = bottom - top
```
root 用 designSize（画布尺寸），子节点相对 root。

## 属性映射

| PSD | Figma |
|---|---|
| opacity (0-255 → 0..1) | `opacity` |
| visible | `visible` |
| blendMode NORMAL | 不设（走默认） |
| blendMode PASS_THROUGH | `blendMode = "PASS_THROUGH"` |
| MULTIPLY/SCREEN/OVERLAY/... | 同名 `blendMode` |
| DISSOLVE 等 | 无对应，忽略 |
| textColor (FillColor.Values 前3) | TEXT `fills[0]` |
| text / fontSize / fontFamily | `characters` / `fontSize` / `fontName`（经 font_map.json） |
| Tracking | `letterSpacing` |
| exportImageName | 留 `upload_assets` 绑定 image fill |
| Stroke 效果 (size/color) | `strokeWeight` + `strokes` |
| DropShadow (distance/angle/size/color) | `effects[]` DROP_SHADOW（offset 由 distance×angle 分解） |
| InnerShadow | `effects[]` INNER_SHADOW |
| ColorOverlay | `fills[0]`（无 image 时作纯色底） |
| GradientOverlay / PatternOverlay | Phase 2 |

## 字体映射

PS 字体名（PostScript 名，如 `ArialMT`、`Roboto-Bold`）→ Figma `font_map.json`：
1. 全名小写直查
2. 清洗后主名（去 `-Bold`/空格后缀）直查
3. 子串回退（`arialmt` 含 `arial` → 命中 Arial）
4. 未命中 → 用原 family 名，Figma 端 `loadFontAsync` 失败时 writer 回退 Inter/Roboto

## 中等保真未覆盖（Phase 2）

- 富文本 run 拆分（多样式段落）→ 仅取第一个 run 主样式
- 形状图层矢量填充/路径 → 栅格化为位图
- 渐变/图案叠加
- 图层蒙版 → Figma "Use as mask"
- 剪贴蒙版 → clipsContent
- 段落对齐 → 默认 LEFT（PSD ParagraphStyle 未提取）
- 颜色空间（CMYK/Lab → sRGB）→ 直接取前 3 值，可能偏色
