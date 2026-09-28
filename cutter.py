import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
from utils import auto_analyze


class SpriteCutter:
    def __init__(self, parent):
        self.parent = parent
        self.sheet = None
        self.frames = []
        self.frames_pil = []
        self.current = 0
        self.playing = False
        self.after_id = None
        self.preview_img = None
        self.loading = False

        self.dragging = None
        self.scale = 1.0
        self.disp_w = 0
        self.disp_h = 0

        self.seeking = False

        self.preview_cw = 620
        self.preview_ch = 420
        self.anim_cw = 500
        self.anim_ch = 300

        self._build_ui()

    def _build_ui(self):
        top = tk.Frame(self.parent)
        top.pack(pady=10)

        tk.Button(top, text="加载图片", command=self.load_image).pack(side=tk.LEFT, padx=5)
        self.path_label = tk.Label(top, text="未加载", fg="gray")
        self.path_label.pack(side=tk.LEFT, padx=10)

        middle = tk.Frame(self.parent)
        middle.pack(pady=10, padx=10, fill="both", expand=True)

        params = tk.LabelFrame(middle, text="切割参数")
        params.pack(side=tk.LEFT, fill="y", padx=(0, 10))

        self.offset_x = self._add_param(params, "起始X偏移", "0", 0)
        self.offset_y = self._add_param(params, "起始Y偏移", "0", 1)
        self.frame_w = self._add_param(params, "每帧宽度", "100", 2)
        self.frame_h = self._add_param(params, "每帧高度", "100", 3)
        self.frame_count = self._add_param(params, "横向帧数", "4", 4)
        self.row_count = self._add_param(params, "纵向行数", "3", 5)
        self.fps = self._add_param(params, "FPS", "10", 6)

        tk.Button(params, text="应用切割", command=self.slice_frames).grid(
            row=7, column=0, columnspan=2, pady=8)

        preview_frame = tk.LabelFrame(middle, text="切割预览（拖动红线改偏移和宽高）")
        preview_frame.pack(side=tk.LEFT, fill="both", expand=True)

        self.preview_canvas = tk.Canvas(preview_frame, bg="#1e1e1e")
        self.preview_canvas.pack(fill="both", expand=True, padx=5, pady=5)

        self.preview_canvas.bind("<Configure>", self.on_preview_resize)
        self.preview_canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.preview_canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.preview_canvas.bind("<Motion>", self.on_mouse_move)

        anim_frame = tk.LabelFrame(self.parent, text="动画预览（自动播放）")
        anim_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.canvas = tk.Canvas(anim_frame, bg="#1e1e1e")
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        self.canvas.bind("<Configure>", self.on_anim_resize)

        slider_frame = tk.Frame(anim_frame)
        slider_frame.pack(pady=5, fill="x", padx=5)

        self.frame_label = tk.Label(slider_frame, text="帧：0 / 0", width=14)
        self.frame_label.pack(side=tk.LEFT)

        self.slider = tk.Scale(slider_frame, from_=0, to=0, orient=tk.HORIZONTAL,
                               showvalue=0, command=self.on_slider)
        self.slider.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        self.slider.bind("<ButtonPress-1>", self.on_slider_press)
        self.slider.bind("<ButtonRelease-1>", self.on_slider_release)

        bottom = tk.Frame(self.parent)
        bottom.pack(pady=10)

        self.play_btn = tk.Button(bottom, text="▶ 播放", width=10,
                                  command=self.toggle_play, state=tk.DISABLED)
        self.play_btn.pack(side=tk.LEFT, padx=5)

        tk.Button(bottom, text="⏹ 停止", width=10,
                  command=self.stop).pack(side=tk.LEFT, padx=5)

        tk.Button(bottom, text="💾 导出GIF", width=10,
                  command=self.export_gif).pack(side=tk.LEFT, padx=5)

        self.status = tk.Label(self.parent, text="请先加载图片", fg="gray")
        self.status.pack(pady=5)

    def on_preview_resize(self, event):
        self.preview_cw = event.width
        self.preview_ch = event.height
        self.update_preview()

    def on_anim_resize(self, event):
        self.anim_cw = event.width
        self.anim_ch = event.height
        self.show_frame()

    def _add_param(self, parent, label, default, row):
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=5, pady=3)
        var = tk.StringVar(value=default)
        entry = tk.Entry(parent, width=10, textvariable=var)
        entry.grid(row=row, column=1, sticky="w", padx=5, pady=3)
        var.trace_add("write", lambda *args: self.update_preview())
        entry.var = var
        return entry

    def _get_int(self, entry, name, silent=False):
        try:
            return int(entry.var.get())
        except ValueError:
            if not silent:
                messagebox.showerror("参数错误", f"{name} 必须是整数")
            return None

    def load_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if not path:
            return
        try:
            self.sheet = Image.open(path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("加载失败", str(e))
            return

        self.path_label.config(text=os.path.basename(path), fg="black")
        self.apply_auto_analyze(self.sheet)

    def apply_auto_analyze(self, img):
        self.sheet = img
        col_blocks, row_blocks = auto_analyze(img)
        n_cols, n_rows = len(col_blocks), len(row_blocks)

        info = f"图片尺寸：{img.width} × {img.height}"
        if n_cols > 0 and n_rows > 0:
            ox = col_blocks[0][0]
            oy = row_blocks[0][0]

            self.loading = True
            self._set_entry(self.offset_x, ox)
            self._set_entry(self.offset_y, oy)
            self._set_entry(self.frame_w, 100)
            self._set_entry(self.frame_h, 100)
            self._set_entry(self.frame_count, n_cols)
            self._set_entry(self.row_count, n_rows)
            self.loading = False

            info += f"　|　自动分析：偏移({ox},{oy})，横向 {n_cols} 帧，纵向 {n_rows} 行"
        else:
            info += "　|　自动分析失败，请手动填写参数"

        self.status.config(text=info)
        self.frames = []
        self.frames_pil = []
        self.canvas.delete("all")
        self.play_btn.config(state=tk.DISABLED)
        self.update_preview()

    def _set_entry(self, entry, value):
        entry.var.set(str(value))

    def update_preview(self):
        if self.loading:
            return
        self.preview_canvas.delete("all")
        if self.sheet is None:
            return

        ox = self._get_int(self.offset_x, "起始X偏移", silent=True)
        oy = self._get_int(self.offset_y, "起始Y偏移", silent=True)
        fw = self._get_int(self.frame_w, "每帧宽度", silent=True)
        fh = self._get_int(self.frame_h, "每帧高度", silent=True)
        fc = self._get_int(self.frame_count, "横向帧数", silent=True)
        rc = self._get_int(self.row_count, "纵向行数", silent=True)
        if None in (ox, oy, fw, fh, fc, rc) or fw <= 0 or fh <= 0:
            return

        cw = max(1, self.preview_cw - 10)
        ch = max(1, self.preview_ch - 10)
        self.scale = min(cw / self.sheet.width, ch / self.sheet.height, 1.0)
        self.disp_w = int(self.sheet.width * self.scale)
        self.disp_h = int(self.sheet.height * self.scale)

        disp = self.sheet.resize((self.disp_w, self.disp_h), Image.NEAREST).copy()
        draw = ImageDraw.Draw(disp)

        for i in range(fc + 1):
            x = int((ox + i * fw) * self.scale)
            if 0 <= x <= self.disp_w:
                draw.line([(x, 0), (x, self.disp_h)], fill=(0, 255, 0), width=1)
        for j in range(rc + 1):
            y = int((oy + j * fh) * self.scale)
            if 0 <= y <= self.disp_h:
                draw.line([(0, y), (self.disp_w, y)], fill=(0, 255, 0), width=1)

        for r in range(rc):
            for c in range(fc):
                idx = r * fc + c
                cx = int((ox + (c + 0.5) * fw) * self.scale)
                cy = int((oy + (r + 0.5) * fh) * self.scale)
                if 0 <= cx < self.disp_w and 0 <= cy < self.disp_h:
                    draw.text((cx - 6, cy - 6), str(idx + 1), fill=(255, 255, 0))

        x_left = int(ox * self.scale)
        x_right = int((ox + fw) * self.scale)
        y_top = int(oy * self.scale)
        y_bottom = int((oy + fh) * self.scale)

        if 0 <= x_left <= self.disp_w:
            draw.line([(x_left, 0), (x_left, self.disp_h)], fill=(255, 80, 80), width=2)
        if 0 <= x_right <= self.disp_w:
            draw.line([(x_right, 0), (x_right, self.disp_h)], fill=(255, 80, 80), width=2)
        if 0 <= y_top <= self.disp_h:
            draw.line([(0, y_top), (self.disp_w, y_top)], fill=(255, 80, 80), width=2)
        if 0 <= y_bottom <= self.disp_h:
            draw.line([(0, y_bottom), (self.disp_w, y_bottom)], fill=(255, 80, 80), width=2)

        # ---- 高亮当前帧 ----
        if self.frames_pil and 0 <= self.current < len(self.frames_pil):
            row = self.current // fc
            col = self.current % fc
            hx1 = int((ox + col * fw) * self.scale)
            hy1 = int((oy + row * fh) * self.scale)
            hx2 = int((ox + (col + 1) * fw) * self.scale)
            hy2 = int((oy + (row + 1) * fh) * self.scale)
            for offset in range(2):
                draw.rectangle(
                    [(hx1 - offset, hy1 - offset), (hx2 + offset, hy2 + offset)],
                    outline=(255, 255, 0),
                    width=1
                )

        self.preview_img = ImageTk.PhotoImage(disp)
        px = max(0, (self.preview_cw - self.disp_w) // 2)
        py = max(0, (self.preview_ch - self.disp_h) // 2)
        self.preview_canvas.create_image(px, py, anchor=tk.NW, image=self.preview_img)

        self.preview_offset_x = px
        self.preview_offset_y = py

    def _near_lines(self, event):
        ox = self._get_int(self.offset_x, "起始X偏移", silent=True)
        oy = self._get_int(self.offset_y, "起始Y偏移", silent=True)
        fw = self._get_int(self.frame_w, "每帧宽度", silent=True)
        fh = self._get_int(self.frame_h, "每帧高度", silent=True)
        if None in (ox, oy, fw, fh):
            return None

        mx = event.x - getattr(self, "preview_offset_x", 0)
        my = event.y - getattr(self, "preview_offset_y", 0)

        x_left = ox * self.scale
        x_right = (ox + fw) * self.scale
        y_top = oy * self.scale
        y_bottom = (oy + fh) * self.scale

        threshold = 6
        if abs(mx - x_left) <= threshold:
            return "left"
        if abs(mx - x_right) <= threshold:
            return "right"
        if abs(my - y_top) <= threshold:
            return "top"
        if abs(my - y_bottom) <= threshold:
            return "bottom"
        return None

    def on_mouse_down(self, event):
        if self.sheet is None:
            return
        self.dragging = self._near_lines(event)

    def on_mouse_drag(self, event):
        if self.dragging is None or self.sheet is None:
            return

        mx = event.x - getattr(self, "preview_offset_x", 0)
        my = event.y - getattr(self, "preview_offset_y", 0)

        ox = self._get_int(self.offset_x, "起始X偏移", silent=True) or 0
        oy = self._get_int(self.offset_y, "起始Y偏移", silent=True) or 0
        fw = self._get_int(self.frame_w, "每帧宽度", silent=True) or 1
        fh = self._get_int(self.frame_h, "每帧高度", silent=True) or 1

        if self.dragging == "left":
            new_x = int(mx / self.scale)
            new_x = max(0, min(new_x, ox + fw - 1))
            self._set_entry(self.offset_x, new_x)
        elif self.dragging == "right":
            new_right = int(mx / self.scale)
            new_w = new_right - ox
            new_w = max(1, min(new_w, self.sheet.width - ox))
            self._set_entry(self.frame_w, new_w)
        elif self.dragging == "top":
            new_y = int(my / self.scale)
            new_y = max(0, min(new_y, oy + fh - 1))
            self._set_entry(self.offset_y, new_y)
        elif self.dragging == "bottom":
            new_bottom = int(my / self.scale)
            new_h = new_bottom - oy
            new_h = max(1, min(new_h, self.sheet.height - oy))
            self._set_entry(self.frame_h, new_h)

    def on_mouse_up(self, event):
        self.dragging = None

    def on_mouse_move(self, event):
        if self.sheet is None:
            return
        line = self._near_lines(event)
        if line in ("left", "right"):
            self.preview_canvas.config(cursor="sb_h_double_arrow")
        elif line in ("top", "bottom"):
            self.preview_canvas.config(cursor="sb_v_double_arrow")
        else:
            self.preview_canvas.config(cursor="")

    def on_slider_press(self, event):
        self.seeking = True
        self.pause()

    def on_slider_release(self, event):
        self.seeking = False

    def on_slider(self, value):
        if not self.frames:
            return
        idx = int(float(value))
        if 0 <= idx < len(self.frames):
            self.current = idx
            self.show_frame()
            self.frame_label.config(text=f"帧：{idx+1} / {len(self.frames)}")
            self.update_preview()

    def slice_frames(self):
        if self.sheet is None:
            messagebox.showwarning("提示", "请先加载图片")
            return

        ox = self._get_int(self.offset_x, "起始X偏移")
        oy = self._get_int(self.offset_y, "起始Y偏移")
        fw = self._get_int(self.frame_w, "每帧宽度")
        fh = self._get_int(self.frame_h, "每帧高度")
        fc = self._get_int(self.frame_count, "横向帧数")
        rc = self._get_int(self.row_count, "纵向行数")
        if None in (ox, oy, fw, fh, fc, rc):
            return
        if fw <= 0 or fh <= 0 or fc <= 0 or rc <= 0:
            messagebox.showerror("错误", "参数必须大于 0")
            return
        if ox < 0 or oy < 0:
            messagebox.showerror("错误", "偏移不能为负数")
            return

        self.frames = []
        self.frames_pil = []
        skipped = 0
        for r in range(rc):
            for c in range(fc):
                x = ox + c * fw
                y = oy + r * fh
                if x + fw > self.sheet.width or y + fh > self.sheet.height:
                    skipped += 1
                    continue
                frame = self.sheet.crop((x, y, x + fw, y + fh))
                self.frames_pil.append(frame)
                self.frames.append(ImageTk.PhotoImage(frame))

        if not self.frames:
            messagebox.showerror("错误", "切不出任何帧，请检查参数")
            return

        self.current = 0
        self.show_frame()

        self.slider.config(from_=0, to=len(self.frames) - 1)
        self.slider.set(0)
        self.frame_label.config(text=f"帧：1 / {len(self.frames)}")

        self.play_btn.config(state=tk.NORMAL)
        msg = f"已切出 {len(self.frames)} 帧（按行优先顺序播放）"
        if skipped:
            msg += f"，跳过 {skipped} 帧（越界）"
        self.status.config(text=msg)
        self.update_preview()
        self.play()

    def export_gif(self):
        if not self.frames_pil:
            messagebox.showwarning("提示", "请先切割出帧")
            return

        self.pause()

        fps = self._get_int(self.fps, "FPS", silent=True) or 10
        duration = max(20, int(1000 / fps))

        path = filedialog.asksaveasfilename(
            defaultextension=".gif",
            filetypes=[("GIF 图片", "*.gif")],
            initialfile="animation.gif")
        if not path:
            return

        try:
            rgb_frames = []
            for f in self.frames_pil:
                bg = Image.new("RGB", f.size, (30, 30, 30))
                if f.mode == "RGBA":
                    bg.paste(f, (0, 0), f)
                else:
                    bg.paste(f, (0, 0))
                rgb_frames.append(bg)

            rgb_frames[0].save(
                path,
                save_all=True,
                append_images=rgb_frames[1:],
                duration=duration,
                loop=0,
                optimize=False
            )
            self.status.config(text=f"GIF 已导出：{path}")
            messagebox.showinfo("导出成功", f"GIF 已保存到：\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def show_frame(self):
        self.canvas.delete("all")
        if not self.frames:
            return
        img = self.frames[self.current]

        cw = max(1, self.anim_cw - 10)
        ch = max(1, self.anim_ch - 10)
        scale = min(cw / img.width(), ch / img.height(), 1.0)
        nw = max(1, int(img.width() * scale))
        nh = max(1, int(img.height() * scale))

        if scale < 1.0:
            pil = ImageTk.getimage(img).resize((nw, nh), Image.NEAREST)
            self._scaled_img = ImageTk.PhotoImage(pil)
            show = self._scaled_img
        else:
            show = img

        x = (self.anim_cw - nw) // 2
        y = (self.anim_ch - nh) // 2
        self.canvas.create_image(x, y, anchor=tk.NW, image=show)

    def toggle_play(self):
        if self.playing:
            self.pause()
        else:
            self.play()

    def play(self):
        if not self.frames:
            return
        self.playing = True
        self.play_btn.config(text="⏸ 暂停")
        self._next_frame()

    def _next_frame(self):
        if not self.playing or self.seeking:
            return
        self.current = (self.current + 1) % len(self.frames)
        self.show_frame()
        self.slider.set(self.current)
        self.frame_label.config(text=f"帧：{self.current+1} / {len(self.frames)}")
        self.update_preview()
        fps = self._get_int(self.fps, "FPS", silent=True) or 10
        delay = max(1, int(1000 / fps))
        self.after_id = self.parent.after(delay, self._next_frame)

    def pause(self):
        self.playing = False
        self.play_btn.config(text="▶ 播放")
        if self.after_id:
            self.parent.after_cancel(self.after_id)
            self.after_id = None

    def stop(self):
        self.pause()
        self.current = 0
        self.slider.set(0)
        self.frame_label.config(text=f"帧：1 / {len(self.frames)}" if self.frames else "帧：0 / 0")
        self.show_frame()
        self.update_preview()