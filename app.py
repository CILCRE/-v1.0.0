import tkinter as tk
from tkinter import messagebox
from PIL import Image
from cutter import SpriteCutter
from merger import SpriteMerger
from utils import auto_analyze


class SpriteAnimator:
    def __init__(self, root):
        self.root = root
        self.root.title("精灵表工具")

        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.attributes("-zoomed", True)

        menubar = tk.Menu(self.root)
        func_menu = tk.Menu(menubar, tearoff=0)
        func_menu.add_command(label="精灵表切割", command=self.show_cutter)
        func_menu.add_command(label="序列图拼接", command=self.show_merger)
        menubar.add_cascade(label="功能", menu=func_menu)
        self.root.config(menu=menubar)

        self.container = tk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        self.cutter_frame = None
        self.merger_frame = None

        self.show_cutter()

    def clear_container(self):
        for w in self.container.winfo_children():
            w.destroy()

    def show_cutter(self):
        self.clear_container()
        self.cutter_frame = SpriteCutter(self.container)

    def show_merger(self):
        self.clear_container()
        self.merger_frame = SpriteMerger(self.container, self)

    def send_to_cutter(self, img):
        self.show_cutter()
        cutter = self.cutter_frame
        cutter.path_label.config(text="来自序列拼接", fg="black")
        cutter.apply_auto_analyze(img)