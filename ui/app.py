import customtkinter as ctk
import threading
import os
import re
import shutil
import tkinter as tk

from tkinter import filedialog, simpledialog, messagebox
from agente import pensar, limpiar_memoria, get_memoria_size, set_instrucciones
from herramientas import listar_archivos, set_directorio_base, get_directorio_base, escribir_archivo
from iconos import obtener_icono
from core.state import (
    append_conversation,
    append_task,
    clear_history,
    clear_tasks,
    load_conversations,
    load_settings,
    load_tasks,
    save_settings,
)

# Snapshot del árbol de archivos para detectar cambios
_ultimo_snapshot = set()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

SETTINGS = load_settings()


def save_ui_state():
    SETTINGS["open_files"] = list(editores_abiertos.keys())
    SETTINGS["workdir"] = get_directorio_base()
    SETTINGS["model"] = selector_modelo.get() if "selector_modelo" in globals() else SETTINGS.get("model")
    save_settings(SETTINGS)


def cargar_estado_ui():
    workdir = SETTINGS.get("workdir", "")
    if workdir and os.path.isdir(workdir):
        set_directorio_base(workdir)
        titulo_archivos.configure(text=os.path.basename(workdir))

    for ruta in SETTINGS.get("open_files", []):
        if os.path.isfile(ruta):
            abrir_editor(ruta, os.path.basename(ruta))


app = ctk.CTk()
app.title("Artraxer AI Agent Premium")
app.geometry("1200x750")

app.protocol("WM_DELETE_WINDOW", lambda: (save_ui_state(), app.destroy()))

cancelar_generacion = False
auto_corregido = False
# -------- ESTRUCTURA PRINCIPAL --------
main_frame = ctk.CTkFrame(app, fg_color="transparent")
main_frame.pack(fill="both", expand=True)

# -------- PANEL IZQUIERDO: BARRA LATERAL --------
sidebar = ctk.CTkScrollableFrame(
    main_frame, 
    width=260, 
    corner_radius=15,
    scrollbar_button_color="#2f3640",
    scrollbar_button_hover_color="#718093"
)
sidebar.pack(side="left", fill="y", padx=(20, 0), pady=20)

# Cabecera Lateral
header_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
header_frame.pack(fill="x", pady=(0, 10))

btn_directorio = ctk.CTkButton(
    header_frame, 
    text="📂 Cambiar Workspace", 
    command=lambda: cambiar_directorio(), 
    fg_color="#27ae60", 
    hover_color="#2ecc71",
    height=30
)
btn_directorio.pack(pady=(10, 10), fill="x")

titulo_archivos = ctk.CTkLabel(
    header_frame, 
    text=os.path.basename(get_directorio_base()), 
    font=("Arial", 16, "bold"),
    text_color="#fbc531"
)
titulo_archivos.pack(pady=(0, 5))

# Separador
separador = ctk.CTkFrame(sidebar, height=2, fg_color="#353b48")
separador.pack(fill="x", pady=(0, 10))

frame_lista_archivos = ctk.CTkFrame(sidebar, fg_color="transparent")
frame_lista_archivos.pack(fill="both", expand=True)

# Estado de carpetas expandidas (persistente entre recargas del árbol)
carpetas_expandidas = set()

# -------- FUNCIÓN CAMBIAR DIRECTORIO --------
def cambiar_directorio():
    ruta = filedialog.askdirectory(title="Seleccionar carpeta de trabajo")
    if ruta:
        set_directorio_base(ruta)
        nombre_carpeta = os.path.basename(ruta)
        titulo_archivos.configure(text=nombre_carpeta)
        actualizar_arbol_archivos(forzar=True)
        save_ui_state()

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

