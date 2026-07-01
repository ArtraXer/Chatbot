import os
import fnmatch
import subprocess

_SKIP_DIRS = {"__pycache__", "venv", "env", "node_modules", ".git", ".mypy_cache", ".pytest_cache"}


def listar_nodos_arbol(base, filtro=None, max_items=None):
    """Devuelve nodos del árbol de archivos.

    Sin filtro, devuelve una estructura jerárquica de carpetas y archivos.
    Con filtro, devuelve resultados rankeados de búsqueda por nombre y contenido.
    """
    if not base or not os.path.exists(base):
        return []

    term = (filtro or "").strip().lower()

    if not term:
        return _walk_tree(base, max_items)

    return _search(base, term, max_items or 100)


def _walk_tree(base, max_items=None):
    """Construye el árbol jerárquico completo sin filtro."""
    def _walk(current_path, depth=0):
        try:
            raw_entries = [
                name for name in os.listdir(current_path)
                if not name.startswith(".") and name not in _SKIP_DIRS
            ]
        except OSError:
            return []

        dirs = sorted([n for n in raw_entries if os.path.isdir(os.path.join(current_path, n))], key=str.lower)
        files = sorted([n for n in raw_entries if os.path.isfile(os.path.join(current_path, n))], key=_file_key)

        nodes = []
        for name in dirs:
            full_path = os.path.join(current_path, name)
            children = _walk(full_path, depth + 1)
            nodes.append({"type": "dir", "name": name, "path": full_path, "children": children, "depth": depth})

        for name in files:
            full_path = os.path.join(current_path, name)
            if max_items is None or len(nodes) < max_items:
                nodes.append({"type": "file", "name": name, "path": full_path, "children": [], "depth": depth})

        return nodes

    return _walk(base)


def _search(base, term, max_items=100):
    """
    Búsqueda rápida combinada:
    1. Coincidencias exactas en nombre de archivo (instantáneo vía os.walk)
    2. Coincidencias de contenido con grep (para buscar dentro del código)
    Resultados rankeados: nombre > contenido.
    """
    results = []
    seen = set()
    term_lower = term.lower()

    # ── 1. Búsqueda por nombre de archivo (os.walk filtrado) ──────────────
    for dirpath, dirnames, filenames in os.walk(base):
        # Excluir carpetas pesadas in-place
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]

        for name in filenames:
            if name.startswith("."):
                continue
            if term_lower in name.lower():
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, base)
                if rel not in seen:
                    seen.add(rel)
                    results.append({
                        "type": "file",
                        "name": name,
                        "path": full,
                        "rel": rel,
                        "children": [],
                        "depth": 0,
                        "match_type": "name",
                        "snippet": "",
                    })
                if len(results) >= max_items:
                    return results

    # ── 2. Búsqueda de contenido con grep ─────────────────────────────────
    if len(results) < max_items:
        try:
            exclude_dirs = ",".join(_SKIP_DIRS)
            cmd = [
                "grep", "-rl",
                f"--exclude-dir={{{exclude_dirs}}}",
                "--include=*.py", "--include=*.js", "--include=*.ts",
                "--include=*.html", "--include=*.css", "--include=*.json",
                "--include=*.md", "--include=*.txt", "--include=*.yaml",
                "--include=*.sh", "--include=*.toml",
                "-i", term, "."
            ]
            proc = subprocess.run(cmd, cwd=base, capture_output=True, text=True, timeout=3)
            for line in proc.stdout.splitlines():
                full = os.path.normpath(os.path.join(base, line.lstrip("./")))
                rel = os.path.relpath(full, base)
                if rel in seen or not os.path.isfile(full):
                    continue
                seen.add(rel)
                # Get a snippet of the first matching line
                snippet = _get_snippet(full, term_lower)
                results.append({
                    "type": "file",
                    "name": os.path.basename(full),
                    "path": full,
                    "rel": rel,
                    "children": [],
                    "depth": 0,
                    "match_type": "content",
                    "snippet": snippet,
                })
                if len(results) >= max_items:
                    break
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    return results


def _get_snippet(filepath, term):
    """Devuelve la primera línea del archivo que contenga el término."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if term in line.lower():
                    return line.strip()[:80]
    except OSError:
        pass
    return ""


def _file_key(name):
    nl = name.lower()
    if nl.startswith("readme"):
        return (0, nl)
    for i, ext in enumerate([".py", ".sh", ".js", ".ts"], start=1):
        if nl.endswith(ext):
            return (i, nl)
    return (99, nl)
