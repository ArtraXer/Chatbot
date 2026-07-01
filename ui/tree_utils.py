import os


def listar_nodos_arbol(base, filtro=None, max_items=None):
    """Devuelve nodos del árbol de archivos.

    Sin filtro, devuelve una estructura jerárquica de carpetas y archivos.
    Con filtro, devuelve una lista plana de coincidencias con un nivel de
    profundidad para que la UI pueda renderizarlas de forma estable.
    """
    if not base or not os.path.exists(base):
        return []

    term = (filtro or "").strip().lower()

    def _match(name, target):
        if not target:
            return True
        return target in name.lower()

    def _walk(current_path, depth=0):
        try:
            raw_entries = [name for name in os.listdir(current_path) if not name.startswith(".")]
        except OSError:
            return []

        # Separate dirs and files first
        dirs = [n for n in raw_entries if os.path.isdir(os.path.join(current_path, n))]
        files = [n for n in raw_entries if os.path.isfile(os.path.join(current_path, n))]

        # Directories shown alphabetically by default
        dirs_sorted = sorted(dirs, key=lambda n: n.lower())

        # File ordering: README and scripts first
        script_ext_priority = [".py", ".sh", ".js", ".ts"]

        def file_key(name):
            nl = name.lower()
            if nl.startswith("readme"):
                return (0, nl)
            for i, ext in enumerate(script_ext_priority, start=1):
                if nl.endswith(ext):
                    return (i, nl)
            return (99, nl)

        files_sorted = sorted(files, key=file_key)

        nodes = []

        # Process directories first (preserve hierarchy when no filter)
        for name in dirs_sorted:
            full_path = os.path.join(current_path, name)
            if not term:
                children = _walk(full_path, depth + 1)
                nodes.append({"type": "dir", "name": name, "path": full_path, "children": children, "depth": depth})
            else:
                child_nodes = _walk(full_path, depth + 1)
                # include folder if it matches or contains matches
                if _match(name, term) or any(_match(node["name"], term) for node in child_nodes):
                    nodes.append({"type": "dir", "name": name, "path": full_path, "children": [], "depth": depth})
                if child_nodes:
                    nodes.extend(child_nodes)
                if max_items is not None and len(nodes) >= max_items:
                    return nodes

        # Then files
        for name in files_sorted:
            full_path = os.path.join(current_path, name)
            if not term or _match(name, term):
                if max_items is None or len(nodes) < max_items:
                    nodes.append({"type": "file", "name": name, "path": full_path, "children": [], "depth": depth})

        return nodes

    return _walk(base)
