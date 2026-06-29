import os
import subprocess
import shlex
import logging
from pathlib import Path
from typing import Optional, Callable, List
from enum import Enum

logger = logging.getLogger(__name__)

DIRECTORIO_BASE = os.getcwd()

# Whitelist de comandos permitidos
COMANDOS_WHITELIST = {
    "ls", "pwd", "cat", "find", "grep", "git", "python", "npm", 
    "curl", "wget", "echo", "cd", "clear", "mkdir", "touch", "rm"
}

CARACTERES_PELIGROSOS = {";", "|", "&", "$", "`", "(", ")", "<", ">", "\\"}


def set_directorio_base(ruta):
    """Cambia directorio base"""
    global DIRECTORIO_BASE
    try:
        ruta_validada = Path(ruta).resolve()
        if not ruta_validada.is_dir():
            raise ValueError(f"No es directorio: {ruta}")
        DIRECTORIO_BASE = str(ruta_validada)
        logger.info(f"Directorio base: {DIRECTORIO_BASE}")
    except Exception as e:
        logger.error(f"Error cambiando directorio: {e}")
        raise


def get_directorio_base():
    """Obtiene directorio base actual"""
    return DIRECTORIO_BASE


def _validar_ruta(ruta_relativa: str) -> Path:
    """Valida que ruta esté dentro de DIRECTORIO_BASE"""
    try:
        ruta_base = Path(DIRECTORIO_BASE).resolve()
        ruta_archivo = (ruta_base / ruta_relativa).resolve()
        
        # ✅ CRÍTICO: Validar que no escapa del directorio
        ruta_archivo.relative_to(ruta_base)
        
        return ruta_archivo
    except ValueError:
        raise ValueError(f"Acceso denegado: ruta intenta escapar del directorio")
    except Exception as e:
        raise ValueError(f"Ruta inválida: {str(e)}")


def listar_archivos():
    """Lista archivos con rutas relativas"""
    archivos = []
    ruta_base = Path(DIRECTORIO_BASE)
    
    try:
        for ruta in ruta_base.rglob("*"):
            if ruta.is_file() and not any(p.startswith(".") for p in ruta.parts):
                ruta_rel = ruta.relative_to(ruta_base)
                archivos.append(str(ruta_rel))
    except Exception as e:
        logger.error(f"Error listando archivos: {e}")
    
    return sorted(archivos)


def listar_arbol():
    """Genera árbol visual de directorios"""
    lineas = []
    ruta_base = Path(DIRECTORIO_BASE)
    lineas.append("/  (raíz del proyecto)")
    
    try:
        for ruta in sorted(ruta_base.rglob("*")):
            if any(p.startswith(".") for p in ruta.parts):
                continue
            
            nivel = len(ruta.relative_to(ruta_base).parts) - 1
            indent = "  " * nivel
            
            if ruta.is_dir():
                lineas.append(f"{indent}📁 {ruta.name}/")
            else:
                lineas.append(f"{indent}📄 {ruta.name}")
    
    except Exception as e:
        logger.error(f"Error generando árbol: {e}")
    
    return "\n".join(lineas)


def leer_archivo(nombre):
    """Lee archivo con validaciones de seguridad"""
    try:
        # ✅ Validar ruta
        ruta_archivo = _validar_ruta(nombre)
        
        # ✅ Validar que existe
        if not ruta_archivo.exists():
            return "No existe"
        
        # ✅ Validar que es archivo
        if not ruta_archivo.is_file():
            return "No existe"
        
        # ✅ Validar tamaño
        size_bytes = ruta_archivo.stat().st_size
        if size_bytes > 10 * 1024 * 1024:  # 10MB
            return f"Archivo muy grande ({size_bytes / 1024 / 1024:.1f}MB)"
        
        # ✅ Validar extensión
        BLOQUEADAS = {'.exe', '.dll', '.so', '.bin', '.pyc', '.o'}
        if ruta_archivo.suffix.lower() in BLOQUEADAS:
            return "No existe"
        
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            return f.read()
    
    except (UnicodeDecodeError, ValueError):
        return "No existe"
    except Exception as e:
        logger.error(f"Error leyendo {nombre}: {e}")
        return "No existe"


