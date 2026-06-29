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

# Snapshot del árbol de archivos para detectar cambios
_ultimo_snapshot = set()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Artraxer AI Agent Premium")
app.geometry("1200x750")

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

# -------- PANEL DERECHO: CHAT IA --------
right_pane = ctk.CTkFrame(main_frame, width=400, fg_color="transparent")
right_pane.pack(side="right", fill="y", padx=(10, 20), pady=20)
right_pane.pack_propagate(False) # Evitar que se encoja automáticamente

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
    
    # Texto
    texto_editor = ctk.CTkTextbox(tab, font=("Consolas", 14), wrap="none")
    texto_editor.pack(fill="both", expand=True, padx=5, pady=5)
    
    aplicar_sintaxis(texto_editor, contenido)
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
        except Exception as e:
            chat.insert("end", f"⚠️ Error al guardar: {e}\n\n")
            
    def cerrar_pestana():
        del editores_abiertos[ruta_absoluta]
        editor_tabs.delete(nombre)
            
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
# -------- CONTROLES SUPERIORES --------
top_controls = ctk.CTkFrame(right_pane, fg_color="transparent")
top_controls.pack(fill="x", pady=(0, 5))

# Ajustes
def abrir_ajustes():
    ventana = ctk.CTkToplevel(app)
    ventana.title("⚙️ Ajustes del agente")
    ventana.geometry("500x400")
    ventana.grab_set()
    
    ctk.CTkLabel(ventana, text="Instrucciones Extra (System Prompt):", font=("Arial", 14, "bold")).pack(pady=10)
    
    from agente import instrucciones_extra
    caja = ctk.CTkTextbox(ventana, font=("Arial", 14), wrap="word")
    caja.pack(fill="both", expand=True, padx=20, pady=10)
    caja.insert("0.0", instrucciones_extra)
    
    def guardar_ajustes():
        set_instrucciones(caja.get("0.0", "end-1c"))
        ventana.destroy()
        
    ctk.CTkButton(ventana, text="Guardar Ajustes", command=guardar_ajustes).pack(pady=10)

btn_ajustes = ctk.CTkButton(top_controls, text="⚙️", width=40, height=30, fg_color="#34495e", hover_color="#2c3e50", command=abrir_ajustes)
btn_ajustes.pack(side="left", padx=(0, 10))

# Medidor de Memoria
frame_memoria = ctk.CTkFrame(top_controls, fg_color="transparent")
frame_memoria.pack(side="left", fill="x", expand=True)
ctk.CTkLabel(frame_memoria, text="Memoria:", font=("Arial", 12)).pack(side="left", padx=5)
barra_memoria = ctk.CTkProgressBar(frame_memoria, width=200, height=10)
barra_memoria.pack(side="left", padx=5)
barra_memoria.set(0)
lbl_tokens = ctk.CTkLabel(frame_memoria, text="0 / 8000 tokens", font=("Arial", 10, "italic"), text_color="gray")
lbl_tokens.pack(side="left")

def actualizar_medidor_memoria():
    tokens = get_memoria_size()
    max_tokens = 8000
    progreso = min(tokens / max_tokens, 1.0)
    barra_memoria.set(progreso)
    lbl_tokens.configure(text=f"{tokens} / {max_tokens} tokens")
    
    if progreso > 0.8:
        barra_memoria.configure(progress_color="#e74c3c") # Rojo
    elif progreso > 0.5:
        barra_memoria.configure(progress_color="#f1c40f") # Amarillo
    else:
        barra_memoria.configure(progress_color="#2ecc71") # Verde

def limpiar_memoria_ui():
    limpiar_memoria()
    chat.delete("0.0", "end")
    actualizar_medidor_memoria()
    escribir("🧠 Memoria borrada. Nuevo chat iniciado.\n")

btn_limpiar = ctk.CTkButton(top_controls, text="Limpiar memoria", width=120, height=30, fg_color="#b33939", hover_color="#cd6133", command=limpiar_memoria_ui)
btn_limpiar.pack(side="right")

# -------- CHAT --------
chat = ctk.CTkTextbox(right_pane, corner_radius=15, font=("Arial", 16), wrap="word")
chat.pack(pady=(10, 0), fill="both", expand=True)

