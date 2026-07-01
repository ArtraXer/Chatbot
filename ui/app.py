import customtkinter as ctk
import threading
import os
import re
import shutil
import time
import tkinter as tk
from datetime import datetime

from tkinter import filedialog, simpledialog, messagebox
from agente import pensar, set_instrucciones
from herramientas import listar_archivos, set_directorio_base, get_directorio_base, escribir_archivo
from iconos import obtener_icono
from ui.tree_utils import listar_nodos_arbol
from ui.folder_picker import show_folder_picker
from core.state import (
    append_conversation,
    append_task,
    clear_history,
    clear_tasks,
    load_conversations,
    load_settings,
    load_tasks,
    save_settings,
    save_session,
    load_sessions,
    delete_session,
)

# Snapshot del árbol de archivos para detectar cambios
_ultimo_snapshot = set()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

SETTINGS = load_settings()


def save_ui_state():
    SETTINGS["open_files"] = list(editores_abiertos.keys())
    SETTINGS["workdir"] = get_directorio_base()
    SETTINGS["model"] = selected_model_var.get()
    save_settings(SETTINGS)


def cargar_estado_ui():
    workdir = SETTINGS.get("workdir", "")
    if workdir and os.path.isdir(workdir):
        set_directorio_base(workdir)
        titulo_archivos.configure(text=os.path.basename(workdir))

    rutas = [ruta for ruta in SETTINGS.get("open_files", []) if os.path.isfile(ruta)]
    if not rutas:
        return

    def abrir_siguiente(ind=0):
        if ind >= len(rutas):
            return
        ruta = rutas[ind]
        abrir_editor(ruta, os.path.basename(ruta))
        app.after(80, lambda: abrir_siguiente(ind + 1))

    app.after(150, lambda: abrir_siguiente(0))


app = ctk.CTk()
app.title("AI Agent")
app.geometry("1920x1080")

app.protocol("WM_DELETE_WINDOW", lambda: (save_ui_state(), app.destroy()))

cancelar_generacion = False
auto_corregido = False
# -------- ESTRUCTURA PRINCIPAL --------
main_frame = ctk.CTkFrame(app, fg_color="transparent")
main_frame.pack(fill="both", expand=True)

# -------- PANEL IZQUIERDO: BARRA LATERAL --------
sidebar = ctk.CTkScrollableFrame(
    main_frame,
    width=320,
    corner_radius=20,
    fg_color="#131b28",
    scrollbar_button_color="#2f3640",
    scrollbar_button_hover_color="#718093",
    border_width=0,
)
sidebar.pack(side="left", fill="y", padx=(18, 0), pady=18)

workspace_card = ctk.CTkFrame(sidebar, fg_color="#191f2f", corner_radius=20, border_width=1, border_color="#2f3640")
workspace_card.pack(fill="x", padx=14, pady=(14, 8))

header_top = ctk.CTkFrame(workspace_card, fg_color="transparent")
header_top.pack(fill="x", padx=16, pady=(16, 6))

ctk.CTkLabel(
    header_top,
    text="WORKSPACE",
    font=("Inter", 11, "bold"),
    text_color="#7f8fa6"
).pack(side="left")

ctk.CTkLabel(
    header_top,
    text="●",
    font=("Inter", 12, "bold"),
    text_color="#2ecc71"
).pack(side="right")

titulo_archivos = ctk.CTkLabel(
    workspace_card,
    text=os.path.basename(get_directorio_base()),
    font=("Inter", 20, "bold"),
    text_color="#f5f6fa"
)
titulo_archivos.pack(anchor="w", padx=16)

ruta_workspace = ctk.CTkLabel(
    workspace_card,
    text=get_directorio_base(),
    font=("Inter", 10),
    text_color="#95a5a6",
    wraplength=280,
    justify="left"
)
ruta_workspace.pack(anchor="w", padx=16, pady=(4, 0))

botones_workspace = ctk.CTkFrame(workspace_card, fg_color="transparent")
botones_workspace.pack(fill="x", padx=16, pady=(16, 16))

btn_directorio = ctk.CTkButton(
    botones_workspace,
    text="Cambiar",
    command=lambda: cambiar_directorio(),
    fg_color="#2f3640",
    hover_color="#3d4d6b",
    height=36,
    corner_radius=14,
    font=("Inter", 11, "bold")
)
btn_directorio.pack(side="left", fill="x", expand=True, padx=(0, 8))

btn_refresh = ctk.CTkButton(
    botones_workspace,
    text="Refrescar",
    command=lambda: actualizar_arbol_archivos(forzar=True),
    fg_color="#2f3640",
    hover_color="#3d4d6b",
    height=36,
    corner_radius=14,
    font=("Inter", 11, "bold")
)
btn_refresh.pack(side="left", fill="x", expand=True)

btn_api_key = ctk.CTkButton(
    botones_workspace,
    text="🔑",
    command=lambda: abrir_panel_api_keys(),
    fg_color="#2f3640",
    hover_color="#3d4d6b",
    height=36,
    width=44,
    corner_radius=14,
    font=("Inter", 14)
)
btn_api_key.pack(side="left", padx=(8, 0))

search_var = tk.StringVar(value="")
search_entry = ctk.CTkEntry(
    sidebar,
    textvariable=search_var,
    placeholder_text="Buscar...",
    width=280,
    corner_radius=16,
    fg_color="#171f2f",
    text_color="#f5f6fa",
    placeholder_text_color="#7f8fa6",
    border_width=1,
    border_color="#2f3640",
    font=("Inter", 12),
    height=36,
)
search_entry.pack(fill="x", padx=14, pady=(0, 12))

frame_lista_archivos = ctk.CTkFrame(sidebar, fg_color="#151d2d", corner_radius=18)
frame_lista_archivos.pack(fill="both", expand=True, padx=14, pady=(0, 8))

# -------- PANEL HISTORIAL DE SESIONES --------
historial_card = ctk.CTkFrame(sidebar, fg_color="#191f2f", corner_radius=18, border_width=1, border_color="#2f3640")
historial_card.pack(fill="x", padx=14, pady=(0, 14))

hist_header = ctk.CTkFrame(historial_card, fg_color="transparent")
hist_header.pack(fill="x", padx=16, pady=(12, 4))

ctk.CTkLabel(hist_header, text="HISTORIAL", font=("Inter", 11, "bold"), text_color="#7f8fa6").pack(side="left")

_chat_messages_cache = []  # Lista de dicts {role, content} de la sesión actual

def _actualizar_panel_historial():
    for w in hist_list_frame.winfo_children():
        w.destroy()
    sesiones = load_sessions()
    if not sesiones:
        ctk.CTkLabel(hist_list_frame, text="Sin sesiones guardadas", font=("Inter", 11), text_color="#4a5568").pack(pady=8)
        return
    for ses in sesiones[:15]:
        ses_id = ses.get("id", "")
        ses_name = ses.get("name", "Sin nombre")
        ses_time = ses.get("timestamp", "")[:16].replace("T", " ")

        row = ctk.CTkFrame(hist_list_frame, fg_color="#131b28", corner_radius=10)
        row.pack(fill="x", pady=2, padx=4)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=(8, 0))

        ctk.CTkLabel(info, text=ses_name[:28], font=("Inter", 12, "bold"), text_color="#dfe6e9", anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=ses_time, font=("Inter", 10), text_color="#636e72", anchor="w").pack(anchor="w")

        def _cargar(s=ses):
            _cargar_sesion(s)
        def _borrar(sid=ses_id):
            delete_session(sid)
            _actualizar_panel_historial()

        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.pack(side="right", padx=4, pady=4)
        ctk.CTkButton(btn_frame, text="📂", width=28, height=28, fg_color="#2f3640", hover_color="#3d4d6b", command=_cargar, font=("Inter", 12)).pack(pady=2)
        ctk.CTkButton(btn_frame, text="🗑", width=28, height=28, fg_color="#3d1f2a", hover_color="#6b2737", command=_borrar, font=("Inter", 12)).pack(pady=2)

def _cargar_sesion(sesion):
    chat.configure(state="normal")
    chat.delete("1.0", "end")
    for msg in sesion.get("messages", []):
        rol = msg.get("role", "")
        contenido = msg.get("content", "")
        if isinstance(contenido, list):
            contenido = contenido[0].get("text", "")
        if rol == "user":
            chat.insert("end", f"👤 Tú:\n{contenido}\n\n")
        elif rol == "assistant":
            chat.insert("end", f"🤖 Agente:\n{contenido}\n\n")
    chat.see("end")

hist_search_var = tk.StringVar()
hist_search = ctk.CTkEntry(hist_header, textvariable=hist_search_var, placeholder_text="Buscar...", width=110, height=24, font=("Inter", 11), fg_color="#1a1d2e", border_color="#2f3640")
hist_search.pack(side="right")

hist_list_frame = ctk.CTkScrollableFrame(historial_card, fg_color="transparent", height=160)
hist_list_frame.pack(fill="x", padx=4, pady=(0, 8))

def _nueva_sesion():
    global _chat_messages_cache
    if _chat_messages_cache:
        nombre = f"Sesión {datetime.now().strftime('%d/%m %H:%M')}"
        save_session(nombre, _chat_messages_cache)
        _chat_messages_cache = []
    chat.configure(state="normal")
    chat.delete("1.0", "end")
    from core.agent_runtime import _memoria
    _memoria.limpiar()
    _actualizar_panel_historial()

btn_nueva_sesion = ctk.CTkButton(
    historial_card, text="＋ Nueva sesión",
    fg_color="#2f3640", hover_color="#3d4d6b",
    height=30, corner_radius=10, font=("Inter", 11, "bold"),
    command=_nueva_sesion
)
btn_nueva_sesion.pack(fill="x", padx=16, pady=(0, 10))



explorer_header = ctk.CTkFrame(frame_lista_archivos, fg_color="transparent")
explorer_header.pack(fill="x", padx=16, pady=(16, 0))

ctk.CTkLabel(
    explorer_header,
    text="EXPLORER",
    font=("Inter", 11, "bold"),
    text_color="#7f8fa6"
).pack(side="left")

