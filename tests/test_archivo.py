import re

def procesar_archivos(texto):
    print(f"--- TEST: {repr(texto[:20])}... ---")
    bloques_archivos = re.split(r"ARCHIVO:\s*", texto)
    for bloque in bloques_archivos[1:]:
        datos = bloque.split("\n", 1)
        if len(datos) == 2:
            nombre = datos[0].strip()
            codigo = datos[1].replace("</pensar>", "").strip()
            print(f"Nombre: {repr(nombre)}")
            print(f"Código: {repr(codigo[:20])}")
        else:
            print("Datos no tiene len 2")

procesar_archivos("Aquí tienes:\nARCHIVO: test.py\nprint('hola')")
procesar_archivos("Aquí tienes:\n**ARCHIVO:** test.py\nprint('hola')")
procesar_archivos("Aquí tienes:\nARCHIVO: `test.py`\n```python\nprint('hola')\n```")
