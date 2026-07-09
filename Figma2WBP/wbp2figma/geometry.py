# -*- coding: utf-8 -*-
"""
geometry.py — UMG CanvasPanelSlot 锚点 → 像素矩形求解（纯 Python，无 unreal 依赖）

UMG Canvas 槽位用 (Anchors + Offsets + Alignment + Size) 描述子控件位置；
Figma 用绝对像素 x/y/width/height。本模块做这层换算，供 UE 提取脚本与翻译器共用。

slot dict 约定:
  {
    "type": "CanvasPanelSlot",
    "anchors": {"min": {"x": 0.5, "y": 0.0}, "max": {"x": 0.5, "y": 0.0}},
    "offsets": {"left": -100, "top": 20, "right": 200, "bottom": 40},
    "alignment": {"x": 0.5, "y": 0.0}      # 可选, 缺省 {0,0}
  }

UMG 语义:
  - 点锚 (min == max, 逐轴判断): Position = anchor*parent + offset(left/top)
                                  Size = offset(right/bottom)
                                  左上角 = Position - alignment*Size
  - 拉伸锚 (min != max): left   = min*parent + offset.left
                          right  = max*parent - offset.right
                          width  = right - left   (alignment 对拉伸轴无效)
  X/Y 轴独立判定, 允许一轴点锚一轴拉伸。
"""

EPS = 1e-6


def _is_point(a_min, a_max):
    return abs(a_min - a_max) < EPS


def slot_to_rect(slot, parent_w, parent_h):
    """返回相对父节点的 (x, y, width, height) 像素矩形。

    parent_w / parent_h: 父容器设计尺寸 (px)。
    """
    anchors = slot.get("anchors", {"min": {"x": 0, "y": 0}, "max": {"x": 0, "y": 0}})
    offsets = slot.get("offsets", {"left": 0, "top": 0, "right": 0, "bottom": 0})
    align = slot.get("alignment", {"x": 0.0, "y": 0.0})

    min_x = anchors["min"]["x"]
    max_x = anchors["max"]["x"]
    min_y = anchors["min"]["y"]
    max_y = anchors["max"]["y"]

    # ── X 轴 ──
    if _is_point(min_x, max_x):
        # 点锚: position_x = min_x*parent_w + offset.left; size_x = offset.right
        pos_x = min_x * parent_w + offsets["left"]
        w = offsets["right"]
        x = pos_x - align["x"] * w
    else:
        # 拉伸锚: left = min*parent + offset.left; right = max*parent - offset.right
        x = min_x * parent_w + offsets["left"]
        right = max_x * parent_w - offsets["right"]
        w = right - x

    # ── Y 轴 ──
    if _is_point(min_y, max_y):
        pos_y = min_y * parent_h + offsets["top"]
        h = offsets["bottom"]
        y = pos_y - align["y"] * h
    else:
        y = min_y * parent_h + offsets["top"]
        bottom = max_y * parent_h - offsets["bottom"]
        h = bottom - y

    return x, y, w, h


def rect_to_slot(x, y, w, h, parent_w, parent_h):
    """反向工具: 像素矩形 → 等价的点锚 slot (alignment={0,0})。调试/对账用。"""
    return {
        "type": "CanvasPanelSlot",
        "anchors": {"min": {"x": 0.0, "y": 0.0}, "max": {"x": 0.0, "y": 0.0}},
        "offsets": {"left": x, "top": y, "right": w, "bottom": h},
        "alignment": {"x": 0.0, "y": 0.0},
    }
