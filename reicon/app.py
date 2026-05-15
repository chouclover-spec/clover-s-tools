"""
ReIcon - Windows 文件夹图标自定义工具
使用 PNG 图片自定义 Windows 文件夹图标
"""

import os
import sys
import shutil
import subprocess
import ctypes
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

try:
    import win32com.client
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# ── 颜色主题 ──────────────────────────────────────────────
BG       = "#1e1e2e"
SURFACE  = "#2a2a3e"
SURFACE2 = "#313145"
ACCENT   = "#7c6af7"
ACCENT_H = "#9d8fff"
TEXT     = "#cdd6f4"
TEXT_SUB = "#a6adc8"
SUCCESS  = "#a6e3a1"
WARNING  = "#f38ba8"
BORDER   = "#45475a"


def resource_path(relative):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def png_to_ico(png_path: str, ico_path: str):
    """将 PNG 转换为多尺寸 ICO 文件"""
    img = Image.open(png_path).convert("RGBA")
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    icons = []
    for size in sizes:
        resized = img.resize(size, Image.LANCZOS)
        icons.append(resized)
    icons[0].save(ico_path, format="ICO", sizes=sizes, append_images=icons[1:])


def apply_folder_icon(folder_path: str, ico_path: str) -> bool:
    """通过 desktop.ini 将 ICO 应用到文件夹"""
    try:
        folder = Path(folder_path)
        dest_ico = folder / "folder_icon.ico"
        ini_path = folder / "desktop.ini"

        # 若文件已存在且带有系统/隐藏属性，先清除，否则无法覆盖
        for p in (dest_ico, ini_path):
            if p.exists():
                subprocess.run(["attrib", "-h", "-s", "-r", str(p)], shell=True)

        shutil.copy2(ico_path, dest_ico)

        ini_content = (
            "[.ShellClassInfo]\r\n"
            "IconResource=folder_icon.ico,0\r\n"
            "[ViewState]\r\n"
            "Mode=\r\n"
            "Vid=\r\n"
            "FolderType=Generic\r\n"
        )
        ini_path.write_text(ini_content, encoding="utf-8")

        subprocess.run(["attrib", "+h", "+s", str(dest_ico)], shell=True)
        subprocess.run(["attrib", "+h", "+s", str(ini_path)], shell=True)
        subprocess.run(["attrib", "+r", str(folder)], shell=True)

        ctypes.windll.shell32.SHChangeNotify(0x8000000, 0, None, None)
        return True
    except Exception as e:
        messagebox.showerror("错误", f"应用图标失败：\n{e}")
        return False


def restore_folder_icon(folder_path: str) -> bool:
    """恢复文件夹默认图标"""
    try:
        folder = Path(folder_path)
        ini_path = folder / "desktop.ini"
        ico_path = folder / "folder_icon.ico"

        for p in [ini_path, ico_path]:
            if p.exists():
                subprocess.run(["attrib", "-h", "-s", str(p)], shell=True)
                p.unlink()

        subprocess.run(["attrib", "-r", str(folder)], shell=True)
        ctypes.windll.shell32.SHChangeNotify(0x8000000, 0, None, None)
        return True
    except Exception as e:
        messagebox.showerror("错误", f"恢复图标失败：\n{e}")
        return False


def apply_shortcut_icon(lnk_path: str, ico_path: str) -> bool:
    """将 ICO 应用到 Windows 快捷方式 (.lnk)"""
    if not HAS_WIN32:
        messagebox.showerror("缺少依赖", "快捷方式支持需要 pywin32 库。\n请运行：pip install pywin32")
        return False
    try:
        dest_ico = Path(lnk_path).parent / (Path(lnk_path).stem + ".ico")
        shutil.copy2(ico_path, dest_ico)
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(lnk_path)
        shortcut.IconLocation = f"{dest_ico},0"
        shortcut.Save()
        ctypes.windll.shell32.SHChangeNotify(0x8000000, 0, None, None)
        return True
    except Exception as e:
        messagebox.showerror("错误", f"应用快捷方式图标失败：\n{e}")
        return False


def restore_shortcut_icon(lnk_path: str) -> bool:
    """恢复快捷方式默认图标"""
    if not HAS_WIN32:
        messagebox.showerror("缺少依赖", "快捷方式支持需要 pywin32 库。\n请运行：pip install pywin32")
        return False
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(lnk_path)
        shortcut.IconLocation = ""
        shortcut.Save()
        dest_ico = Path(lnk_path).parent / (Path(lnk_path).stem + ".ico")
        if dest_ico.exists():
            dest_ico.unlink()
        ctypes.windll.shell32.SHChangeNotify(0x8000000, 0, None, None)
        return True
    except Exception as e:
        messagebox.showerror("错误", f"恢复快捷方式图标失败：\n{e}")
        return False