# Configurar tags de sintaxis
chat.tag_config("code", foreground="#78e08f")
chat.tag_config("thought", foreground="#7f8c8d")
chat.tag_config("normal", foreground="white")

# -------- ENTRADA --------
zona = ctk.CTkFrame(right_pane, fg_color="transparent")
zona.pack(fill="x", pady=(5, 0))

modelos = [
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.1-405b-instruct",
    "mistralai/mistral-large",
    "nvidia/nemotron-4-340b-instruct"
]

selector_modelo = ctk.CTkOptionMenu(zona, values=modelos, width=200, height=45, font=("Arial", 14))
selector_modelo.pack(side="left", padx=(0, 10))

entrada = ctk.CTkEntry(zona, placeholder_text="Escribe una orden...", height=45, font=("Arial", 16))
entrada.pack(side="left", fill="x", expand=True)

def escribir(texto, end="\n\n", tags=None):
    if tags:
        chat.insert("end", texto + end, tags)
    else:
        chat.insert("end", texto + end)
    chat.see("end")

def check_cancel():
    global cancelar_generacion
    return cancelar_generacion

def btn_cancelar_accion():
    global cancelar_generacion
    cancelar_generacion = True

btn_cancelar = ctk.CTkButton(zona, text="Cancelar", width=90, height=45, fg_color="#718093", hover_color="#2f3640", command=btn_cancelar_accion)
btn_cancelar.pack(side="left", padx=(10, 0))

boton = ctk.CTkButton(zona, text="Enviar", width=100, height=45, command=lambda: responder())
boton.pack(side="right", padx=(10, 0))

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

    entrada.delete(0, "end")
    
    if not auto_mensaje:
        escribir("👤 Tú:\n" + mensaje)
    else:
        escribir(f"🤖 Ejecución automática:\n{mensaje}")
        
    escribir("🤖 Agente:\n", end="")
    idx_inicio_respuesta = chat.index("end-1c")

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
                
            ctk.CTkButton(botones_frame, text="✅ Aceptar Cambios", fg_color="#27ae60", hover_color="#2ecc71", command=al_aceptar).pack(side="left", expand=True, padx=10)
            ctk.CTkButton(botones_frame, text="❌ Rechazar", fg_color="#c0392b", hover_color="#e74c3c", command=al_rechazar).pack(side="right", expand=True, padx=10)
            
            # Por si el usuario cierra la ventana con la X
            ventana.protocol("WM_DELETE_WINDOW", al_rechazar)

        app.after(0, mostrar_dialogo)
        evento.wait() # Bloquea el hilo de la IA hasta que el usuario responda
        return resultado[0]

    threading.Thread(
        target=trabajo_ia,
        args=(mensaje, modelo_seleccionado, idx_inicio_respuesta, confirmacion_ui_segura),
        daemon=True
    ).start()

def trabajo_ia(mensaje, modelo, idx_inicio, confirmacion_ui_segura):
    global auto_corregido
    
    texto_acumulado = ""
    try:
        generador = pensar(mensaje, modelo, check_cancel, confirmacion_ui_segura)
        
        for fragmento, terminado, comando_output in generador:
            if not terminado:
                texto_acumulado += fragmento
                app.after(0, lambda t=texto_acumulado: parse_and_insert(t, idx_inicio))
            else:
                app.after(0, lambda: chat.insert("end", "\n\n"))
                app.after(0, actualizar_arbol_archivos)
                app.after(0, actualizar_medidor_memoria)
                
                if comando_output:
                    if not auto_corregido:
                        auto_corregido = True
                        app.after(0, lambda o=comando_output: responder(auto_mensaje=o))
                    else:
                        app.after(0, lambda o=comando_output: escribir(f"⚠️ Se ha ejecutado el comando pero se ha alcanzado el límite de auto-corrección automática.\n{o}"))
                        
    except Exception as e:
        app.after(0, lambda err=str(e): escribir(f"\n[Error de conexión o API: {err}]"))

entrada.bind("<Return>", lambda e: responder())
entrada.focus()

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