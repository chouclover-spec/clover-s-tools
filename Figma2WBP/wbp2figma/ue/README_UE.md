# UE 侧提取说明 (export_wbp.py)

把 UE4 WBP 导出成 `wbp.json` + 纹理 PNG，供 `wbp2figma.py` 翻译。

## 前置

1. 编辑器启用 **Python 插件** (`Edit → Plugins → Scripting → Python Editor Script Plugin`)。
2. （图片导出）编译 `cpp/ExportTextureUtil.h/.cpp` 进任意 Editor 模块。新建模块示例：
   - 模块名 `Wbp2FigmaEditor`，类型 `Editor`，Build.cs 依赖加 `"ImageWrapper","ImageWriteQueue"`。
   - 把两个文件放进模块的 `Public/Private`，`.h` 用 `UCLASS(BlueprintType)`。
   - 重新编译项目 → Python 里 `unreal.ExportTextureUtil` 即可用。
   - 若暂不编译：脚本会跳过导出、只打印纹理清单，由设计师手动把纹理导出 PNG 放进 `output/exported_textures/`，文件名 = 资产名。

> 纹理若为 DXT 压缩，导出前请在纹理编辑器里把 `Compression Settings` 设为 `VectorDisplacementmap`（无压缩 BGRA8），否则 4.24 回退路径拿到的是压缩块。4.25+ 走 `UImageWriteBlueprintLibrary` 无此问题。

## 运行

在 UE 编辑器 `Output Log` 切到 Python，或用 Editor Utility 调用：

```python
import sys
sys.path.append(r"D:\ClaudeCode\Figma2WBP\wbp2figma\ue")
import export_wbp

# 单个
export_wbp.export_wbp("/Game/UI/WBP_Button", r"D:\ClaudeCode\Figma2WBP\wbp2figma\ue\output")

# 批量
export_wbp.export_many(
    ["/Game/UI/WBP_Button", "/Game/UI/WBP_HUD"],
    r"D:\ClaudeCode\Figma2WBP\wbp2figma\ue\output"
)
```

产出：
- `output/{asset}_wbp.json` — 节点树 + `textures` 清单
- `output/exported_textures/{name}.png` — 纹理（若 C++ util 可用）

## API 假设与校准

UMG Python API 在不同 UE4 小版本略有差异，脚本全部用 `try/except` 兜底。若某字段在输出里缺失，按此表校准：

| 读取项 | 调用 | 兜底 |
|---|---|---|
| 子节点 | `widget.get_child_count()` / `get_child_at(i)`（仅 `UPanelWidget`） | `_is_panel` 用 `unreal.cast` |
| Canvas slot | `slot.get_anchors()` / `get_offsets()` / `get_alignment()` | 结构体走 `get_editor_property` |
| 文本 | `widget.get_text()` → `unreal.TextLibrary.text_to_string` | `str(ftext)` |
| 字体 | `widget.get_font()` → `.size/.typeface/.font_object` | — |
| 笔刷 | `widget.get_brush()` → `.tint/.resource_object` | `get_background_brush` |
| 颜色 | `FLinearColor` 的 `.r/.g/.b/.a` | `get_editor_property` |

颜色取自 `FLinearColor`（线性空间），Figma 用 sRGB —— 中等保真下直接传 0..1，视觉会略偏亮，Phase 2 做 gamma 校正。

根节点设计尺寸优先取 `root_widget.get_desired_size()`，读不到则兜底 1920×1080。WBP 若用 `Design Screen Size`/`Design DPI` 自定义，请在 `export_wbp()` 后手动覆盖 `doc["designSize"]`。

## 已知限制（中等保真）

- RenderTransform（平移/缩放/旋转/剪切）已记录到 `renderTransform` 字段但**未应用**到矩形 —— Phase 2 映射到 Figma `relativeTransform`。
- 九宫格切片（Border 的 Brush margin+borders）未处理 —— Border 当前只取 tint 填充 + padding。
- ScrollBox 仅标 `clipsContent`，未还原滚动条与裁剪视口。
- 字体 family 取 `font_object.get_name()`，可能是资产名而非真实 family；用 `font_map.json` 人工映射。
