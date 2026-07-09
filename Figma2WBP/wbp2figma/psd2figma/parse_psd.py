# -*- coding: utf-8 -*-
"""
parse_psd.py — PSD → psd.json + 位图 PNG 解析器（路线 C 第 ① 段）

用 psd-tools 解析 Photoshop 文件，产出与 slim.json 契约对齐的 psd.json，
并把像素/智能对象/形状图层栅格化导出为 PNG（供 figma_writer 的 upload_assets 绑定）。

用法:
  py -3 parse_psd.py <input.psd> [out_dir]       # 单文件
  py -3 parse_psd.py <dir>                         # 批量处理目录下 *.psd

输出 (out_dir, 默认 <input 同目录>/output):
  {name}_psd.json          — 图层树
  exported_textures/*.png  — 栅格化位图（pixel/smartobject/shape）

字段约定 (与 wbp2figma 的 wbp.json 同构, 供 psd2figma.py 翻译):
  name, psdKind, left/top/right/bottom (画布绝对坐标),
  opacity(0..1), visible, blendMode,
  text/fontSize/fontFamily/textColor/tracking (type),
  exportImageName (位图图层),
  strokeWeight/strokeColor/effects/colorOverlay (图层效果),
  children (group)

依赖: psd-tools, Pillow
"""
import json
import math
import os
import re
import sys

from psd_tools import PSDImage


# ═══════════════════════════════════════════════════════════════════════════
#  工具
# ═══════════════════════════════════════════════════════════════════════════
def _sanitize(name):
    s = re.sub(r"[^\w\-.]+", "_", str(name or "").strip())
    return s or "layer"


def _blend_name(bm):
    """BlendMode enum → 字符串名 (NORMAL / PASS_THROUGH / MULTIPLY ...)。"""
    try:
        return bm.name
    except Exception:
        s = str(bm)
        return s.split(".")[-1] if "." in s else s


def _color_from_values(values):
    """文本 FillColor.Values → {r,g,b,a}∈[0,1]。前 3 值当 RGB, alpha=1。

    psd-tools 的 FillColor.Values 长度不固定 (RGB 3 / CMYK 4 / 含 alpha)。
    中等保真: 取前 3 值为 RGB, alpha=1; 颜色空间混合导致的偏色留待 Phase 2。
    """
    if not values or len(values) < 3:
        return None
    r = max(0.0, min(1.0, float(values[0])))
    g = max(0.0, min(1.0, float(values[1])))
    b = max(0.0, min(1.0, float(values[2])))
    return {"r": r, "g": g, "b": b, "a": 1.0}


# ═══════════════════════════════════════════════════════════════════════════
#  文本提取
# ═══════════════════════════════════════════════════════════════════════════
def _get(obj, *path, default=None):
    """在 psd-tools 的 Dict 树里逐级取值。"""
    cur = obj
    for k in path:
        if cur is None:
            return default
        try:
            cur = cur.get(k)
        except Exception:
            return default
    return cur if cur is not None else default


def extract_text(layer):
    """TypeLayer → 文本字段。取第一个 run 的样式作主样式 (富文本 run 拆分留 Phase 2)。"""
    out = {}
    try:
        out["text"] = layer.text or ""
    except Exception:
        out["text"] = ""

    ed = getattr(layer, "engine_dict", None) or {}
    runs = _get(ed, "StyleRun", "RunArray", default=[])
    if runs:
        style = _get(runs[0], "StyleSheet", "StyleSheetData", default={}) or {}
        fs = style.get("FontSize")
        if fs is not None:
            out["fontSize"] = round(float(fs), 2)
        tracking = style.get("Tracking")
        if tracking:
            out["tracking"] = float(tracking)
        fill = style.get("FillColor")
        if fill:
            c = _color_from_values(fill.get("Values"))
            if c:
                out["textColor"] = c
        # 字体名: Font 索引 → DocumentResources.FontSet[idx].Name
        font_idx = style.get("Font")
        font_set = _get(ed, "DocumentResources", "FontSet", default=[]) or []
        if isinstance(font_idx, int) and 0 <= font_idx < len(font_set):
            fam = font_set[font_idx].get("Name")
            if fam:
                out["fontFamily"] = fam
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  效果提取
# ═══════════════════════════════════════════════════════════════════════════
def _eff_color(eff, opacity=None):
    """效果 color dict {b'Rd ':,b'Grn ':,b'Bl ':}(0-255) → {r,g,b,a}∈[0,1]。

    opacity (0..100) 传入时折算进 alpha。
    """
    c = getattr(eff, "color", None)
    if c is None:
        return None

    def pick(*keys):
        for k in keys:
            try:
                v = c.get(k)
            except Exception:
                v = None
            if v is not None:
                return float(v)
        return 0.0

    r = pick(b"Rd  ", "Rd  ", "Rd") / 255.0
    g = pick(b"Grn ", "Grn ", "Grn") / 255.0
    b = pick(b"Bl  ", "Bl  ", "Bl") / 255.0
    a = 1.0
    if opacity is not None:
        a = max(0.0, min(1.0, float(opacity) / 100.0))
    return {"r": r, "g": g, "b": b, "a": a}


