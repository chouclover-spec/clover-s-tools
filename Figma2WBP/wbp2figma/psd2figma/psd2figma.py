# -*- coding: utf-8 -*-
"""
psd2figma.py — psd.json → scene.json 翻译器（路线 C 第 ② 段）

把 parse_psd.py 产出的 psd.json 翻译成与 wbp2figma 同格式的 scene.json，
figma_writer.js.template 零改动复用（路线 C 的核心复用点）。

用法:
  py -3 psd2figma.py <psd.json> [scene.json]      # 单文件
  py -3 psd2figma.py <dir>                          # 批量 *_psd.json

映射:
  group        → FRAME (子节点绝对定位, 坐标转相对父组)
  type         → TEXT
  pixel/shape/smartobject → RECTANGLE (image fill, 由 writer 上传 PNG)
  其他 (adjustment/fill 等) → FRAME 占位

属性: opacity/visible/blendMode 直传; textColor→TEXT fill; 字体走 font_map.json;
      stroke→strokeWeight+strokes; drop_shadow/inner_shadow→effects; colorOverlay→fill。
"""
import json
import os
import sys
import glob

# 复用 wbp2figma 的字体表 (上一级目录)
_HERE = os.path.dirname(os.path.abspath(__file__))
_FONT_MAP_PATH = os.path.normpath(os.path.join(_HERE, "..", "font_map.json"))


# ═══════════════════════════════════════════════════════════════════════════
#  字体映射
# ═══════════════════════════════════════════════════════════════════════════
def load_font_map(path=None):
    if path is None:
        path = _FONT_MAP_PATH
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _clean_font_family(fam):
    """PS 字体名 → 主名 (去 -Regular/-Bold 等后缀, 供 font_map 匹配)。"""
    if not fam:
        return ""
    s = str(fam)
    # 去常见后缀
    for sep in ("-", " "):
        if sep in s:
            base = s.split(sep)[0]
            if base:
                s = base
                break
    return s


def map_font(ue_family, font_map):
    """PS 字体 → Figma {family, style}。先查 font_map, 未命中用清洗后的主名或 Inter。"""
    if ue_family:
        fl = str(ue_family).strip().lower()
        # 1. 全名直查
        entry = font_map.get(fl)
        if isinstance(entry, dict):
            return {"family": entry["family"], "style": entry.get("style", "Regular")}
        # 2. 清洗后主名 (去 -Bold/ 空格后缀) 直查
        base = _clean_font_family(ue_family).lower()
        entry = font_map.get(base)
        if isinstance(entry, dict):
            return {"family": entry["family"], "style": entry.get("style", "Regular")}
        # 3. 子串回退: font_map 的 key 是否是字体名的子串 (处理 ArialMT / Roboto-Regular 等 PS 名)
        for k, v in font_map.items():
            if not isinstance(v, dict):
                continue
            if k and k in fl:
                return {"family": v["family"], "style": v.get("style", "Regular")}
    return {"family": ue_family or "Inter", "style": "Regular"}


# ═══════════════════════════════════════════════════════════════════════════
#  颜色 / 效果
# ═══════════════════════════════════════════════════════════════════════════
def solid_fill(color):
    if not isinstance(color, dict):
        return None
    return {
        "type": "SOLID",
        "color": {"r": color.get("r", 0), "g": color.get("g", 0), "b": color.get("b", 0)},
        "opacity": color.get("a", 1) if color.get("a", 1) is not None else 1,
    }


# PSD BlendMode → Figma blendMode (NORMAL 不设, 走默认)
BLEND_MAP = {
    "PASS_THROUGH": "PASS_THROUGH",
    "MULTIPLY": "MULTIPLY", "SCREEN": "SCREEN", "OVERLAY": "OVERLAY",
    "DARKEN": "DARKEN", "LIGHTEN": "LIGHTEN", "COLOR_DODGE": "COLOR_DODGE",
    "COLOR_BURN": "COLOR_BURN", "HARD_LIGHT": "HARD_LIGHT", "SOFT_LIGHT": "SOFT_LIGHT",
    "DIFFERENCE": "DIFFERENCE", "EXCLUSION": "EXCLUSION",
    "HUE": "HUE", "SATURATION": "SATURATION", "COLOR": "COLOR", "LUMINOSITY": "LUMINOSITY",
    "LINEAR_DODGE": "LINEAR_DODGE", "LINEAR_BURN": "LINEAR_BURN",
    "DARKER_COLOR": "DARKEN", "LIGHTER_COLOR": "LIGHTEN",
}


def map_blend(bm):
    if not bm or bm == "NORMAL":
        return None
    return BLEND_MAP.get(bm)  # 未命中返回 None (如 DISSOLVE 无对应)