count_label = ctk.CTkLabel(
    explorer_header,
    text="",
    font=("Inter", 11),
    text_color="#95a5a6"
)
count_label.pack(side="right")

ctk.CTkFrame(frame_lista_archivos, height=1, fg_color="#2f3640").pack(fill="x", padx=16, pady=(8, 10))

tree_content = ctk.CTkFrame(frame_lista_archivos, fg_color="transparent")
tree_content.pack(fill="both", expand=True, padx=12, pady=(0, 12))

tree_content.columnconfigure(0, weight=1)

# Estado de carpetas expandidas (persistente entre recargas del árbol)
carpetas_expandidas = set()
ultima_interaccion_arbol = 0.0
search_filter = ""

_search_debounce_id = None

def aplicar_filtro_arbol(event=None):
    global search_filter, _search_debounce_id
    if _search_debounce_id is not None:
        app.after_cancel(_search_debounce_id)
    _search_debounce_id = app.after(280, _ejecutar_filtro)

def _ejecutar_filtro():
    global search_filter, _search_debounce_id
    _search_debounce_id = None
    nuevo = search_var.get().strip().lower()
    search_filter = nuevo
    actualizar_arbol_archivos(forzar=True)

search_entry.bind("<KeyRelease>", aplicar_filtro_arbol)

# -------- FUNCIÓN CAMBIAR DIRECTORIO --------
# -------- PANEL CLAVES API --------
def abrir_panel_api_keys():
    ventana = ctk.CTkToplevel(app)
    ventana.title("🔑 Claves API y configuración")
    ventana.geometry("560x320")
    ventana.grab_set()
    ventana.configure(fg_color="#151d2d")

    ctk.CTkLabel(ventana, text="Claves API y configuración de acceso", font=("Inter", 16, "bold"), text_color="#f5f6fa").pack(anchor="w", padx=24, pady=(20, 4))
    ctk.CTkLabel(ventana, text="Las claves se guardan localmente en tu perfil y nunca se envían a terceros.", font=("Inter", 11), text_color="#95a5a6").pack(anchor="w", padx=24, pady=(0, 14))

    # NVIDIA API Key
    nvidia_frame = ctk.CTkFrame(ventana, fg_color="#1c2537", corner_radius=12)
    nvidia_frame.pack(fill="x", padx=24, pady=(0, 10))
    ctk.CTkLabel(nvidia_frame, text="NVIDIA API Key:", font=("Inter", 12, "bold"), text_color="#b2bec3", width=160, anchor="w").pack(side="left", padx=(16, 8), pady=12)
    
    nvidia_key_var = tk.StringVar(value=SETTINGS.get("api_key", os.environ.get("NVIDIA_API_KEY", "")))
    nvidia_entry = ctk.CTkEntry(nvidia_frame, textvariable=nvidia_key_var, show="●", font=("Inter", 12), fg_color="#121826", border_color="#2f3640", height=36)
    nvidia_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=12)

    mostrar_var = tk.BooleanVar(value=False)
    def _toggle_show():
        nvidia_entry.configure(show="" if mostrar_var.get() else "●")
    ctk.CTkCheckBox(nvidia_frame, text="Mostrar", variable=mostrar_var, command=_toggle_show, font=("Inter", 11), width=80).pack(side="right", padx=(0, 12))

    botones = ctk.CTkFrame(ventana, fg_color="transparent")
    botones.pack(fill="x", padx=24, pady=16)

    def guardar():
        api_key = nvidia_key_var.get().strip()
        SETTINGS["api_key"] = api_key
        if api_key:
            os.environ["NVIDIA_API_KEY"] = api_key
        save_settings(SETTINGS)
        ventana.destroy()

    ctk.CTkButton(botones, text="Cancelar", width=110, height=38, command=ventana.destroy, fg_color="#2f3640", hover_color="#3d4d6b", corner_radius=12).pack(side="right", padx=(8, 0))
    ctk.CTkButton(botones, text="Guardar", width=110, height=38, command=guardar, fg_color="#2980b9", hover_color="#3498db", corner_radius=12).pack(side="right")


# -------- FUNCIÓN CAMBIAR DIRECTORIO --------
def cambiar_directorio():

    ventana = ctk.CTkToplevel(app)
    ventana.title("Cambiar workspace")
    ventana.geometry("560x220")
    ventana.minsize(520, 220)
    ventana.transient(app)
    ventana.grab_set()
    ventana.configure(fg_color="#151d2d")

    ctk.CTkLabel(
        ventana,
        text="Selecciona la carpeta de trabajo",
        font=("Inter", 16, "bold"),
        text_color="#f5f6fa"
    ).pack(anchor="w", padx=24, pady=(20, 6))

    ctk.CTkLabel(
        ventana,
        text="Elige una carpeta existente para usarla como workspace del agente.",
        font=("Inter", 11),
        text_color="#95a5a6"
    ).pack(anchor="w", padx=24, pady=(0, 14))

    ruta_var = tk.StringVar(value=get_directorio_base())
    frame_ruta = ctk.CTkFrame(ventana, fg_color="#1c2537", corner_radius=14)
    frame_ruta.pack(fill="x", padx=24, pady=(0, 12))

    entrada_ruta = ctk.CTkEntry(
        frame_ruta,
        textvariable=ruta_var,
        fg_color="#121826",
        border_color="#2f3640",
        text_color="#f5f6fa",
        font=("Inter", 12),
        height=38,
    )
    entrada_ruta.pack(side="left", fill="x", expand=True, padx=(10, 8), pady=10)

    def seleccionar_ruta():
        ruta = show_folder_picker(ventana, initialdir=ruta_var.get() or get_directorio_base())
        if ruta:
            ruta_var.set(ruta)

    ctk.CTkButton(
        frame_ruta,
        text="Explorar",
        width=90,
        height=38,
        command=seleccionar_ruta,
        fg_color="#2f3640",
        hover_color="#3d4d6b",
        corner_radius=12,
    ).pack(side="right", padx=(0, 10), pady=10)

    botones = ctk.CTkFrame(ventana, fg_color="transparent")
    botones.pack(fill="x", padx=24, pady=(8, 20))

    def confirmar():
        ruta = ruta_var.get().strip()
        if not ruta or not os.path.isdir(ruta):
            messagebox.showerror("Ruta inválida", "La ruta seleccionada no es una carpeta válida.")
            return
        set_directorio_base(ruta)
        nombre_carpeta = os.path.basename(ruta)
        titulo_archivos.configure(text=nombre_carpeta)
        ruta_workspace.configure(text=ruta)
        actualizar_arbol_archivos(forzar=True)
        save_ui_state()
        ventana.destroy()

    ctk.CTkButton(
        botones,
        text="Cancelar",
        width=110,
        height=38,
        command=ventana.destroy,
        fg_color="#2f3640",
        hover_color="#3d4d6b",
        corner_radius=12,
    ).pack(side="right", padx=(8, 0))

    ctk.CTkButton(
        botones,
        text="Aceptar",
        width=110,
        height=38,
        command=confirmar,
        fg_color="#2980b9",
        hover_color="#3498db",
        corner_radius=12,
    ).pack(side="right")

    ventana.bind("<Return>", lambda _event: confirmar())
    ventana.bind("<Escape>", lambda _event: ventana.destroy())

# -------- MENÚ CONTEXTUAL CUSTOMTKINTER --------
class MenuContextualCustom(ctk.CTkToplevel):
    def __init__(self, parent, x, y, opciones):
        super().__init__(parent)
        self.overrideredirect(True)
        self.geometry(f"+{x+5}+{y+5}")
        self.attributes("-topmost", True)
        
        self.frame = ctk.CTkFrame(self, fg_color="#2f3640", corner_radius=8, border_width=1, border_color="#353b48")
        self.frame.pack(fill="both", expand=True)
        
        for texto, comando in opciones:
            if texto == "-":
                ctk.CTkFrame(self.frame, height=1, fg_color="#4b4b4b").pack(fill="x", padx=10, pady=2)
            else:
                btn = ctk.CTkButton(
                    self.frame, text=texto, anchor="w", fg_color="transparent",
                    hover_color="#3498db", text_color="white", font=("Arial", 13),
                    command=lambda c=comando: self._ejecutar_y_cerrar(c)
                )
                btn.pack(fill="x", padx=2, pady=2)
                
        self.bind("<Escape>", lambda e: self._cerrar_limpio())
        self.after(100, self._activar_cierre_global)

    def _activar_cierre_global(self):
        self._bind_id_1 = app.bind_all("<Button-1>", self._cerrar_si_fuera, add="+")
        self._bind_id_3 = app.bind_all("<Button-3>", self._cerrar_si_fuera, add="+")

    def _cerrar_si_fuera(self, event):
        if event.widget.winfo_toplevel() != self:
            self._cerrar_limpio()
            
    def _cerrar_limpio(self):
        try:
            app.unbind_all("<Button-1>")
            app.unbind_all("<Button-3>")
        except:
            pass
        self.destroy()

    def _ejecutar_y_cerrar(self, comando):
        self._cerrar_limpio()
        if comando:
            comando()

# -------- MENÚS CONTEXTUALES --------
def mostrar_menu_raiz(event):
    base = get_directorio_base()
    opciones = [
        ("📄 Nuevo archivo", lambda: _nuevo_archivo_en(base)),
        ("📁 Nueva carpeta", lambda: _nueva_carpeta_en(base))
    ]
    MenuContextualCustom(app, event.x_root, event.y_root, opciones)

frame_lista_archivos.bind("<Button-3>", mostrar_menu_raiz)
try:
    sidebar._parent_canvas.bind("<Button-3>", mostrar_menu_raiz)
except:
    sidebar.bind("<Button-3>", mostrar_menu_raiz)

def mostrar_menu_archivo(event, ruta_absoluta, nombre):
    opciones = [
        ("👁️ Previsualizar", lambda: _preview(ruta_absoluta, nombre)),
        ("✏️ Editar", lambda: abrir_editor(ruta_absoluta, nombre)),
        ("-", None),
        ("📝 Renombrar", lambda: _renombrar_archivo(ruta_absoluta, nombre)),
        ("🗑️ Eliminar", lambda: _eliminar_archivo(ruta_absoluta, nombre))
    ]
    MenuContextualCustom(app, event.x_root, event.y_root, opciones)