def extract_effects(layer):
    """图层效果 → stroke 字段 + effects 数组 + colorOverlay。

    psd-tools Effects API: `layer.effects.items` 是属性 (list), 每项 .name 区分类型
    (Stroke / DropShadow / InnerShadow / ColorOverlay / GradientOverlay ...)。
    中等保真: stroke/drop_shadow/inner_shadow 映射; color_overlay 记为 overlay fill;
    gradient/pattern overlay 留 Phase 2。
    """
    out = {}
    try:
        eff = layer.effects
    except Exception:
        eff = None
    if not eff:
        return out
    items = getattr(eff, "items", None) or []

    effects = []
    overlay = None
    for it in items:
        name = getattr(it, "name", "")
        if name == "Stroke":
            sw = getattr(it, "size", None)
            if sw is not None:
                out["strokeWeight"] = float(sw)
            sc = _eff_color(it, getattr(it, "opacity", 100))
            if sc:
                out["strokeColor"] = sc
        elif name in ("DropShadow", "InnerShadow"):
            col = _eff_color(it, getattr(it, "opacity", 100))
            if col:
                distance = float(getattr(it, "distance", 0) or 0)
                angle = float(getattr(it, "angle", 0) or 0)
                rad = math.radians(angle)
                dx = round(distance * math.cos(rad), 2)
                dy = round(distance * math.sin(rad), 2)
                effects.append({
                    "type": "DROP_SHADOW" if name == "DropShadow" else "INNER_SHADOW",
                    "color": col,
                    "offset": {"x": dx, "y": dy},
                    "radius": float(getattr(it, "size", getattr(it, "blur", 0)) or 0),
                })
        elif name == "ColorOverlay":
            overlay = _eff_color(it, getattr(it, "opacity", 100))
    if overlay:
        out["colorOverlay"] = overlay
    if effects:
        out["effects"] = effects
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  位图导出
# ═══════════════════════════════════════════════════════════════════════════
def export_image(layer, tex_dir, seq):
    """像素/智能对象/形状图层 → PNG。返回文件名(无路径) 或 None。"""
    try:
        img = layer.topil()
    except Exception:
        img = None
    if img is None:
        return None
    name = f"{seq:03d}_{_sanitize(layer.name)}.png"
    os.makedirs(tex_dir, exist_ok=True)
    path = os.path.join(tex_dir, name)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    img.save(path, "PNG")
    return name


# ═══════════════════════════════════════════════════════════════════════════
#  递归遍历
# ═══════════════════════════════════════════════════════════════════════════
BITMAP_KINDS = {"pixel", "smartobject"}   # 栅格化为 image fill
SHAPE_KINDS = {"shape"}                    # 优先栅格化; 矢量填充/路径还原留 Phase 2


def walk_layer(layer, tex_dir, counter):
    """单个图层 → node dict。counter = [int] 用于位图文件名编号。"""
    kind = layer.kind
    node = {
        "name": layer.name,
        "psdKind": kind,
        "left": int(layer.left), "top": int(layer.top),
        "right": int(layer.right), "bottom": int(layer.bottom),
        "width": int(layer.right - layer.left),
        "height": int(layer.bottom - layer.top),
        "visible": bool(layer.visible),
        "opacity": round(layer.opacity / 255.0, 4),
        "blendMode": _blend_name(layer.blend_mode),
    }

    if kind == "type":
        node.update(extract_text(layer))

    if kind in BITMAP_KINDS or kind in SHAPE_KINDS:
        counter[0] += 1
        img_name = export_image(layer, tex_dir, counter[0])
        if img_name:
            node["exportImageName"] = img_name

    node.update(extract_effects(layer))

    if layer.is_group():
        node["children"] = [walk_layer(c, tex_dir, counter) for c in layer]
    return node


# ═══════════════════════════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════════════════════════
def parse_psd(psd_path, out_dir=None):
    """解析单个 PSD → {name}_psd.json + exported_textures/。返回 json 路径。"""
    psd = PSDImage.open(psd_path)
    asset_name = os.path.splitext(os.path.basename(psd_path))[0]

    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(psd_path), "output")
    tex_dir = os.path.join(out_dir, "exported_textures")
    os.makedirs(out_dir, exist_ok=True)

    counter = [0]
    children = [walk_layer(L, tex_dir, counter) for L in psd]

    doc = {
        "assetName": asset_name,
        "designSize": {"width": int(psd.width), "height": int(psd.height)},
        "root": {
            "name": asset_name,
            "psdKind": "group",
            "left": 0, "top": 0, "right": int(psd.width), "bottom": int(psd.height),
            "width": int(psd.width), "height": int(psd.height),
            "visible": True, "opacity": 1.0, "blendMode": "NORMAL",
            "children": children,
        },
    }

    json_path = os.path.join(out_dir, asset_name + "_psd.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    return json_path


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  py -3 parse_psd.py <input.psd> [out_dir]")
        print("  py -3 parse_psd.py <dir>      # 批量 *.psd")
        sys.exit(1)
    target = sys.argv[1]
    if os.path.isdir(target):
        import glob
        files = sorted(glob.glob(os.path.join(target, "*.psd")))
        if not files:
            print("No .psd in: " + target); sys.exit(1)
        for fp in files:
            print("  {} -> {}".format(os.path.basename(fp), parse_psd(fp)))
        return
    out = sys.argv[2] if len(sys.argv) >= 3 else None
    print("{} -> {}".format(target, parse_psd(target, out)))


if __name__ == "__main__":
    main()
