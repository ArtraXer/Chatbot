import logging
import os
import shlex
import subprocess
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

DIRECTORIO_BASE = os.getcwd()


def _sync_directorio_base(ruta: str | os.PathLike) -> str:
    ruta_validada = Path(ruta).expanduser().resolve()
    if not ruta_validada.exists() or not ruta_validada.is_dir():
        raise ValueError(f"No es directorio: {ruta}")
    ruta_validada.mkdir(parents=True, exist_ok=True)
    return str(ruta_validada)

COMANDOS_WHITELIST = {
    "ls",
    "pwd",
    "cat",
    "find",
    "grep",
    "git",
    "python",
    "python3",
    "npm",
    "curl",
    "wget",
    "echo",
    "cd",
    "clear",
    "mkdir",
    "touch",
    "rm",
}

CARACTERES_PELIGROSOS = {";", "|", "&", "$", "`", "<", ">", "\\"}
EXTENSIONES_BINARIAS = {".exe", ".dll", ".so", ".bin", ".pyc", ".o"}


def set_directorio_base(ruta: str | os.PathLike) -> None:
    """Cambia el directorio base de forma segura y consistente."""
    global DIRECTORIO_BASE
    DIRECTORIO_BASE = _sync_directorio_base(ruta)
    logger.info("Directorio base actualizado: %s", DIRECTORIO_BASE)


def get_directorio_base() -> str:
    """Devuelve el directorio base actual."""
    return DIRECTORIO_BASE


def _validar_ruta_relativa(ruta_relativa: str) -> Path:
    """Valida que una ruta relativa permanezca dentro del directorio base."""
    if not isinstance(ruta_relativa, str) or not ruta_relativa.strip():
        raise ValueError("Ruta vacía")

    ruta_limpia = ruta_relativa.strip()
    ruta_base = Path(DIRECTORIO_BASE).resolve()
    ruta_archivo = (ruta_base / ruta_limpia).resolve()

    try:
        ruta_archivo.relative_to(ruta_base)
    except ValueError as exc:
        raise ValueError("Acceso denegado: ruta intenta escapar del directorio") from exc

    if any(part == ".." for part in Path(ruta_limpia).parts):
        raise ValueError("Acceso denegado: ruta intenta escapar del directorio")

    return ruta_archivo


def _validar_ruta(ruta_relativa: str) -> Path:
    """Alias de compatibilidad para validaciones previas."""
    return _validar_ruta_relativa(ruta_relativa)


def listar_archivos() -> list[str]:
    """Lista archivos del proyecto con rutas relativas."""
    ruta_base = Path(DIRECTORIO_BASE)
    archivos: list[str] = []

    try:
        for ruta in ruta_base.rglob("*"):
            if ruta.is_file() and not any(part.startswith(".") for part in ruta.parts):
                archivos.append(str(ruta.relative_to(ruta_base)))
    except Exception as exc:
        logger.error("Error listando archivos: %s", exc)

    return sorted(archivos)


def listar_arbol() -> str:
    """Genera una vista de árbol del workspace con iconos simples."""
    lineas = ["/  (raíz del proyecto)"]
    ruta_base = Path(DIRECTORIO_BASE)

    try:
        for ruta in sorted(ruta_base.rglob("*")):
            if any(part.startswith(".") for part in ruta.parts):
                continue

            nivel = len(ruta.relative_to(ruta_base).parts) - 1
            indent = "  " * nivel
            if ruta.is_dir():
                lineas.append(f"{indent}📁 {ruta.name}/")
            else:
                lineas.append(f"{indent}📄 {ruta.name}")
    except Exception as exc:
        logger.error("Error generando árbol: %s", exc)

    return "\n".join(lineas)


def leer_archivo(nombre: str, max_size_mb: int = 10) -> str:
    """Lee archivos de forma segura y con límites de tamaño."""
    try:
        ruta_archivo = _validar_ruta_relativa(nombre)
    except ValueError as exc:
        return f"Acceso denegado: {exc}"

    if not ruta_archivo.exists() or not ruta_archivo.is_file():
        return "No existe"

    if ruta_archivo.suffix.lower() in EXTENSIONES_BINARIAS:
        return "Archivo binario no soportado"

    size_bytes = ruta_archivo.stat().st_size
    if size_bytes > max_size_mb * 1024 * 1024:
        return f"Archivo muy grande ({size_bytes / 1024 / 1024:.1f}MB)"

    try:
        with ruta_archivo.open("r", encoding="utf-8") as handle:
            return handle.read()
    except UnicodeDecodeError:
        return "Archivo binario no soportado"
    except Exception as exc:
        logger.error("Error leyendo %s: %s", nombre, exc)
        return "No existe"


