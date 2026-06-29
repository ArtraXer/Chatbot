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

def pensar(mensaje, modelo="meta/llama-3.1-8b-instruct", check_cancel=None, callback_confirmar_archivo=None):
    proyecto = listar_archivos()
    directorio_actual = get_directorio_base()

    contexto = f"""
    Eres un agente programador autónomo de élite.
    Estás trabajando en el directorio: {directorio_actual}
    
    Tienes Git instalado en el sistema. Puedes y debes usar comandos de Git para guardar tu trabajo automáticamente.

    Archivos actuales (solo nombres):
    {proyecto}

    ACCIONES PERMITIDAS:
    
    1. Si necesitas leer el contenido de un archivo existente para entenderlo antes de editarlo:
    COMANDO: leer nombre_archivo.py
    
    2. Si necesitas crear o sobreescribir un archivo:
    ARCHIVO:nombre_archivo.py
    (código completo aquí)

    3. Si necesitas crear una carpeta vacía:
    CARPETA:nombre_carpeta

    4. Si necesitas ejecutar un script de python o comandos de sistema (ej: git add ., git commit -m "..."):
    COMANDO: ejecutar git status

    5. Si necesitas buscar información en internet (ej: leer documentación moderna, ver ejemplos):
    COMANDO: buscar_web consulta_aqui

    IMPORTANTE:
    - Las rutas que devuelvas (en ARCHIVO: o COMANDO:) deben ser relativas a {directorio_actual}.
    - No respondas con ejemplos, usa comandos reales.
    - Antes de escribir el código o los comandos, piensa paso a paso tu plan de acción dentro de etiquetas <pensar> y </pensar>.
    - ¡No adivines el contenido de un archivo! Usa COMANDO: leer primero si no lo conoces.
    - Si vas a usar una librería que no conoces perfectamente, usa COMANDO: buscar_web primero.

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
    comando_output = procesar_acciones(texto_completo, callback_confirmar_archivo)
    yield "", True, comando_output


def procesar_acciones(texto, callback_confirmar_archivo):
    # Procesar archivos
    bloques_archivos = re.split(r"ARCHIVO:\s*", texto)
    for bloque in bloques_archivos[1:]:
        datos = bloque.split("\n", 1)
        if len(datos) == 2:
            nombre = datos[0].strip()
            codigo = datos[1]
            codigo = codigo.replace("</pensar>", "").strip()
            
            # Comprobar si el archivo ya existe
            ruta_completa = os.path.join(get_directorio_base(), nombre)
            if os.path.exists(ruta_completa) and callback_confirmar_archivo:
                # Si existe, pedir confirmación a través del callback
                aceptado = callback_confirmar_archivo(nombre, codigo)
                if aceptado:
                    escribir_archivo(nombre, codigo)
            else:
                # Si no existe, crear directamente
                escribir_archivo(nombre, codigo)
            
    # Procesar comandos y carpetas
    lineas = texto.split('\n')
    for linea in lineas:
        if linea.startswith("CARPETA:"):
            carpeta = linea.replace("CARPETA:", "").strip()
            crear_carpeta(carpeta)
            
        elif linea.startswith("COMANDO: leer "):
            archivo = linea.replace("COMANDO: leer ", "").strip()
            contenido = leer_archivo(archivo)
            return f"He leído '{archivo}'. Contenido:\n\n{contenido}"
            
        elif linea.startswith("COMANDO: buscar_web "):
            consulta = linea.replace("COMANDO: buscar_web ", "").strip()
            resultado = buscar_web(consulta)
            return f"He buscado en la web '{consulta}'. Resultados:\n\n{resultado}"
            
        elif linea.startswith("COMANDO: ejecutar "):
            comando = linea.replace("COMANDO: ejecutar ", "").strip()
            
            # Ejecutar de forma diferente dependiendo si es python u otro
            if comando.startswith("python "):
                archivo = comando.replace("python ", "").strip()
                resultado = ejecutar_python(archivo)
            else:
                # Soporte para git y otros comandos básicos del sistema
                import subprocess
                try:
                    res = subprocess.run(comando.split(), capture_output=True, text=True, cwd=get_directorio_base(), timeout=10)
                    resultado = res.stdout if res.returncode == 0 else res.stderr
                except Exception as e:
                    resultado = str(e)
                    
            return f"He ejecutado '{comando}'. Resultado:\n{resultado}"
            
    return None