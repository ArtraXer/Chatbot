from openai import OpenAI
import os
import re

from herramientas import *

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"]
)

memoria = []
instrucciones_extra = ""

def limpiar_memoria():
    global memoria
    memoria = []

def get_memoria_size():
    # Estimación simple: 1 token ≈ 4 caracteres
    total_chars = sum(len(m["content"]) for m in memoria)
    return total_chars // 4

def set_instrucciones(texto):
    global instrucciones_extra
    instrucciones_extra = texto

def pensar(mensaje, modelo="meta/llama-3.1-8b-instruct", check_cancel=None, callback_confirmar_archivo=None, callback_terminal=None):
    arbol = listar_arbol()
    directorio_actual = get_directorio_base()

    contexto = f"""
    Eres un agente programador autónomo de élite.
    Directorio raíz del proyecto: {directorio_actual}
    
    ÁRBOL DE ARCHIVOS Y CARPETAS ACTUALES:
    {arbol}

    ACCIONES PERMITIDAS:
    
    1. Si necesitas leer el contenido de un archivo existente:
    COMANDO: leer carpeta/archivo.py
    (usa la ruta relativa tal como aparece en el árbol)
    
    2. Si necesitas crear o sobreescribir un archivo:
    ARCHIVO: carpeta/subcarpeta/nombre_archivo.py
    (código completo aquí, SIN bloques markdown)
    
    CRÍTICO: Si el usuario menciona una carpeta específica (ej: "dentro de proyecto"), 
    la ruta DEBE incluir esa carpeta: ARCHIVO: proyecto/index.html
    NUNCA uses solo el nombre del archivo sin la ruta si hay una carpeta destino.

    3. Si necesitas crear una carpeta vacía:
    CARPETA: nombre_carpeta

    4. Si necesitas ejecutar comandos del sistema:
    COMANDO: ejecutar git status

    5. Si necesitas buscar información en internet:
    COMANDO: buscar_web consulta_aqui

    REGLAS IMPORTANTES:
    - Las rutas en ARCHIVO: son SIEMPRE relativas a {directorio_actual}.
    - NO envuelvas el código en bloques ```markdown```. Escribe el código directamente.
    - Antes de actuar, piensa dentro de etiquetas <pensar> y </pensar>.
    - ¡No adivines el contenido de un archivo! Usa COMANDO: leer primero.
    - Si vas a usar una librería que no conoces, usa COMANDO: buscar_web primero.
    - Cuando hayas completado una tarea, confírmala brevemente y DETENTE. No inventes más pasos.

    INSTRUCCIONES EXTRA DEL USUARIO:
    {instrucciones_extra}
    """

    if not memoria:
        memoria.append({"role": "system", "content": contexto})
    else:
        memoria[0] = {"role": "system", "content": contexto}

    memoria.append({"role": "user", "content": mensaje})

    respuesta = client.chat.completions.create(
        model=modelo,
        messages=memoria,
        max_tokens=8000,
        stream=True
    )

    texto_completo = ""

    for chunk in respuesta:
        if check_cancel and check_cancel():
            texto_completo += "\n[Generación Cancelada]"
            break
        
        if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content is not None:
            fragmento = chunk.choices[0].delta.content
            texto_completo += fragmento
            yield fragmento, False, None

    memoria.append({"role": "assistant", "content": texto_completo})
    
    # Procesar acciones
    comando_output = procesar_acciones(texto_completo, callback_confirmar_archivo, callback_terminal)
    yield "", True, comando_output


def procesar_acciones(texto, callback_confirmar_archivo, callback_terminal):
    respuestas = []
    requiere_respuesta = False

    # Procesar archivos
    bloques_archivos = re.split(r"(?i)\*?\*?ARCHIVO:\*?\*?\s*", texto)
    for bloque in bloques_archivos[1:]:
        datos = bloque.split("\n", 1)
        if len(datos) == 2:
            nombre = datos[0].replace("`", "").replace("*", "").strip()
            codigo = datos[1].replace("</pensar>", "").strip()
            
            # Limpiar bloques de código markdown
            if codigo.startswith("```"):
                partes = codigo.split("\n```")
                if len(partes) > 1:
                    codigo = partes[0].split("\n", 1)[-1]
            codigo = codigo.strip()
            
            # Comprobar si el archivo ya existe
            ruta_completa = os.path.join(get_directorio_base(), nombre)
            if os.path.exists(ruta_completa) and callback_confirmar_archivo:
                # Si existe, pedir confirmación a través del callback
                aceptado = callback_confirmar_archivo(nombre, codigo)
                if aceptado:
                    escribir_archivo(nombre, codigo)
                    respuestas.append(f"He modificado el archivo '{nombre}'")
            else:
                # Si no existe, crear directamente
                escribir_archivo(nombre, codigo)
                respuestas.append(f"He creado el archivo '{nombre}'")
            
    # Procesar comandos y carpetas
    lineas = texto.split('\n')
    for linea in lineas:
        linea_stripped = linea.strip()
        
        match_carpeta = re.search(r"\*?\*?CARPETA:\*?\*?\s*[`\*]?(.+?)[`\*]?$", linea_stripped, re.IGNORECASE)
        if match_carpeta:
            carpeta = match_carpeta.group(1).strip()
            if carpeta:
                res = crear_carpeta(carpeta)
                respuestas.append(f"He ejecutado la creación de carpeta. Resultado:\n{res}")
            
        match_leer = re.search(r"\*?\*?COMANDO:\s*leer\s*[`\*]?(.+?)[`\*]?$", linea_stripped, re.IGNORECASE)
        if match_leer:
            archivo = match_leer.group(1).strip()
            contenido = leer_archivo(archivo)
            respuestas.append(f"He leído '{archivo}'. Contenido:\n\n{contenido}")
            requiere_respuesta = True
            
        match_web = re.search(r"\*?\*?COMANDO:\s*buscar_web\s*[`\*]?(.+?)[`\*]?$", linea_stripped, re.IGNORECASE)
        if match_web:
            consulta = match_web.group(1).strip()
            resultado = buscar_web(consulta)
            respuestas.append(f"He buscado en la web '{consulta}'. Resultados:\n\n{resultado}")
            requiere_respuesta = True
            
        match_ejec = re.search(r"\*?\*?COMANDO:\s*ejecutar\s*[`\*]?(.+?)[`\*]?$", linea_stripped, re.IGNORECASE)
        if match_ejec:
            comando = match_ejec.group(1).strip()
            resultado = ejecutar_comando(comando, callback_terminal)
            respuestas.append(f"He ejecutado '{comando}'. Resultado:\n{resultado}")
            requiere_respuesta = True
            
    if respuestas:
        return "\n\n".join(respuestas), requiere_respuesta
    return None, False