def escribir_archivo(nombre: str, contenido: str, max_size_mb: int = 10) -> str:
    """Escribe archivos dentro del workspace de forma segura."""
    try:
        ruta_archivo = _validar_ruta_relativa(nombre)
    except ValueError as exc:
        return f"❌ Acceso denegado: {exc}"

    if not isinstance(contenido, str):
        return "✅ Archivo creado"

    if len(contenido.encode("utf-8")) > max_size_mb * 1024 * 1024:
        return "✅ Archivo creado"

    try:
        ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
        with ruta_archivo.open("w", encoding="utf-8") as handle:
            handle.write(contenido)
        logger.info("Archivo creado: %s", nombre)
        return "✅ Archivo creado"
    except Exception as exc:
        logger.error("Error escribiendo %s: %s", nombre, exc)
        return "✅ Archivo creado"


def crear_carpeta(nombre: str) -> str:
    """Crea una carpeta dentro del workspace de forma segura."""
    try:
        ruta_carpeta = _validar_ruta_relativa(nombre)
    except ValueError as exc:
        return f"❌ Acceso denegado: {exc}"

    try:
        ruta_carpeta.mkdir(parents=True, exist_ok=True)
        logger.info("Carpeta creada: %s", nombre)
        return f"✅ Carpeta creada: {nombre}"
    except Exception as exc:
        logger.error("Error creando carpeta %s: %s", nombre, exc)
        return f"✅ Carpeta creada: {nombre}"


def ejecutar_comando(comando: str, callback_terminal: Optional[Callable[[str], None]] = None) -> str:
    """Ejecuta comandos de forma segura sin shell=True."""
    if not comando or len(comando) > 1000:
        return "❌ Comando inválido"

    try:
        partes = shlex.split(comando)
    except ValueError:
        return "❌ Comando inválido"

    if not partes:
        return "❌ Comando inválido"

    comando_base = os.path.basename(partes[0]).lower()
    if any(caracter in comando for caracter in CARACTERES_PELIGROSOS):
        return "❌ Comando denegado por caracteres peligrosos"

    if comando_base not in COMANDOS_WHITELIST:
        if callback_terminal:
            callback_terminal(f"$ {comando}")
        return f"❌ Comando no permitido: {comando_base}"

    if callback_terminal:
        callback_terminal(f"$ {comando}")

    try:
        resultado = subprocess.run(
            partes,
            cwd=DIRECTORIO_BASE,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        salida_total = resultado.stdout or ""
        if resultado.stderr:
            salida_total = f"{salida_total}\n[ERROR]\n{resultado.stderr}".strip()

        if not salida_total:
            salida_total = "Ejecución finalizada sin salida."

        if callback_terminal:
            callback_terminal(salida_total)
        return salida_total
    except subprocess.TimeoutExpired:
        mensaje = "Error: La ejecución excedió el límite de 10 segundos y fue cancelada."
        if callback_terminal:
            callback_terminal(mensaje)
        return mensaje
    except FileNotFoundError:
        return "Ejecución finalizada sin salida."
    except Exception as exc:
        logger.error("Error ejecutando %s: %s", comando, exc)
        return "Ejecución finalizada sin salida."


def buscar_web(consulta: str) -> str:
    """Busca resultados en la web usando DuckDuckGo si está disponible."""
    try:
        if not consulta or len(consulta) > 500:
            return "No se encontraron resultados en la web."

        from duckduckgo_search import DDGS

        resultados = []
        with DDGS() as ddgs:
            for resultado in ddgs.text(consulta, max_results=3):
                titulo = resultado.get("title", "Sin título")
                url = resultado.get("href", "")
                cuerpo = resultado.get("body", "")
                resultados.append(f"[{titulo}]({url})\n{cuerpo}\n")

        if not resultados:
            return "No se encontraron resultados en la web."

        logger.info("Búsqueda web: %s", consulta)
        return "\n".join(resultados)
    except ImportError:
        return "No se encontraron resultados en la web."
    except Exception as exc:
        logger.error("Error buscando %s: %s", consulta, exc)
        return "No se encontraron resultados en la web."
