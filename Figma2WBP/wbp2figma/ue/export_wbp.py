# -*- coding: utf-8 -*-
"""
export_wbp.py — UE4 编辑器内 Python 脚本: 把 WBP (Widget Blueprint) 导出成 wbp.json + 纹理 PNG。

在 UE4 编辑器内运行 (Python 插件 / Editor Utility)。运行方式见同目录 README_UE.md。

产出 (写到 out_dir, 默认 <脚本所在目录>/output):
  {assetName}_wbp.json      — UMG 节点树, 字段对齐 slim.json 契约, 供 wbp2figma.py 翻译
  exported_textures/*.png   — WBP 引用到的 UTexture2D (需编译 ExportTextureUtil C++ helper;
                              若未提供, 仅记录资产名, 由设计师手动导出 PNG 到此目录)

字段约定 (与 wbp2figma.py / geometry.py 对齐):
  name, umgType, width, height, x, y (canvas 子节点已求解), slot{...},
  content/fontSize/fontFamily/textAlignHorizontal/textColor (TextBlock),
  fillColor/fillOpacity/exportImageName (Image/Border),
  opacity, visible, clipsContent, children

注意:
  - 锚点数学与 wbp2figma/geometry.py:slot_to_rect 保持一致 (此处内联一份, 避免在 UE 沙箱里折腾 sys.path)。
  - UMG Python API 在不同 UE4 小版本略有差异, 读取属性均用 try/except 兜底; 校准见 README_UE.md。
  - 颜色取自 FLinearColor (线性空间), Figma 用 sRGB; 中等保真下直接传 0..1, 视觉会略偏亮, Phase 2 再做 gamma。
"""
import json
import os
import unreal

# ═══════════════════════════════════════════════════════════════════════════
#  锚点数学 (与 geometry.slot_to_rect 同步; 改动两处一起改)
# ═══════════════════════════════════════════════════════════════════════════
_EPS = 1e-6


def slot_to_rect(slot, parent_w, parent_h):
    anchors = slot.get("anchors", {"min": {"x": 0, "y": 0}, "max": {"x": 0, "y": 0}})
    offsets = slot.get("offsets", {"left": 0, "top": 0, "right": 0, "bottom": 0})
    align = slot.get("alignment", {"x": 0.0, "y": 0.0})
    min_x, max_x = anchors["min"]["x"], anchors["max"]["x"]
    min_y, max_y = anchors["min"]["y"], anchors["max"]["y"]

    def axis(min_a, max_a, off_pos, off_size, parent_size, al):
        if abs(min_a - max_a) < _EPS:  # 点锚
            pos = min_a * parent_size + off_pos
            size = off_size
            return pos - al * size, size
        else:                           # 拉伸锚
            left = min_a * parent_size + off_pos
            right = max_a * parent_size - off_size  # off_size 在拉伸轴表示 margin
            return left, right - left

    x, w = axis(min_x, max_x, offsets["left"], offsets["right"], parent_w, align["x"])
    y, h = axis(min_y, max_y, offsets["top"], offsets["bottom"], parent_h, align["y"])
    return x, y, w, h


# ═══════════════════════════════════════════════════════════════════════════
#  UE 结构体 → 纯 dict
# ═══════════════════════════════════════════════════════════════════════════
def _v2(v):
    """FVector2D → {x,y}。"""
    if v is None:
        return {"x": 0.0, "y": 0.0}
    try:
        return {"x": float(v.x), "y": float(v.y)}
    except Exception:
        try:
            return {"x": float(v.get_editor_property("x")), "y": float(v.get_editor_property("y"))}
        except Exception:
            return {"x": 0.0, "y": 0.0}


def _margin(m):
    """FMargin → {left,top,right,bottom}。"""
    if m is None:
        return {"left": 0.0, "top": 0.0, "right": 0.0, "bottom": 0.0}
    try:
        return {
            "left": float(m.left), "top": float(m.top),
            "right": float(m.right), "bottom": float(m.bottom),
        }
    except Exception:
        try:
            g = m.get_editor_property
            return {"left": float(g("left")), "top": float(g("top")),
                    "right": float(g("right")), "bottom": float(g("bottom"))}
        except Exception:
            return {"left": 0.0, "top": 0.0, "right": 0.0, "bottom": 0.0}


