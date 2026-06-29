import os
import subprocess
import shlex
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, List
from enum import Enum

logger = logging.getLogger(__name__)

DIRECTORIO_BASE = os.getcwd()

# Whitelist de comandos permitidos
class ComandoPermitido(Enum):
    LS = "ls"
    PWD = "pwd"
    CAT = "cat"
    FIND = "find"
    GREP = "grep"
    GIT = "git"
    PYTHON = "python"
    NPM = "npm"
    CURL = "curl"
    WGET = "wget"

COMANDOS_WHITELIST = {cmd.value for cmd in ComandoPermitido}
CARACTERES_PELIGROSOS = {";", "|", "&", "$", "`", "(", ")", "<", ">", "\\"};


def set_directorio_base(ruta: str) -> None:
    """Cambia directorio base con validación"""
    global DIRECTORIO_BASE
    
    ruta_validada = Path(ruta).resolve()
    
    if not ruta_validada.is_dir():
        raise ValueError(f"Directorio no existe: {ruta}")
    
    DIRECTORIO_BASE = str(ruta_validada)
    logger.info(f"Directorio base cambiado a: {DIRECTORIO_BASE}")


def get_directorio_base() -> str:
    """Obtiene directorio base actual"""
    return DIRECTORIO_BASE


def _validar_ruta_relativa(ruta_relativa: str) -> Path:
    """
    Valida que ruta esté dentro de DIRECTORIO_BASE (previene path traversal).
    
    Raises:
        ValueError: Si ruta intenta escapar
    """
    ruta_base = Path(DIRECTORIO_BASE).resolve()
    ruta_archivo = (ruta_base / ruta_relativa).resolve()
    
    # ✅ VALIDACIÓN CRÍTICA
    try:
        ruta_archivo.relative_to(ruta_base)  # Lanza error si está fuera
    except ValueError:
        raise ValueError(
            f"❌ Acceso denegado: ruta '{ruta_relativa}' "
            f"intenta salir de {ruta_base}"
        )
    
    return ruta_archivo


def listar_archivos() -> List[str]:
    """Lista archivos con rutas relativas"""
    archivos = []
    ruta_base = Path(DIRECTORIO_BASE)
    
    try:
        for ruta in ruta_base.rglob("*"):
            # Ignorar directorios ocultos
            if ruta.is_file() and not any(p.startswith(".") for p in ruta.parts):
                ruta_rel = ruta.relative_to(ruta_base)
                archivos.append(str(ruta_rel))
    
    except Exception as e:
        logger.error(f"Error listando archivos: {e}")
    
    return sorted(archivos)


def listar_arbol() -> str:
    """Genera árbol de directorios visual"""
    lineas = []
    ruta_base = Path(DIRECTORIO_BASE)
    lineas.append("/ (raíz del proyecto)")
    
    try:
        for ruta in sorted(ruta_base.rglob("*")):
            # Ignorar ocultos
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


def leer_archivo(ruta_relativa: str, max_size_mb: int = 10) -> str:
    """
    Lee archivo con validaciones de seguridad.
    
    Args:
        ruta_relativa: Ruta relativa a DIRECTORIO_BASE
        max_size_mb: Tamaño máximo en MB
    
    Returns:
        Contenido del archivo o mensaje de error
    """
    try:
        # ✅ Validar ruta
        ruta_archivo = _validar_ruta_relativa(ruta_relativa)
        
        # ✅ Validar que existe
        if not ruta_archivo.exists():
            return f"❌ Archivo no encontrado: {ruta_relativa}"
        
        # ✅ Validar que es archivo, no directorio
        if not ruta_archivo.is_file():
            return f"❌ No es un archivo: {ruta_relativa}"
        
        # ✅ Validar tamaño
        size_bytes = ruta_archivo.stat().st_size
        if size_bytes > max_size_mb * 1024 * 1024:
            return (
                f"⚠️ Archivo muy grande ({size_bytes / 1024 / 1024:.1f}MB > "
                f"{max_size_mb}MB). Use max_size_mb para aumentar límite."
            )
        
        # ✅ Validar extensión (bloquear binarios)
        EXTENSIONES_BLOQUEADAS = {
            '.exe', '.dll', '.so', '.bin', '.pyc', '.o',
            '.zip', '.tar', '.gz', '.rar'
        }
        if ruta_archivo.suffix.lower() in EXTENSIONES_BLOQUEADAS:
            return f"❌ No se puede leer archivo binario: {ruta_archivo.suffix}"
        
        # ✅ Leer archivo
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            return f.read()
    
    except ValueError as e:
        return f"❌ {str(e)}"
    except UnicodeDecodeError:
        return f"❌ Archivo binario o encoding no soportado"
    except Exception as e:
        logger.exception(f"Error leyendo {ruta_relativa}")
        return f"❌ Error: {type(e).__name__}: {str(e)}"