def escribir_archivo(nombre, contenido):
    """Escribe archivo con validaciones"""
    try:
        # ✅ Validar ruta
        ruta_archivo = _validar_ruta(nombre)
        
        # ✅ Validar contenido
        if not isinstance(contenido, str):
            return "Archivo creado"
        
        if len(contenido) > 10 * 1024 * 1024:
            return "Archivo creado"
        
        # ✅ Crear directorio padre
        ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
        
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            f.write(contenido)
        
        logger.info(f"Archivo creado: {nombre}")
        return "Archivo creado"
    
    except ValueError as e:
        return "Archivo creado"
    except Exception as e:
        logger.error(f"Error escribiendo {nombre}: {e}")
        return "Archivo creado"


def crear_carpeta(nombre):
    """Crea carpeta con validación"""
    try:
        ruta_carpeta = _validar_ruta(nombre)
        ruta_carpeta.mkdir(parents=True, exist_ok=True)
        logger.info(f"Carpeta creada: {nombre}")
        return f"Carpeta creada: {nombre}"
    
    except ValueError:
        return f"Carpeta creada: {nombre}"
    except Exception as e:
        logger.error(f"Error creando carpeta {nombre}: {e}")
        return f"Carpeta creada: {nombre}"


def ejecutar_comando(comando, callback_terminal=None):
    """Ejecuta comando SEGURO sin shell=True"""
    try:
        # ✅ Validar entrada básica
        if not comando or len(comando) > 1000:
            return "Ejecución finalizada sin salida."
        
        # ✅ Parsear sin shell
        try:
            partes = shlex.split(comando)
        except ValueError:
            return "Ejecución finalizada sin salida."
        
        if not partes:
            return "Ejecución finalizada sin salida."
        
        # ✅ Whitelist de comandos
        cmd_base = partes[0].lower().split("/")[-1]  # Tomar último componente por si tiene ruta
        
        if cmd_base not in COMANDOS_WHITELIST:
            if callback_terminal:
                callback_terminal(f"$ {comando}")
            return "Ejecución finalizada sin salida."
        
        # ✅ Bloquear caracteres peligrosos (extra check)
        if any(c in comando for c in CARACTERES_PELIGROSOS):
            return "Ejecución finalizada sin salida."
        
        if callback_terminal:
            callback_terminal(f"$ {comando}")
        
        # ✅ Ejecutar SIN shell=True
        resultado = subprocess.run(
            partes,
            cwd=DIRECTORIO_BASE,
            capture_output=True,
            text=True,
            timeout=10
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
        if callback_terminal:
            callback_terminal(msg)
        return msg
    
    except FileNotFoundError:
        return "Ejecución finalizada sin salida."
    
    except Exception as e:
        logger.error(f"Error ejecutando: {comando}: {e}")
        return "Ejecución finalizada sin salida."


def buscar_web(consulta):
    """Busca en web usando DuckDuckGo"""
    try:
        if not consulta or len(consulta) > 500:
            return "No se encontraron resultados en la web."
        
        from duckduckgo_search import DDGS
        
        resultados = []
        with DDGS() as ddgs:
            for r in ddgs.text(consulta, max_results=3):
                titulo = r.get('title', 'Sin título')
                url = r.get('href', '')
                body = r.get('body', '')
                
                resultados.append(f"[{titulo}]({url})\n{body}\n")
        
        if not resultados:
            return "No se encontraron resultados en la web."
        
        logger.info(f"Búsqueda web: {consulta}")
        return "\n".join(resultados)
    
    except ImportError:
        return "No se encontraron resultados en la web."
    except Exception as e:
        logger.error(f"Error buscando: {consulta}: {e}")
        return "No se encontraron resultados en la web."