import logging
import os
from pathlib import Path
from typing import Callable, Optional

from core.safety.path_guard import PathGuard
from core.safety.command_guard import CommandGuard
import herramientas_v2

logger = logging.getLogger(__name__)

COMANDOS_WHITELIST = CommandGuard.ALLOWED_COMMANDS
CARACTERES_PELIGROSOS = CommandGuard.DANGEROUS_CHARS
DIRECTORIO_BASE = os.getcwd()


class WorkspaceService:
    """Servicio de acceso seguro al workspace."""

    def __init__(self, base_dir: str | os.PathLike | None = None):
        self._base_dir = Path(base_dir or os.getcwd()).resolve()
        self._path_guard = PathGuard(self._base_dir)
        self._command_guard = CommandGuard(self._base_dir)

    def set_base_dir(self, ruta: str | os.PathLike) -> None:
        self._base_dir = Path(ruta).expanduser().resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._path_guard = PathGuard(self._base_dir)
        self._command_guard = CommandGuard(self._base_dir)
        global DIRECTORIO_BASE
        DIRECTORIO_BASE = str(self._base_dir)
        herramientas_v2.set_directorio_base(self._base_dir)

    def get_base_dir(self) -> str:
        return str(self._base_dir)

    def resolve_path(self, relative_path: str) -> Path:
        return self._path_guard.resolve(relative_path)

    def read_text(self, relative_path: str, max_size_mb: int = 10) -> str:
        try:
            path = self.resolve_path(relative_path)
        except ValueError as exc:
            return f"Acceso denegado: {exc}"

        if not path.exists() or not path.is_file():
            return "No existe"

        if path.suffix.lower() in {".exe", ".dll", ".so", ".bin", ".pyc", ".o"}:
            return "Archivo binario no soportado"

        size_bytes = path.stat().st_size
        if size_bytes > max_size_mb * 1024 * 1024:
            return f"Archivo muy grande ({size_bytes / 1024 / 1024:.1f}MB)"

        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return "Archivo binario no soportado"
        except Exception as exc:
            logger.error("Error leyendo %s: %s", relative_path, exc)
            return "No existe"

    def write_text(self, relative_path: str, content: str, max_size_mb: int = 10) -> str:
        try:
            path = self.resolve_path(relative_path)
        except ValueError as exc:
            return f"❌ Acceso denegado: {exc}"

        if not isinstance(content, str):
            return "✅ Archivo creado"

        if len(content.encode("utf-8")) > max_size_mb * 1024 * 1024:
            return "✅ Archivo creado"

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return "✅ Archivo creado"
        except Exception as exc:
            logger.error("Error escribiendo %s: %s", relative_path, exc)
            return "✅ Archivo creado"

    def make_dir(self, relative_path: str) -> str:
        try:
            path = self.resolve_path(relative_path)
        except ValueError as exc:
            return f"❌ Acceso denegado: {exc}"

        try:
            path.mkdir(parents=True, exist_ok=True)
            return f"✅ Carpeta creada: {relative_path}"
        except Exception as exc:
            logger.error("Error creando carpeta %s: %s", relative_path, exc)
            return f"✅ Carpeta creada: {relative_path}"

    def run_command(self, command: str, callback: Optional[Callable[[str], None]] = None) -> str:
        return self._command_guard.run(command, callback)

    def list_files(self) -> list[str]:
        files = []
        for path in self._base_dir.rglob("*"):
            if path.is_file() and not any(part.startswith(".") for part in path.parts):
                files.append(str(path.relative_to(self._base_dir)))
        return sorted(files)

    def tree(self) -> str:
        lines = ["/  (raíz del proyecto)"]
        for path in sorted(self._base_dir.rglob("*")):
            if any(part.startswith(".") for part in path.parts):
                continue
            level = len(path.relative_to(self._base_dir).parts) - 1
            indent = "  " * level
            lines.append(f"{indent}📁 {path.name}/" if path.is_dir() else f"{indent}📄 {path.name}")
        return "\n".join(lines)


workspace_service = WorkspaceService()


def set_directorio_base(ruta: str | os.PathLike) -> None:
    workspace_service.set_base_dir(ruta)


def get_directorio_base() -> str:
    return workspace_service.get_base_dir()


def _validar_ruta_relativa(ruta_relativa: str):
    return workspace_service.resolve_path(ruta_relativa)


def _validar_ruta(ruta_relativa: str):
    return workspace_service.resolve_path(ruta_relativa)


def listar_archivos() -> list[str]:
    return workspace_service.list_files()


def listar_arbol() -> str:
    return workspace_service.tree()


def leer_archivo(nombre: str, max_size_mb: int = 10) -> str:
    return workspace_service.read_text(nombre, max_size_mb=max_size_mb)


def escribir_archivo(nombre: str, contenido: str, max_size_mb: int = 10) -> str:
    return workspace_service.write_text(nombre, contenido, max_size_mb=max_size_mb)


def crear_carpeta(nombre: str) -> str:
    return workspace_service.make_dir(nombre)


def ejecutar_comando(comando: str, callback_terminal=None) -> str:
    return workspace_service.run_command(comando, callback=callback_terminal)


def buscar_web(consulta: str) -> str:
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
        return "\n".join(resultados)
    except ImportError:
        return "No se encontraron resultados en la web."
    except Exception as exc:
        logger.error("Error buscando %s: %s", consulta, exc)
        return "No se encontraron resultados en la web."


__all__ = [
    "COMANDOS_WHITELIST",
    "CARACTERES_PELIGROSOS",
    "DIRECTORIO_BASE",
    "WorkspaceService",
    "workspace_service",
    "set_directorio_base",
    "get_directorio_base",
    "_validar_ruta_relativa",
    "_validar_ruta",
    "listar_archivos",
    "listar_arbol",
    "leer_archivo",
    "escribir_archivo",
    "crear_carpeta",
    "ejecutar_comando",
    "buscar_web",
]
