import os
import shlex
import subprocess
from typing import Callable, Optional


class CommandGuard:
    """Valida y ejecuta comandos de forma segura."""

    ALLOWED_COMMANDS = {
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

    DANGEROUS_CHARS = {";", "|", "&", "$", "`", "<", ">", "\\"}

    def __init__(self, cwd: str | os.PathLike):
        self.cwd = os.fspath(cwd)

    def validate(self, command: str) -> list[str]:
        if not isinstance(command, str) or not command.strip():
            raise ValueError("Comando vacío")
        if len(command) > 1000:
            raise ValueError("Comando demasiado largo")
        if any(char in command for char in self.DANGEROUS_CHARS):
            raise ValueError("Comando denegado por caracteres peligrosos")

        parts = shlex.split(command)
        if not parts:
            raise ValueError("Comando vacío")

        base = os.path.basename(parts[0]).lower()
        if base not in self.ALLOWED_COMMANDS:
            raise PermissionError(f"Comando no permitido: {base}")

        return parts

    def run(self, command: str, callback: Optional[Callable[[str], None]] = None) -> str:
        try:
            parts = self.validate(command)
        except (ValueError, PermissionError) as exc:
            return f"❌ {exc}"

        if callback:
            callback(f"$ {command}")

        try:
            result = subprocess.run(
                parts,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            output = result.stdout or ""
            if result.stderr:
                output = f"{output}\n[ERROR]\n{result.stderr}".strip()
            if not output:
                output = "Ejecución finalizada sin salida."
            if callback:
                callback(output)
            return output
        except subprocess.TimeoutExpired:
            message = "Error: La ejecución excedió el límite de 10 segundos y fue cancelada."
            if callback:
                callback(message)
            return message
        except FileNotFoundError:
            return "Ejecución finalizada sin salida."
