# -*- coding: utf-8 -*-
"""
slim_json.py  —  精简 Figma2Json 导出的 JSON，只保留布局所需字段
用法:
  python slim_json.py <input.json> [output_slim.json]   # 单文件
  python slim_json.py <目录>                             # 批量处理目录下所有 .json

保留字段:
  name, type, x, y, width, height, children, fontSize
可选保留(按需开关):
  opacity, fills[].opacity, cornerRadius
"""
import json
import sys
import os
import glob

# ── 可选：需要额外保留的字段 ──────────────────────────────────────────
EXTRA_FIELDS = [
    # "opacity",        # 整体透明度（半透明节点时开启）
    # "cornerRadius",   # 圆角（圆角矩形时开启）
    # "fills",          # 填充色（纯色背景时开启）
]
# ─────────────────────────────────────────────────────────────────────

BASE_FIELDS = {"name", "type", "x", "y", "width", "height", "exportImageName"}
KEEP_FIELDS = BASE_FIELDS | set(EXTRA_FIELDS)

# ── 从嵌套对象中提取到顶层的字段 ─────────────────────────────────────
NESTED_FIELDS = {
    "text": ["fontSize", "fontFamily", "fontStyle", "textAlignHorizontal", "textAlignVertical", "letterSpacing", "content", "autoResize"],
    "autoLayout": ["layoutMode", "primaryAxisAlignItems", "counterAxisAlignItems", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "itemSpacing"],
    "layoutSizing": ["layoutSizingHorizontal", "layoutSizingVertical"],
}
# ─────────────────────────────────────────────────────────────────────


def _round6(v):
    """如果 v 是浮点数，保留最多6位小数；否则原样返回。"""
    if isinstance(v, float):
        return round(v, 6)
    return v


def slim(node):
    """递归精简单个节点。"""
    result = {k: _round6(node[k]) for k in KEEP_FIELDS if k in node}
    # 提取嵌套字段到顶层
    for parent_key, fields in NESTED_FIELDS.items():
        sub = node.get(parent_key)
        if isinstance(sub, dict):
            for f in fields:
                if f in sub:
                    result[f] = _round6(sub[f])

    # 提取 text.textColor（文本颜色对象）
    text_obj = node.get("text")
    if isinstance(text_obj, dict):
        tc = text_obj.get("textColor")
        if isinstance(tc, dict):
            result["textColor"] = tc

    # 提取 opacity（节点整体透明度）
    opacity = node.get("opacity")
    if opacity is not None:
        result["opacity"] = _round6(opacity)

    # 提取 fills[0].color（第一个填充的颜色, SOLID 类型）
    fills = node.get("fills")
    if isinstance(fills, list) and len(fills) > 0:
        fill0 = fills[0]
        if isinstance(fill0, dict) and fill0.get("type") == "SOLID":
            color = fill0.get("color")
            if isinstance(color, dict):
                result["fillColor"] = {
                    "r": color.get("r", 0),
                    "g": color.get("g", 0),
                    "b": color.get("b", 0),
                    "a": color.get("a", 1),
                }
            fill_opacity = fill0.get("opacity")
            if fill_opacity is not None:
                result["fillOpacity"] = _round6(fill_opacity)

    # 提取 visible（仅在 false 时保留）
    visible = node.get("visible")
    if visible is False:
        result["visible"] = False

    # 提取 clipsContent（是否裁剪子控件）
    clips = node.get("clipsContent")
    if clips is not None:
        result["clipsContent"] = clips

    # 提取 strokes[0] 的 weight 和 align
    strokes = node.get("strokes")
    if isinstance(strokes, list) and len(strokes) > 0:
        stroke0 = strokes[0]
        if isinstance(stroke0, dict):
            sw = stroke0.get("weight")
            if sw is not None:
                result["strokeWeight"] = sw
            sa = stroke0.get("align")
            if sa is not None:
                result["strokeAlign"] = sa

    children = node.get("children", [])
    if children:
        # GROUP 子控件的坐标是绝对坐标，需转为相对于 GROUP 的局部坐标
        is_group = (node.get("type") == "GROUP")
        parent_x = node.get("x", 0) if is_group else 0
        parent_y = node.get("y", 0) if is_group else 0
        slimmed = []
        for c in children:
            sc = slim(c)
            if is_group:
                sc["x"] = _round6(sc.get("x", 0) - parent_x)
                sc["y"] = _round6(sc.get("y", 0) - parent_y)
            slimmed.append(sc)
        result["children"] = slimmed
    return result