def aplicar_sintaxis(caja, texto):
    # Un resaltador de sintaxis de Python extremadamente básico
    caja.tag_config("keyword", foreground="#ff79c6") # Rosa
    caja.tag_config("string", foreground="#f1fa8c")  # Amarillo
    caja.tag_config("comment", foreground="#6272a4") # Gris azulado
    caja.tag_config("number", foreground="#bd93f9")  # Morado
    caja.tag_config("def_class", foreground="#50fa7b") # Verde
    
    # Aplicar regex básico (requeriría un loop complejo, para simplificar lo hacemos en pasadas)
    caja.delete("0.0", "end")
    caja.insert("0.0", texto)
    
    keywords = ["and", "as", "assert", "break", "class", "continue", "def", "del", "elif", "else", "except", "False", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "None", "nonlocal", "not", "or", "pass", "raise", "return", "True", "try", "while", "with", "yield"]
    
    # Implementación ultra básica para no bloquear la UI:
    # No coloreamos en tiempo real completo, solo lo básico.
    for kw in keywords:
        start = "1.0"
        while True:
            pos = caja.search(r"\b" + kw + r"\b", start, stopindex="end", regexp=True)
            if not pos: break
            length = len(kw)
            end = f"{pos}+{length}c"
            caja.tag_add("keyword", pos, end)
            start = end

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
        line_numbers.yview_moveto(args[0])
        texto_editor.yview_moveto(args[0])
        scrollbar.set(*args)

    texto_editor.configure(yscrollcommand=lambda *args: sync_scroll(*args))
    line_numbers.configure(yscrollcommand=lambda *args: sync_scroll(*args))
    scrollbar.configure(command=sync_scroll)

    def actualizar_numeros_de_linea(event=None):
        contenido_actual = texto_editor.get("0.0", "end-1c")
        line_count = max(contenido_actual.count("\n") + 1, 1)
        numeros = "\n".join(str(i) for i in range(1, line_count + 1))
        line_numbers.configure(state="normal")
        line_numbers.delete("0.0", "end")
        line_numbers.insert("0.0", numeros)
        line_numbers.configure(state="disabled")

    texto_editor.bind("<KeyRelease>", actualizar_numeros_de_linea)
    texto_editor.bind("<MouseWheel>", actualizar_numeros_de_linea)
    texto_editor.bind("<ButtonRelease-1>", actualizar_numeros_de_linea)

    aplicar_sintaxis(texto_editor, contenido)
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
            aplicar_sintaxis(texto_editor, nuevo_contenido)
            save_ui_state()
        except Exception as e:
            chat.insert("end", f"⚠️ Error al guardar: {e}\n\n")
            chat.see("end")
            
    def cerrar_pestana():
        if ruta_absoluta in editores_abiertos:
            del editores_abiertos[ruta_absoluta]
        editor_tabs.delete(nombre)
        save_ui_state()
            
    ctk.CTkButton(frame_botones, text="Guardar Cambios", command=guardar, fg_color="#2980b9", hover_color="#3498db").pack(side="left", padx=10, expand=True)
    ctk.CTkButton(frame_botones, text="Cerrar Pestaña", command=cerrar_pestana, fg_color="#c0392b", hover_color="#e74c3c").pack(side="right", padx=10, expand=True)

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
    if frame.winfo_ismapped():
        frame.pack_forget()
        btn.configure(text=btn.cget("text").replace("📂", "📁"))
        carpetas_expandidas.discard(ruta_carpeta)
    else:
        frame.pack(fill="x", padx=(0, 0), pady=0)
        btn.configure(text=btn.cget("text").replace("📁", "📂"))
        carpetas_expandidas.add(ruta_carpeta)

def construir_arbol(contenedor, ruta_base):
    try:
        elementos = os.listdir(ruta_base)
    except:
        return
        
    elementos.sort()
    carpetas = [e for e in elementos if os.path.isdir(os.path.join(ruta_base, e))]
    archivos = [e for e in elementos if os.path.isfile(os.path.join(ruta_base, e))]
    
    for c in carpetas:
        if c.startswith("."): continue
        ruta_c = os.path.join(ruta_base, c)
        
        node_frame = ctk.CTkFrame(contenedor, fg_color="transparent")
        node_frame.pack(fill="x")
        
        btn = ctk.CTkButton(
            node_frame, text=f"📁 {c}", anchor="w", fg_color="transparent", 
            hover_color="#2f3640", text_color="#fbc531", font=("Arial", 14, "bold")
        )
        btn.pack(fill="x", pady=1)
        
        # Clic derecho en carpeta
        btn.bind("<Button-3>", lambda e, r=ruta_c, n=c: mostrar_menu_carpeta(e, r, n))
        
        sub_frame_wrapper = ctk.CTkFrame(node_frame, fg_color="transparent")
        borde_izq = ctk.CTkFrame(sub_frame_wrapper, width=2, fg_color="#353b48")
        borde_izq.pack(side="left", fill="y", padx=(12, 10))
        sub_frame = ctk.CTkFrame(sub_frame_wrapper, fg_color="transparent")
        sub_frame.pack(side="left", fill="both", expand=True)
        
        btn.configure(command=lambda f=sub_frame_wrapper, b=btn, r=ruta_c: toggle_frame(f, b, r))
        construir_arbol(sub_frame, ruta_c)
        
        # Si la carpeta estaba expandida antes de la recarga, abrirla
        if ruta_c in carpetas_expandidas:
            sub_frame_wrapper.pack(fill="x", padx=(0, 0), pady=0)
            btn.configure(text=f"📂 {c}")

    for a in archivos:
        if a.startswith("."): continue
        icono, color = obtener_icono(a)
        ruta_a = os.path.join(ruta_base, a)
        
        manager = ClickManager(ruta_a, a)
        btn_archivo = ctk.CTkButton(
            contenedor, text=f"{icono} {a}", anchor="w", fg_color="transparent",
            hover_color="#2f3640", text_color=color, font=("Arial", 13),
            command=manager.click
        )
        btn_archivo.pack(fill="x", pady=1)
        
        # Clic derecho en archivo
        btn_archivo.bind("<Button-3>", lambda e, r=ruta_a, n=a: mostrar_menu_archivo(e, r, n))