def map_effects(node):
    """psd effects/stroke → Figma effects 数组 + strokeWeight/strokes。"""
    out = {}
    sw = node.get("strokeWeight")
    sc = node.get("strokeColor")
    if sw is not None:
        out["strokeWeight"] = sw
    if sw is not None and sc is not None:
        out["strokes"] = [{"type": "SOLID", "color": sc, "opacity": sc.get("a", 1)}]
    if node.get("effects"):
        out["effects"] = node["effects"]
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  翻译主循环
# ═══════════════════════════════════════════════════════════════════════════
def translate_node(node, parent_left, parent_top, font_map):
    """psd 节点 → Figma scene 节点。坐标转相对父 (parent_left/top 为父组画布坐标)。"""
    kind = node.get("psdKind", "")
    left = node.get("left", 0)
    top = node.get("top", 0)

    out = {
        "name": node.get("name", ""),
        "psdKind": kind,
        # 相对父组的坐标
        "x": round(left - parent_left, 2),
        "y": round(top - parent_top, 2),
        "width": node.get("width", 0),
        "height": node.get("height", 0),
    }

    # ── 类型 ──
    if kind == "type":
        out["type"] = "TEXT"
        if node.get("text") is not None:
            out["text"] = node["text"]
        if node.get("fontSize") is not None:
            out["fontSize"] = node["fontSize"]
        out["fontName"] = map_font(node.get("fontFamily"), font_map)
        out["textAlignHorizontal"] = "LEFT"  # PSD 段落对齐未提取, 默认 LEFT
        if node.get("tracking") is not None:
            out["letterSpacing"] = node["tracking"]
        tc = node.get("textColor")
        fill = solid_fill(tc)
        if fill:
            out["fills"] = [fill]
    elif kind == "group":
        out["type"] = "FRAME"
        out["layoutMode"] = "NONE"  # 子节点绝对定位
        # group 的 fill: 通常无; 若有 colorOverlay 则应用
        co = node.get("colorOverlay")
        if co is not None:
            out["fills"] = [solid_fill(co)]
    else:
        # pixel / shape / smartobject → RECTANGLE (image fill)
        out["type"] = "RECTANGLE"
        if node.get("exportImageName"):
            out["exportImageName"] = node["exportImageName"]
        # colorOverlay 作为底色 (image 上传后会覆盖为 image fill; 无 image 时作纯色)
        co = node.get("colorOverlay")
        if co is not None and not node.get("exportImageName"):
            out["fills"] = [solid_fill(co)]

    # ── 通用属性 ──
    if node.get("opacity") is not None and abs(node["opacity"] - 1.0) > 1e-4:
        out["opacity"] = node["opacity"]
    if node.get("visible") is False:
        out["visible"] = False
    bm = map_blend(node.get("blendMode"))
    if bm:
        out["blendMode"] = bm

    # ── 描边 / 效果 ──
    out.update(map_effects(node))

    # ── 子节点 (group) ──
    children = node.get("children", [])
    if children:
        out["children"] = [translate_node(c, left, top, font_map) for c in children]
    return out


def translate_document(doc, font_map=None):
    if font_map is None:
        font_map = load_font_map()
    design = doc.get("designSize", {})
    dw, dh = design.get("width", 0), design.get("height", 0)
    root = doc.get("root", {})
    scene_root = translate_node(root, 0, 0, font_map)
    scene_root["type"] = "FRAME"
    scene_root["layoutMode"] = "NONE"
    return {
        "assetName": doc.get("assetName", "PSD"),
        "designSize": {"width": dw, "height": dh},
        "root": scene_root,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════
def process_file(in_path, out_path=None):
    with open(in_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    scene = translate_document(doc, load_font_map())
    if out_path is None:
        d = os.path.dirname(in_path)
        base = os.path.splitext(os.path.basename(in_path))[0]
        base = base[:-4] if base.endswith("_psd") else base
        out_path = os.path.join(d, base + "_scene.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(scene, f, ensure_ascii=False, indent=2)
    return out_path


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  py -3 psd2figma.py <psd.json> [scene.json]")
        print("  py -3 psd2figma.py <dir>      # 批量 *_psd.json")
        sys.exit(1)
    target = sys.argv[1]
    if os.path.isdir(target):
        files = sorted(glob.glob(os.path.join(target, "*_psd.json")))
        if not files:
            print("No *_psd.json in: " + target); sys.exit(1)
        for fp in files:
            print("  {} -> {}".format(os.path.basename(fp), process_file(fp)))
        return
    out = sys.argv[2] if len(sys.argv) >= 3 else None
    print("{} -> {}".format(target, process_file(target, out)))


if __name__ == "__main__":
    main()