def process_file(input_path, output_path=None):
    """处理单个 JSON 文件，生成 slim/ 子目录下的输出。"""
    input_dir = os.path.dirname(input_path)
    basename = os.path.splitext(os.path.basename(input_path))[0]
    ext = os.path.splitext(input_path)[1]

    slim_dir = os.path.join(input_dir, "output", "slim")
    os.makedirs(slim_dir, exist_ok=True)

    if output_path is None:
        output_path = os.path.join(slim_dir, basename + "_slim" + ext)

    with open(input_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # 适配 Figma2Json 导出格式：节点树在 "frame" 字段内
    has_frame = "frame" in raw and isinstance(raw["frame"], dict)
    root_node = raw["frame"] if has_frame else raw

    # ── slim 输出 ──────────────────────────────────────────────────
    if has_frame:
        slim_data = dict(raw)
        slim_data["frame"] = slim(root_node)
    else:
        slim_data = slim(root_node)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(slim_data, f, ensure_ascii=False, indent=2)

    raw_size = os.path.getsize(input_path)
    slim_size = os.path.getsize(output_path)
    return raw_size, slim_size, output_path


def print_nodes(node, depth=0):
    """打印节点摘要树。"""
    x = node.get("x", 0)
    y = node.get("y", 0)
    w = node.get("width", 0)
    h = node.get("height", 0)
    t = node.get("type", "")
    print("  " * depth + "[{}] {} | x={} y={} w={} h={}".format(
        t, node.get("name", ""), int(x), int(y), int(w), int(h)))
    for c in node.get("children", []):
        print_nodes(c, depth + 1)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python slim_json.py <input.json> [output_slim.json]")
        print("  python slim_json.py <directory>")
        sys.exit(1)

    target = sys.argv[1]

    # ── 批量模式：传入目录 ──────────────────────────────────────────
    if os.path.isdir(target):
        json_files = sorted(glob.glob(os.path.join(target, "*.json")))
        if not json_files:
            print("No JSON files found in: " + target)
            sys.exit(1)

        total_raw = 0
        total_slim = 0
        print("Processing {} files in: {}\n".format(len(json_files), target))

        for fpath in json_files:
            raw_size, slim_size, out_path = process_file(fpath)
            total_raw += raw_size
            total_slim += slim_size
            ratio = (1 - slim_size / raw_size) * 100 if raw_size else 0
            print("  {} -> {} ({:,} -> {:,}, -{:.1f}%)".format(
                os.path.basename(fpath),
                os.path.basename(out_path),
                raw_size, slim_size, ratio))

        total_ratio = (1 - total_slim / total_raw) * 100 if total_raw else 0
        print("\nTotal: {:,} -> {:,} bytes, -{:.1f}%".format(
            total_raw, total_slim, total_ratio))
        return

    # ── 单文件模式 ──────────────────────────────────────────────────
    input_path = target
    output_path = sys.argv[2] if len(sys.argv) >= 3 else None

    raw_size, slim_size, output_path = process_file(input_path, output_path)
    ratio = (1 - slim_size / raw_size) * 100 if raw_size else 0

    print("Input : {} ({:,} bytes)".format(input_path, raw_size))
    print("Slim  : {} ({:,} bytes, -{:.1f}%)".format(output_path, slim_size, ratio))

    with open(output_path, "r", encoding="utf-8") as f:
        slim_data = json.load(f)

    root = slim_data.get("frame", slim_data)
    print("\n--- Node summary ---")
    print_nodes(root)


if __name__ == "__main__":
    main()