def _get_tree_hash(base):
    """Genera una representación rápida del estado actual del directorio."""
    resultado = []
    if not os.path.exists(base):
        return ""
    for ruta, carpetas, ficheros in os.walk(base):
        carpetas[:] = sorted([c for c in carpetas if not c.startswith(".")])
        for c in carpetas:
            resultado.append(f"D:{os.path.join(ruta, c)}")
        for f in sorted(ficheros):
            if not f.startswith("."):
                ruta_f = os.path.join(ruta, f)
                try:
                    mtime = os.path.getmtime(ruta_f)
                except:
                    mtime = 0
                resultado.append(f"F:{ruta_f}:{mtime}")
    return "\n".join(resultado)

_ultimo_tree_hash = ""

def actualizar_arbol_archivos(forzar=False):
    global _ultimo_tree_hash
    
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
    
    # Estrategia Anti-Parpadeo: Añadir los nuevos al final y luego borrar los viejos de arriba
    widgets_antiguos = list(frame_lista_archivos.winfo_children())
    
    if not os.path.exists(base) or not os.listdir(base):
        ctk.CTkLabel(frame_lista_archivos, text="Directorio vacío", text_color="gray").pack()
    else:
        construir_arbol(frame_lista_archivos, base)
        
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

# Ajustes
def abrir_ajustes():
    ventana = ctk.CTkToplevel(app)
    ventana.title("⚙️ Ajustes del agente")
    ventana.geometry("560x480")
    ventana.grab_set()

    ctk.CTkLabel(ventana, text="Instrucciones Extra (System Prompt):", font=("Arial", 14, "bold")).pack(pady=(10, 4))

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

    ctk.CTkButton(ventana, text="Guardar Ajustes", command=guardar_ajustes).pack(pady=10)

btn_ajustes = ctk.CTkButton(
    botones_header, text="⚙️", width=34, height=34,
    fg_color="#2f3655", hover_color="#3d4775",
    corner_radius=8, font=("Arial", 14), command=abrir_ajustes
)
btn_ajustes.pack(side="left", padx=(0, 6))

btn_limpiar_icono = ctk.CTkButton(
    botones_header, text="🗑️", width=34, height=34,
    fg_color="#3d1f2a", hover_color="#6b2737",
    corner_radius=8, font=("Arial", 14), command=lambda: limpiar_memoria_ui()
)
btn_limpiar_icono.pack(side="left")

# -------- BARRA DE MEMORIA --------
mem_bar_frame = ctk.CTkFrame(right_pane, fg_color="#22253a", corner_radius=10)
mem_bar_frame.pack(fill="x", padx=12, pady=(6, 0))

mem_row = ctk.CTkFrame(mem_bar_frame, fg_color="transparent")
mem_row.pack(fill="x", padx=10, pady=(6, 2))
ctk.CTkLabel(mem_row, text="Memoria del contexto:", font=("Inter", 11), text_color="#8892b0").pack(side="left")
lbl_tokens = ctk.CTkLabel(mem_row, text="0 / 8000 tokens", font=("Inter", 10), text_color="#636b8c")
lbl_tokens.pack(side="right")

barra_memoria = ctk.CTkProgressBar(mem_bar_frame, height=6, corner_radius=3)
barra_memoria.pack(fill="x", padx=10, pady=(0, 8))
barra_memoria.set(0)

