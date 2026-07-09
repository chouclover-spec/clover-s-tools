# -*- coding: utf-8 -*-
"""
figma2ui.py  —  Figma → UMG 控件类型转换（两阶段 AI 辅助流程）

用法:
  # 阶段1: 提取上下文（供 AI 阅读）
  python figma2ui.py <export目录> <文件名> --extract
  python figma2ui.py <export目录> --extract          # 批量

  # 阶段2: 应用 AI 的类型映射
  python figma2ui.py <export目录> <文件名> --apply <mapping.json>
  python figma2ui.py <export目录> --apply             # 批量（读取同名 _mapping.json）

输入:
  - output/slim/      : {文件名}_slim.json   — 完整节点属性 (type, x, y, width, height, autoLayout 等)

输出 (--extract):
  - output/figma2ui_temp/ : {文件名}_context.txt   — 带编号的节点上下文（供 AI 阅读）

输出 (--apply):
  - output/figma2ui/      : {文件名}.figma2ui      — 最终输出（type 已填入 UMG 类型）
  (读取 output/figma2ui_temp/{文件名}_mapping.json 作为输入)

类型映射规则参见 UMG_WIDGET_REFERENCE.md
"""
import json
import sys
import os
import glob
import shutil


# ═══════════════════════════════════════════════════════════════════════════
#  阶段1: 从 slim 提取上下文
# ═══════════════════════════════════════════════════════════════════════════

def extract_context_lines(node, lines=None, depth=0, is_root=False):
    """递归生成带编号的上下文行列表。

    每行格式:
      {编号}. {缩进}{名称} [{Figma类型}] {宽}x{高} {附加信息}

    附加信息包括: autoLayout=方向, ch=子节点数(子类型摘要), leaf, root
    """
    if lines is None:
        lines = []

    name = node.get("name", "")
    figma_type = node.get("type", "")
    w = int(round(node.get("width", node.get("w", 0))))
    h = int(round(node.get("height", node.get("h", 0))))
    children = node.get("children", [])

    # 构建附加信息
    extras = []
    if is_root:
        extras.append("root")

    # autoLayout
    layout_mode = node.get("layoutMode")
    if not layout_mode:
        al = node.get("autoLayout")
        if isinstance(al, dict):
            layout_mode = al.get("layoutMode")
    if layout_mode:
        extras.append(f"autoLayout={layout_mode}")

    # layoutSizing
    lsh = node.get("layoutSizingHorizontal")
    lsv = node.get("layoutSizingVertical")
    if lsh or lsv:
        sizing_parts = []
        if lsh:
            sizing_parts.append(f"H={lsh}")
        if lsv:
            sizing_parts.append(f"V={lsv}")
        extras.append(f"sizing({','.join(sizing_parts)})")

    # 子节点摘要
    if children:
        child_types = [c.get("type", "?") for c in children]
        unique_types = list(dict.fromkeys(child_types))  # 去重保序
        type_summary = ",".join(unique_types) if len(unique_types) <= 3 else f"{unique_types[0]}..x{len(child_types)}"
        extras.append(f"ch={len(children)}({type_summary})")

        # 检测子控件是否溢出父容器（主轴方向）
        if layout_mode == "HORIZONTAL":
            item_spacing = node.get("itemSpacing", 0)
            total_child_w = sum(c.get("width", c.get("w", 0)) for c in children)
            total_w = total_child_w + item_spacing * max(0, len(children) - 1)
            if w > 0 and total_w > w:
                extras.append("overflow")
        elif layout_mode == "VERTICAL":
            item_spacing = node.get("itemSpacing", 0)
            total_child_h = sum(c.get("height", c.get("h", 0)) for c in children)
            total_h = total_child_h + item_spacing * max(0, len(children) - 1)
            if h > 0 and total_h > h:
                extras.append("overflow")
    elif figma_type == "FRAME":
        extras.append("leaf")

    indent = "  " * depth
    extra_str = " " + " ".join(extras) if extras else ""
    line = f"{indent}{name} [{figma_type}] {w}x{h}{extra_str}"
    lines.append(line)

    for child in children:
        extract_context_lines(child, lines, depth + 1, is_root=False)

    return lines


# ═══════════════════════════════════════════════════════════════════════════
#  阶段2: 从 slim 构建最终树并应用映射
# ═══════════════════════════════════════════════════════════════════════════

