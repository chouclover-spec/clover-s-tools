# -*- coding: utf-8 -*-
"""
wbp2figma.py — UMG WBP → Figma 场景描述 (scene.json) 翻译器

单阶段确定性翻译 (不需要 AI 介入, UMG 类型已知)。与 figma2ui/figma2ui.py 对称,
方向相反: wbp.json (UMG 树) → scene.json (Figma 节点树)。

用法:
  python wbp2figma.py <wbp.json> [scene.json]      # 单文件
  python wbp2figma.py <目录>                         # 批量 (处理 *_wbp.json)

输入 wbp.json 由 ue/export_wbp.py 产出; 字段约定见模块内 WBP_NODE 示例。
输出 scene.json 供 figma_writer.js.template (use_figma) 消费。

类型逆映射与布局策略见 UMG_TO_FIGMA_REFERENCE.md。
"""
import json
import sys
import os
import glob

# 复用同一份锚点求解 (UE 提取脚本也用, 保证一致)
from geometry import slot_to_rect


# ═══════════════════════════════════════════════════════════════════════════
#  类型映射表
# ═══════════════════════════════════════════════════════════════════════════
# figmaType: FRAME / TEXT / RECTANGLE
# layout: "absolute" = 子节点带 x/y/width/height (Canvas/Overlay/SizeBox/Grid/Scroll)
#         "auto"     = 父设 auto-layout, 子不带 x/y (VBox/HBox/Wrap/Border)
#         "leaf"     = 无子节点
TYPE_MAP = {
    # 布局容器
    "CanvasPanel":       {"figmaType": "FRAME",      "layout": "absolute"},
    "Overlay":           {"figmaType": "FRAME",      "layout": "absolute"},   # 子节点全 0,0 重叠
    "SizeBox":           {"figmaType": "FRAME",      "layout": "absolute"},   # 固定尺寸, 单子节点填充
    "UniformGridPanel":  {"figmaType": "FRAME",      "layout": "absolute"},   # 子节点按格绝对定位
    "ScrollBox":         {"figmaType": "FRAME",      "layout": "absolute"},   # clipsContent
    "VerticalBox":       {"figmaType": "FRAME",      "layout": "auto", "mode": "VERTICAL"},
    "HorizontalBox":     {"figmaType": "FRAME",      "layout": "auto", "mode": "HORIZONTAL"},
    "WrapBox":           {"figmaType": "FRAME",      "layout": "auto", "mode": "VERTICAL", "wrap": True},
    "Border":            {"figmaType": "FRAME",      "layout": "auto", "mode": "VERTICAL"},  # fill + padding
    "Button":            {"figmaType": "FRAME",      "layout": "auto", "mode": "HORIZONTAL"},
    # 显示
    "TextBlock":         {"figmaType": "TEXT",       "layout": "leaf"},
    "RichTextBlock":     {"figmaType": "TEXT",       "layout": "leaf"},
    "Image":             {"figmaType": "RECTANGLE",  "layout": "leaf"},
    "Spacer":            {"figmaType": "FRAME",      "layout": "leaf"},
    # 交互控件 (无子节点时当叶子, 有子节点时当组合容器)
    "CheckBox":          {"figmaType": "FRAME",      "layout": "auto", "mode": "HORIZONTAL"},
    "Slider":            {"figmaType": "FRAME",      "layout": "leaf"},
    "ProgressBar":       {"figmaType": "FRAME",      "layout": "leaf"},
    "ComboBoxString":    {"figmaType": "FRAME",      "layout": "auto", "mode": "HORIZONTAL"},
    "EditableTextBox":   {"figmaType": "FRAME",      "layout": "leaf"},
    # 根 / 复合
    "UserWidget":        {"figmaType": "FRAME",      "layout": "absolute"},
    "UIWidgetSwitcher":  {"figmaType": "FRAME",      "layout": "absolute"},   # 多子重叠, 显示其一
    "UIScrollBox":       {"figmaType": "FRAME",      "layout": "absolute"},
}

ABSOLUTE_LAYOUTS = {"absolute"}      # 子节点保留 x/y
DEFAULT_FIGMA_TYPE = "FRAME"
DEFAULT_FALLBACK_FONT = {"family": "Inter", "style": "Regular"}

# UMG 文本对齐 → Figma
TEXT_ALIGN_MAP = {
    "Left": "LEFT", "Center": "CENTER", "Right": "RIGHT", "Justify": "JUSTIFIED",
}
TEXT_VALIGN_MAP = {
    "Top": "TOP", "Center": "CENTER", "Bottom": "BOTTOM",
}


# ═══════════════════════════════════════════════════════════════════════════
#  字体映射
# ═══════════════════════════════════════════════════════════════════════════
def load_font_map(path=None):
    """加载 font_map.json: { "<ue_family 小写>": {"family":..,"style":..} }。"""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "font_map.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def map_font(ue_family, ue_style, font_map):
    """UE 字体 → Figma {family, style}。缺省走 fallback。"""
    key = (ue_family or "").strip().lower()
    entry = font_map.get(key)
    if entry:
        return {"family": entry["family"], "style": entry.get("style", ue_style or "Regular")}
    # 未命中: family 用原值或 fallback, style 原样
    return {
        "family": ue_family or DEFAULT_FALLBACK_FONT["family"],
        "style": ue_style or DEFAULT_FALLBACK_FONT["style"],
    }


