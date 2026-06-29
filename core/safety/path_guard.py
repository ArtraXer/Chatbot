import os
from pathlib import Path


class PathGuard:
    """Protege el acceso a archivos dentro del workspace."""

    def __init__(self, base_dir: str | os.PathLike | None = None):
        self.base_dir = Path(base_dir or os.getcwd()).resolve()

    def resolve(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("Ruta vacía")

        candidate = (self.base_dir / relative_path).resolve()
        try:
            candidate.relative_to(self.base_dir)
        except ValueError as exc:
            raise ValueError("Acceso denegado: ruta intenta escapar del directorio") from exc

        if any(part == ".." for part in Path(relative_path).parts):
            raise ValueError("Acceso denegado: ruta intenta escapar del directorio")

        return candidate

    def ensure_base_dir(self) -> Path:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        return self.base_dir
