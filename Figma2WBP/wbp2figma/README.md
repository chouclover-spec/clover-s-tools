# WBP → Figma 通用组件

把 UE4 WBP (Widget Blueprint / UMG) 转成 Figma 可复用 Component + Variables 主题。
与上层 `figma2ui/`（Figma → UMG）方向相反，三段独立管线：

```
UE4 WBP  ──ue/export_wbp.py──▶  *_wbp.json  ──wbp2figma.py──▶  *_scene.json  ──use_figma──▶  Figma Component
```

## 目录

```
wbp2figma/
  geometry.py              锚点数学 (slot_to_rect), UE 脚本与翻译器共用
  wbp2figma.py             翻译器: wbp.json → scene.json
  font_map.json            UE 字体 → Figma 字体映射
  UMG_TO_FIGMA_REFERENCE.md  类型/属性逆映射参考
  figma_writer.js.template  use_figma 驱动模板 (建 Component + Variables + 节点)
  ue/
    export_wbp.py          UE 编辑器内提取脚本
    README_UE.md           运行说明 + API 校准
    cpp/ExportTextureUtil.*  (可选) Texture→PNG C++ helper
  tests/
    mock_wbp.json          翻译器测试夹具
    test_wbp2figma.py      锚点数学 + 翻译单测
```

## 端到端流程

### ① 提取（UE 侧）
见 `ue/README_UE.md`。在 UE 编辑器跑 `export_wbp.export_many([...])`，产出 `*_wbp.json` + 纹理 PNG。

### ② 翻译（本机）
```bash
cd wbp2figma
py -3 wbp2figma.py ue/output/WBP_Button_wbp.json          # → WBP_Button_scene.json
py -3 wbp2figma.py ue/output                              # 批量
```

### ③ 写入 Figma（use_figma）
编排（由 Claude 或脚本）：
1. 读 `*_scene.json`，把内容替换进 `figma_writer.js.template` 的 `__SCENE_JSON__`。
2. 用 Figma MCP `use_figma`（先 `/figma-use` skill）执行该 JS，拿到 `{componentId, imageNodes}`。
3. 对 `imageNodes` 里每个 `exportImageName`，用 MCP `upload_assets(fileKey, nodeId=imageNodes[name])` 上传对应 PNG（`ue/output/exported_textures/{name}.png`），自动绑定为 image fill。
4. （可选）`get_screenshot(componentId)` 核对视觉。

目标 fileKey 由用户提供，或用 `create_new_file` + `/figma-create-new-file` 新建。

## 测试

```bash
cd wbp2figma/tests
py -3 test_wbp2figma.py
```
覆盖：点锚+alignment、全拉伸、拉伸带 margin、VerticalBox auto-layout（子节点无 x/y 带 layoutSizing）、TextBlock 映射、字体映射。

## 保真度

中等：布局（锚点数学）+ 颜色 + 文本 + 图片 + 字体。未覆盖项（Phase 2）见 `UMG_TO_FIGMA_REFERENCE.md` 末尾：RenderTransform、九宫格切片、ScrollBox 视口、线性→sRGB gamma。