# ═══════════════════════════════════════════════════════════════════════════
#  颜色归一化
# ═══════════════════════════════════════════════════════════════════════════
def solid_fill(color, opacity=1.0):
    """{r,g,b,a}∈[0,1] → Figma SOLID fill 对象。"""
    if not isinstance(color, dict):
        return None
    c = {
        "r": color.get("r", 0),
        "g": color.get("g", 0),
        "b": color.get("b", 0),
        "a": color.get("a", 1),
    }
    a = c["a"] * (opacity if opacity is not None else 1.0)
    return {"type": "SOLID", "color": c, "opacity": a}


# ═══════════════════════════════════════════════════════════════════════════
#  翻译主循环
# ═══════════════════════════════════════════════════════════════════════════
def translate_node(node, parent_layout, parent_w, parent_h, font_map):
    """递归翻译单个 UMG 节点 → Figma scene 节点。

    parent_layout: 父节点的 layout 模式 ("absolute"/"auto"/"leaf") — 决定本节点是否带 x/y。
    parent_w/h:    父容器尺寸, 用于求解 Canvas slot 矩形。
    """
    umg = node.get("umgType", "")
    spec = TYPE_MAP.get(umg, {"figmaType": DEFAULT_FIGMA_TYPE, "layout": "absolute"})
    layout = spec["layout"]
    figma_type = spec["figmaType"]

    out = {
        "name": node.get("name", ""),
        "type": figma_type,
        "umgType": umg,                # 保留原类型, 便于对账/Code Connect
    }

    # ── 尺寸与位置 ──
    slot = node.get("slot")
    own_w = node.get("width")
    own_h = node.get("height")

    # 若父是绝对布局, 本节点用 slot 求解矩形 (或直接用提取器算好的 x/y/width/height)
    if parent_layout == "absolute":
        if node.get("x") is not None and own_w is not None:
            x, y, w, h = node["x"], node.get("y", 0), own_w, own_h
        elif slot and slot.get("type") == "CanvasPanelSlot":
            x, y, w, h = slot_to_rect(slot, parent_w or 0, parent_h or 0)
        else:
            x, y, w, h = node.get("x", 0), node.get("y", 0), own_w or 0, own_h or 0
        out["x"], out["y"] = round(x, 2), round(y, 2)
        out["width"], out["height"] = round(w, 2), round(h, 2)
        # Overlay/SizeBox/ScrollBox 等要求子节点贴 0,0 时由提取器已置位, 这里尊重原值
    else:
        # auto-layout 子节点: 不带 x/y; 尺寸转 layoutSizing
        if own_w is not None:
            out["width"] = round(own_w, 2)
        if own_h is not None:
            out["height"] = round(own_h, 2)
        _apply_slot_sizing(out, slot)

    # ── 本节点作为父时的布局模式 ──
    if layout == "auto":
        al = {"layoutMode": spec["mode"]}
        if spec.get("wrap"):
            al["layoutWrap"] = "WRAP"
        # spacing / padding 来自 slot 或节点 (UMG Box 间距由子 slot padding 体现, 这里取节点级 itemSpacing 若有)
        for f in ("itemSpacing", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft"):
            v = node.get(f)
            if v:
                al[f] = v
        # Border 的 padding 常在 slot 或节点 "padding" 里
        if umg == "Border":
            pad = node.get("padding")
            if isinstance(pad, dict):
                al["paddingTop"] = pad.get("top", 0)
                al["paddingRight"] = pad.get("right", 0)
                al["paddingBottom"] = pad.get("bottom", 0)
                al["paddingLeft"] = pad.get("left", 0)
        out["autoLayout"] = al

    # clipsContent (ScrollBox / 显式裁剪)
    if node.get("clipsContent") is not None:
        out["clipsContent"] = bool(node["clipsContent"])
    elif umg in ("ScrollBox", "UIScrollBox"):
        out["clipsContent"] = True

    # ── 类型专属属性 ──
    if figma_type == "TEXT":
        _apply_text(out, node, font_map)
    elif umg == "Image" or umg == "Border":
        _apply_image(out, node)
    else:
        # 通用 fillColor (背景)
        fc = node.get("fillColor")
        fo = node.get("fillOpacity", 1.0)
        fill = solid_fill(fc, fo) if fc is not None else None
        if fill:
            out["fills"] = [fill]

    # 圆角 / 描边 / 透明度 / 可见
    if node.get("cornerRadius") is not None:
        out["cornerRadius"] = node["cornerRadius"]
    sw = node.get("strokeWeight")
    if sw is not None:
        out["strokeWeight"] = sw
        sc = node.get("strokeColor")
        if sc is not None:
            out["strokes"] = [{"type": "SOLID", "color": sc}]
    if node.get("opacity") is not None:
        out["opacity"] = node["opacity"]
    if node.get("visible") is False:
        out["visible"] = False

    # ── 子节点 ──
    children = node.get("children", [])
    if children:
        # 本节点作为父时的尺寸上下文 (auto 节点用自身 width/height; absolute 用求解后的)
        ctx_w = out.get("width", parent_w or 0)
        ctx_h = out.get("height", parent_h or 0)
        out["children"] = [
            translate_node(c, layout, ctx_w, ctx_h, font_map) for c in children
        ]
    return out


def _apply_slot_sizing(out, slot):
    """把 Box/Border slot 的 sizeOverride → Figma layoutSizing (FILL/FIXED/HUG)。"""
    if not slot:
        return
    so = slot.get("sizeOverride")
    if not so:
        return
    # sizeOverride: {"horizontal": "FIXED"|"FILL"|"HUG", "vertical": ...}
    h = so.get("horizontal")
    v = so.get("vertical")
    if h:
        out["layoutSizingHorizontal"] = h  # FIXED / FILL / HUG
    if v:
        out["layoutSizingVertical"] = v


def _apply_text(out, node, font_map):
    """TextBlock → TEXT 字段。"""
    if node.get("content") is not None:
        out["text"] = node["content"]
    if node.get("fontSize") is not None:
        out["fontSize"] = node["fontSize"]
    fam = map_font(node.get("fontFamily"), node.get("fontStyle"), font_map)
    out["fontName"] = fam
    ah = node.get("textAlignHorizontal")
    if ah:
        out["textAlignHorizontal"] = TEXT_ALIGN_MAP.get(ah, "LEFT")
    av = node.get("textAlignVertical")
    if av:
        out["textAlignVertical"] = TEXT_VALIGN_MAP.get(av, "TOP")
    if node.get("letterSpacing") is not None:
        out["letterSpacing"] = node["letterSpacing"]
    # 文本颜色 → fill
    tc = node.get("textColor")
    fill = solid_fill(tc, 1.0) if tc is not None else None
    if fill:
        out["fills"] = [fill]
    # autoResize (wrap) → textAutoResize
    if node.get("autoResize") == "WrapText":
        out["textAutoResize"] = "HEIGHT"
    elif node.get("autoResize") == "None":
        out["textAutoResize"] = "NONE"


def _apply_image(out, node):
    """Image / Border → 矩形 fill (纯色 or 图片引用)。"""
    img_name = node.get("exportImageName")
    if img_name:
        out["exportImageName"] = img_name       # 由 figma_writer 上传后替换为 image fill
        out["imageFill"] = True
    fc = node.get("fillColor")
    fo = node.get("fillOpacity", 1.0)
    fill = solid_fill(fc, fo) if fc is not None else None
    if fill:
        out["fills"] = [fill]


# ═══════════════════════════════════════════════════════════════════════════
#  顶层入口
# ═══════════════════════════════════════════════════════════════════════════
def translate_document(doc, font_map=None):
    """翻译整个 wbp.json 文档 → scene 文档。

    wbp.json 结构:
      { "assetName": "...", "designSize": {"width":1920,"height":1080}, "root": {...} }
    或裸 root 节点。
    """
    if font_map is None:
        font_map = load_font_map()

    if isinstance(doc, dict) and "root" in doc:
        asset_name = doc.get("assetName", "WBP")
        design = doc.get("designSize", {})
        root = doc["root"]
        dw, dh = design.get("width", 0), design.get("height", 0)
    else:
        asset_name = doc.get("name", "WBP")
        root = doc
        dw, dh = root.get("width", 0), root.get("height", 0)

    # root 视为 absolute 父 (其子节点用 designSize 求解)
    scene_root = translate_node(root, "absolute", dw, dh, font_map)
    return {"assetName": asset_name, "designSize": {"width": dw, "height": dh}, "root": scene_root}


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════
def process_file(in_path, out_path=None):
    with open(in_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    font_map = load_font_map()
    scene = translate_document(doc, font_map)
    if out_path is None:
        d = os.path.dirname(in_path)
        base = os.path.splitext(os.path.basename(in_path))[0]
        base = base[:-4] if base.endswith("_wbp") else base
        out_path = os.path.join(d, base + "_scene.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(scene, f, ensure_ascii=False, indent=2)
    return out_path


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python wbp2figma.py <wbp.json> [scene.json]")
        print("  python wbp2figma.py <dir>      # 批量处理 *_wbp.json")
        sys.exit(1)

    target = sys.argv[1]
    if os.path.isdir(target):
        files = sorted(glob.glob(os.path.join(target, "*_wbp.json")))
        if not files:
            print("No *_wbp.json in: " + target)
            sys.exit(1)
        print("Processing {} files\n".format(len(files)))
        for fp in files:
            op = process_file(fp)
            print("  {} -> {}".format(os.path.basename(fp), os.path.basename(op)))
        return

    out = sys.argv[2] if len(sys.argv) >= 3 else None
    op = process_file(target, out)
    print("{} -> {}".format(target, op))


if __name__ == "__main__":
    main()
