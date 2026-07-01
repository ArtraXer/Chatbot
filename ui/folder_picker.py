import os
import customtkinter as ctk
import tkinter as tk


def show_folder_picker(parent, initialdir=None):
    selected = {"path": None}

    if not initialdir or not os.path.isdir(initialdir):
        initialdir = os.path.expanduser("~")

    win = ctk.CTkToplevel(parent)
    win.title("Seleccionar carpeta de trabajo")
    win.geometry("640x380")
    win.transient(parent)
    win.grab_set()

    # Header
    header = ctk.CTkFrame(win, fg_color="transparent")
    header.pack(fill="x", padx=12, pady=(12, 6))
    path_var = tk.StringVar(value=initialdir)

    ctk.CTkLabel(header, text="Directorio:", width=90, anchor="w").pack(side="left", padx=(6, 8))
    path_entry = ctk.CTkComboBox(header, values=[initialdir], variable=path_var, width=420)
    path_entry.pack(side="left", fill="x", expand=True)

    up_btn = ctk.CTkButton(header, text="↑", width=34, command=lambda: _go_up())
    up_btn.pack(side="left", padx=(8, 2))

    # Content list
    content_frame = ctk.CTkFrame(win)
    content_frame.pack(fill="both", expand=True, padx=12, pady=(6, 12))

    list_frame = ctk.CTkScrollableFrame(content_frame, fg_color="#111219")
    list_frame.pack(fill="both", expand=True, side="left")

    scrollbar = tk.Scrollbar(content_frame)
    scrollbar.pack(side="left", fill="y")

    # Footer
    footer = ctk.CTkFrame(win, fg_color="transparent")
    footer.pack(fill="x", padx=12, pady=(0, 12))

    selection_var = tk.StringVar(value=initialdir)
    ctk.CTkLabel(footer, text="Selección:", width=90, anchor="w").pack(side="left", padx=(6, 8))
    sel_entry = ctk.CTkEntry(footer, textvariable=selection_var, width=420)
    sel_entry.pack(side="left", fill="x", expand=True)

    def _refresh_list(path):
        for w in list_frame.winfo_children():
            w.destroy()
        try:
            entries = sorted([e for e in os.listdir(path)])
        except Exception:
            entries = []

        # folders first
        folders = [e for e in entries if os.path.isdir(os.path.join(path, e))]
        files = [e for e in entries if os.path.isfile(os.path.join(path, e))]

        # parent link
        parent_dir = os.path.dirname(path)
        def add_row(name, kind, fullpath):
            frame = ctk.CTkFrame(list_frame, fg_color="#15171a")
            frame.pack(fill="x", pady=1, padx=6)
            icon = "📁" if kind == "dir" else "📄"
            lbl_icon = ctk.CTkLabel(frame, text=icon, width=28)
            lbl_icon.pack(side="left", padx=(6, 10))
            btn = ctk.CTkButton(frame, text=name, anchor="w", fg_color="transparent", hover_color="#22252a", command=lambda p=fullpath, k=kind: _on_activate(p, k))
            btn.pack(side="left", fill="x", expand=True, padx=(0,6))
            btn.bind('<Double-Button-1>', lambda e, p=fullpath, k=kind: _on_double(p, k))

        if parent_dir and parent_dir != path:
            add_row('..', 'dir', parent_dir)

        for f in folders:
            add_row(f, 'dir', os.path.join(path, f))

        for f in files:
            add_row(f, 'file', os.path.join(path, f))

    def _on_activate(path, kind):
        if kind == 'dir':
            path_var.set(path)
            selection_var.set(path)
            _refresh_list(path)
        else:
            selection_var.set(path)

    def _on_double(path, kind):
        if kind == 'dir':
            _on_activate(path, kind)
        else:
            selection_var.set(path)

    def _go_up():
        cur = path_var.get()
        parent_dir = os.path.dirname(cur)
        if parent_dir and os.path.isdir(parent_dir):
            path_var.set(parent_dir)
            selection_var.set(parent_dir)
            _refresh_list(parent_dir)

    def _ok():
        sel = selection_var.get().strip()
        if sel and os.path.isdir(sel):
            selected['path'] = sel
            win.destroy()
        else:
            tk.messagebox.showerror('Ruta inválida', 'Selecciona una carpeta válida')

    def _cancel():
        selected['path'] = None
        win.destroy()

    ctk.CTkButton(footer, text="Cancelar", width=120, command=_cancel, fg_color="#2f3640").pack(side="right", padx=(8,6))
    ctk.CTkButton(footer, text="OK", width=120, command=_ok, fg_color="#2980b9").pack(side="right")

    # initialize
    _refresh_list(initialdir)
    selection_var.set(initialdir)

    win.wait_window()
    return selected['path']

