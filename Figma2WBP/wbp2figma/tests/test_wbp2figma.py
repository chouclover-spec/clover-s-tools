# -*- coding: utf-8 -*-
"""
test_wbp2figma.py — 翻译器与锚点数学单测 (本机可跑, 不依赖 UE/Figma)。

运行:
  cd wbp2figma/tests
  python test_wbp2figma.py
"""
import json
import os
import sys

# 让 tests/ 能 import 上层 wbp2figma 模块
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from geometry import slot_to_rect
from wbp2figma import translate_document, load_font_map


def approx(a, b, eps=0.01):
    return abs(a - b) < eps


def find_node(node, name):
    if node.get("name") == name:
        return node
    for c in node.get("children", []):
        r = find_node(c, name)
        if r:
            return r
    return None


def test_geometry():
    print("[geometry] slot_to_rect ...")
    # 点锚 + alignment (Title)
    slot = {
        "type": "CanvasPanelSlot",
        "anchors": {"min": {"x": 0.5, "y": 0.0}, "max": {"x": 0.5, "y": 0.0}},
        "offsets": {"left": -100, "top": 20, "right": 200, "bottom": 40},
        "alignment": {"x": 0.5, "y": 0.0},
    }
    x, y, w, h = slot_to_rect(slot, 1920, 1080)
    # pos_x = 960-100=860; x = 860 - 0.5*200 = 760; w=200; y=20; h=40
    assert approx(x, 760) and approx(y, 20) and approx(w, 200) and approx(h, 40), (x, y, w, h)

    # 全拉伸 (Bg)
    slot_full = {
        "type": "CanvasPanelSlot",
        "anchors": {"min": {"x": 0, "y": 0}, "max": {"x": 1, "y": 1}},
        "offsets": {"left": 0, "top": 0, "right": 0, "bottom": 0},
        "alignment": {"x": 0, "y": 0},
    }
    x, y, w, h = slot_to_rect(slot_full, 1920, 1080)
    assert approx(x, 0) and approx(y, 0) and approx(w, 1920) and approx(h, 1080), (x, y, w, h)

    # 右侧拉伸带 margin (RightPanel): x=0.7*1920+10=1354; right=1920-20=1900; w=546
    slot_right = {
        "type": "CanvasPanelSlot",
        "anchors": {"min": {"x": 0.7, "y": 0}, "max": {"x": 1.0, "y": 1.0}},
        "offsets": {"left": 10, "top": 0, "right": 20, "bottom": 0},
        "alignment": {"x": 0, "y": 0},
    }
    x, y, w, h = slot_to_rect(slot_right, 1920, 1080)
    assert approx(x, 1354) and approx(y, 0) and approx(w, 546) and approx(h, 1080), (x, y, w, h)
    print("  OK")


def test_translate():
    print("[translate] mock_wbp.json ...")
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "mock_wbp.json"), "r", encoding="utf-8") as f:
        doc = json.load(f)
    font_map = load_font_map(os.path.join(here, "..", "font_map.json"))
    scene = translate_document(doc, font_map)
    root = scene["root"]

    # root 是 CanvasPanel → FRAME
    assert root["type"] == "FRAME" and root["umgType"] == "CanvasPanel"

    # Bg: 全拉伸 → 0,0,1920,1080; RECTANGLE; 有 fill
    bg = find_node(root, "Bg")
    assert bg["type"] == "RECTANGLE"
    assert approx(bg["x"], 0) and approx(bg["y"], 0) and approx(bg["width"], 1920) and approx(bg["height"], 1080)
    assert bg["fills"][0]["color"]["r"] == 0.1

    # RightPanel: 拉伸锚宽 546
    rp = find_node(root, "RightPanel")
    assert approx(rp["x"], 1354) and approx(rp["width"], 546), (rp["x"], rp["width"])

    # Title: 点锚+alignment → x=760 y=20 w=200 h=40; TEXT; 字体映射 Roboto/Regular
    title = find_node(root, "Title")
    assert title["type"] == "TEXT"
    assert approx(title["x"], 760) and approx(title["y"], 20) and approx(title["width"], 200) and approx(title["height"], 40)
    assert title["text"] == "Hello"
    assert title["fontSize"] == 24
    assert title["fontName"] == {"family": "Roboto", "style": "Regular"}
    assert title["textAlignHorizontal"] == "CENTER"
    assert title["fills"][0]["color"]["a"] == 1

    # List: VerticalBox → FRAME + autoLayout VERTICAL; 子节点无 x/y
    lst = find_node(root, "List")
    assert lst["type"] == "FRAME" and lst["umgType"] == "VerticalBox"
    assert lst["autoLayout"]["layoutMode"] == "VERTICAL"
    # List 自身是 Canvas 子节点, 有点锚矩形: x=50, y=0.2*1080+50=266, w=300, h=600
    assert approx(lst["x"], 50) and approx(lst["y"], 266) and approx(lst["width"], 300) and approx(lst["height"], 600)
    # 子节点是 auto 子 → 不应出现 x/y
    item1 = find_node(root, "Item1")
    assert "x" not in item1 and "y" not in item1, item1
    assert item1["layoutSizingHorizontal"] == "FILL"
    assert item1["layoutSizingVertical"] == "HUG"
    assert item1["type"] == "TEXT"

    print("  OK")


if __name__ == "__main__":
    test_geometry()
    test_translate()
    print("\nAll tests passed.")