def actualizar_medidor_memoria():
    tokens = get_memoria_size()
    max_tokens = 8000
    progreso = min(tokens / max_tokens, 1.0)
    barra_memoria.set(progreso)
    lbl_tokens.configure(text=f"{tokens} / {max_tokens} tokens")
    
    if progreso > 0.8:
        barra_memoria.configure(progress_color="#e74c3c")
    elif progreso > 0.5:
        barra_memoria.configure(progress_color="#f1c40f")
    else:
        barra_memoria.configure(progress_color="#2ecc71")

def limpiar_memoria_ui():
    limpiar_memoria()
    chat.delete("0.0", "end")
    actualizar_medidor_memoria()
    escribir("🧠 Memoria borrada. Nuevo chat iniciado.\n")

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

# Fila selector + cancelar
fila_top = ctk.CTkFrame(zona, fg_color="transparent")
fila_top.pack(fill="x", padx=8, pady=(8, 4))

selector_modelo = ctk.CTkOptionMenu(
    fila_top, values=modelos, width=230, height=32,
    font=("Inter", 12),
    fg_color="#2f3655", button_color="#3d4775", button_hover_color="#4a5590",
    dropdown_fg_color="#22253a", dropdown_hover_color="#2f3655"
)
selector_modelo.pack(side="left")
selector_modelo.set(SETTINGS.get("model", modelos[0]))

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
    global cancelar_generacion, auto_corregido
    cancelar_generacion = False

    if auto_mensaje:
        mensaje = auto_mensaje
    else:
        mensaje = entrada.get()
        auto_corregido = False

    if mensaje == "":
        return

    modo_programacion = "plan" in mensaje.lower() or "pasos" in mensaje.lower() or "modo programación" in mensaje.lower()
    if modo_programacion:
        mensaje = f"Actúa como agente de programación. Divide esta solicitud en pasos claros y explícitos. Solicitud: {mensaje}"
        append_task("plan", f"Planificando: {mensaje[:80]}")

    entrada.delete(0, "end")
    append_conversation({"role": "user", "content": mensaje})

    if not auto_mensaje:
        escribir("👤 Tú:\n" + mensaje)
    else:
        escribir(f"🤖 Ejecución automática:\n{mensaje}")
        
    escribir("🤖 Agente: ⏳ Iniciando modelo (puede tardar unos segundos)...\n", end="")
    chat.mark_set("inicio_respuesta", "end-1c")
    chat.mark_gravity("inicio_respuesta", "left")
    idx_inicio_respuesta = "inicio_respuesta"

    modelo_seleccionado = selector_modelo.get()
    
    def confirmacion_ui_segura(nombre, codigo):
        resultado = [False]
        evento = threading.Event()
        
        def mostrar_dialogo():
            ventana = ctk.CTkToplevel(app)
            ventana.title(f"⚠️ Confirmar sobreescritura: {nombre}")
            ventana.geometry("600x400")
            ventana.grab_set()
            
            ctk.CTkLabel(ventana, text=f"El agente quiere modificar el archivo existente:\n{nombre}", font=("Arial", 14, "bold")).pack(pady=10)
            
            # Textbox con el código propuesto
            caja = ctk.CTkTextbox(ventana, font=("Consolas", 14), wrap="none")
            caja.pack(fill="both", expand=True, padx=20, pady=10)
            caja.insert("0.0", codigo)
            caja.configure(state="disabled") # Solo lectura
            
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
                
            ctk.CTkButton(botones_frame, text="✅ Aceptar cambios", fg_color="#27ae60", hover_color="#2ecc71", command=al_aceptar).pack(side="left", expand=True, padx=10)
            ctk.CTkButton(botones_frame, text="❌ Rechazar", fg_color="#c0392b", hover_color="#e74c3c", command=al_rechazar).pack(side="right", expand=True, padx=10)
            
            # Por si el usuario cierra la ventana con la X
            ventana.protocol("WM_DELETE_WINDOW", al_rechazar)

        app.after(0, mostrar_dialogo)
        evento.wait() # Bloquea el hilo de la IA hasta que el usuario responda
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
                app.after(0, actualizar_medidor_memoria)
                app.after(0, actualizar_panel_tareas)
                append_conversation({"role": "assistant", "content": texto_acumulado})
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

cargar_estado_ui()
cargar_historial_ui()
actualizar_panel_tareas()

# -------- VIGILANTE DE ARCHIVOS (Auto-Sync cada 2s) --------
def vigilar_archivos():
    try:
        actualizar_arbol_archivos()
    except Exception:
        pass
    app.after(2000, vigilar_archivos)

actualizar_arbol_archivos(forzar=True)
actualizar_medidor_memoria()
app.after(2000, vigilar_archivos)
app.mainloop()