def escribir_archivo(ruta_relativa: str, contenido: str) -> str:
    """
    Escribe archivo con validaciones.
    
    Args:
        ruta_relativa: Ruta relativa a DIRECTORIO_BASE
        contenido: Contenido a escribir
    
    Returns:
        Mensaje de confirmación o error
    """
    try:
        # ✅ Validar ruta
        ruta_archivo = _validar_ruta_relativa(ruta_relativa)
        
        # ✅ Validar contenido
        if not isinstance(contenido, str):
            return "❌ Contenido debe ser string"
        
        if len(contenido) > 10 * 1024 * 1024:  # 10MB
            return "❌ Contenido muy grande (>10MB)"
        
        # ✅ Crear directorio padre
        ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
        
        # ✅ Escribir archivo
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            f.write(contenido)
        
        logger.info(f"Archivo creado: {ruta_relativa}")
        return f"✅ Archivo creado: {ruta_relativa}"
    
    except ValueError as e:
        return f"❌ {str(e)}"
    except Exception as e:
        logger.exception(f"Error escribiendo {ruta_relativa}")
        return f"❌ Error: {type(e).__name__}"


def crear_carpeta(ruta_relativa: str) -> str:
    """Crea carpeta con validación"""
    try:
        ruta_carpeta = _validar_ruta_relativa(ruta_relativa)
        ruta_carpeta.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Carpeta creada: {ruta_relativa}")
        return f"✅ Carpeta creada: {ruta_relativa}"
    
    except ValueError as e:
        return f"❌ {str(e)}"
    except Exception as e:
        logger.exception(f"Error creando carpeta {ruta_relativa}")
        return f"❌ Error: {type(e).__name__}"


def ejecutar_comando(
    comando: str,
    callback_terminal: Optional[Callable] = None,
    timeout: int = 10
) -> str:
    """
    Ejecuta comando SEGURO sin shell=True.
    
    Args:
        comando: Comando a ejecutar (ej: "git status")
        callback_terminal: Callback para imprimir output en tiempo real
        timeout: Segundos máximo de ejecución
    
    Returns:
        Output del comando o mensaje de error
    """
    try:
        # ✅ Parsear comando sin shell
        partes = shlex.split(comando)
        
        if not partes:
            return "❌ Comando vacío"
        
        cmd_base = partes[0].lower()
        
        # ✅ Whitelist de comandos
        if cmd_base not in COMANDOS_WHITELIST:
            permitidos = ", ".join(sorted(COMANDOS_WHITELIST))
            return f"❌ Comando '{cmd_base}' no permitido.\nPermitidos: {permitidos}"
        
        # ✅ Bloquear caracteres peligrosos (extra check)
        if any(c in comando for c in CARACTERES_PELIGROSOS):
            return "❌ Comando contiene caracteres peligrosos"
        
        if callback_terminal:
            callback_terminal(f"$ {' '.join(partes)}")
        
        # ✅ Ejecutar SIN shell=True (es más seguro)
        resultado = subprocess.run(
            partes,
            cwd=DIRECTORIO_BASE,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        salida = resultado.stdout or "Ejecución completada sin output."
        
        if resultado.stderr:
            salida += f"\n[STDERR]\n{resultado.stderr}"
        
        if callback_terminal:
            callback_terminal(salida)
        
        return salida
    
    except subprocess.TimeoutExpired:
        msg = f"⏱️ Timeout: comando excedió {timeout} segundos"
        if callback_terminal:
            callback_terminal(msg)
        return msg
    
    except FileNotFoundError:
        return f"❌ Comando no encontrado: {partes[0]}"
    
    except Exception as e:
        logger.exception(f"Error ejecutando comando: {comando}")
        return f"❌ Error: {type(e).__name__}: {str(e)}"


def buscar_web(consulta: str) -> str:
    """
    Busca en la web usando DuckDuckGo.
    
    Args:
        consulta: Términos de búsqueda
    
    Returns:
        Resultados formateados o mensaje de error
    """
    try:
        if not consulta or len(consulta) > 500:
            return "❌ Consulta inválida (vacía o >500 caracteres)"
        
        from duckduckgo_search import DDGS
        
        resultados = []
        with DDGS() as ddgs:
            for r in ddgs.text(consulta, max_results=3):
                titulo = r.get('title', 'Sin título')
                url = r.get('href', '')
                body = r.get('body', '')
                
                resultados.append(f"**{titulo}**\n{url}\n{body}\n")
        
        if not resultados:
            return "⚠️ No se encontraron resultados"
        
        logger.info(f"Búsqueda web: {consulta}")
        return "\n".join(resultados)
    
    except ImportError:
        return "❌ Librería 'duckduckgo_search' no instalada"
    except Exception as e:
        logger.exception(f"Error buscando: {consulta}")
        return f"❌ Error de búsqueda: {type(e).__name__}"