def mostrar_menu_carpeta(event, ruta_absoluta, nombre):
    opciones = [
        ("📄 Nuevo archivo", lambda: _nuevo_archivo_en(ruta_absoluta)),
        ("📁 Nueva carpeta", lambda: _nueva_carpeta_en(ruta_absoluta)),
        ("-", None),
        ("📝 Renombrar", lambda: _renombrar_archivo(ruta_absoluta, nombre)),
        ("🗑️ Eliminar carpeta", lambda: _eliminar_carpeta(ruta_absoluta, nombre))
    ]
    MenuContextualCustom(app, event.x_root, event.y_root, opciones)

# -------- FUNCIONES DE ARCHIVOS --------
def _preview(ruta, nombre):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
        chat.insert("end", f"👁️ Previsualizando: {nombre}\n\n{contenido}\n\n")
        chat.see("end")
    except Exception as e:
        chat.insert("end", f"⚠️ Error: {e}\n\n")
        chat.see("end")

def _pedir_texto(titulo, mensaje):
    dialogo = ctk.CTkInputDialog(text=mensaje, title=titulo)
    return dialogo.get_input()

def _confirmar_accion(titulo, mensaje):
    resultado = [False]
    evento = threading.Event()
    
    def mostrar_dialogo():
        ventana = ctk.CTkToplevel(app)
        ventana.title(titulo)
        ventana.geometry("400x200")
        ventana.grab_set()
        
        ctk.CTkLabel(ventana, text=mensaje, font=("Arial", 14), wraplength=350).pack(pady=30)
        
        botones_frame = ctk.CTkFrame(ventana, fg_color="transparent")
        botones_frame.pack(fill="x", pady=10)
        
        def al_aceptar():
            resultado[0] = True
            ventana.destroy()
            evento.set()
            
        def al_rechazar():
            resultado[0] = False
            ventana.destroy()
            evento.set()
            
        ctk.CTkButton(botones_frame, text="✅ Sí", fg_color="#c0392b", hover_color="#e74c3c", command=al_aceptar, width=100).pack(side="left", expand=True, padx=10)
        ctk.CTkButton(botones_frame, text="❌ No", fg_color="#7f8c8d", hover_color="#95a5a6", command=al_rechazar, width=100).pack(side="right", expand=True, padx=10)
        
        ventana.protocol("WM_DELETE_WINDOW", al_rechazar)

    app.after(0, mostrar_dialogo)
    evento.wait()
    return resultado[0]

def _mostrar_error(mensaje):
    app.after(0, lambda: chat.insert("end", f"⚠️ Error: {mensaje}\n\n"))
    app.after(0, lambda: chat.see("end"))

def _renombrar_archivo(ruta_absoluta, nombre_actual):
    nuevo_nombre = _pedir_texto("Renombrar", f"Nuevo nombre para:\n'{nombre_actual}'")
    if nuevo_nombre and nuevo_nombre != nombre_actual:
        nueva_ruta = os.path.join(os.path.dirname(ruta_absoluta), nuevo_nombre)
        try:
            os.rename(ruta_absoluta, nueva_ruta)
            actualizar_arbol_archivos(forzar=True)
        except Exception as e:
            _mostrar_error(f"No se pudo renombrar: {e}")

def _eliminar_archivo(ruta_absoluta, nombre):
    def proceso_eliminar():
        if _confirmar_accion("Confirmar eliminación", f"¿Estás seguro de que quieres eliminar:\n\n'{nombre}'?"):
            try:
                os.remove(ruta_absoluta)
                app.after(0, lambda: actualizar_arbol_archivos(forzar=True))
            except Exception as e:
                _mostrar_error(f"No se pudo eliminar: {e}")
    threading.Thread(target=proceso_eliminar, daemon=True).start()

def _eliminar_carpeta(ruta_absoluta, nombre):
    def proceso_eliminar():
        if _confirmar_accion("Confirmar eliminación", f"¿Eliminar la carpeta '{nombre}' y TODO su contenido?\n\n⚠️ Esta acción no se puede deshacer."):
            try:
                shutil.rmtree(ruta_absoluta)
                app.after(0, lambda: actualizar_arbol_archivos(forzar=True))
            except Exception as e:
                _mostrar_error(f"No se pudo eliminar: {e}")
    threading.Thread(target=proceso_eliminar, daemon=True).start()

def _nuevo_archivo_en(ruta_carpeta):
    nombre = _pedir_texto("Nuevo archivo", "Nombre del nuevo archivo (ej: app.py):")
    if nombre:
        ruta = os.path.join(ruta_carpeta, nombre)
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("")
            actualizar_arbol_archivos(forzar=True)
        except Exception as e:
            _mostrar_error(f"No se pudo crear: {e}")

def _nueva_carpeta_en(ruta_carpeta):
    nombre = _pedir_texto("Nueva carpeta", "Nombre de la nueva carpeta:")
    if nombre:
        ruta = os.path.join(ruta_carpeta, nombre)
        try:
            os.makedirs(ruta, exist_ok=True)
            actualizar_arbol_archivos(forzar=True)
        except Exception as e:
            _mostrar_error(f"No se pudo crear: {e}")

# -------- PANEL DERECHO: CHAT IA --------
right_pane = ctk.CTkFrame(main_frame, width=420, fg_color="#1a1d2e", corner_radius=16)
right_pane.pack(side="right", fill="y", padx=(8, 16), pady=16)
right_pane.pack_propagate(False)

# -------- PANEL CENTRAL: EDITOR Y TERMINAL --------
middle_pane = ctk.CTkFrame(main_frame, fg_color="transparent")
middle_pane.pack(side="left", fill="both", expand=True, padx=10, pady=20)

# Pestañas del Editor
editor_tabs = ctk.CTkTabview(middle_pane)
editor_tabs.pack(fill="both", expand=True, pady=(0, 10))

# Consola de Terminal Integrada
terminal_frame = ctk.CTkFrame(middle_pane, height=200, corner_radius=10)
terminal_frame.pack(fill="x", side="bottom")
terminal_frame.pack_propagate(False)

terminal_label = ctk.CTkLabel(terminal_frame, text="💻 Consola de Salida", font=("Arial", 12, "bold"), text_color="#7f8c8d")
terminal_label.pack(anchor="w", padx=10, pady=(5, 0))

terminal_salida = ctk.CTkTextbox(terminal_frame, font=("Consolas", 12), fg_color="#1e272e", text_color="#bdc3c7", wrap="word")
terminal_salida.pack(fill="both", expand=True, padx=10, pady=(5, 10))
terminal_salida.configure(state="disabled")

def escribir_terminal(texto):
    terminal_salida.configure(state="normal")
    terminal_salida.insert("end", texto + "\n")
    terminal_salida.see("end")
    terminal_salida.configure(state="disabled")

# Diccionario para trackear editores abiertos {ruta_absoluta: caja_de_texto}
editores_abiertos = {}

def aplicar_sintaxis(caja, texto, filename=""):
    caja.delete("0.0", "end")
    caja.insert("0.0", texto)

    if len(texto) > 100000:
        return

    try:
        import pygments
        from pygments.lexers import guess_lexer_for_filename, TextLexer
        from pygments.token import Token
    except ImportError:
        return

    try:
        lexer = guess_lexer_for_filename(filename, texto)
    except Exception:
        lexer = TextLexer()

    color_map = {
        Token.Keyword: "#ff79c6",
        Token.Name.Class: "#50fa7b",
        Token.Name.Function: "#50fa7b",
        Token.Name.Builtin: "#8be9fd",
        Token.Name.Decorator: "#50fa7b",
        Token.String: "#f1fa8c",
        Token.Number: "#bd93f9",
        Token.Comment: "#6272a4",
        Token.Operator: "#ff79c6",
    }

    for token, color in color_map.items():
        caja.tag_config(str(token), foreground=color)

    caja.mark_set("range_start", "1.0")
    for token, content in pygments.lex(texto, lexer):
        color_token = token
        while color_token not in color_map and color_token.parent:
            color_token = color_token.parent

        if color_token in color_map:
            caja.mark_set("range_end", f"range_start + {len(content)}c")
            caja.tag_add(str(color_token), "range_start", "range_end")
        
        caja.mark_set("range_start", f"range_start + {len(content)}c")