def _color(c):
    """FLinearColor → {r,g,b,a}∈[0,1]。"""
    if c is None:
        return None
    try:
        return {"r": float(c.r), "g": float(c.g), "b": float(c.b), "a": float(c.a)}
    except Exception:
        try:
            g = c.get_editor_property
            return {"r": float(g("r")), "g": float(g("g")), "b": float(g("b")), "a": float(g("a"))}
        except Exception:
            return None


def _anchors(a):
    """FAnchors → {min{x,y}, max{x,y}}。"""
    if a is None:
        return {"min": {"x": 0.0, "y": 0.0}, "max": {"x": 0.0, "y": 0.0}}
    # FAnchors 既有 minimum/maximum (Vector2D), 也有 left/top/right/bottom
    try:
        return {"min": _v2(a.minimum), "max": _v2(a.maximum)}
    except Exception:
        try:
            g = a.get_editor_property
            return {"min": _v2(g("minimum")), "max": _v2(g("maximum"))}
        except Exception:
            try:
                return {"min": {"x": float(a.left), "y": float(a.top)},
                        "max": {"x": float(a.right), "y": float(a.bottom)}}
            except Exception:
                return {"min": {"x": 0.0, "y": 0.0}, "max": {"x": 0.0, "y": 0.0}}


# ═══════════════════════════════════════════════════════════════════════════
#  属性读取
# ═══════════════════════════════════════════════════════════════════════════
def _get(obj, name, default=None):
    """优先 get_editor_property, 回退属性访问。"""
    try:
        return obj.get_editor_property(name)
    except Exception:
        try:
            return getattr(obj, name)
        except Exception:
            return default


def _call(obj, name, *args, default=None):
    try:
        return getattr(obj, name)(*args)
    except Exception:
        return default


def _is_panel(widget):
    """是否为 UPanelWidget (有子节点)。"""
    try:
        return bool(unreal.cast(widget, unreal.PanelWidget))
    except Exception:
        cls = widget.get_class()
        try:
            return cls.is_child_of(unreal.PanelWidget.static_class())
        except Exception:
            return False


def get_children(widget):
    if _is_panel(widget):
        try:
            n = widget.get_child_count()
            return [widget.get_child_at(i) for i in range(int(n))]
        except Exception:
            pass
    return []


def read_slot(slot):
    """UPanelSlot → dict。返回 None 表示无 slot (根节点)。"""
    if slot is None:
        return None
    slot_type = slot.get_class().get_name()
    info = {"type": slot_type}

    if slot_type == "CanvasPanelSlot":
        info["anchors"] = _anchors(_call(slot, "get_anchors"))
        info["offsets"] = _margin(_call(slot, "get_offsets"))
        info["alignment"] = _v2(_call(slot, "get_alignment"))
        size = _call(slot, "get_size", default=None)
        if size is not None:
            info["size"] = _v2(size)
    elif slot_type in ("VerticalBoxSlot", "HorizontalBoxSlot", "WrapBoxSlot"):
        info["padding"] = _margin(_call(slot, "get_padding", default=None))
        info["alignment"] = _v2(_call(slot, "get_alignment", default=None))
        so = _read_size_override(slot)
        if so:
            info["sizeOverride"] = so
    elif slot_type == "BorderSlot":
        info["padding"] = _margin(_call(slot, "get_padding", default=None))
        info["alignment"] = _v2(_call(slot, "get_alignment", default=None))
        so = _read_size_override(slot)
        if so:
            info["sizeOverride"] = so
    elif slot_type == "OverlaySlot":
        info["padding"] = _margin(_call(slot, "get_padding", default=None))
        info["alignment"] = _v2(_call(slot, "get_alignment", default=None))
    elif slot_type == "SizeBoxSlot":
        so = _read_size_override(slot)
        if so:
            info["sizeOverride"] = so
    return info


def _read_size_override(slot):
    """Box/Border slot 的 Size (FVector2D) → {horizontal, vertical} sizing 提示。"""
    try:
        size = slot.get_size()
        sv = _v2(size)
        out = {}
        # 粗映射: 非 0 → FIXED; 0 → FILL (UMG 约定 0=fill)
        out["horizontal"] = "FIXED" if abs(sv["x"]) > _EPS else "FILL"
        out["vertical"] = "FIXED" if abs(sv["y"]) > _EPS else "FILL"
        return out
    except Exception:
        return None


