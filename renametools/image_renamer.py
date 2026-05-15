import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk
import threading
from typing import List, Tuple, Optional


class ImageRenamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片重命名工具")
        # 颜色配置
        self.colors = {
            "primary": "#6B46C1",      # 主紫色
            "primary_light": "#9F7AEA", # 亮紫色
            "primary_deep": "#44337A", # 深紫色
            "bg": "#F7FAFC",           # 极简浅灰背景
            "white": "#FFFFFF",
            "text": "#2D3748",         # 深灰文字
            "accent": "#ED64A6"        # 粉紫点缀
        }
        
        # 数据存储
        self.selected_folder = ""
        self.selected_images = []
        self.preview_images = {}
        
        # 设置样式
        self.setup_styles()
        
        # 创建界面
        self.create_widgets()
        
    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 自定义按钮样式
        self.style.configure("Primary.TButton", 
                            foreground="white", 
                            background=self.colors["primary"],
                            padding=(15, 5),
                            font=('Microsoft YaHei', 10, 'bold'))
        self.style.map("Primary.TButton",
                      background=[('active', self.colors["primary_light"]), 
                                 ('pressed', self.colors["primary_deep"])])
        
        # 标签样式
        self.style.configure("Title.TLabel", 
                            foreground=self.colors["primary_deep"], 
                            font=('Microsoft YaHei', 16, 'bold'),
                            background=self.colors["bg"])
                            
        self.style.configure("TFrame", background=self.colors["bg"])
        self.style.configure("TLabelframe", background=self.colors["bg"], relief="flat")
        self.style.configure("TLabelframe.Label", 
                            foreground=self.colors["primary"], 
                            background=self.colors["bg"],
                            font=('Microsoft YaHei', 10, 'bold'))
        
        self.root.configure(bg=self.colors["bg"])
        
    def create_widgets(self):
        # 自定义顶部标题栏
        header_frame = tk.Frame(self.root, bg=self.colors["primary"], height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="✨ 图片重命名工具", 
                 fg="white", bg=self.colors["primary"],
                 font=('Microsoft YaHei', 14, 'bold')).pack(side=tk.LEFT, padx=20)

        # 主要内容区
        main_container = ttk.Frame(self.root, padding="20")
        main_container.pack(fill=tk.BOTH, expand=True)

        # 第一行：路径选择
        folder_frame = ttk.Frame(main_container)
        folder_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.folder_var = tk.StringVar(value="还没有选择文件夹...")
        path_label = tk.Label(folder_frame, textvariable=self.folder_var, 
                             fg=self.colors["text"], bg="#EDF2F7",
                             anchor="w", padx=10, font=('Microsoft YaHei', 9))
        path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        
        ttk.Button(folder_frame, text="选择文件夹", style="Primary.TButton",
                  command=self.select_folder).pack(side=tk.LEFT, padx=(10, 0))
        
        # 第二行：重命名设置
        rename_frame = ttk.LabelFrame(main_container, text=" 配置选项 ", padding="15")
        rename_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 这里的网格布局调整
        controls_frame = ttk.Frame(rename_frame)
        controls_frame.pack(fill=tk.X)

        ttk.Label(controls_frame, text="前缀 A:").pack(side=tk.LEFT)
        self.prefix_a_var = tk.StringVar(value="")
        prefix_a_combo = ttk.Combobox(controls_frame, textvariable=self.prefix_a_var, 
                                      values=["", "Bg", "Icon", "Img", "Btn", "Bar"],
                                      state="readonly", width=10)
        prefix_a_combo.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(controls_frame, text="中间 B:").pack(side=tk.LEFT)
        self.prefix_b_var = tk.StringVar(value="")
        prefix_b_entry = ttk.Entry(controls_frame, textvariable=self.prefix_b_var, width=15)
        prefix_b_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(controls_frame, text="立即重命名", style="Primary.TButton",
                  command=self.execute_rename).pack(side=tk.RIGHT)
        
        # 底部：分栏
        content_paned = ttk.Panedwindow(main_container, orient=tk.HORIZONTAL)
        content_paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：列表
        list_frame = ttk.LabelFrame(content_paned, text=" 选中的文件 ", padding="5")
        content_paned.add(list_frame, weight=1)
        
        self.image_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, 
                                        bg=self.colors["white"], fg=self.colors["text"],
                                        borderwidth=0, highlightthickness=0,
                                        font=('Microsoft YaHei', 9))
        self.image_listbox.pack(fill=tk.BOTH, expand=True)
        
        # 右侧：预览
        preview_frame = ttk.LabelFrame(content_paned, text=" 效果预览 ", padding="5")
        content_paned.add(preview_frame, weight=2)
        
        self.preview_label = tk.Label(preview_frame, text="准备就绪", 
                                     bg=self.colors["white"], fg="#A0AEC0")
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        
        # 绑定点击
        self.image_listbox.bind('<<ListboxSelect>>', self.on_image_select)
        
    def select_folder(self):
        """选择文件夹"""
        folder = filedialog.askdirectory(title="选择包含图片的文件夹")
        if folder:
            self.selected_folder = folder
            self.folder_var.set(folder)
            self.load_images_from_folder()
    
    def load_images_from_folder(self):
        """从文件夹加载图片"""
        if not self.selected_folder:
            return
        
        folder_path = Path(self.selected_folder)
        image_extensions = {'.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG'}
        
        # 获取所有图片文件
        image_files = [f for f in folder_path.iterdir() 
                      if f.is_file() and f.suffix in image_extensions]
        
        if not image_files:
            messagebox.showinfo("提示", "该文件夹中没有找到图片文件（png/jpg格式）")
            return
        
        # 打开图片选择对话框
        self.select_images_dialog(image_files)
    
    def select_images_dialog(self, image_files: List[Path]):
        """打开图片选择对话框"""
        # 创建新窗口用于选择图片
        select_window = tk.Toplevel(self.root)
        select_window.title("选择图片 - 缩略图视图")
        select_window.geometry("1000x800")
        
        # 记录选中的路径
        self.dialog_selected_paths = set()
        # 记录显示用的图片对象，防止垃圾回收
        self.dialog_photos = {}
        
        # 顶部按钮
        button_frame = tk.Frame(select_window, bg=self.colors["primary_deep"])
        button_frame.pack(fill=tk.X, padx=0, pady=0)
        # 内部容器用于模拟 padding
        button_inner = tk.Frame(button_frame, bg=self.colors["primary_deep"])
        button_inner.pack(fill=tk.X, padx=10, pady=10)
        
        style = ttk.Style()
        style.configure("Dialog.TButton", font=('Microsoft YaHei', 9))

        ttk.Button(button_inner, text="全选", style="Dialog.TButton",
                  command=lambda: self.toggle_all_thumbnails(True, thumb_container, image_files)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_inner, text="取消全选", style="Dialog.TButton",
                  command=lambda: self.toggle_all_thumbnails(False, thumb_container, image_files)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_inner, text="确认添加", style="Primary.TButton",
                  command=lambda: self.confirm_thumbnail_selection(select_window)).pack(side=tk.LEFT, padx=20)
        
        self.select_status_label = tk.Label(button_inner, text="已选择: 0 张", 
                                           fg="white", bg=self.colors["primary_deep"])
        self.select_status_label.pack(side=tk.RIGHT, padx=10)
        
        # 使用 Canvas
        view_frame = tk.Frame(select_window, bg=self.colors["bg"])
        view_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        canvas = tk.Canvas(view_frame, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(view_frame, orient="vertical", command=canvas.yview)
        thumb_container = tk.Frame(canvas, bg=self.colors["bg"])
        
        thumb_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=thumb_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 鼠标滚轮支持
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # 加载缩略图网格
        self.load_thumbnail_grid(thumb_container, sorted(image_files, key=lambda x: x.name))

    def load_thumbnail_grid(self, container, image_files: List[Path]):
        """加载缩略图网格"""
        columns = 5 # 每行5个
        
        for i, img_path in enumerate(image_files):
            row = i // columns
            col = i % columns
            
            # 外部框架
            item_frame = tk.Frame(container, bd=2, relief=tk.FLAT, bg="white", padx=5, pady=5)
            item_frame.grid(row=row, column=col, padx=5, pady=5)
            
            # 加载并缩样
            try:
                img = Image.open(img_path)
                img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.dialog_photos[img_path] = photo # 保持引用
                
                label = tk.Label(item_frame, image=photo, bg="white")
                label.pack()
                
                name_label = tk.Label(item_frame, text=img_path.name, wraplength=140, 
                                     font=("TkDefaultFont", 8), bg="white")
                name_label.pack()
                
                # 绑定点击事件
                for widget in [item_frame, label, name_label]:
                    widget.bind("<Button-1>", lambda e, p=img_path, f=item_frame: self.toggle_selection(p, f))
            except Exception as e:
                error_label = tk.Label(item_frame, text=f"加载失败\n{img_path.name}", wraplength=140, fg="red", bg="white")
                error_label.pack()

    def toggle_selection(self, img_path, frame):
        """切换选中状态"""
        if img_path in self.dialog_selected_paths:
            self.dialog_selected_paths.remove(img_path)
            frame.config(bg=self.colors["bg"], relief=tk.FLAT)
            for widget in frame.winfo_children():
                widget.config(bg=self.colors["bg"], fg=self.colors["text"])
        else:
            self.dialog_selected_paths.add(img_path)
            frame.config(bg=self.colors["primary"], relief=tk.SOLID)
            for widget in frame.winfo_children():
                widget.config(bg=self.colors["primary"], fg="white")
        
        self.select_status_label.config(text=f"已选择: {len(self.dialog_selected_paths)} 张")

    def toggle_all_thumbnails(self, select_all, container, image_files):
        """全选或取消全选缩略图"""
        if select_all:
            for img_path in image_files:
                self.dialog_selected_paths.add(img_path)
        else:
            self.dialog_selected_paths.clear()
            
        # 更新UI
        bg_main = self.colors["primary"] if select_all else self.colors["bg"]
        fg_main = "white" if select_all else self.colors["text"]
        relief_val = tk.SOLID if select_all else tk.FLAT
        
        for child in container.winfo_children():
            child.config(bg=bg_main, relief=relief_val)
            for widget in child.winfo_children():
                widget.config(bg=bg_main, fg=fg_main)
                
        self.select_status_label.config(text=f"已选择: {len(self.dialog_selected_paths)} 张")

    def confirm_thumbnail_selection(self, window):
        """确认缩略图选择"""
        if not self.dialog_selected_paths:
            messagebox.showwarning("警告", "请至少选择一张图片")
            return
        
        self.selected_images = []
        for img_path in sorted(list(self.dialog_selected_paths)):
            self.selected_images.append((img_path, img_path.name))
        
        self.update_image_list()
        window.destroy()
        self.load_previews_async()

    def select_all_images(self, listbox):
        """全选列表中的图片"""
        listbox.selection_set(0, tk.END)
    
    def confirm_selection(self, listbox, window, image_files):
        """确认选择的图片"""
        selected_indices = listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("警告", "请至少选择一张图片")
            return
        
        # 获取选中的图片路径
        self.selected_images = []
        folder_path = Path(self.selected_folder)
        
        for idx in selected_indices:
            filename = listbox.get(idx)
            img_path = folder_path / filename
            self.selected_images.append((img_path, filename))
        
        # 更新列表显示
        self.update_image_list()
        
        # 关闭选择窗口
        window.destroy()
        
        # 异步加载预览
        self.load_previews_async()
    
    def update_image_list(self):
        """更新图片列表显示"""
        self.image_listbox.delete(0, tk.END)
        for img_path, filename in self.selected_images:
            self.image_listbox.insert(tk.END, filename)
    
    def load_previews_async(self):
        """异步加载图片预览"""
        def load_previews():
            for img_path, filename in self.selected_images:
                try:
                    # 加载图片并调整大小
                    img = Image.open(img_path)
                    img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    # 在主线程中更新UI
                    self.root.after(0, self.update_preview_cache, filename, photo)
                except Exception as e:
                    print(f"加载预览失败 {filename}: {e}")
        
        # 在后台线程中加载
        thread = threading.Thread(target=load_previews, daemon=True)
        thread.start()
    
    def update_preview_cache(self, filename, photo):
        """更新预览缓存"""
        self.preview_images[filename] = photo
    
    def on_image_select(self, event):
        """当选择列表中的图片时显示预览"""
        selection = self.image_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        if idx < len(self.selected_images):
            _, filename = self.selected_images[idx]
            
            # 显示预览
            if filename in self.preview_images:
                self.preview_label.config(image=self.preview_images[filename], text="")
            else:
                self.preview_label.config(image="", text="加载中...")
                # 如果还没有加载，立即加载
                self.load_single_preview(idx)
    
    def load_single_preview(self, idx):
        """加载单个图片预览"""
        def load():
            img_path, filename = self.selected_images[idx]
            try:
                img = Image.open(img_path)
                img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.root.after(0, lambda: self.preview_label.config(image=photo, text=""))
                self.preview_images[filename] = photo
            except Exception as e:
                self.root.after(0, lambda: self.preview_label.config(
                    image="", text=f"加载失败: {e}"))
        
        thread = threading.Thread(target=load, daemon=True)
        thread.start()
    
    def execute_rename(self):
        """执行重命名操作"""
        if not self.selected_images:
            messagebox.showwarning("警告", "请先选择要重命名的图片")
            return
        
        # 获取重命名参数
        prefix_a = self.prefix_a_var.get()
        prefix_b = self.prefix_b_var.get()
        
        # 确定数字格式（根据数量）
        num_format = "01" if len(self.selected_images) <= 100 else "001"
        
        # 检查已存在的文件名
        folder_path = Path(self.selected_folder)
        existing_numbers = self.get_existing_numbers(folder_path, prefix_a, prefix_b, num_format)
        
        # 生成新文件名
        rename_plan = []
        start_num = max(existing_numbers) + 1 if existing_numbers else 1
        
        for i, (img_path, old_filename) in enumerate(self.selected_images):
            num_str = str(start_num + i).zfill(len(num_format))
            
            # 构建新文件名
            parts = []
            if prefix_a:
                parts.append(prefix_a)
            if prefix_b:
                parts.append(prefix_b)
            parts.append(num_str)
            
            # 如果只有一个部分（只有数字），直接使用；否则用下划线连接
            if len(parts) == 1:
                new_name = parts[0] + img_path.suffix
            else:
                new_name = "_".join(parts) + img_path.suffix
            new_path = folder_path / new_name
            
            rename_plan.append((img_path, new_path, old_filename, new_name))
        
        # 确认重命名
        confirm_msg = f"将重命名 {len(rename_plan)} 张图片：\n\n"
        for old_path, new_path, old_name, new_name in rename_plan[:5]:
            confirm_msg += f"{old_name} -> {new_name}\n"
        if len(rename_plan) > 5:
            confirm_msg += f"... 还有 {len(rename_plan) - 5} 张图片\n"
        
        if not messagebox.askyesno("确认", confirm_msg + "\n确定要执行重命名吗？"):
            return
        
        # 执行重命名
        success_count = 0
        failed_files = []
        
        for old_path, new_path, old_name, new_name in rename_plan:
            try:
                # 检查新文件名是否已存在
                if new_path.exists() and new_path != old_path:
                    failed_files.append(f"{old_name}: 目标文件已存在")
                    continue
                
                old_path.rename(new_path)
                success_count += 1
            except Exception as e:
                failed_files.append(f"{old_name}: {str(e)}")
        
        # 显示结果
        result_msg = f"重命名完成！\n成功: {success_count} 张"
        if failed_files:
            result_msg += f"\n失败: {len(failed_files)} 张"
            result_msg += "\n\n失败详情:\n" + "\n".join(failed_files[:10])
            if len(failed_files) > 10:
                result_msg += f"\n... 还有 {len(failed_files) - 10} 个失败项"
        
        messagebox.showinfo("结果", result_msg)
        
        # 更新列表
        if success_count > 0:
            self.selected_images = []
            self.preview_images = {}
            self.image_listbox.delete(0, tk.END)
            self.preview_label.config(image="", text="请选择图片查看预览")
    
    def get_existing_numbers(self, folder_path: Path, prefix_a: str, 
                            prefix_b: str, num_format: str) -> List[int]:
        """获取已存在的文件编号"""
        existing_numbers = []
        
        # 构建文件名模式
        parts = []
        if prefix_a:
            parts.append(prefix_a)
        if prefix_b:
            parts.append(prefix_b)
        
        prefix_pattern = "_".join(parts) if parts else ""
        
        # 遍历文件夹中的所有文件
        for file_path in folder_path.iterdir():
            if not file_path.is_file():
                continue
            
            filename = file_path.stem  # 不含扩展名的文件名
            
            # 检查是否匹配模式
            if prefix_pattern:
                # 有前缀：必须是 prefix_pattern_数字 格式
                expected_prefix = prefix_pattern + "_"
                if not filename.startswith(expected_prefix):
                    continue
                # 提取数字部分
                num_part = filename[len(expected_prefix):]
                # 数字部分后面不应该有其他内容
                if num_part and num_part.isdigit():
                    try:
                        num = int(num_part)
                        existing_numbers.append(num)
                    except ValueError:
                        continue
            else:
                # 没有前缀：文件名应该就是纯数字
                if filename.isdigit():
                    try:
                        num = int(filename)
                        existing_numbers.append(num)
                    except ValueError:
                        continue
        
        return existing_numbers


def main():
    root = tk.Tk()
    app = ImageRenamerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
