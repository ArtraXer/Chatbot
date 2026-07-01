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
            process = subprocess.Popen(
                parts,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            
            output_lines = []
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    if callback:
                        callback(line)
                    output_lines.append(line)
                    
            returncode = process.poll()
            output = "".join(output_lines)
            if not output:
                output = "Ejecución finalizada sin salida."
            return output
        except FileNotFoundError:
            return "Ejecución finalizada sin salida. (Comando no encontrado)"
        except Exception as exc:
            return f"Error: {exc}"
