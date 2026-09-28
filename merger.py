import math
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw


class SpriteMerger:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.images = []
        self.preview_img = None
        self.scale = 1.0

        self._build_ui()

    def _build_ui(self):
        top = tk.Frame(self.parent)
        top.pack(pady=10)

        tk.Button(top, text="选择序列图片", command=self.load_images).pack(side=tk.LEFT, padx=5)
        self.count_label = tk.Label(top, text="未选择", fg="gray")
        self.count_label.pack(side=tk.LEFT, padx=10)

        params = tk.LabelFrame(self.parent, text="拼接参数")
        params.pack(pady=10, padx=10, fill="x")

        tk.Label(params, text="排列方式").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        self.mode_var = tk.StringVar(value="auto")
        tk.Radiobutton(params, text="自动计算", variable=self.mode_var,
                       value="auto", command=self.update_preview).grid(row=0, column=1, sticky="w")
        tk.Radiobutton(params, text="手动指定列数", variable=self.mode_var,
                       value="manual", command=self.update_preview).grid(row=0, column=2, sticky="w")

        tk.Label(params, text="每行帧数").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        self.cols_var = tk.StringVar(value="4")
        self.cols_entry = tk.Entry(params, width=10, textvariable=self.cols_var)
        self.cols_entry.grid(row=1, column=1, sticky="w", padx=5, pady=3)
        self.cols_var.trace_add("write", lambda *args: self.update_preview())

        tk.Label(params, text="帧间距(像素)").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        self.gap_var = tk.StringVar(value="0")
        gap_entry = tk.Entry(params, width=10, textvariable=self.gap_var)
        gap_entry.grid(row=2, column=1, sticky="w", padx=5, pady=3)
        self.gap_var.trace_add("write", lambda *args: self.update_preview())

        tk.Label(params, text="背景色(R,G,B,A)").grid(row=3, column=0, sticky="e", padx=5, pady=3)
        self.bg_var = tk.StringVar(value="0,0,0,0")
        bg_entry = tk.Entry(params, width=15, textvariable=self.bg_var)
        bg_entry.grid(row=3, column=1, sticky="w", padx=5, pady=3)
        self.bg_var.trace_add("write", lambda *args: self.update_preview())

        btn_frame = tk.Frame(params)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=8)

        tk.Button(btn_frame, text="拼接并保存", command=self.merge_and_save).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="→ 导入到切割界面", command=self.send_to_cutter).pack(side=tk.LEFT, padx=5)

        preview_frame = tk.LabelFrame(self.parent, text="拼接预览")
        preview_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.preview_canvas = tk.Canvas(preview_frame, bg="#1e1e1e")
        self.preview_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        self.preview_canvas.bind("<Configure>", self.on_resize)

        self.status = tk.Label(self.parent, text="请先选择序列图片", fg="gray")
        self.status.pack(pady=5)

    def on_resize(self, event):
        self.update_preview()

    def _get_int(self, var, name, default=None):
        try:
            return int(var.get())
        except ValueError:
            if default is not None:
                return default
            messagebox.showerror("参数错误", f"{name} 必须是整数")
            return None

    def load_images(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if not paths:
            return

        paths = sorted(paths)

        self.images = []
        for p in paths:
            try:
                img = Image.open(p).convert("RGBA")
                self.images.append(img)
            except Exception as e:
                messagebox.showerror("加载失败", f"{p}\n{e}")
                return

        self.count_label.config(text=f"已选择 {len(self.images)} 张", fg="black")
        self.status.config(text=f"已加载 {len(self.images)} 张，尺寸 {self.images[0].size}")
        self.update_preview()

    def _parse_bg(self):
        try:
            parts = [int(x.strip()) for x in self.bg_var.get().split(",")]
            if len(parts) == 4:
                return tuple(parts)
            elif len(parts) == 3:
                return (parts[0], parts[1], parts[2], 255)
            else:
                return (0, 0, 0, 0)
        except ValueError:
            return (0, 0, 0, 0)

    def compute_layout(self):
        n = len(self.images)
        if n == 0:
            return None, None, None

        gap = self._get_int(self.gap_var, "帧间距", default=0)
        if gap is None or gap < 0:
            gap = 0

        if self.mode_var.get() == "auto":
            cols = max(1, int(math.ceil(math.sqrt(n))))
        else:
            cols = self._get_int(self.cols_var, "每行帧数")
            if cols is None or cols <= 0:
                return None, None, None

        rows = max(1, math.ceil(n / cols))
        return cols, rows, gap

    def build_merged(self):
        cols, rows, gap = self.compute_layout()
        if cols is None:
            return None

        fw, fh = self.images[0].size
        fixed = []
        for img in self.images:
            if img.size != (fw, fh):
                img = img.resize((fw, fh), Image.NEAREST)
            fixed.append(img)

        W = cols * fw + (cols - 1) * gap
        H = rows * fh + (rows - 1) * gap

        bg = self._parse_bg()
        canvas = Image.new("RGBA", (W, H), bg)

        for idx, img in enumerate(fixed):
            r = idx // cols
            c = idx % cols
            x = c * (fw + gap)
            y = r * (fh + gap)
            canvas.paste(img, (x, y), img if img.mode == "RGBA" else None)

        return canvas

    def update_preview(self):
        self.preview_canvas.delete("all")
        if not self.images:
            return

        merged = self.build_merged()
        if merged is None:
            return

        cw = max(1, self.preview_canvas.winfo_width() - 10)
        ch = max(1, self.preview_canvas.winfo_height() - 10)
        self.scale = min(cw / merged.width, ch / merged.height, 1.0)
        dw = int(merged.width * self.scale)
        dh = int(merged.height * self.scale)

        disp = merged.resize((dw, dh), Image.NEAREST)
        draw = ImageDraw.Draw(disp)

        cols, rows, gap = self.compute_layout()
        fw, fh = self.images[0].size
        for c in range(cols + 1):
            x = int(c * (fw + gap) * self.scale)
            if x <= dw:
                draw.line([(x, 0), (x, dh)], fill=(0, 255, 0), width=1)
        for r in range(rows + 1):
            y = int(r * (fh + gap) * self.scale)
            if y <= dh:
                draw.line([(0, y), (dw, y)], fill=(0, 255, 0), width=1)

        self.preview_img = ImageTk.PhotoImage(disp)
        px = max(0, (self.preview_canvas.winfo_width() - dw) // 2)
        py = max(0, (self.preview_canvas.winfo_height() - dh) // 2)
        self.preview_canvas.create_image(px, py, anchor=tk.NW, image=self.preview_img)

        self.status.config(
            text=f"{len(self.images)} 帧　|　{cols} 列 × {rows} 行　|　间距 {gap}px　|　输出 {merged.width}×{merged.height}")

    def merge_and_save(self):
        if not self.images:
            messagebox.showwarning("提示", "请先选择序列图片")
            return

        merged = self.build_merged()
        if merged is None:
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG 图片", "*.png")],
            initialfile="merged_sprite.png")
        if not path:
            return

        try:
            merged.save(path, "PNG")
            self.status.config(text=f"已保存：{path}")
            messagebox.showinfo("拼接成功", f"已保存到：\n{path}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def send_to_cutter(self):
        if not self.images:
            messagebox.showwarning("提示", "请先选择序列图片")
            return

        merged = self.build_merged()
        if merged is None:
            return

        self.app.send_to_cutter(merged)