def show_file_picker(parent, initialdir=None, filetypes=None):
    selected = {"path": None}

    if not initialdir or not os.path.isdir(initialdir):
        initialdir = os.path.expanduser("~")

    win = ctk.CTkToplevel(parent)
    win.title("Seleccionar archivo")
    win.geometry("640x380")
    win.transient(parent)
    win.grab_set()

    header = ctk.CTkFrame(win, fg_color="transparent")
    header.pack(fill="x", padx=12, pady=(12, 6))
    path_var = tk.StringVar(value=initialdir)

    ctk.CTkLabel(header, text="Directorio:", width=90, anchor="w").pack(side="left", padx=(6, 8))
    path_entry = ctk.CTkComboBox(header, values=[initialdir], variable=path_var, width=420)
    path_entry.pack(side="left", fill="x", expand=True)

    up_btn = ctk.CTkButton(header, text="↑", width=34, command=lambda: _go_up())
    up_btn.pack(side="left", padx=(8, 2))

    content_frame = ctk.CTkFrame(win)
    content_frame.pack(fill="both", expand=True, padx=12, pady=(6, 12))

    list_frame = ctk.CTkScrollableFrame(content_frame, fg_color="#111219")
    list_frame.pack(fill="both", expand=True, side="left")

    footer = ctk.CTkFrame(win, fg_color="transparent")
    footer.pack(fill="x", padx=12, pady=(0, 12))

    selection_var = tk.StringVar(value="")
    ctk.CTkLabel(footer, text="Archivo:", width=90, anchor="w").pack(side="left", padx=(6, 8))
    sel_entry = ctk.CTkEntry(footer, textvariable=selection_var, width=420)
    sel_entry.pack(side="left", fill="x", expand=True)

    def _refresh_list(path):
        for w in list_frame.winfo_children():
            w.destroy()
        try:
            entries = sorted([e for e in os.listdir(path)])
        except Exception:
            entries = []

        folders = [e for e in entries if os.path.isdir(os.path.join(path, e))]
        files = [e for e in entries if os.path.isfile(os.path.join(path, e))]

        if filetypes:
            import fnmatch
            filtered_files = []
            for f in files:
                for ext in filetypes:
                    if fnmatch.fnmatch(f, ext):
                        filtered_files.append(f)
                        break
            files = filtered_files

        parent_dir = os.path.dirname(path)
        def add_row(name, kind, fullpath):
            frame = ctk.CTkFrame(list_frame, fg_color="#15171a")
            frame.pack(fill="x", pady=1, padx=6)
            icon = "📁" if kind == "dir" else "📄"
            lbl_icon = ctk.CTkLabel(frame, text=icon, width=28)
            lbl_icon.pack(side="left", padx=(6, 10))
            btn = ctk.CTkButton(frame, text=name, anchor="w", fg_color="transparent", hover_color="#22252a", command=lambda p=fullpath, k=kind: _on_activate(p, k))
            btn.pack(side="left", fill="x", expand=True, padx=(0,6))
            btn.bind('<Double-Button-1>', lambda e, p=fullpath, k=kind: _on_double(p, k))

        if parent_dir and parent_dir != path:
            add_row('..', 'dir', parent_dir)

        for f in folders:
            add_row(f, 'dir', os.path.join(path, f))

        for f in files:
            add_row(f, 'file', os.path.join(path, f))

    def _on_activate(path, kind):
        if kind == 'dir':
            path_var.set(path)
            selection_var.set("")
            _refresh_list(path)
        else:
            selection_var.set(path)

    def _on_double(path, kind):
        if kind == 'dir':
            _on_activate(path, kind)
        else:
            selection_var.set(path)
            _ok()

    def _go_up():
        cur = path_var.get()
        parent_dir = os.path.dirname(cur)
        if parent_dir and os.path.isdir(parent_dir):
            path_var.set(parent_dir)
            selection_var.set("")
            _refresh_list(parent_dir)

    def _ok():
        sel = selection_var.get().strip()
        if sel and os.path.isfile(sel):
            selected['path'] = sel
            win.destroy()
        else:
            tk.messagebox.showerror('Ruta inválida', 'Selecciona un archivo válido')

    def _cancel():
        selected['path'] = None
        win.destroy()

    ctk.CTkButton(footer, text="Cancelar", width=120, command=_cancel, fg_color="#2f3640").pack(side="right", padx=(8,6))
    ctk.CTkButton(footer, text="OK", width=120, command=_ok, fg_color="#2980b9").pack(side="right")

    _refresh_list(initialdir)

    win.wait_window()
    return selected['path']
