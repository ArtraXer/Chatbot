import os
import subprocess

DIRECTORIO_BASE = os.getcwd()

def set_directorio_base(ruta):
    global DIRECTORIO_BASE
    DIRECTORIO_BASE = ruta

def get_directorio_base():
    return DIRECTORIO_BASE

def listar_archivos():
    archivos = []
    for ruta, carpetas, ficheros in os.walk(DIRECTORIO_BASE):
        for f in ficheros:
            archivos.append(os.path.join(ruta, f))
    return archivos

def leer_archivo(nombre):
    ruta_completa = os.path.join(DIRECTORIO_BASE, nombre)
    try:
        with open(ruta_completa, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "No existe"

def escribir_archivo(nombre, contenido):
    ruta_completa = os.path.join(DIRECTORIO_BASE, nombre)
    directorio = os.path.dirname(ruta_completa)
    
    if directorio:
        os.makedirs(directorio, exist_ok=True)

    with open(ruta_completa, "w", encoding="utf-8") as f:
        f.write(contenido)

    return "Archivo creado"

def crear_carpeta(nombre):
    ruta_completa = os.path.join(DIRECTORIO_BASE, nombre)
    os.makedirs(ruta_completa, exist_ok=True)
    return f"Carpeta creada: {nombre}"

def ejecutar_comando(comando, callback_terminal=None):
    if callback_terminal:
        callback_terminal(f"$ {comando}")
    try:
        resultado = subprocess.run(
            comando, shell=True, cwd=get_directorio_base(),
            capture_output=True, text=True, timeout=10
        )
        salida_total = ""
        if resultado.stdout:
            salida_total += resultado.stdout
        if resultado.stderr:
            salida_total += f"\n[ERROR]\n{resultado.stderr}"
            
        if not salida_total:
            salida_total = "Ejecución finalizada sin salida."
            
        if callback_terminal:
            callback_terminal(salida_total)
            
        return salida_total
    except subprocess.TimeoutExpired:
        msg = "Error: La ejecución excedió el límite de 10 segundos y fue cancelada."
        if callback_terminal: callback_terminal(msg)
        return msg
    except Exception as e:
        msg = f"Error inesperado al ejecutar: {e}"
        if callback_terminal: callback_terminal(msg)
        return msg

def buscar_web(consulta):
    try:
        from duckduckgo_search import DDGS
        resultados = []
        with DDGS() as ddgs:
            for r in ddgs.text(consulta, max_results=3):
                resultados.append(f"[{r.get('title')}]({r.get('href')})\n{r.get('body')}\n")
        
        if not resultados:
            return "No se encontraron resultados en la web."
            
        return "\n".join(resultados)
    except Exception as e:
        return f"Error al buscar en la web: {e}"