def read_text_props(widget, out):
    # content
    ftext = _call(widget, "get_text", default=None)
    if ftext is not None:
        try:
            out["content"] = unreal.TextLibrary.text_to_string(ftext) if hasattr(unreal, "TextLibrary") else str(ftext)
        except Exception:
            try:
                out["content"] = str(ftext)
            except Exception:
                out["content"] = ""
    # font
    font = _call(widget, "get_font", default=None)
    if font is not None:
        size = _get(font, "size")
        if size is not None:
            out["fontSize"] = int(round(float(size)))
        typeface = _get(font, "typeface")
        font_obj = _get(font, "font_object")
        legacy_name = _get(font, "font_name")
        fam = None
        if font_obj is not None:
            try:
                fam = font_obj.get_name()
            except Exception:
                fam = None
        if not fam and legacy_name:
            fam = str(legacy_name)
        if fam:
            out["fontFamily"] = fam
        if typeface:
            out["fontStyle"] = str(typeface)
    # color
    col = _call(widget, "get_color_and_opacity", default=None)
    tc = _color(col)
    if tc is not None:
        out["textColor"] = tc
    # justification
    just = _get(widget, "justification")
    if just is not None:
        out["textAlignHorizontal"] = str(just).split(".")[-1]  # ETextJustify::Center → Center
    # wrap
    wrapping = _get(widget, "wrapping_policy")
    auto_wrap = _get(widget, "auto_wrap_text")
    if auto_wrap:
        out["autoResize"] = "WrapText"


def read_brush_props(widget, out, texture_collector):
    brush = _call(widget, "get_brush", default=None) \
        or _call(widget, "get_background_brush", default=None)
    if brush is None:
        return
    tint = _get(brush, "tint")
    fc = _color(tint)
    if fc is not None and (fc["a"] > 0):
        out["fillColor"] = fc
    # 纹理引用
    res_obj = _get(brush, "resource_object")
    res_name = _get(brush, "resource_name")
    if res_obj is not None:
        try:
            asset_name = res_obj.get_name()
            out["exportImageName"] = asset_name
            texture_collector[asset_name] = res_obj
        except Exception:
            pass
    elif res_name:
        out["exportImageName"] = str(res_name)


def read_widget(widget, parent_size, texture_collector):
    cls_name = widget.get_class().get_name()
    node = {
        "name": widget.get_name(),
        "umgType": cls_name,
    }

    # 尺寸: 优先用 slot 求解 (canvas), 否则读 desired size
    slot = read_slot(_call(widget, "get_slot", default=None))
    if slot:
        node["slot"] = slot

    parent_w, parent_h = parent_size
    own_w, own_h = 0.0, 0.0
    if slot and slot.get("type") == "CanvasPanelSlot" and parent_w and parent_h:
        x, y, w, h = slot_to_rect(slot, parent_w, parent_h)
        node["x"], node["y"] = round(x, 2), round(y, 2)
        node["width"], node["height"] = round(w, 2), round(h, 2)
        own_w, own_h = w, h
    else:
        ds = _call(widget, "get_desired_size", default=None)
        if ds is not None:
            v = _v2(ds)
            own_w, own_h = v["x"], v["y"]
            node["width"], node["height"] = round(own_w, 2), round(own_h, 2)

    # 类型专属
    if cls_name == "TextBlock" or cls_name == "RichTextBlock":
        read_text_props(widget, node)
    elif cls_name in ("Image", "Border", "Button"):
        read_brush_props(widget, node, texture_collector)
        if cls_name == "Border":
            pad = _call(widget, "get_padding", default=None)
            if pad is not None:
                node["padding"] = _margin(pad)

    # 通用
    rop = _get(widget, "render_opacity")
    if rop is not None and abs(float(rop) - 1.0) > _EPS:
        node["opacity"] = float(rop)
    vis = _call(widget, "get_visibility", default=None)
    if vis is not None:
        vis_str = str(vis).split(".")[-1]  # ESlateVisibility::Collapsed → Collapsed
        if vis_str in ("Collapsed", "Hidden"):
            node["visible"] = False
    if cls_name in ("ScrollBox", "UIScrollBox"):
        node["clipsContent"] = True
    # render transform (Phase 2 用, 先记录)
    rt = _call(widget, "get_render_transform", default=None)
    if rt is not None:
        try:
            node["renderTransform"] = {
                "translation": _v2(_get(rt, "translation")),
                "scale": _v2(_get(rt, "scale")),
                "shear": _v2(_get(rt, "shear")),
                "angle": float(_get(rt, "angle", 0.0) or 0.0),
            }
        except Exception:
            pass

    # 子节点
    children = get_children(widget)
    if children:
        node["children"] = [read_widget(c, (own_w, own_h), texture_collector) for c in children]
    return node