# -------- EDITOR DE CÓDIGO INTEGRADO --------
def abrir_editor(ruta_absoluta, nombre):
    if ruta_absoluta in editores_abiertos:
        editor_tabs.set(nombre)
        return

    try:
        with open(ruta_absoluta, "r", encoding="utf-8") as f:
            contenido = f.read()
    except Exception as e:
        chat.insert("end", f"⚠️ Error al leer: {e}\n\n")
        return
        
    try:
        editor_tabs.add(nombre)
    except Exception:
        pass # La pestaña ya existe o hubo un error (el nombre debe ser único en CTkTabview)
    
    editor_tabs.set(nombre)
    tab = editor_tabs.tab(nombre)
    
    editor_area = ctk.CTkFrame(tab, fg_color="transparent")
    editor_area.pack(fill="both", expand=True, padx=5, pady=5)

    line_numbers = ctk.CTkTextbox(
        editor_area, width=60, fg_color="#1e272e", text_color="#7f8c8d",
        font=("Consolas", 12), state="disabled", corner_radius=8,
        wrap="none", border_width=0
    )
    line_numbers.pack(side="left", fill="y", padx=(0, 6), pady=0)

    texto_editor = ctk.CTkTextbox(editor_area, font=("Consolas", 14), wrap="none")
    texto_editor.pack(side="left", fill="both", expand=True)

    scrollbar = ctk.CTkScrollbar(editor_area, orientation="vertical")
    scrollbar.pack(side="right", fill="y", pady=0)

    def sync_scroll(*args):
        if not args:
            return

        if args[0] == "moveto" and len(args) > 1:
            fraction = args[1]
            line_numbers.yview_moveto(fraction)
            texto_editor.yview_moveto(fraction)
            return

        if args[0] == "scroll" and len(args) > 2:
            try:
                count = int(args[1])
            except ValueError:
                return
            unit = args[2]
            line_numbers.yview_scroll(count, unit)
            texto_editor.yview_scroll(count, unit)
            return

        if len(args) == 2:
            line_numbers.yview_moveto(args[0])
            texto_editor.yview_moveto(args[0])
            scrollbar.set(args[0], args[1])
            return

    def on_editor_mousewheel(event):
        if event.num == 4 or getattr(event, 'delta', 0) > 0:
            texto_editor.yview_scroll(-1, "units")
        else:
            texto_editor.yview_scroll(1, "units")
        line_numbers.yview_moveto(texto_editor.yview()[0])
        return "break"

    texto_editor.configure(yscrollcommand=lambda *args: sync_scroll(*args))
    line_numbers.configure(yscrollcommand=lambda *args: scrollbar.set(*args))
    scrollbar.configure(command=sync_scroll)

    texto_editor.bind("<MouseWheel>", on_editor_mousewheel)
    texto_editor.bind("<Button-4>", on_editor_mousewheel)
    texto_editor.bind("<Button-5>", on_editor_mousewheel)

    def actualizar_numeros_de_linea(event=None):
        contenido_actual = texto_editor.get("0.0", "end-1c")
        line_count = max(contenido_actual.count("\n") + 1, 1)
        numeros = "\n".join(str(i) for i in range(1, line_count + 1))
        yview = line_numbers.yview()
        line_numbers.configure(state="normal")
        line_numbers.delete("0.0", "end")
        line_numbers.insert("0.0", numeros)
        line_numbers.configure(state="disabled")
        if yview:
            try:
                line_numbers.yview_moveto(yview[0])
            except Exception:
                pass

    texto_editor.bind("<KeyRelease>", actualizar_numeros_de_linea)
    texto_editor.bind("<ButtonRelease-1>", actualizar_numeros_de_linea)

    aplicar_sintaxis(texto_editor, contenido, nombre)
    actualizar_numeros_de_linea()
    editores_abiertos[ruta_absoluta] = texto_editor
    
    frame_botones = ctk.CTkFrame(tab, fg_color="transparent")
    frame_botones.pack(fill="x", pady=5)
    
    def guardar():
        nuevo_contenido = texto_editor.get("0.0", "end-1c")
        try:
            with open(ruta_absoluta, "w", encoding="utf-8") as f:
                f.write(nuevo_contenido)
            chat.insert("end", f"💾 Archivo '{nombre}' guardado correctamente.\n\n")
            chat.see("end")
            aplicar_sintaxis(texto_editor, nuevo_contenido, nombre)
            save_ui_state()
        except Exception as e:
            chat.insert("end", f"⚠️ Error al guardar: {e}\n\n")
            chat.see("end")
            
    def cerrar_pestana():
        if ruta_absoluta in editores_abiertos:
            del editores_abiertos[ruta_absoluta]
        editor_tabs.delete(nombre)
        save_ui_state()
            
    ctk.CTkButton(frame_botones, text="Guardar cambios", command=guardar, fg_color="#2980b9", hover_color="#3498db").pack(side="left", padx=10, expand=True)
    ctk.CTkButton(frame_botones, text="Cerrar pestaña", command=cerrar_pestana, fg_color="#c0392b", hover_color="#e74c3c").pack(side="right", padx=10, expand=True)