# ── 主窗口 ────────────────────────────────────────────────
class ReIconApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ReIcon · 图标自定义")
        self.root.geometry("860x580")
        self.root.minsize(720, 500)
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        self._png_path: str | None = None
        self._ico_path: str | None = None
        self._targets: dict[str, str] = {}  # path -> "folder" | "shortcut"
        self._preview_img = None  # 防止 GC

        self._setup_styles()
        self._build_ui()

    # ── 样式 ─────────────────────────────────────────────
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Sub.TLabel", background=BG, foreground=TEXT_SUB, font=("Segoe UI", 9))
        style.configure("Card.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff",
                        font=("Segoe UI", 10, "bold"), borderwidth=0, padding=(14, 7))
        style.map("Accent.TButton",
                  background=[("active", ACCENT_H), ("disabled", BORDER)],
                  foreground=[("disabled", TEXT_SUB)])
        style.configure("Ghost.TButton", background=SURFACE2, foreground=TEXT,
                        font=("Segoe UI", 10), borderwidth=0, padding=(10, 6))
        style.map("Ghost.TButton", background=[("active", BORDER)])
        style.configure("Danger.TButton", background="#3a2030", foreground=WARNING,
                        font=("Segoe UI", 10), borderwidth=0, padding=(10, 6))
        style.map("Danger.TButton", background=[("active", "#502040")])
        style.configure("Treeview", background=SURFACE, foreground=TEXT,
                        fieldbackground=SURFACE, rowheight=30,
                        font=("Segoe UI", 9), borderwidth=0)
        style.configure("Treeview.Heading", background=SURFACE2, foreground=TEXT_SUB,
                        font=("Segoe UI", 9, "bold"), relief="flat")
        style.map("Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#ffffff")])
        style.configure("Vertical.TScrollbar", background=SURFACE2,
                        troughcolor=SURFACE, borderwidth=0, arrowsize=12)

    # ── UI 构建 ───────────────────────────────────────────
    def _build_ui(self):
        # 顶栏
        header = tk.Frame(self.root, bg=SURFACE, height=54)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        tk.Label(header, text="🎨  ReIcon", bg=SURFACE, fg=TEXT,
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=20)
        tk.Label(header, text="Windows 图标自定义工具 · 文件夹 & 快捷方式", bg=SURFACE, fg=TEXT_SUB,
                 font=("Segoe UI", 9)).pack(side="left")

        # 主体
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=14)
        body.columnconfigure(0, weight=0, minsize=220)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_left(body)
        self._build_right(body)

    def _build_left(self, parent):
        left = tk.Frame(parent, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.rowconfigure(2, weight=1)

        # 标题
        tk.Label(left, text="PNG 图片", bg=BG, fg=TEXT_SUB,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))

        # 拖拽 / 点击区域
        drop_outer = tk.Frame(left, bg=BORDER, padx=1, pady=1)
        drop_outer.grid(row=1, column=0, sticky="ew")

        self._drop_frame = tk.Frame(drop_outer, bg=SURFACE, cursor="hand2")
        self._drop_frame.pack(fill="both")

        self._drop_label = tk.Label(
            self._drop_frame,
            text="🖼\n\n拖拽 PNG 到此处\n或点击选择",
            bg=SURFACE, fg=TEXT_SUB,
            font=("Segoe UI", 10),
            pady=18, cursor="hand2"
        )
        self._drop_label.pack(fill="x")

        for w in (self._drop_frame, self._drop_label):
            w.bind("<Button-1>", lambda e: self._pick_png())
            w.bind("<Enter>", lambda e: self._drop_frame.config(bg=SURFACE2) or
                   self._drop_label.config(bg=SURFACE2))
            w.bind("<Leave>", lambda e: self._drop_frame.config(bg=SURFACE) or
                   self._drop_label.config(bg=SURFACE))

        # 预览
        preview_outer = tk.Frame(left, bg=BORDER, padx=1, pady=1)
        preview_outer.grid(row=2, column=0, sticky="nsew", pady=(8, 0))

        preview_inner = tk.Frame(preview_outer, bg=SURFACE)
        preview_inner.pack(fill="both", expand=True)

        self._preview_label = tk.Label(preview_inner, bg=SURFACE,
                                       text="—", fg=BORDER,
                                       font=("Segoe UI", 24))
        self._preview_label.pack(expand=True, fill="both", padx=8, pady=8)

        # 文件名
        self._img_name_var = tk.StringVar(value="未选择图片")
        tk.Label(left, textvariable=self._img_name_var, bg=BG, fg=TEXT_SUB,
                 font=("Segoe UI", 8), wraplength=210).grid(row=3, column=0,
                                                             sticky="w", pady=(5, 0))

        # 选图按钮
        ttk.Button(left, text="📂  选择 PNG 图片",
                   style="Ghost.TButton",
                   command=self._pick_png).grid(row=4, column=0, sticky="ew", pady=(8, 0))

        # 注册拖拽
        if HAS_DND:
            for w in (self._drop_frame, self._drop_label):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self._on_drop)

    def _build_right(self, parent):
        right = tk.Frame(parent, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        # 标题
        tk.Label(right, text="目标列表", bg=BG, fg=TEXT_SUB,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))

        # Treeview 容器
        tree_outer = tk.Frame(right, bg=BORDER, padx=1, pady=1)
        tree_outer.grid(row=1, column=0, sticky="nsew")
        tree_outer.rowconfigure(0, weight=1)
        tree_outer.columnconfigure(0, weight=1)

        self._tree = ttk.Treeview(tree_outer, columns=("type", "path", "status"),
                                  show="headings", selectmode="extended")
        self._tree.heading("type", text="类型")
        self._tree.heading("path", text="路径")
        self._tree.heading("status", text="状态")
        self._tree.column("type", width=80, stretch=False, anchor="center")
        self._tree.column("path", width=340, stretch=True)
        self._tree.column("status", width=90, stretch=False, anchor="center")
        self._tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(tree_outer, orient="vertical", command=self._tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=vsb.set)

        # 操作按钮行
        btn_row = tk.Frame(right, bg=BG)
        btn_row.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        ttk.Button(btn_row, text="➕  添加文件夹",
                   style="Ghost.TButton",
                   command=self._add_folder).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="🔗  添加快捷方式",
                   style="Ghost.TButton",
                   command=self._add_shortcut).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="🗑  移除选中",
                   style="Ghost.TButton",
                   command=self._remove_selected).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="🔄  恢复默认图标",
                   style="Danger.TButton",
                   command=self._restore_selected).pack(side="left")

        # 底部状态 + 应用按钮
        bottom = tk.Frame(right, bg=BG)
        bottom.grid(row=3, column=0, sticky="ew", pady=(14, 0))

        self._status_var = tk.StringVar(value="就绪")
        tk.Label(bottom, textvariable=self._status_var, bg=BG, fg=TEXT_SUB,
                 font=("Segoe UI", 9)).pack(side="left")

        ttk.Button(bottom, text="✅  应用图标到全部目标",
                   style="Accent.TButton",
                   command=self._apply_all).pack(side="right")

        # 注册 Treeview 拖放（文件夹/快捷方式）
        if HAS_DND:
            self._tree.drop_target_register(DND_FILES)
            self._tree.dnd_bind("<<Drop>>", self._on_tree_drop)

    # ── 事件 ─────────────────────────────────────────────
    def _on_drop(self, event):
        raw = event.data.strip()
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        for p in raw.split():
            p = p.strip()
            if p.lower().endswith(".png") and os.path.isfile(p):
                self._load_png(p)
                break

    def _on_tree_drop(self, event):
        raw = event.data.strip()
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        for p in raw.split():
            p = p.strip()
            if not p or p in self._targets:
                continue
            if os.path.isdir(p):
                self._targets[p] = "folder"
                self._tree.insert("", "end", iid=p, values=("📁 文件夹", p, "待处理"))
            elif p.lower().endswith(".lnk") and os.path.isfile(p):
                if not HAS_WIN32:
                    messagebox.showerror("缺少依赖", "拖入快捷方式需要 pywin32 库。\n请运行：pip install pywin32")
                    continue
                self._targets[p] = "shortcut"
                self._tree.insert("", "end", iid=p, values=("🔗 快捷方式", p, "待处理"))

    def _pick_png(self):
        path = filedialog.askopenfilename(
            title="选择 PNG 图片",
            filetypes=[("PNG 图片", "*.png"), ("所有文件", "*.*")]
        )
        if path:
            self._load_png(path)

    def _load_png(self, path: str):
        try:
            img = Image.open(path).convert("RGBA")
            self._png_path = path
            self._img_name_var.set(os.path.basename(path))
            self._drop_label.config(text="✅  图片已加载")

            # 预览
            preview = img.copy()
            preview.thumbnail((200, 200), Image.LANCZOS)
            self._preview_img = ImageTk.PhotoImage(preview)
            self._preview_label.config(image=self._preview_img, text="")

            # 预转换 ICO
            tmp_dir = Path(os.environ.get("TEMP", ".")) / "reicon"
            tmp_dir.mkdir(exist_ok=True)
            self._ico_path = str(tmp_dir / "preview_icon.ico")
            png_to_ico(path, self._ico_path)
            self._status_var.set(f"已加载：{os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("错误", f"加载图片失败：\n{e}")

    def _add_folder(self):
        path = filedialog.askdirectory(title="选择文件夹")
        if path and path not in self._targets:
            self._targets[path] = "folder"
            self._tree.insert("", "end", iid=path, values=("📁 文件夹", path, "待处理"))

    def _add_shortcut(self):
        if not HAS_WIN32:
            messagebox.showerror("缺少依赖", "快捷方式支持需要 pywin32 库。\n请运行：pip install pywin32")
            return
        path = filedialog.askopenfilename(
            title="选择 Windows 快捷方式",
            filetypes=[("Windows 快捷方式", "*.lnk"), ("所有文件", "*.*")]
        )
        if path and path not in self._targets:
            self._targets[path] = "shortcut"
            self._tree.insert("", "end", iid=path, values=("🔗 快捷方式", path, "待处理"))

    def _remove_selected(self):
        for item in self._tree.selection():
            self._targets.pop(item, None)
            self._tree.delete(item)

    def _restore_selected(self):
        selected = self._tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先在列表中选中要恢复的项目")
            return
        ok = 0
        for item in selected:
            target_type = self._targets.get(item)
            if target_type == "folder":
                success = restore_folder_icon(item)
            elif target_type == "shortcut":
                success = restore_shortcut_icon(item)
            else:
                continue
            if success:
                self._tree.set(item, "status", "✅ 已恢复")
                ok += 1
        self._status_var.set(f"已恢复 {ok} 个项目的默认图标")

    def _apply_all(self):
        if not self._png_path:
            messagebox.showwarning("提示", "请先选择一张 PNG 图片")
            return
        if not self._targets:
            messagebox.showwarning("提示", "请先添加目标文件夹或快捷方式")
            return

        tmp_dir = Path(os.environ.get("TEMP", ".")) / "reicon"
        tmp_dir.mkdir(exist_ok=True)
        ico = str(tmp_dir / "apply_icon.ico")
        png_to_ico(self._png_path, ico)

        ok = 0
        for path, target_type in self._targets.items():
            try:
                if target_type == "folder":
                    success = apply_folder_icon(path, ico)
                else:
                    success = apply_shortcut_icon(path, ico)
                if success:
                    self._tree.set(path, "status", "✅ 完成")
                    ok += 1
                else:
                    self._tree.set(path, "status", "❌ 失败")
            except Exception as e:
                self._tree.set(path, "status", "❌ 失败")
                messagebox.showerror("错误", f"{path}\n{e}")

        total = len(self._targets)
        self._status_var.set(f"完成！成功 {ok} / {total} 个目标")

        # 导出 ICO 到 assets/
        export_msg = ""
        if ok > 0:
            try:
                assets_dir = Path(resource_path("assets"))
                assets_dir.mkdir(exist_ok=True)
                stem = Path(self._png_path).stem
                export_path = assets_dir / f"{stem}.ico"
                shutil.copy2(ico, str(export_path))
                export_msg = f"\n\n已导出 ICO：assets/{stem}.ico"
            except Exception as e:
                export_msg = f"\n\n导出 ICO 失败：{e}"

        if ok == total and ok > 0:
            messagebox.showinfo(
                "完成 🎉",
                f"已成功为 {ok} 个目标应用自定义图标！\n\n"
                f"若图标未立即刷新，请按 F5 刷新资源管理器。{export_msg}"
            )


# ── 入口 ──────────────────────────────────────────────────
def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    try:
        root.iconbitmap(resource_path("icon.ico"))
    except Exception:
        pass

    ReIconApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