# ═══════════════════════════════════════════════════════════════════════════
#  纹理导出
# ═══════════════════════════════════════════════════════════════════════════
def export_textures(texture_collector, out_dir):
    """把收集到的 UTexture2D 导出为 PNG。

    首选调用项目里的 C++ helper UExportTextureUtil::ExportToPng (见 cpp/)。
    若不可用, 仅打印资产清单, 由设计师手动导出到 exported_textures/。
    """
    tex_dir = os.path.join(out_dir, "exported_textures")
    os.makedirs(tex_dir, exist_ok=True)
    util = getattr(unreal, "ExportTextureUtil", None)
    exported = []
    if util is None:
        unreal.log_warning(
            "[wbp2figma] unreal.ExportTextureUtil 未找到 — 请编译 ue/cpp/ExportTextureUtil。"
            " 本次仅记录纹理清单, 请手动导出 PNG 到: " + tex_dir)
        for name, tex in texture_collector.items():
            try:
                path = tex.get_path_name()
            except Exception:
                path = "?"
            exported.append({"name": name, "path": path, "exported": False})
        return exported

    for name, tex in texture_collector.items():
        png_path = os.path.join(tex_dir, name + ".png")
        try:
            util.export_to_png(tex, png_path)
            exported.append({"name": name, "path": tex.get_path_name(), "exported": True})
        except Exception as e:
            unreal.log_warning("[wbp2figma] export failed: {} ({})".format(name, e))
            exported.append({"name": name, "path": "?", "exported": False})
    return exported


# ═══════════════════════════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════════════════════════
def export_wbp(asset_path, out_dir):
    """导出单个 WBP 资产。asset_path 形如 /Game/UI/WBP_Button。"""
    bp = unreal.EditorAssetLibrary.load_asset(asset_path)
    if bp is None:
        raise RuntimeError("load failed: " + asset_path)
    if not isinstance(bp, unreal.WidgetBlueprint):
        raise RuntimeError("not a WidgetBlueprint: " + asset_path)

    widget_tree = _get(bp, "widget_tree") or _call(bp, "get_widget_tree", default=None)
    if widget_tree is None:
        raise RuntimeError("no widget tree: " + asset_path)
    root_widget = _call(widget_tree, "get_root_widget", default=None)
    if root_widget is None:
        raise RuntimeError("no root widget: " + asset_path)

    asset_name = asset_path.rsplit("/", 1)[-1]
    # 设计尺寸: 优先读 root widget 的预置尺寸, 兜底 1920x1080
    root_size = _call(root_widget, "get_desired_size", default=None)
    if root_size is not None:
        v = _v2(root_size)
        design_w, design_h = int(round(v["x"])), int(round(v["y"]))
    else:
        design_w, design_h = 1920, 1080
    if design_w == 0 or design_h == 0:
        design_w, design_h = 1920, 1080

    texture_collector = {}
    root_node = read_widget(root_widget, (design_w, design_h), texture_collector)

    doc = {
        "assetName": asset_name,
        "assetPath": asset_path,
        "designSize": {"width": design_w, "height": design_h},
        "root": root_node,
    }

    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, asset_name + "_wbp.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    tex_manifest = export_textures(texture_collector, out_dir)
    # 把纹理清单附进 json 便于对账
    doc["textures"] = tex_manifest
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    n_nodes = _count_nodes(root_node)
    unreal.log("[wbp2figma] {} -> {} ({} nodes, {} textures)".format(
        asset_name, json_path, n_nodes, len(tex_manifest)))
    return json_path


def _count_nodes(node):
    n = 1
    for c in node.get("children", []):
        n += _count_nodes(c)
    return n


def export_many(asset_paths, out_dir=None):
    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    results = []
    for p in asset_paths:
        try:
            results.append(export_wbp(p, out_dir))
        except Exception as e:
            unreal.log_error("[wbp2figma] FAILED {}: {}".format(p, e))
    return results


# ── 在编辑器 Python 控制台直接调用 ──────────────────────────────────────
# 示例:
#   import sys
#   sys.path.append(r"D:\ClaudeCode\Figma2WBP\wbp2figma\ue")
#   import export_wbp
#   export_wbp.export_many(["/Game/UI/WBP_Button", "/Game/UI/WBP_HUD"],
#                          r"D:\ClaudeCode\Figma2WBP\wbp2figma\ue\output")