def build_and_apply(node, mapping, counter=None):
    """从 slim 节点直接构建最终 .figma2ui 树，同时应用 AI 的类型映射。

    mapping: dict, key 为字符串行号 "1","2",..., value 为 UMG 类型
    counter: [int] 可变列表，跟踪当前行号（与 extract_context_lines 同步 DFS 顺序）
    """
    if counter is None:
        counter = [0]

    counter[0] += 1
    idx = str(counter[0])

    w_key = "width" if "width" in node else "w"
    h_key = "height" if "height" in node else "h"

    result = {
        "name": node.get("name", ""),
        "type": mapping.get(idx, ""),
        "x": node.get("x", 0),
        "y": node.get("y", 0),
        "w": round(node.get(w_key, 0), 1),
        "h": round(node.get(h_key, 0), 1),
    }

    # text fields
    text_obj = node.get("text")
    for field in ("fontSize", "fontFamily", "fontStyle", "textAlignHorizontal", "textAlignVertical", "letterSpacing", "content", "autoResize"):
        val = node.get(field)
        if val is None and isinstance(text_obj, dict):
            val = text_obj.get(field)
        if val is not None:
            result[field] = val

    # padding 和 itemSpacing
    for field in ("paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "itemSpacing"):
        val = node.get(field)
        if val is not None and val > 0:
            result[field] = val

    # layoutSizing
    for field in ("layoutSizingHorizontal", "layoutSizingVertical"):
        val = node.get(field)
        if val is not None:
            result[field] = val

    # alignment
    for field in ("primaryAxisAlignItems", "counterAxisAlignItems"):
        val = node.get(field)
        if val is not None:
            result[field] = val

    # color and opacity (for Image-type nodes)
    opacity = node.get("opacity")
    if opacity is not None:
        result["opacity"] = opacity
    fill_color = node.get("fillColor")
    if fill_color is not None:
        result["fillColor"] = fill_color
    fill_opacity = node.get("fillOpacity")
    if fill_opacity is not None:
        result["fillOpacity"] = fill_opacity

    # textColor (for Text nodes)
    text_color = node.get("textColor")
    if text_color is not None:
        result["textColor"] = text_color

    # strokeWeight / strokeAlign
    for field in ("strokeWeight", "strokeAlign"):
        val = node.get(field)
        if val is not None:
            result[field] = val

    # clipsContent
    clips = node.get("clipsContent")
    if clips is not None:
        result["clipsContent"] = clips

    # visible
    visible = node.get("visible")
    if visible is False:
        result["visible"] = False

    # image reference (from plugin's image export)
    export_image_name = node.get("exportImageName")
    if export_image_name is not None:
        result["exportImageName"] = export_image_name

    children = node.get("children", [])

    # UIScrollBox: 计算滚动方向和每行/列最大数量
    if result["type"] == "UIScrollBox" and children:
        layout_mode = node.get("layoutMode")
        if layout_mode == "HORIZONTAL":
            result["scrollOrientation"] = "Vertical"
            child_w = children[0].get("width", children[0].get("w", 0))
            if child_w > 0:
                result["maxNumInline"] = int(node.get(w_key, 0) // child_w)
        elif layout_mode == "VERTICAL":
            result["scrollOrientation"] = "Horizontal"
            child_h = children[0].get("height", children[0].get("h", 0))
            if child_h > 0:
                result["maxNumInline"] = int(node.get(h_key, 0) // child_h)

    if children:
        result["children"] = [
            build_and_apply(child, mapping, counter)
            for child in children
        ]

    return result


# ═══════════════════════════════════════════════════════════════════════════
#  打印工具
# ═══════════════════════════════════════════════════════════════════════════

def print_tree(node, prefix="", is_last=True, is_root=True):
    """打印控件树摘要。"""
    name = node.get("name", "")
    umg = node.get("type", "")

    if is_root:
        print(f"{name}  [{umg}]")
        child_prefix = ""
    else:
        connector = "└─" if is_last else "├─"
        print(f"{prefix}{connector}{name}  [{umg}]")
        child_prefix = prefix + ("  " if is_last else "│ ")

    children = node.get("children", [])
    for i, child in enumerate(children):
        print_tree(child, child_prefix, i == len(children) - 1, False)


# ═══════════════════════════════════════════════════════════════════════════
#  文件处理
# ═══════════════════════════════════════════════════════════════════════════

def get_slim_root(slim_path):
    """读取 slim JSON 并返回根节点。"""
    with open(slim_path, "r", encoding="utf-8") as f:
        slim_raw = json.load(f)
    return slim_raw.get("frame", slim_raw)


def process_extract(slim_path, temp_dir, name):
    """阶段1: 从 slim 提取 _context.txt 到中间产物目录。"""
    root = get_slim_root(slim_path)

    lines = extract_context_lines(root, is_root=True)

    context_path = os.path.join(temp_dir, name + "_context.txt")
    os.makedirs(temp_dir, exist_ok=True)

    header = f"# {name}: {len(lines)} nodes\n# 参考: UMG_WIDGET_REFERENCE.md\n\n"
    with open(context_path, "w", encoding="utf-8") as f:
        f.write(header)
        for i, line in enumerate(lines, 1):
            f.write(f"{i}. {line}\n")

    ctx_size = os.path.getsize(context_path)
    return ctx_size, len(lines)


def process_apply(slim_path, out_dir, temp_dir, name, mapping_path=None):
    """阶段2: 从 slim 直接构建树并应用映射，输出 .figma2ui。"""
    root = get_slim_root(slim_path)
    final_path = os.path.join(out_dir, name + ".figma2ui")

    if mapping_path is None:
        mapping_path = os.path.join(temp_dir, name + "_mapping.json")

    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    result = build_and_apply(root, mapping)

    os.makedirs(out_dir, exist_ok=True)
    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return os.path.getsize(final_path)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI 入口
# ═══════════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python figma2ui.py <export_dir> [name] --extract")
        print("  python figma2ui.py <export_dir> [name] --apply [mapping.json]")
        sys.exit(1)

    args = sys.argv[1:]

    # 解析 --extract / --apply 标志
    mode = None
    mapping_arg = None
    clean_args = []
    i = 0
    while i < len(args):
        if args[i] == "--extract":
            mode = "extract"
        elif args[i] == "--apply":
            mode = "apply"
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                mapping_arg = args[i + 1]
                i += 1
        else:
            clean_args.append(args[i])
        i += 1

    if not clean_args:
        print("Error: need export directory")
        sys.exit(1)

    target = clean_args[0]
    file_name = clean_args[1] if len(clean_args) >= 2 else None

    if not os.path.isdir(target):
        print(f"Error: directory not found: {target}")
        sys.exit(1)

    slim_dir = os.path.join(target, "output", "slim")
    out_dir = os.path.join(target, "output")
    temp_dir = os.path.join(target, "output", "figma2ui_temp")

    if not os.path.isdir(slim_dir):
        print("Error: slim/ directory not found in: " + target)
        sys.exit(1)

    # 收集要处理的文件
    if file_name:
        slim_path = os.path.join(slim_dir, file_name + "_slim.json")
        if not os.path.exists(slim_path):
            print(f"Error: {slim_path} not found")
            sys.exit(1)
        files = [(file_name, slim_path)]
    else:
        slim_files = sorted(glob.glob(os.path.join(slim_dir, "*_slim.json")))
        if not slim_files:
            print("No _slim.json files found in: " + slim_dir)
            sys.exit(1)
        files = [
            (os.path.basename(p).replace("_slim.json", ""), p)
            for p in slim_files
        ]

    # ── extract 模式 ──
    if mode == "extract":
        # 清除旧的中间产物
        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)
        print(f"Extracting {len(files)} files -> {temp_dir}/\n")
        for name, slim_path in files:
            ctx_size, node_count = process_extract(slim_path, temp_dir, name)
            print(f"  [OK] {name}: {node_count} nodes, context={ctx_size:,}B")
        print("\nDone. AI 可读取 _context.txt 文件进行类型映射。")
        return

    # ── apply 模式 ──
    if mode == "apply":
        print(f"Applying mappings for {len(files)} files -> {out_dir}/\n")
        for name, slim_path in files:
            mp = mapping_arg if mapping_arg and len(files) == 1 else None
            size = process_apply(slim_path, out_dir, temp_dir, name, mapping_path=mp)
            print(f"  [OK] {name} -> {name}.figma2ui ({size:,} bytes)")
        print("\nDone.")
        return

    # ── 无模式: 显示帮助 ──
    print("Please specify a mode:")
    print("  --extract   提取上下文（供 AI 阅读）")
    print("  --apply     应用 AI 的类型映射")
    sys.exit(1)


if __name__ == "__main__":
    main()
