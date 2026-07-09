# psd2figma — GUI 的 PSD → Figma

路线 C：解析 PSD → JSON → 翻译 → use_figma 写 Figma。与 `wbp2figma/`（UE→Figma）同构，
**写入端 `figma_writer.js.template` 零改动复用**，仅新写解析器 + 翻译器。

```
PSD ──parse_psd.py──▶ *_psd.json ──psd2figma.py──▶ *_scene.json ──use_figma──▶ Figma Component
                                                          ↑ 复用 wbp2figma/figma_writer
```

## 目录

```
psd2figma/
  parse_psd.py              解析器: PSD → psd.json + 位图 PNG
  psd2figma.py              翻译器: psd.json → scene.json
  PSD_TO_FIGMA_REFERENCE.md 映射参考
  tests/
    test_psd2figma.py       单测 (坐标转换/类型/混合模式/效果)
    psd/*.psd               测试 PSD (来自 psd-tools fixtures)
    output/                 解析+翻译产物 (psd.json / scene.json / exported_textures/)
```

## 依赖

```bash
py -3 -m pip install psd-tools Pillow
```
（本机已验证 psd-tools 1.17.4 + Python 3.14。）

## 端到端

```bash
cd wbp2figma/psd2figma

# ① 解析: PSD → psd.json + PNG
py -3 parse_psd.py tests/psd/group.psd tests/output       # 单文件
py -3 parse_psd.py tests/psd tests/output                  # 批量

# ② 翻译: psd.json → scene.json
py -3 psd2figma.py tests/output/group_psd.json
py -3 psd2figma.py tests/output                            # 批量

# ③ 写入 Figma (复用 wbp2figma/figma_writer.js.template)
#    把 scene.json 替换进模板占位符, 用 Figma MCP use_figma 执行;
#    再用 upload_assets 上传 exported_textures/*.png 到对应 nodeId 绑 image fill。
```

## 测试

```bash
cd tests
py -3 test_psd2figma.py
```
覆盖：坐标绝对→相对父组、group→FRAME、pixel/shape→RECTANGLE+image、type→TEXT、
blendMode（PASS_THROUGH/MULTIPLY/NORMAL）、stroke/drop_shadow/colorOverlay、字体子串匹配。

## 与 wbp2figma 的复用关系

| 共享资产 | 来源 |
|---|---|
| `figma_writer.js.template` | `wbp2figma/`（已扩展支持 blendMode/effects，向后兼容） |
| `scene.json` 数据契约 | 同一格式 |
| `font_map.json` | `wbp2figma/font_map.json` |
| 坐标转换思路 | `figma2ui/slim_json.py` 的 GROUP 绝对→相对 |

新增成本仅 = `parse_psd.py` + `psd2figma.py`。

## 保真度

中等：图层树 + 坐标 + 颜色 + 文本 + 图片 + 混合模式 + stroke/shadow 效果。
未覆盖项见 `PSD_TO_FIGMA_REFERENCE.md` 末尾（富文本 run、矢量填充、蒙版、渐变、CMYK 颜色空间）。
GUI 稿（扁平、文本多）保真度中高；厚效果视觉稿建议整组位图兜底。
