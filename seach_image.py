import os
import shutil
import platform
import subprocess
import tempfile
import json
import re
from PIL import Image
from PIL.PngImagePlugin import PngImageFile
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from PIL import ImageTk

HISTORY_FILE = "keyword_history.json"
SOURCE_FOLDER = os.path.abspath("./images")


def get_metadata(filepath):
    try:
        img: PngImageFile = Image.open(filepath)
        return img.info.get("parameters", "").lower()
    except Exception as e:
        print(f"[エラー] {filepath}: {e}")
        return ""


def search_metadata(folder, keywords, mode="AND"):
    matched = []
    for filename in os.listdir(folder):
        if filename.lower().endswith(".png"):
            path = os.path.join(folder, filename)
            metadata = get_metadata(path)
            if mode == "AND":
                if all(k in metadata for k in keywords):
                    matched.append(path)
            elif mode == "OR":
                if any(k in metadata for k in keywords):
                    matched.append(path)
    return matched


def save_history(keyword):
    try:
        history = load_history()
        if keyword not in history:
            history.insert(0, keyword)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history[:20], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[履歴保存エラー] {e}")


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def show_image_viewer(image_paths):
    viewer = tk.Toplevel()
    viewer.title("検索結果一覧")
    canvas = tk.Canvas(viewer)
    scrollbar = ttk.Scrollbar(viewer, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    viewer.bind_all("<MouseWheel>", _on_mousewheel)

    max_columns = 6
    thumb_size = 160
    for i, path in enumerate(image_paths):
        try:
            img = Image.open(path)
            img.thumbnail((thumb_size, thumb_size))
            img_tk = ImageTk.PhotoImage(img)

            def on_click(p=path):
                show_image_detail(p)

            btn = tk.Button(scrollable_frame, image=img_tk, command=on_click)
            btn.image = img_tk
            row, col = divmod(i, max_columns)
            btn.grid(row=row, column=col, padx=5, pady=5)
        except Exception as e:
            print(f"[画像表示エラー] {e}")


def show_image_detail(path):
    detail = tk.Toplevel()
    detail.title("画像詳細")
    img = Image.open(path)
    img_tk = ImageTk.PhotoImage(img)

    label = tk.Label(detail, image=img_tk)
    label.image = img_tk
    label.pack()

    ttk.Label(detail, text=f"パス: {path}").pack(pady=5)

    btn_frame = ttk.Frame(detail)
    btn_frame.pack(pady=10)

    def copy_file():
        dest = filedialog.askdirectory()
        if dest:
            shutil.copy(path, dest)

    def move_file():
        dest = filedialog.askdirectory()
        if dest:
            shutil.move(path, dest)

    def open_in_os_viewer():
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])

    ttk.Button(btn_frame, text="コピー", command=copy_file).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="移動", command=move_file).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="OSビューアで開く", command=open_in_os_viewer).pack(side="left", padx=5)


def launch_search_gui():
    def perform_search():
        folder = folder_entry.get()
        folder = os.path.normpath(folder)
        if not os.path.isdir(folder):
            messagebox.showerror("エラー", "有効なフォルダを指定してくださいませ")
            return

        raw_keywords = keyword_entry.get().strip().lower()
        keywords = [k.strip() for k in raw_keywords.split(",") if k.strip()]
        if not keywords:
            messagebox.showerror("エラー", "キーワードを入力してくださいませ")
            return

        save_history(raw_keywords)
        mode = mode_var.get()
        matched_files = search_metadata(folder, keywords, mode)
        show_image_viewer(matched_files)

    def insert_history_keyword(event):
        keyword_entry.delete(0, tk.END)
        keyword_entry.insert(0, history_var.get())

    root = tk.Tk()
    root.title("キャラ画像メタデータ検索")
    root.configure(bg="#2e2e2e")

    frm = ttk.Frame(root, padding=10)
    frm.pack(anchor="w")

    ttk.Label(frm, text="検索対象フォルダ:").grid(row=0, column=0, sticky="e")
    folder_entry = ttk.Entry(frm, width=40)
    folder_entry.insert(0, SOURCE_FOLDER)
    folder_entry.grid(row=0, column=1)
    ttk.Button(frm, text="参照", command=lambda: folder_entry.delete(0, tk.END) or folder_entry.insert(0, os.path.normpath(filedialog.askdirectory()))).grid(row=0, column=2)

    ttk.Label(frm, text="キーワード (カンマ区切り):").grid(row=1, column=0, sticky="e")
    keyword_entry = ttk.Entry(frm, width=40)
    keyword_entry.grid(row=1, column=1, columnspan=2, sticky="w")

    history = load_history()
    history_var = tk.StringVar(value=history[0] if history else "")
    history_menu = ttk.OptionMenu(frm, history_var, history_var.get(), *history)
    history_menu.grid(row=2, column=1, columnspan=2, sticky="w")
    history_menu.bind("<ButtonRelease-1>", insert_history_keyword)

    mode_var = tk.StringVar(value="AND")
    ttk.Label(frm, text="検索モード:").grid(row=3, column=0, sticky="e")
    mode_frame = ttk.Frame(frm)
    mode_frame.grid(row=3, column=1, columnspan=2, sticky="w")
    ttk.Radiobutton(mode_frame, text="AND", variable=mode_var, value="AND").pack(side="left", padx=2)
    ttk.Radiobutton(mode_frame, text="OR", variable=mode_var, value="OR").pack(side="left", padx=2)

    ttk.Button(frm, text="検索", command=perform_search).grid(row=4, column=0, columnspan=3, pady=10)

    root.mainloop()


if __name__ == "__main__":
    launch_search_gui()
