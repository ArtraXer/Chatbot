def procesar(texto):
    lineas = texto.split('\n')
    for linea in lineas:
        linea_stripped = linea.strip()
        if linea_stripped.startswith("CARPETA:") or linea_stripped.startswith("CARPETA: "):
            carpeta = linea_stripped.split(":", 1)[1].strip()
            if carpeta:
                return f"He ejecutado la creación de carpeta: {carpeta}"
    return "None"

print(procesar("CARPETA: proyecto"))
print(procesar("```bash\nCARPETA: proyecto\n```"))
print(procesar(" CARPETA: proyecto "))
print(procesar("**CARPETA:** proyecto"))
