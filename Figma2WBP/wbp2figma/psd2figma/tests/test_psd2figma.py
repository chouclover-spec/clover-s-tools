# -*- coding: utf-8 -*-
"""
test_psd2figma.py — 翻译器单测 (坐标转换 / 类型映射 / 混合模式 / 效果)。

运行:
  cd wbp2figma/psd2figma/tests
  py -3 test_psd2figma.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from psd2figma import translate_document, map_blend, map_font, load_font_map


def approx(a, b, eps=0.01):
    return abs(a - b) < eps


def find(node, name):
    if node.get("name") == name:
        return node
    for c in node.get("children", []):
        r = find(c, name)
        if r:
            return r
    return None


# ── 手写 mock psd.json, 覆盖坐标转换/类型/混合模式/效果 ──
MOCK = {
    "assetName": "mock",
    "designSize": {"width": 100, "height": 200},
    "root": {
        "name": "mock", "psdKind": "group",
        "left": 0, "top": 0, "right": 100, "bottom": 200, "width": 100, "height": 200,
        "visible": True, "opacity": 1.0, "blendMode": "NORMAL",
        "children": [
            {"name": "BG", "psdKind": "pixel", "left": 0, "top": 0, "right": 100, "bottom": 200,
             "width": 100, "height": 200, "visible": True, "opacity": 1.0, "blendMode": "NORMAL",
             "exportImageName": "bg.png"},
            {"name": "Panel", "psdKind": "group", "left": 10, "top": 10, "right": 60, "bottom": 90,
             "width": 50, "height": 80, "visible": True, "opacity": 0.8, "blendMode": "PASS_THROUGH",
             "children": [
                 {"name": "Icon", "psdKind": "shape", "left": 10, "top": 10, "right": 40, "bottom": 40,
                  "width": 30, "height": 30, "visible": True, "opacity": 1.0, "blendMode": "NORMAL",
                  "exportImageName": "icon.png", "strokeWeight": 2.0,
                  "strokeColor": {"r": 1, "g": 0, "b": 0, "a": 1}},
                 {"name": "Label", "psdKind": "type", "left": 10, "top": 60, "right": 40, "bottom": 80,
                  "width": 30, "height": 20, "visible": False, "opacity": 1.0, "blendMode": "NORMAL",
                  "text": "Hi", "fontSize": 14, "fontFamily": "ArialMT",
                  "textColor": {"r": 0.2, "g": 0.3, "b": 0.4, "a": 1}},
             ]},
            {"name": "Title", "psdKind": "type", "left": 0, "top": 0, "right": 100, "bottom": 20,
             "width": 100, "height": 20, "visible": True, "opacity": 1.0, "blendMode": "MULTIPLY",
             "text": "T", "fontSize": 24, "textColor": {"r": 1, "g": 1, "b": 1, "a": 1}},
        ],
    },
}


def test_translate():
    print("[translate] mock psd ...")
    scene = translate_document(MOCK, load_font_map())
    root = scene["root"]

    # root
    assert root["type"] == "FRAME" and root["layoutMode"] == "NONE"
    assert root["width"] == 100 and root["height"] == 200

    # BG: pixel → RECTANGLE, 相对 root (0,0), exportImageName
    bg = find(root, "BG")
    assert bg["type"] == "RECTANGLE"
    assert approx(bg["x"], 0) and approx(bg["y"], 0)
    assert bg["exportImageName"] == "bg.png"

    # Panel: group → FRAME, 相对 root (10,10), blendMode PASS_THROUGH, opacity 0.8
    panel = find(root, "Panel")
    assert panel["type"] == "FRAME"
    assert approx(panel["x"], 10) and approx(panel["y"], 10)
    assert panel["blendMode"] == "PASS_THROUGH"
    assert approx(panel["opacity"], 0.8)

    # Icon: shape → RECTANGLE, 相对 Panel (0,0) (Icon.left 10 - Panel.left 10), stroke
    icon = find(root, "Icon")
    assert icon["type"] == "RECTANGLE"
    assert approx(icon["x"], 0) and approx(icon["y"], 0), (icon["x"], icon["y"])
    assert icon["strokeWeight"] == 2.0
    assert icon["strokes"][0]["color"]["r"] == 1

    # Label: type → TEXT, 相对 Panel (0, 50) (60-10), visible=False, 字体映射
    label = find(root, "Label")
    assert label["type"] == "TEXT"
    assert approx(label["x"], 0) and approx(label["y"], 50), (label["x"], label["y"])
    assert label["visible"] is False
    assert label["fontSize"] == 14
    assert label["fills"][0]["color"]["g"] == 0.3
    # ArialMT → 清洗为 Arial → font_map 命中
    assert label["fontName"]["family"] == "Arial", label["fontName"]

    # Title: type, blendMode MULTIPLY
    title = find(root, "Title")
    assert title["type"] == "TEXT"
    assert title["blendMode"] == "MULTIPLY"
    assert "blendMode" not in bg  # NORMAL 不设
    print("  OK")


def test_blend_map():
    print("[blend] map_blend ...")
    assert map_blend("NORMAL") is None
    assert map_blend("PASS_THROUGH") == "PASS_THROUGH"
    assert map_blend("MULTIPLY") == "MULTIPLY"
    assert map_blend("DISSOLVE") is None  # 无对应
    print("  OK")


def test_end_to_end_real():
    """若真实 psd.json 存在, 验证 type-layer → TEXT。"""
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "output", "type-layer_psd.json")
    if not os.path.exists(p):
        print("[e2e] type-layer_psd.json 不存在, 跳过 (先跑 parse_psd.py)")
        return
    print("[e2e] type-layer ...")
    with open(p, "r", encoding="utf-8") as f:
        doc = json.load(f)
    scene = translate_document(doc, load_font_map())
    t = scene["root"]["children"][0]
    assert t["type"] == "TEXT"
    assert t["text"] == "A"
    assert t["fontSize"] == 30.0
    assert t["fills"][0]["color"]["r"] == 1.0  # 黄色
    print("  OK")


if __name__ == "__main__":
    test_translate()
    test_blend_map()
    test_end_to_end_real()
    print("\nAll tests passed.")