class ClickManager:
    def __init__(self, ruta, nombre):
        self.ruta = ruta
        self.nombre = nombre
        self.timer = None
        self.clicks = 0

    def click(self):
        self.clicks += 1
        if self.clicks == 1:
            self.timer = app.after(250, self.single_click)
        elif self.clicks == 2:
            if self.timer:
                app.after_cancel(self.timer)
            self.double_click()
            self.clicks = 0

    def single_click(self):
        self.clicks = 0
        try:
            with open(self.ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                chat.insert("end", f"👁️ Previsualizando: {self.nombre}\n\n{contenido}\n\n")
                chat.see("end")
        except Exception as e:
            chat.insert("end", f"⚠️ Error: {e}\n\n")
            chat.see("end")

    def double_click(self):
        abrir_editor(self.ruta, self.nombre)


def toggle_frame(frame, btn, ruta_carpeta):
    global ultima_interaccion_arbol
    ultima_interaccion_arbol = time.time()
    if frame.winfo_ismapped():
        frame.pack_forget()
        btn.configure(text=btn.cget("text").replace("📂", "📁"))
        carpetas_expandidas.discard(ruta_carpeta)
    else:
        if not getattr(frame, "loaded", False):
            construir_arbol(frame, ruta_carpeta)
            frame.loaded = True
        frame.pack(fill="x", padx=(16, 0), pady=(0, 4))
        btn.configure(text=btn.cget("text").replace("📁", "📂"))
        carpetas_expandidas.add(ruta_carpeta)

def construir_arbol(contenedor, ruta_base):
    try:
        nodos = listar_nodos_arbol(ruta_base, filtro=search_filter, max_items=200)
    except Exception:
        return 0

    total = 0
    hay_filtro = bool(search_filter)

    def renderizar_nodo(nodo, parent_widget, nivel=0):
        nonlocal total
        if nodo["type"] == "dir":
            total += 1
            ruta_c = nodo["path"]
            try:
                items = [n for n in os.listdir(ruta_c) if not n.startswith('.') and n not in ("__pycache__", "venv", "env", "node_modules")]
                n_files = sum(1 for n in items if os.path.isfile(os.path.join(ruta_c, n)))
                n_dirs = sum(1 for n in items if os.path.isdir(os.path.join(ruta_c, n)))
            except Exception:
                n_files = n_dirs = 0

            node_frame = ctk.CTkFrame(parent_widget, fg_color="transparent")
            node_frame.pack(fill="x")

            header_frame = ctk.CTkFrame(node_frame, fg_color="#141821")
            header_frame.pack(fill="x", pady=1)

            badge = ctk.CTkLabel(header_frame, text="📁", width=30, height=30, fg_color="#f1c40f", text_color="#1b1b1b", corner_radius=8, font=("Arial", 12, "bold"))
            badge.pack(side="left", padx=(6 + nivel * 10, 10), pady=3)

            display_name = f"{nodo['name']}  —  {n_dirs} dirs, {n_files} files"
            sub_frame = ctk.CTkFrame(node_frame, fg_color="transparent")
            sub_frame.loaded = False

            btn = ctk.CTkButton(header_frame, text=display_name, anchor="w", fg_color="transparent", hover_color="#232a39", text_color="#fbc531", font=("Arial", 13, "bold"), corner_radius=0)
            btn.configure(command=lambda f=sub_frame, b=btn, r=ruta_c: toggle_frame(f, b, r))
            btn.pack(side="left", fill="x", expand=True, pady=3, padx=(0, 6))

            badge.bind("<Button-3>", lambda e, r=ruta_c, n=nodo["name"]: mostrar_menu_carpeta(e, r, n))
            btn.bind("<Button-3>", lambda e, r=ruta_c, n=nodo["name"]: mostrar_menu_carpeta(e, r, n))

            if ruta_c in carpetas_expandidas:
                child_container = ctk.CTkFrame(sub_frame, fg_color="transparent")
                child_container.pack(fill="x", padx=(10 + nivel * 10, 0), pady=(0, 2))
                for child in nodo.get("children", []):
                    renderizar_nodo(child, child_container, nivel + 1)
                sub_frame.loaded = True
                sub_frame.pack(fill="x")
                badge.configure(text="📂")

        else:
            total += 1
            ruta_a = nodo["path"]
            icono, color = obtener_icono(nodo["name"])
            manager = ClickManager(ruta_a, nodo["name"])

            if hay_filtro:
                match_type = nodo.get("match_type", "name")
                snippet = nodo.get("snippet", "")
                rel = nodo.get("rel", os.path.relpath(ruta_a, ruta_base))

                card = ctk.CTkFrame(parent_widget, fg_color="#141821", corner_radius=8)
                card.pack(fill="x", pady=2, padx=2)

                top_row = ctk.CTkFrame(card, fg_color="transparent")
                top_row.pack(fill="x", padx=6, pady=(4, 0))

                badge_lbl = ctk.CTkLabel(top_row, text=icono, width=26, height=26, fg_color=color, text_color="white", corner_radius=6, font=("Arial", 11, "bold"))
                badge_lbl.pack(side="left", padx=(0, 8))

                tipo_txt = "nombre" if match_type == "name" else "contenido"
                tipo_col = "#2980b9" if match_type == "name" else "#8e44ad"
                ctk.CTkLabel(top_row, text=tipo_txt, font=("Inter", 9, "bold"), fg_color=tipo_col, text_color="white", corner_radius=4, width=60, height=18).pack(side="right", padx=(0, 4))

                btn_archivo = ctk.CTkButton(top_row, text=nodo["name"], anchor="w", fg_color="transparent", hover_color="#232a39", text_color="#dcdde1", font=("Arial", 13), corner_radius=0, command=manager.click)
                btn_archivo.pack(side="left", fill="x", expand=True)

                ctk.CTkLabel(card, text=os.path.dirname(rel) or ".", font=("Inter", 10), text_color="#636e72", anchor="w").pack(fill="x", padx=(42, 8), pady=(0, 2))

                if snippet:
                    ctk.CTkLabel(card, text=f"  {snippet}", font=("Consolas", 11), text_color="#95a5a6", anchor="w", wraplength=270).pack(fill="x", padx=(42, 8), pady=(0, 4))

                for w in (badge_lbl, btn_archivo, card):
                    w.bind("<Button-3>", lambda e, r=ruta_a, n=nodo["name"]: mostrar_menu_archivo(e, r, n))
            else:
                item_frame = ctk.CTkFrame(parent_widget, fg_color="#141821")
                item_frame.pack(fill="x", pady=1)

                badge_lbl = ctk.CTkLabel(item_frame, text=icono, width=30, height=30, fg_color=color, text_color="white", corner_radius=8, font=("Arial", 12, "bold"))
                badge_lbl.pack(side="left", padx=(6 + nivel * 10, 10), pady=3)

                btn_archivo = ctk.CTkButton(item_frame, text=nodo["name"], anchor="w", fg_color="transparent", hover_color="#232a39", text_color="#dcdde1", font=("Arial", 13), corner_radius=0, command=manager.click)
                btn_archivo.pack(side="left", fill="x", expand=True, pady=3, padx=(0, 6))

                badge_lbl.bind("<Button-1>", lambda e, m=manager: m.click())
                badge_lbl.bind("<Button-3>", lambda e, r=ruta_a, n=nodo["name"]: mostrar_menu_archivo(e, r, n))
                btn_archivo.bind("<Button-3>", lambda e, r=ruta_a, n=nodo["name"]: mostrar_menu_archivo(e, r, n))

    for nodo in nodos:
        renderizar_nodo(nodo, contenedor)

    return total

def _get_tree_hash(base):
    """Genera una representación rápida del estado actual del directorio."""
    resultado = []
    if not os.path.exists(base):
        return ""

    for ruta, carpetas, ficheros in os.walk(base):
        rel_dir = os.path.relpath(ruta, base)
        if rel_dir == ".":
            rel_dir = ""
        carpetas[:] = sorted([c for c in carpetas if not c.startswith(".") and c not in ("__pycache__", "venv", "env", "node_modules")])
        ficheros = sorted([f for f in ficheros if not f.startswith(".")])

        for c in carpetas:
            ruta_rel = os.path.join(rel_dir, c) if rel_dir else c
            resultado.append(f"D:{ruta_rel}")

        for f in ficheros:
            ruta_rel = os.path.join(rel_dir, f) if rel_dir else f
            try:
                stat = os.stat(os.path.join(ruta, f))
                resultado.append(f"F:{ruta_rel}:{stat.st_size}:{int(stat.st_mtime)}")
            except Exception:
                resultado.append(f"F:{ruta_rel}:error")

    return "\n".join(resultado)

_ultimo_tree_hash = ""

def actualizar_arbol_archivos(forzar=False):
    global _ultimo_tree_hash
    
    if not forzar and time.time() - ultima_interaccion_arbol < 0.5:
        return
    
    base = get_directorio_base()
    
    # Calcular hash del estado actual del árbol
    nuevo_hash = _get_tree_hash(base)
    
    # Si no cambió nada, no reconstruir (evita el salto visual)
    if not forzar and nuevo_hash == _ultimo_tree_hash:
        return
    _ultimo_tree_hash = nuevo_hash
    
    # Guardar posición de scroll actual
    try:
        scroll_pos = sidebar._parent_canvas.yview()[0]
    except:
        scroll_pos = 0.0
    
    widgets_antiguos = list(tree_content.winfo_children())
    
    if not os.path.exists(base) or not os.listdir(base):
        ctk.CTkLabel(tree_content, text="Directorio vacío", text_color="gray").pack(pady=18)
        count_label.configure(text="0 elementos")
    else:
        total = construir_arbol(tree_content, base)
        if total == 0:
            ctk.CTkLabel(tree_content, text="No hay coincidencias.", text_color="gray").pack(pady=18)
        count_label.configure(text=f"{total} elementos")
    
    for w in widgets_antiguos:
        w.destroy()
    
    # Restaurar posición de scroll
    app.update_idletasks()
    try:
        sidebar._parent_canvas.yview_moveto(scroll_pos)
    except:
        pass


# El contenido principal ahora usa top_controls y zona que deben empaquetarse en right_pane
# -------- CABECERA DEL PANEL DERECHO --------
agente_header = ctk.CTkFrame(right_pane, fg_color="#22253a", corner_radius=12)
agente_header.pack(fill="x", padx=12, pady=(12, 0))

agente_avatar = ctk.CTkLabel(agente_header, text="🤖", font=("Arial", 28))
agente_avatar.pack(side="left", padx=(14, 6), pady=10)

agente_info = ctk.CTkFrame(agente_header, fg_color="transparent")
agente_info.pack(side="left", fill="y", pady=8)
ctk.CTkLabel(agente_info, text="Agente AI", font=("Inter", 15, "bold"), text_color="#e8eaf6").pack(anchor="w")
lbl_estado = ctk.CTkLabel(agente_info, text="● Activo", font=("Inter", 11), text_color="#2ecc71")
lbl_estado.pack(anchor="w")

# Ajustes y limpiar en la cabecera
botones_header = ctk.CTkFrame(agente_header, fg_color="transparent")
botones_header.pack(side="right", padx=10)

# -------- EDITOR DE SYSTEM PROMPT --------
ROLES_PREDEFINIDOS = {
    "Ninguno": "",
    "Experto Python": "Eres un experto en Python. Escribe código limpio, idiomático y bien documentado. Usa type hints y sigue PEP 8.",
    "Arquitecto de Software": "Eres un arquitecto de software senior. Propones diseños escalables, aplicas SOLID y piensas en el largo plazo antes de escribir código.",
    "Frontend Dev": "Eres un experto frontend especializado en HTML, CSS, JavaScript y React. Creas UIs modernas, accesibles y responsive.",
    "DevOps": "Eres un experto en DevOps. Dominas Docker, CI/CD, Kubernetes y automatización. Priorizas la seguridad y la infraestructura como código.",
    "Revisor de Código": "Actúa como revisor de código senior. Detecta bugs, vulnerabilidades de seguridad, código muerto y sugiere mejoras con explicaciones claras.",
    "Asistente Conciso": "Responde siempre de forma ultra concisa. Sin explicaciones largas. Código directo y funcional.",
}

def abrir_editor_prompt():
    ventana = ctk.CTkToplevel(app)
    ventana.title("⚙️ System Prompt del Agente")
    ventana.geometry("600x520")
    ventana.grab_set()
    ventana.configure(fg_color="#151d2d")

    ctk.CTkLabel(ventana, text="Configura el rol y comportamiento del agente", font=("Inter", 16, "bold"), text_color="#f5f6fa").pack(anchor="w", padx=24, pady=(20, 4))
    ctk.CTkLabel(ventana, text="Las instrucciones se aplican en todas las conversaciones de esta sesión.", font=("Inter", 11), text_color="#95a5a6").pack(anchor="w", padx=24, pady=(0, 12))

    # Selector de roles predefinidos
    roles_frame = ctk.CTkFrame(ventana, fg_color="#1c2537", corner_radius=12)
    roles_frame.pack(fill="x", padx=24, pady=(0, 12))
    ctk.CTkLabel(roles_frame, text="Rol predefinido:", font=("Inter", 12, "bold"), text_color="#b2bec3").pack(side="left", padx=(16, 8), pady=12)
    rol_var = tk.StringVar(value="Ninguno")
    rol_menu = ctk.CTkOptionMenu(roles_frame, values=list(ROLES_PREDEFINIDOS.keys()), variable=rol_var, width=200, height=32, font=("Inter", 12))
    rol_menu.pack(side="left", pady=12)

    # Textbox del prompt
    ctk.CTkLabel(ventana, text="Instrucciones personalizadas:", font=("Inter", 12, "bold"), text_color="#b2bec3").pack(anchor="w", padx=24)
    caja = ctk.CTkTextbox(ventana, font=("Inter", 13), wrap="word", fg_color="#121826", border_color="#2f3640", border_width=1, corner_radius=12)
    caja.pack(fill="both", expand=True, padx=24, pady=(6, 0))
    caja.insert("0.0", SETTINGS.get("system_prompt", ""))

    def _aplicar_rol(*_):
        rol = rol_var.get()
        texto = ROLES_PREDEFINIDOS.get(rol, "")
        if texto:
            caja.delete("0.0", "end")
            caja.insert("0.0", texto)
    rol_var.trace_add("write", _aplicar_rol)

    botones = ctk.CTkFrame(ventana, fg_color="transparent")
    botones.pack(fill="x", padx=24, pady=12)

    def guardar():
        prompt = caja.get("0.0", "end-1c").strip()
        SETTINGS["system_prompt"] = prompt
        save_settings(SETTINGS)
        set_instrucciones(prompt)
        ventana.destroy()

    ctk.CTkButton(botones, text="Cancelar", width=110, height=38, command=ventana.destroy, fg_color="#2f3640", hover_color="#3d4d6b", corner_radius=12).pack(side="right", padx=(8, 0))
    ctk.CTkButton(botones, text="Guardar", width=110, height=38, command=guardar, fg_color="#2980b9", hover_color="#3498db", corner_radius=12).pack(side="right")

def abrir_ajustes():
    ventana = ctk.CTkToplevel(app)
    ventana.title("⚙️ Ajustes del agente")
    ventana.geometry("560x480")
    ventana.grab_set()

    ctk.CTkLabel(ventana, text="Instrucciones extra (System Prompt):", font=("Arial", 14, "bold")).pack(pady=(10, 4))

    from agente import instrucciones_extra
    caja = ctk.CTkTextbox(ventana, font=("Arial", 14), wrap="word")
    caja.pack(fill="both", expand=True, padx=20, pady=(0, 10))
    caja.insert("0.0", instrucciones_extra)

    ctk.CTkLabel(ventana, text="Modelo por defecto:", font=("Arial", 12, "bold")).pack(anchor="w", padx=20)
    selector_ajustes = ctk.CTkOptionMenu(ventana, values=MODELOS_GRATIS, width=260)
    selector_ajustes.pack(anchor="w", padx=20, pady=(4, 8))
    selector_ajustes.set(SETTINGS.get("model", MODELOS_GRATIS[0]))

    safe_var = tk.BooleanVar(value=SETTINGS.get("safe_mode", True))
    ctk.CTkCheckBox(ventana, text="Modo seguro visible activo", variable=safe_var).pack(anchor="w", padx=20, pady=(0, 6))

    def guardar_ajustes():
        set_instrucciones(caja.get("0.0", "end-1c"))
        SETTINGS["model"] = selector_ajustes.get()
        SETTINGS["safe_mode"] = bool(safe_var.get())
        save_settings(SETTINGS)
        selector_modelo.set(SETTINGS["model"])
        ventana.destroy()

    ctk.CTkButton(ventana, text="Guardar ajustes", command=guardar_ajustes).pack(pady=10)

btn_ajustes = ctk.CTkButton(
    botones_header, text="⚙️", width=34, height=34,
    fg_color="#2f3655", hover_color="#3d4775",
    corner_radius=8, font=("Arial", 14), command=abrir_ajustes
)
btn_ajustes.pack(side="left", padx=(0, 6))

# Botón editor de system prompt
btn_prompt = ctk.CTkButton(
    botones_header, text="📝", width=34, height=34,
    fg_color="#2f3655", hover_color="#3d4775",
    corner_radius=8, font=("Arial", 14), command=abrir_editor_prompt
)
btn_prompt.pack(side="left", padx=(0, 6))

# Botón exportar conversación
def exportar_conversacion():
    from ui.folder_picker import show_file_picker
    nombre_default = f"chat_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    ventana_exp = ctk.CTkToplevel(app)
    ventana_exp.title("Exportar conversación")
    ventana_exp.geometry("480x180")
    ventana_exp.grab_set()
    ventana_exp.configure(fg_color="#151d2d")

    ctk.CTkLabel(ventana_exp, text="Exportar conversación a Markdown", font=("Inter", 15, "bold"), text_color="#f5f6fa").pack(anchor="w", padx=24, pady=(20, 4))

    nombre_var = tk.StringVar(value=nombre_default)
    frame_n = ctk.CTkFrame(ventana_exp, fg_color="#1c2537", corner_radius=12)
    frame_n.pack(fill="x", padx=24, pady=(8, 0))
    ctk.CTkLabel(frame_n, text="Nombre:", width=70, anchor="w", font=("Inter", 12)).pack(side="left", padx=(12, 6), pady=10)
    ctk.CTkEntry(frame_n, textvariable=nombre_var, font=("Inter", 12), fg_color="#121826", border_color="#2f3640").pack(side="left", fill="x", expand=True, padx=(0, 12), pady=10)

    def _hacer_export():
        nombre = nombre_var.get().strip()
        if not nombre:
            return
        if not nombre.endswith(".md"):
            nombre += ".md"
        ruta_dest = os.path.join(get_directorio_base(), nombre)
        contenido_chat = chat.get("1.0", "end-1c")
        try:
            with open(ruta_dest, "w", encoding="utf-8") as f:
                f.write(f"# Conversación - {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
                f.write(contenido_chat)
            chat.insert("end", f"\n\n📤 Conversación exportada como '{nombre}'\n\n")
            chat.see("end")
            actualizar_arbol_archivos(forzar=True)
            ventana_exp.destroy()
        except Exception as e:
            chat.insert("end", f"⚠️ Error al exportar: {e}\n\n")
            ventana_exp.destroy()

    botones_exp = ctk.CTkFrame(ventana_exp, fg_color="transparent")
    botones_exp.pack(fill="x", padx=24, pady=12)
    ctk.CTkButton(botones_exp, text="Cancelar", width=100, command=ventana_exp.destroy, fg_color="#2f3640", hover_color="#3d4d6b", corner_radius=10).pack(side="right", padx=(8, 0))
    ctk.CTkButton(botones_exp, text="📤 Exportar", width=120, command=_hacer_export, fg_color="#2980b9", hover_color="#3498db", corner_radius=10).pack(side="right")

btn_export = ctk.CTkButton(
    botones_header, text="📤", width=34, height=34,
    fg_color="#2f3655", hover_color="#3d4775",
    corner_radius=8, font=("Arial", 14), command=exportar_conversacion
)
btn_export.pack(side="left", padx=(0, 6))

# -------- PANEL DE TAREAS Y TRAZABILIDAD --------
tasks_frame = ctk.CTkFrame(right_pane, fg_color="#22253a", corner_radius=10)
tasks_frame.pack(fill="x", padx=12, pady=(8, 0))

ctk.CTkLabel(tasks_frame, text="🧭 Tareas y trazabilidad", font=("Inter", 12, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
tasks_box = ctk.CTkTextbox(tasks_frame, height=120, font=("Inter", 12), wrap="word")
tasks_box.pack(fill="x", padx=10, pady=(0, 8))
tasks_box.configure(state="disabled")


def actualizar_panel_tareas():
    tasks_box.configure(state="normal")
    tasks_box.delete("0.0", "end")
    tareas = load_tasks()
    if not tareas:
        tasks_box.insert("end", "No hay tareas registradas aún.\n")
    else:
        for item in reversed(tareas[-8:]):
            tasks_box.insert("end", f"[{item.get('estado','completado')}] {item.get('detalle','')}\n")
    tasks_box.configure(state="disabled")

# -------- CHAT --------
chat = ctk.CTkTextbox(
    right_pane, corner_radius=12,
    font=("Inter", 15), wrap="word",
    fg_color="#12141f",
    text_color="#cdd6f4",
    scrollbar_button_color="#2f3655",
    scrollbar_button_hover_color="#3d4775"
)
chat.pack(pady=(8, 0), fill="both", expand=True, padx=12)

# Configurar tags de sintaxis
chat.tag_config("code", foreground="#78e08f")
chat.tag_config("thought", foreground="#7f8c8d")
chat.tag_config("normal", foreground="white")

# -------- ENTRADA --------
zona = ctk.CTkFrame(right_pane, fg_color="#22253a", corner_radius=12)
zona.pack(fill="x", padx=12, pady=(8, 12))

from modelos import MODELOS_GRATIS
modelos = MODELOS_GRATIS
selected_model_var = tk.StringVar(value=SETTINGS.get("model", modelos[0]))
_modelo_popup = None

class ModeloPopup(ctk.CTkToplevel):
    def __init__(self, parent, opciones, on_select, x, y):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.on_select = on_select
        self.parent = parent

        ancho = 240
        alto_max = 260
        alto = min(alto_max, 12 + len(opciones) * 28 + 12)
        alto = max(alto, 110)

        pantalla_alto = parent.winfo_screenheight()
        if y + alto > pantalla_alto - 20:
            y = max(10, y - alto - 8)

        self.geometry(f"{ancho}x{alto}+{x}+{y}")

        self.frame = ctk.CTkFrame(self, fg_color="#171b2d", corner_radius=8, border_width=1, border_color="#2f3655")
        self.frame.pack(fill="both", expand=True, padx=1, pady=1)

        self.canvas = tk.Canvas(self.frame, bg="#171b2d", highlightthickness=0, height=alto - 12)
        self.canvas.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)

        self.scrollbar = ctk.CTkScrollbar(self.frame, orientation="vertical", command=self.canvas.yview, height=alto - 12)
        self.scrollbar.pack(side="right", fill="y", padx=(0, 6), pady=6)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.inner = ctk.CTkFrame(self.canvas, fg_color="transparent")
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        for opcion in opciones:
            btn = ctk.CTkButton(
                self.inner,
                text=opcion,
                fg_color="transparent",
                hover_color="#24304e",
                text_color="#f1f5f9",
                anchor="w",
                corner_radius=6,
                height=24,
                border_width=0,
                font=("Inter", 12),
                command=lambda m=opcion: self._seleccionar(m)
            )
            btn.pack(fill="x", padx=4, pady=2)

        self.inner.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.parent.bind_all("<Button-1>", self._cerrar_si_fuera, add="+")
        self.parent.bind_all("<Escape>", lambda e: self._cerrar())
        self.focus_force()

    def _seleccionar(self, modelo):
        self.on_select(modelo)
        self._cerrar()

    def _cerrar_si_fuera(self, event):
        if event.widget.winfo_toplevel() != self:
            self._cerrar()

    def _cerrar(self):
        try:
            self.parent.unbind_all("<Button-1>")
        except Exception:
            pass
        self.destroy()


def actualizar_selector_modelo():
    selector_modelo.configure(text=f"{selected_model_var.get()}  ▼")


def seleccionar_modelo(modelo):
    selected_model_var.set(modelo)
    SETTINGS["model"] = modelo
    save_settings(SETTINGS)
    actualizar_selector_modelo()


def abrir_selector_modelo(event=None):
    global _modelo_popup
    if _modelo_popup is not None:
        _modelo_popup._cerrar()
        _modelo_popup = None
        return

    x = selector_modelo.winfo_rootx()
    y = selector_modelo.winfo_rooty() + selector_modelo.winfo_height()
    _modelo_popup = ModeloPopup(app, modelos, seleccionar_modelo, x, y)


# Fila selector + cancelar
fila_top = ctk.CTkFrame(zona, fg_color="transparent")
fila_top.pack(fill="x", padx=8, pady=(8, 4))

selector_modelo = ctk.CTkButton(
    fila_top,
    text=f"{selected_model_var.get()}  ▼",
    width=230,
    height=32,
    fg_color="#2f3655",
    hover_color="#3d4775",
    corner_radius=8,
    font=("Inter", 12),
    command=abrir_selector_modelo
)
selector_modelo.pack(side="left")


def btn_cancelar_accion():
    global cancelar_generacion
    cancelar_generacion = True

btn_cancelar = ctk.CTkButton(
    fila_top, text="⏹ Parar", width=90, height=32,
    fg_color="#3d1f2a", hover_color="#6b2737",
    corner_radius=8, font=("Inter", 12),
    command=btn_cancelar_accion
)
btn_cancelar.pack(side="right")

# Fila entrada + enviar
fila_input = ctk.CTkFrame(zona, fg_color="transparent")
fila_input.pack(fill="x", padx=8, pady=(0, 8))

entrada = ctk.CTkEntry(
    fila_input, placeholder_text="Escribe una orden al agente...",
    height=40, font=("Inter", 14),
    fg_color="#1a1d2e", border_color="#2f3655",
    border_width=1, corner_radius=8
)
entrada.pack(side="left", fill="x", expand=True, padx=(0, 8))

sugerencias_frame = ctk.CTkFrame(zona, fg_color="transparent")
sugerencias_frame.pack(fill="x", padx=8, pady=(0, 8))
sugerencias_label = ctk.CTkLabel(sugerencias_frame, text="", font=("Inter", 11), text_color="#7f8c8d")
sugerencias_label.pack(anchor="w")

sugerencias_panel = ctk.CTkFrame(
    zona,
    fg_color="#161a2b",
    border_width=1,
    border_color="#2f3655",
    corner_radius=8,
)
sugerencias_panel.pack(fill="x", padx=8, pady=(0, 8))
sugerencias_panel.pack_forget()

sugerencias_actuales = []
sugerencia_index = 0
modo_sugerencia = False
sugerencias_botones = []

boton = ctk.CTkButton(
    fila_input, text="↑ Enviar", width=90, height=40,
    fg_color="#3d4775", hover_color="#5468a8",
    corner_radius=8, font=("Inter", 13, "bold"),
    command=lambda: responder()
)
boton.pack(side="right")

_imagen_adjunta = None

image_card = ctk.CTkFrame(zona, fg_color="#191f2f", corner_radius=20, border_width=1, border_color="#2f3640")

img_header = ctk.CTkFrame(image_card, fg_color="transparent")
img_header.pack(fill="x", padx=16, pady=(12, 4))

ctk.CTkLabel(img_header, text="IMAGEN ADJUNTA", font=("Inter", 11, "bold"), text_color="#7f8fa6").pack(side="left")
ctk.CTkLabel(img_header, text="●", font=("Inter", 12, "bold"), text_color="#3498db").pack(side="right")

img_filename_label = ctk.CTkLabel(image_card, text="", font=("Inter", 14, "bold"), text_color="#f5f6fa")
img_filename_label.pack(anchor="w", padx=16)

def quitar_imagen():
    global _imagen_adjunta
    _imagen_adjunta = None
    image_card.pack_forget()

btn_quitar_img = ctk.CTkButton(image_card, text="Quitar", fg_color="#c0392b", hover_color="#e74c3c", width=80, height=28, command=quitar_imagen)
btn_quitar_img.pack(anchor="w", padx=16, pady=(8, 12))

def seleccionar_imagen():
    global _imagen_adjunta
    import base64
    import os
    from ui.folder_picker import show_file_picker
    ruta = show_file_picker(app, initialdir=get_directorio_base(), filetypes=["*.png", "*.jpg", "*.jpeg", "*.gif"])
    if ruta:
        try:
            with open(ruta, "rb") as img_file:
                _imagen_adjunta = base64.b64encode(img_file.read()).decode("utf-8")
            img_filename_label.configure(text=os.path.basename(ruta))
            image_card.pack(fill="x", padx=8, pady=(0, 8), before=fila_input)
        except Exception as e:
            print("Error cargando imagen", e)

btn_imagen = ctk.CTkButton(
    fila_input, text="📎", width=40, height=40,
    fg_color="#3d4775", hover_color="#5468a8",
    corner_radius=8, font=("Inter", 13, "bold"),
    command=seleccionar_imagen
)
btn_imagen.pack(side="right", padx=(0, 8))

def escribir(texto, end="\n\n", tags=None):
    if tags:
        chat.insert("end", texto + end, tags)
    else:
        chat.insert("end", texto + end)
    chat.see("end")


def obtener_sugerencias(texto: str):
    base_dir = get_directorio_base()
    if not os.path.isdir(base_dir):
        return []

    texto = texto.strip()
    if not texto:
        return []

    if texto.startswith("@"):
        termino = texto[1:].strip().lower()
    else:
        termino = texto.lower()

    if not termino:
        return []

    candidatos = []
    for path in os.walk(base_dir):
        root, dirs, files = path
        for name in files + dirs:
            if name.startswith('.'):
                continue
            rel = os.path.relpath(os.path.join(root, name), base_dir)
            rel_lower = rel.lower()
            if rel_lower.startswith(termino) or rel_lower.endswith(termino) or termino in rel_lower:
                candidatos.append(rel)
    candidatos = sorted(set(candidatos))
    if len(candidatos) > 8:
        candidatos = candidatos[:8]
    return candidatos


def mostrar_sugerencias(event=None):
    global sugerencias_actuales, sugerencia_index, modo_sugerencia

    if event is not None and event.keysym in {"Up", "Down", "Tab", "Return", "Escape"}:
        return

    texto = entrada.get().strip()
    if not texto.startswith("@"):
        sugerencias_actuales = []
        sugerencia_index = 0
        modo_sugerencia = False
        actualizar_panel_sugerencias()
        return

    sugerencias_actuales = obtener_sugerencias(texto)
    sugerencia_index = 0
    modo_sugerencia = bool(sugerencias_actuales)
    actualizar_panel_sugerencias()


def actualizar_panel_sugerencias():
    global sugerencias_actuales, sugerencia_index, modo_sugerencia

    if not modo_sugerencia or not sugerencias_actuales:
        for boton in sugerencias_botones:
            boton.pack_forget()
        sugerencias_panel.pack_forget()
        sugerencias_label.configure(text="")
        return

    sugerencias_panel.pack(fill="x", padx=8, pady=(0, 8))
    sugerencias_label.configure(text="Usa ↑↓ para moverte y Tab para aceptar")

    while len(sugerencias_botones) < len(sugerencias_actuales):
        boton = ctk.CTkButton(
            sugerencias_panel,
            text="",
            anchor="w",
            fg_color="#1f2438",
            hover_color="#2f3655",
            text_color="white",
            height=28,
            corner_radius=6,
            command=None,
        )
        boton.pack(fill="x", padx=6, pady=2)
        sugerencias_botones.append(boton)

    while len(sugerencias_botones) > len(sugerencias_actuales):
        boton = sugerencias_botones.pop()
        boton.destroy()

    for idx, boton in enumerate(sugerencias_botones):
        sugerencia = sugerencias_actuales[idx]
        boton.configure(
            text=sugerencia,
            fg_color="#3d4775" if idx == sugerencia_index else "#1f2438",
            command=lambda i=idx: seleccionar_sugerencia(i),
        )
        boton.pack(fill="x", padx=6, pady=2)


def seleccionar_sugerencia(index):
    global sugerencia_index
    if not sugerencias_actuales:
        return
    sugerencia_index = max(0, min(index, len(sugerencias_actuales) - 1))
    actualizar_panel_sugerencias()


def mover_sugerencia(delta):
    global sugerencias_actuales, sugerencia_index, modo_sugerencia
    texto_actual = entrada.get().strip()
    if not modo_sugerencia or not sugerencias_actuales or not texto_actual.startswith("@"):
        return "break"

    sugerencia_index = (sugerencia_index + delta) % len(sugerencias_actuales)
    actualizar_panel_sugerencias()
    return "break"


def aceptar_sugerencia(event=None):
    global sugerencias_actuales, sugerencia_index, modo_sugerencia
    texto_actual = entrada.get().strip()
    if not modo_sugerencia or not sugerencias_actuales or not texto_actual.startswith("@"):
        return "break"

    if sugerencia_index >= len(sugerencias_actuales):
        sugerencia_index = 0

    sugerencia = sugerencias_actuales[sugerencia_index]
    entrada.delete(0, "end")
    entrada.insert(0, f"@{sugerencia}")
    modo_sugerencia = False
    sugerencias_actuales = []
    sugerencia_index = 0
    actualizar_panel_sugerencias()
    return "break"

def check_cancel():
    global cancelar_generacion
    return cancelar_generacion




def parse_and_insert(texto, start_index):
    # Borrar el texto actual del asistente para re-insertarlo con formato
    chat.delete(start_index, "end")
    
    # Simple state machine para formatear en tiempo real
    en_codigo = False
    en_pensamiento = False
    buffer = ""
    
    i = 0
    while i < len(texto):
        if not en_codigo and not en_pensamiento:
            if texto[i:].startswith("```"):
                chat.insert("end", buffer, "normal")
                buffer = ""
                en_codigo = True
                i += 3
                continue
            elif texto[i:].startswith("<pensar>"):
                chat.insert("end", buffer, "normal")
                buffer = "🤔 "
                en_pensamiento = True
                i += 8
                continue
        elif en_codigo:
            if texto[i:].startswith("```"):
                chat.insert("end", buffer, "code")
                buffer = ""
                en_codigo = False
                i += 3
                continue
        elif en_pensamiento:
            if texto[i:].startswith("</pensar>"):
                chat.insert("end", buffer, "thought")
                buffer = ""
                en_pensamiento = False
                i += 9
                continue
        
        buffer += texto[i]
        i += 1
        
    # Insert remaining buffer
    tag = "normal"
    if en_codigo: tag = "code"
    elif en_pensamiento: tag = "thought"
    chat.insert("end", buffer, tag)
    chat.see("end")


def responder(auto_mensaje=None):
    global cancelar_generacion, auto_corregido, _imagen_adjunta
    cancelar_generacion = False

    if auto_mensaje:
        mensaje = auto_mensaje
    else:
        mensaje = entrada.get()
        auto_corregido = False
        
    if _imagen_adjunta and mensaje:
        mensaje_original = mensaje
        mensaje = [
            {"type": "text", "text": mensaje_original},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_imagen_adjunta}"}}
        ]
        _imagen_adjunta = None
        image_card.pack_forget()

    if mensaje == "":
        return

    mensaje_texto = mensaje if isinstance(mensaje, str) else mensaje[0]['text']
    modo_programacion = "plan" in mensaje_texto.lower() or "pasos" in mensaje_texto.lower() or "modo programación" in mensaje_texto.lower()
    if modo_programacion:
        if isinstance(mensaje, str): mensaje = f"Actúa como agente de programación. Divide esta solicitud en pasos claros y explícitos. Solicitud: {mensaje}"
        append_task("plan", f"Planificando: {mensaje[:80]}")

    entrada.delete(0, "end")
    append_conversation({"role": "user", "content": mensaje})
    _chat_messages_cache.append({"role": "user", "content": mensaje})

    mensaje_texto = mensaje if isinstance(mensaje, str) else mensaje[0]["text"]
    if not auto_mensaje:
        escribir("👤 Tú:\n" + mensaje_texto + (" [🖼️ Imagen adjunta]" if not isinstance(mensaje, str) else ""))
    else:
        escribir(f"🤖 Ejecución automática:\n{mensaje_texto}")
        
    escribir("🤖 Agente: ⏳ Iniciando modelo (puede tardar unos segundos)...\n", end="")
    chat.mark_set("inicio_respuesta", "end-1c")
    chat.mark_gravity("inicio_respuesta", "left")
    idx_inicio_respuesta = "inicio_respuesta"

    modelo_seleccionado = selected_model_var.get()
    
    def confirmacion_ui_segura(nombre, codigo):
        resultado = [False]
        evento = threading.Event()
        
        def mostrar_dialogo():
            es_parche = nombre.startswith("PARCHE a ")
            ventana = ctk.CTkToplevel(app)
            ventana.title(f"⚠️ {'Revisar parche' if es_parche else 'Confirmar sobreescritura'}: {nombre}")
            ventana.geometry("680x460")
            ventana.grab_set()
            ventana.configure(fg_color="#151d2d")
            
            titulo_txt = f"Parche para: {nombre.replace('PARCHE a ', '')}" if es_parche else f"Modificar archivo existente: {nombre}"
            ctk.CTkLabel(ventana, text=titulo_txt, font=("Inter", 13, "bold"), text_color="#f5f6fa", wraplength=600).pack(pady=(14, 4), padx=20)

            if es_parche:
                ctk.CTkLabel(ventana, text="🟢 verde = añadido  |  🔴 rojo = eliminado", font=("Inter", 11), text_color="#7f8fa6").pack(pady=(0, 6))
            
            caja = ctk.CTkTextbox(ventana, font=("Consolas", 13), wrap="none", fg_color="#0d1117", border_color="#2f3640", border_width=1, corner_radius=10)
            caja.pack(fill="both", expand=True, padx=20, pady=4)
            caja.tag_config("add", foreground="#2ecc71")
            caja.tag_config("del", foreground="#e74c3c")
            caja.tag_config("ctx", foreground="#b2bec3")

            for linea in codigo.splitlines(keepends=True):
                if linea.startswith("+"):
                    caja.insert("end", linea, "add")
                elif linea.startswith("-"):
                    caja.insert("end", linea, "del")
                else:
                    caja.insert("end", linea, "ctx")
            caja.configure(state="disabled")
            
            botones_frame = ctk.CTkFrame(ventana, fg_color="transparent")
            botones_frame.pack(fill="x", pady=10)
            
            def al_aceptar():
                resultado[0] = True
                ventana.destroy()
                evento.set()
                
            def al_rechazar():
                resultado[0] = False
                ventana.destroy()
                evento.set()
                
            ctk.CTkButton(botones_frame, text="✅ Aceptar cambios", fg_color="#27ae60", hover_color="#2ecc71", height=38, corner_radius=10, command=al_aceptar).pack(side="left", expand=True, padx=10)
            ctk.CTkButton(botones_frame, text="❌ Rechazar", fg_color="#c0392b", hover_color="#e74c3c", height=38, corner_radius=10, command=al_rechazar).pack(side="right", expand=True, padx=10)
            
            ventana.protocol("WM_DELETE_WINDOW", al_rechazar)

        app.after(0, mostrar_dialogo)
        evento.wait()
        return resultado[0]

    threading.Thread(
        target=trabajo_ia,
        args=(mensaje, modelo_seleccionado, idx_inicio_respuesta, confirmacion_ui_segura, modo_programacion),
        daemon=True
    ).start()

def extract_steps(texto):
    pasos = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        match = re.match(r'^(?:\d+[\.)]|[-*•])\s*(.+)$', linea)
        if match:
            pasos.append(match.group(1).strip())
            continue
        if linea.lower().startswith("paso "):
            pasos.append(linea)
            continue
    return pasos


def trabajo_ia(mensaje, modelo, idx_inicio, confirmacion_ui_segura, modo_programacion=False):
    global auto_corregido
    
    texto_acumulado = ""
    def _print_to_terminal(msg):
        app.after(0, lambda: escribir_terminal(msg))
        
    try:
        generador = pensar(mensaje, modelo, check_cancel, confirmacion_ui_segura, _print_to_terminal)
        
        for fragmento, terminado, comando_output in generador:
            if not terminado:
                texto_acumulado += fragmento
                app.after(0, lambda t=texto_acumulado: parse_and_insert(t, idx_inicio))
            else:
                app.after(0, lambda: chat.insert("end", "\n\n"))
                app.after(0, actualizar_arbol_archivos)
                app.after(0, actualizar_panel_tareas)
                append_conversation({"role": "assistant", "content": texto_acumulado})
                _chat_messages_cache.append({"role": "assistant", "content": texto_acumulado})
                append_task("respuesta", f"Respuesta procesada para: {mensaje[:80]}")
                if modo_programacion:
                    pasos = extract_steps(texto_acumulado)
                    if pasos:
                        for idx, paso in enumerate(pasos, start=1):
                            append_task("plan_step", f"Paso {idx}: {paso}", estado="pendiente")
                    else:
                        append_task("plan_step", "No se pudieron extraer pasos del resultado.", estado="pendiente")
                    append_task("programacion", "Se activó el modo agente de programación")
                
                app.after(0, actualizar_panel_tareas)
                
                comando_info = comando_output if comando_output else (None, False)
                output_texto, auto_reply = comando_info
                
                if output_texto:
                    if not auto_corregido:
                        auto_corregido = True
                        if auto_reply:
                            app.after(0, lambda o=output_texto: responder(auto_mensaje=o))
                        else:
                            app.after(0, lambda o=output_texto: escribir(f"🤖 Ejecución automática (silenciosa):\n{o}"))
                    else:
                        app.after(0, lambda o=output_texto: escribir(f"⚠️ Se ha ejecutado el comando pero se ha alcanzado el límite de auto-corrección automática.\n{o}"))
                        
    except Exception as e:
        import traceback
        err_details = traceback.format_exc()
        try:
            with open(os.path.join(get_directorio_base(), "_error_log.txt"), "a", encoding="utf-8") as f:
                f.write(f"\n--- ERROR ---\nModelo: {modelo}\nError: {err_details}\n")
        except: pass
        app.after(0, lambda err=str(e), details=err_details: escribir(f"\n[Error de conexión o API: {err}]\n{details}"))

entrada.bind("<Return>", lambda e: responder())
entrada.bind("<KeyRelease>", lambda e: mostrar_sugerencias(e))
entrada.bind("<Tab>", aceptar_sugerencia)
entrada.bind("<KeyPress-Up>", lambda e: mover_sugerencia(-1))
entrada.bind("<KeyPress-Down>", lambda e: mover_sugerencia(1))
entrada.bind("<Up>", lambda e: mover_sugerencia(-1))
entrada.bind("<Down>", lambda e: mover_sugerencia(1))
entrada.focus()

# -------- HISTORIAL DE CONVERSACIONES --------
def cargar_historial_ui():
    historial = load_conversations()
    if not historial:
        return
    for item in historial[-12:]:
        rol = item.get("role", "assistant")
        contenido = item.get("content", "")
        if rol == "user":
            escribir(f"👤 Tú:\n{contenido}")
        else:
            escribir(f"🤖 Agente:\n{contenido}")


def mostrar_estado_carga_arbol():
    if hasattr(tree_content, "winfo_children"):
        for w in tree_content.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            tree_content,
            text="Cargando árbol de archivos...",
            text_color="gray",
            font=("Arial", 12)
        ).pack(pady=12)


def iniciar_carga_inicial():
    cargar_estado_ui()
    cargar_historial_ui()
    actualizar_panel_tareas()
    mostrar_estado_carga_arbol()
    app.after(300, lambda: actualizar_arbol_archivos(forzar=True))
    app.after(2000, vigilar_archivos)

# -------- VIGILANTE DE ARCHIVOS (Auto-Sync cada 2s) --------
def vigilar_archivos():
    try:
        actualizar_arbol_archivos()
    except Exception:
        pass
    app.after(2000, vigilar_archivos)

app.after_idle(iniciar_carga_inicial)

# -------- KEYBINDINGS GLOBALES --------
def _kb_enviar(e=None):
    responder()
    return "break"

def _kb_limpiar(e=None):
    chat.configure(state="normal")
    chat.delete("1.0", "end")
    return "break"

def _kb_foco_entrada(e=None):
    entrada.focus_set()
    return "break"

def _kb_prompt(e=None):
    abrir_editor_prompt()
    return "break"

def _kb_guardar_editor(e=None):
    try:
        tab_actual = editor_tabs.get()
        for ruta, caja in editores_abiertos.items():
            if os.path.basename(ruta) == tab_actual:
                nuevo = caja.get("0.0", "end-1c")
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(nuevo)
                chat.insert("end", f"💾 '{tab_actual}' guardado.\n\n")
                chat.see("end")
                break
    except Exception:
        pass
    return "break"

def _kb_cerrar_tab(e=None):
    try:
        tab_actual = editor_tabs.get()
        for ruta in list(editores_abiertos.keys()):
            if os.path.basename(ruta) == tab_actual:
                del editores_abiertos[ruta]
                editor_tabs.delete(tab_actual)
                break
    except Exception:
        pass
    return "break"

app.bind_all("<Control-Return>", _kb_enviar)
app.bind_all("<Control-l>", _kb_limpiar)
app.bind_all("<Control-L>", _kb_limpiar)
app.bind_all("<Control-e>", _kb_foco_entrada)
app.bind_all("<Control-E>", _kb_foco_entrada)
app.bind_all("<Control-k>", _kb_prompt)
app.bind_all("<Control-K>", _kb_prompt)
app.bind_all("<Control-s>", _kb_guardar_editor)
app.bind_all("<Control-S>", _kb_guardar_editor)
app.bind_all("<Control-w>", _kb_cerrar_tab)
app.bind_all("<Control-W>", _kb_cerrar_tab)

# -------- CARGAR API KEY Y SYSTEM PROMPT GUARDADOS --------
_saved_key = SETTINGS.get("api_key", "")
if _saved_key:
    os.environ.setdefault("NVIDIA_API_KEY", _saved_key)

_saved_prompt = SETTINGS.get("system_prompt", "")
if _saved_prompt:
    set_instrucciones(_saved_prompt)

app.mainloop()